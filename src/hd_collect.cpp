/* HD graphics collector: the export half of the HD pipeline
 * (docs/HD_PIPELINE.md).
 *
 * While "collect" is on, every frame is taken apart into its layers -- BG1,
 * BG2, BG3 and the sprites -- rebuilt from VRAM with the registers each
 * scanline was drawn with. Every 8x8 tile on screen gets a key: its 64 pixel
 * indices (unflipped) plus the colours of its palette. A layer picture is
 * written whenever it shows a key that has fewer than kWanted clean
 * occurrences on record, together with the list of those occurrences:
 *
 *   hd_dump/tiles.tsv                       key, bpp, palette, pixels
 *   hd_dump/captures/<scene>/<layer>_<frame>.png   RGBA, colour 0 transparent
 *   hd_dump/captures/<scene>/<layer>_<frame>.tsv   x y key flip, one per tile
 *
 * The pictures are what an upscaler sees, so it works with the tiles'
 * surroundings; tools/hd/hd_build_pack.py cuts every occurrence back out of
 * the upscaled pictures and merges them per key. A clean occurrence lies
 * wholly inside the 256x224 field, on lines that share one scroll, and (for
 * sprites) is not overlapped by another sprite. Everything here reads host
 * copies of PPU state; nothing touches the guest. */
#include "hd_collect.h"

#include <condition_variable>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <filesystem>
#include <fstream>
#include <mutex>
#include <stdexcept>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

#include "snes/ppu.h"
#include "third_party/stb_image_write.h"

namespace fs = std::filesystem;
static_assert(sizeof(Cv4HdLine) == 32, "lines.bin record layout");

namespace {

constexpr int kW = 256, kH = 224;
constexpr unsigned kWanted = 3;          /* clean occurrences per key */
constexpr unsigned kMinFrameGap = 4;     /* per layer, between captures */
const fs::path kRoot = "hd_dump";

Cv4HdLine g_lines[kCv4HdLines];       /* the frame being drawn */
Cv4HdLine g_last_lines[kCv4HdLines];  /* the last complete frame */
bool g_collect = false, g_collect_loaded = false;
unsigned g_frame = 0, g_last_capture[4] = {0, 0, 0, 0};
/* The frame counter starts over after relaunch. Keep earlier captures intact. */
const std::string g_session = std::to_string(
    std::chrono::system_clock::now().time_since_epoch().count());

struct KeyInfo { unsigned clean = 0; };
std::unordered_map<uint64_t, KeyInfo> g_keys;

struct Job {
    fs::path png, tsv;
    std::vector<uint8_t> rgba;
    std::string occurrences, new_tiles;
};

/* One writer thread, so PNG encoding never stalls a frame. */
class Writer {
 public:
    ~Writer() { Stop(); }
    void Push(Job job) {
        Start();
        std::lock_guard<std::mutex> lock(mutex_);
        queue_.push_back(std::move(job));
        wake_.notify_one();
    }
    void Flush() {
        std::unique_lock<std::mutex> lock(mutex_);
        idle_.wait(lock, [this] { return queue_.empty() && !busy_; });
    }
    unsigned Pending() {
        std::lock_guard<std::mutex> lock(mutex_);
        return (unsigned)queue_.size() + (busy_ ? 1u : 0u);
    }
    std::atomic<unsigned> written{0}, failed{0};

 private:
    void Start() {
        if (!thread_.joinable())
            thread_ = std::thread([this] { Run(); });
    }
    void Stop() {
        {
            std::lock_guard<std::mutex> lock(mutex_);
            stopping_ = true;
            wake_.notify_one();
        }
        if (thread_.joinable())
            thread_.join();
    }
    void Run() {
        for (;;) {
            Job job;
            {
                std::unique_lock<std::mutex> lock(mutex_);
                wake_.wait(lock, [this] { return stopping_ || !queue_.empty(); });
                if (queue_.empty())
                    return;
                job = std::move(queue_.front());
                queue_.pop_front();
                busy_ = true;
            }
            try {
                Write(job);
                written++;
            } catch (const std::exception &e) {
                failed++;
                std::fprintf(stderr, "[hd collect] %s: %s\n", job.png.string().c_str(), e.what());
            }
            {
                std::lock_guard<std::mutex> lock(mutex_);
                busy_ = false;
                idle_.notify_all();
            }
        }
    }
    static void Write(const Job &job) {
        std::error_code error;
        fs::create_directories(job.png.parent_path(), error);
        if (error)
            throw std::runtime_error(error.message());
        if (!job.new_tiles.empty()) {
            std::ofstream tiles(kRoot / "tiles.tsv", std::ios::binary | std::ios::app);
            tiles << job.new_tiles;
            tiles.close();
            if (!tiles)
                throw std::runtime_error("cannot append tiles.tsv");
        }
        if (!stbi_write_png(job.png.string().c_str(), kW, kH, 4, job.rgba.data(), kW * 4))
            throw std::runtime_error("cannot write PNG");
        std::ofstream occurrences(job.tsv, std::ios::binary);
        occurrences << job.occurrences;
        occurrences.close();
        if (!occurrences)
            throw std::runtime_error("cannot write occurrences");
    }
    std::mutex mutex_;
    std::condition_variable wake_, idle_;
    std::deque<Job> queue_;
    std::thread thread_;
    bool busy_ = false, stopping_ = false;
};
Writer g_writer;

/* 5 to 8 bits exactly as the PPU expands them. */
uint32_t Rgba(uint16_t c) {
    auto x = [](uint32_t v) { return v << 3 | v >> 2; };
    uint32_t r = x(c & 31), g = x(c >> 5 & 31), b = x(c >> 10 & 31);
    return r | g << 8 | b << 16 | 0xff000000u;
}

/* An 8x8 tile decoded to colour indices, unflipped. */
struct Tile {
    uint8_t px[64];
    bool opaque;
};

void DecodeTile(const uint16_t *vram, unsigned addr, int bpp, Tile *t) {
    t->opaque = false;
    for (int y = 0; y < 8; y++) {
        uint16_t p01 = vram[(addr + y) & 0x7fff];
        uint16_t p23 = bpp == 4 ? vram[(addr + 8 + y) & 0x7fff] : 0;
        for (int x = 0; x < 8; x++) {
            int bit = 7 - x;
            uint8_t v = (p01 >> bit & 1) | (p01 >> (bit + 8) & 1) << 1;
            if (bpp == 4)
                v |= (p23 >> bit & 1) << 2 | (p23 >> (bit + 8) & 1) << 3;
            t->px[y * 8 + x] = v;
            t->opaque |= v != 0;
        }
    }
}

uint64_t KeyOf(const Tile &t, int bpp, const uint16_t *palette) {
    uint64_t h = 1469598103934665603ull;
    auto mix = [&h](uint8_t b) { h = (h ^ b) * 1099511628211ull; };
    mix((uint8_t)bpp);
    for (uint8_t v : t.px)
        mix(v);
    for (int i = 1; i < (1 << bpp); i++) {   /* colour 0 is transparent */
        mix((uint8_t)palette[i]);
        mix((uint8_t)(palette[i] >> 8));
    }
    return h;
}

std::string Hex16(uint64_t v) {
    char buf[20];
    std::snprintf(buf, sizeof(buf), "%016llx", (unsigned long long)v);
    return buf;
}

/* tiles.tsv line for a key seen for the first time. */
std::string TileLine(uint64_t key, const Tile &t, int bpp, const uint16_t *palette) {
    std::string line = Hex16(key) + "\t" + std::to_string(bpp) + "\t";
    char buf[8];
    for (int i = 0; i < (1 << bpp); i++) {
        std::snprintf(buf, sizeof(buf), "%04x", palette[i]);
        line += buf;
    }
    line += "\t";
    for (uint8_t v : t.px)
        line += "0123456789abcdef"[v];
    return line + "\n";
}

struct Capture {
    std::vector<uint32_t> rgba = std::vector<uint32_t>(kW * kH, 0);
    std::string occurrences, new_tiles;
    bool wants = false;
    unsigned count = 0;
};

void Note(Capture &cap, uint64_t key, const Tile &t, int bpp, const uint16_t *palette,
          int x, int y, int flip, std::vector<uint64_t> &seen) {
    auto [it, inserted] = g_keys.try_emplace(key);
    if (inserted)
        cap.new_tiles += TileLine(key, t, bpp, palette);
    if (it->second.clean < kWanted)
        cap.wants = true;
    char buf[64];
    std::snprintf(buf, sizeof(buf), "%d\t%d\t%s\t%d\n", x, y, Hex16(key).c_str(), flip);
    cap.occurrences += buf;
    cap.count++;
    seen.push_back(key);
}

int LayerBpp(int mode, int layer) {
    if (mode == 0) return 2;
    if (mode == 1) return layer < 2 ? 4 : 2;
    return 0;   /* modes 2-7 are not collected yet */
}

/* One BG layer of the field, rebuilt from the per-line registers. */
void CaptureBg(const Ppu *ppu, int layer, Capture &cap, std::vector<uint64_t> &seen) {
    const uint16_t *vram = ppu->vram;
    struct Run { int first = -1; uint32_t sig = 0; };
    Run run;
    /* Rows (screen y) start a tile row when (scanline + vScroll) % 8 == 0;
     * pending[x0] collects a tile until its 8th row is reached in the same
     * scroll run. */
    for (int y = 0; y < kH; y++) {
        const Cv4HdLine &l = g_lines[y + 1];
        int mode = l.bgmode & 7;
        int bpp = LayerBpp(mode, layer);
        bool on = l.valid && bpp && !(l.inidisp & 0x80) &&
                  ((l.main_screen | l.sub_screen) >> layer & 1);
        if (!on) {
            run.first = -1;
            continue;
        }
        bool big = l.bgmode >> (4 + layer) & 1;
        unsigned map_base = (l.bgXsc[layer] & 0xfc) << 8;
        bool wide = l.bgXsc[layer] & 1, tall = l.bgXsc[layer] & 2;
        unsigned tile_base = (l.bg_tile_adr >> (layer * 4) & 0xf) << 12;
        unsigned hs = l.h_scroll[layer] & 0x3ff, vs = l.v_scroll[layer] & 0x3ff;
        uint32_t sig = hs | vs << 10 | (uint32_t)l.bgXsc[layer] << 20 | (uint32_t)mode << 28 | (uint32_t)big << 31;
        sig ^= (uint32_t)l.bg_tile_adr * 2654435761u;
        if (run.first < 0 || sig != run.sig) {
            run.first = y;
            run.sig = sig;
        }
        int tsize = big ? 16 : 8;
        unsigned map_w = (wide ? 64 : 32) * tsize, map_h = (tall ? 64 : 32) * tsize;
        unsigned my = (y + 1 + vs) % map_h;
        const uint16_t *cg = ppu->cgram;
        int pal_size = 1 << bpp;
        unsigned pal_region = mode == 0 ? layer * 32 : 0;
        for (int x = 0; x < kW; x++) {
            unsigned mx = (x + hs) % map_w;
            unsigned col = mx / tsize, row = my / tsize;
            unsigned addr = map_base + ((col & 31) | (row & 31) << 5);
            if (col & 32) addr += 0x400;
            if (row & 32) addr += wide ? 0x800 : 0x400;
            uint16_t entry = vram[addr & 0x7fff];
            bool hf = entry & 0x4000, vf = entry & 0x8000;
            unsigned tx = mx % tsize, ty = my % tsize;
            if (hf) tx = tsize - 1 - tx;
            if (vf) ty = tsize - 1 - ty;
            unsigned tile = entry & 0x3ff;
            if (big)
                tile += (tx >> 3) + (ty >> 3) * 16;
            unsigned taddr = tile_base + (tile & 0x3ff) * (bpp == 4 ? 16 : 8);
            int bit = 7 - (int)(tx & 7);
            unsigned r = ty & 7;
            uint16_t p01 = vram[(taddr + r) & 0x7fff];
            uint16_t p23 = bpp == 4 ? vram[(taddr + 8 + r) & 0x7fff] : 0;
            int v = (p01 >> bit & 1) | (p01 >> (bit + 8) & 1) << 1;
            if (bpp == 4)
                v |= (p23 >> bit & 1) << 2 | (p23 >> (bit + 8) & 1) << 3;
            unsigned pal = entry >> 10 & 7;
            if (v)
                cap.rgba[y * kW + x] = Rgba(cg[(pal_region + pal * pal_size + v) & 255]);
        }
        /* The 8x8 cells whose last row this is: noted at their top-left pixel
         * when all eight rows were drawn in this scroll run. */
        if ((my & 7) != 7 || y - 7 < run.first)
            continue;
        for (int x0 = (int)((8 - (hs & 7)) & 7); x0 + 8 <= kW; x0 += 8) {
            unsigned mx = (x0 + hs) % map_w;
            unsigned top = (my + map_h - 7) % map_h;
            unsigned col = mx / tsize, row = top / tsize;
            unsigned addr = map_base + ((col & 31) | (row & 31) << 5);
            if (col & 32) addr += 0x400;
            if (row & 32) addr += wide ? 0x800 : 0x400;
            uint16_t entry = vram[addr & 0x7fff];
            bool hf = entry & 0x4000, vf = entry & 0x8000;
            unsigned qx = (mx % tsize) >> 3, qy = (top % tsize) >> 3;   /* big-tile quadrant */
            if (hf && big) qx ^= 1;
            if (vf && big) qy ^= 1;
            unsigned tile = ((entry & 0x3ff) + qx + qy * 16) & 0x3ff;
            unsigned taddr = tile_base + tile * (bpp == 4 ? 16 : 8);
            Tile t;
            DecodeTile(vram, taddr, bpp, &t);
            if (!t.opaque)
                continue;
            unsigned pal = entry >> 10 & 7;
            uint16_t palette[16];
            for (int i = 0; i < pal_size; i++)
                palette[i] = cg[(pal_region + pal * pal_size + i) & 255];
            Note(cap, KeyOf(t, bpp, palette), t, bpp, palette, x0, y - 7,
                 (hf ? 1 : 0) | (vf ? 2 : 0), seen);
        }
    }
}

const uint8_t kObjW[8][2] = {{8, 16}, {8, 32}, {8, 64}, {16, 32}, {16, 64}, {32, 64}, {16, 32}, {16, 32}};
const uint8_t kObjH[8][2] = {{8, 16}, {8, 32}, {8, 64}, {16, 32}, {16, 64}, {32, 64}, {32, 64}, {32, 32}};

/* The sprite layer at frame end (OAM is what the field was drawn from). */
void CaptureObj(const Ppu *ppu, Capture &cap, std::vector<uint64_t> &seen) {
    const Cv4HdLine &l = g_lines[112];
    if (!l.valid || (l.inidisp & 0x80) || !((l.main_screen | l.sub_screen) & 0x10))
        return;
    const uint16_t *vram = ppu->vram;
    unsigned size_sel = l.obsel >> 5;
    unsigned base1 = (l.obsel & 7) << 13;
    unsigned base2 = base1 + (((l.obsel & 0x18) + 8) << 9);
    std::vector<uint8_t> layers(kW * kH, 0);   /* sprites with an opaque pixel here */
    struct Sub { int x, y, flip, sprite; uint64_t key; Tile t; uint16_t pal[16]; };
    std::vector<Sub> subs;
    std::vector<int16_t> owner(kW * kH, -1);
    for (int i = 127; i >= 0; i--) {
        uint16_t w0 = ppu->oam[i * 2], w1 = ppu->oam[i * 2 + 1];
        uint8_t hi = ppu->highOam[i >> 2] >> ((i & 3) * 2) & 3;
        int x = (w0 & 0xff) | (hi & 1) << 8;
        if (x >= 256) x -= 512;
        int y = (w0 >> 8) + 1;
        int big = hi >> 1 & 1;
        int w = kObjW[size_sel][big], h = kObjH[size_sel][big];
        if (y >= kH + 1 || x + w <= 0 || x >= kW)
            continue;
        unsigned name = w1 & 0xff, table = w1 >> 8 & 1, pal = w1 >> 9 & 7;
        bool hf = w1 & 0x4000, vf = w1 & 0x8000;
        uint16_t palette[16];
        for (int c = 0; c < 16; c++)
            palette[c] = ppu->cgram[128 + pal * 16 + c];
        for (int cy = 0; cy < h / 8; cy++) {
            for (int cx = 0; cx < w / 8; cx++) {
                int sx = hf ? w / 8 - 1 - cx : cx, sy = vf ? h / 8 - 1 - cy : cy;
                unsigned ch = ((name & 0x0f) + sx & 0x0f) | (((name >> 4) + sy & 0x0f) << 4);
                unsigned taddr = (table ? base2 : base1) + ch * 16;
                Tile t;
                DecodeTile(vram, taddr, 4, &t);
                if (!t.opaque)
                    continue;
                int ox = x + cx * 8, oy = (y + cy * 8 - 1);
                for (int py = 0; py < 8; py++)
                    for (int px = 0; px < 8; px++) {
                        int X = ox + px, Y = oy + py;
                        if (X < 0 || X >= kW || Y < 0 || Y >= kH)
                            continue;
                        uint8_t v = t.px[(vf ? 7 - py : py) * 8 + (hf ? 7 - px : px)];
                        if (!v)
                            continue;
                        if (layers[Y * kW + X] < 255)
                            layers[Y * kW + X]++;
                        cap.rgba[Y * kW + X] = Rgba(palette[v]);   /* lower index drawn last */
                        owner[Y * kW + X] = (int16_t)i;
                    }
                Sub sub{ox, oy, (hf ? 1 : 0) | (vf ? 2 : 0), i, 0, t, {}};
                std::memcpy(sub.pal, palette, sizeof(palette));
                sub.key = KeyOf(t, 4, palette);
                subs.push_back(sub);
            }
        }
    }
    for (const Sub &s : subs) {
        if (s.x < 0 || s.y < 0 || s.x + 8 > kW || s.y + 8 > kH)
            continue;
        bool clean = true;
        for (int py = 0; py < 8 && clean; py++)
            for (int px = 0; px < 8 && clean; px++) {
                int idx = (s.y + py) * kW + s.x + px;
                clean = layers[idx] <= 1 && (layers[idx] == 0 || owner[idx] == s.sprite);
            }
        if (clean)
            Note(cap, s.key, s.t, 4, s.pal, s.x, s.y, s.flip, seen);
    }
}

void LoadSwitch() {
    if (g_collect_loaded)
        return;
    g_collect_loaded = true;
    const char *env = std::getenv("SNESRECOMP_HD_COLLECT");
    if (env && env[0])
        g_collect = env[0] != '0';
    else
        g_collect = fs::exists(kRoot / "collect.txt");
}

}  // namespace

extern "C" void Cv4HdRecordLine(const Ppu *ppu, int line) {
    if (line < 0 || line >= kCv4HdLines)
        return;
    Cv4HdLine &l = g_lines[line];
    l.valid = 1;
    l.inidisp = ppu->inidisp;
    l.obsel = ppu->obsel;
    l.bgmode = ppu->bgmode;
    std::memcpy(l.bgXsc, ppu->bgXsc, 4);
    l.main_screen = ppu->screenEnabled[0];
    l.sub_screen = ppu->screenEnabled[1];
    l.bg_tile_adr = ppu->bgTileAdr;
    std::memcpy(l.h_scroll, ppu->hScroll, sizeof(l.h_scroll));
    std::memcpy(l.v_scroll, ppu->vScroll, sizeof(l.v_scroll));
}

extern "C" const Cv4HdLine *Cv4HdLines(void) { return g_last_lines; }

extern "C" void Cv4HdFrame(const Ppu *ppu, const char *scene, unsigned block) {
    LoadSwitch();
    g_frame++;
    std::memcpy(g_last_lines, g_lines, sizeof(g_lines));
    /* Bound queued pictures if storage is slower than collection. Retry the
     * tiles next frame; never block simulation waiting for the writer. */
    if (!g_collect || !ppu || g_writer.Pending() >= 64 || g_writer.failed.load()) {
        std::memset(g_lines, 0, sizeof(g_lines));
        return;
    }
    /* Fades change the picture, not the art: collect at full brightness only. */
    if ((g_lines[112].inidisp & 0x8f) != 0x0f) {
        std::memset(g_lines, 0, sizeof(g_lines));
        return;
    }
    char folder[64];
    std::snprintf(folder, sizeof(folder), "%s_b%02x", scene ? scene : "other", block & 0xff);
    static const char *kNames[4] = {"bg1", "bg2", "bg3", "obj"};
    for (int layer = 0; layer < 4; layer++) {
        if (g_frame - g_last_capture[layer] < kMinFrameGap)
            continue;
        Capture cap;
        std::vector<uint64_t> seen;
        if (layer < 3)
            CaptureBg(ppu, layer, cap, seen);
        else
            CaptureObj(ppu, cap, seen);
        if (!cap.wants && cap.new_tiles.empty())
            continue;
        for (uint64_t key : seen)
            g_keys[key].clean++;
        g_last_capture[layer] = g_frame;
        char stem[64];
        std::snprintf(stem, sizeof(stem), "%s_%s_%06u", kNames[layer], g_session.c_str(), g_frame);
        Job job;
        job.png = kRoot / "captures" / folder / (std::string(stem) + ".png");
        job.tsv = kRoot / "captures" / folder / (std::string(stem) + ".tsv");
        job.rgba.resize(kW * kH * 4);
        std::memcpy(job.rgba.data(), cap.rgba.data(), job.rgba.size());
        job.occurrences = std::move(cap.occurrences);
        job.new_tiles = std::move(cap.new_tiles);
        g_writer.Push(std::move(job));
    }
    std::memset(g_lines, 0, sizeof(g_lines));
}

extern "C" int Cv4HdCollecting(void) {
    LoadSwitch();
    return g_collect;
}

extern "C" void Cv4HdSetCollecting(int enabled) {
    LoadSwitch();
    g_collect = enabled != 0;
    std::error_code error;
    if (g_collect) {
        fs::create_directories(kRoot, error);
        std::ofstream(kRoot / "collect.txt") << "Delete this file (or untick the box) to stop collecting.\n";
    } else {
        fs::remove(kRoot / "collect.txt", error);
    }
}

extern "C" void Cv4HdStats(unsigned *tiles, unsigned *captures, unsigned *pending, unsigned *errors) {
    if (tiles) *tiles = (unsigned)g_keys.size();
    if (captures) *captures = g_writer.written.load();
    if (pending) *pending = g_writer.Pending();
    if (errors) *errors = g_writer.failed.load();
}

extern "C" void Cv4HdFlush(void) { g_writer.Flush(); }
