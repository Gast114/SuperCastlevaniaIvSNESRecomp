/* Optional tile-detail replacement. The native raster owns visibility,
 * priority, silhouettes and windows; this surface adds RGB detail inside its
 * visible texels. Neither guest picture memory nor save states are modified. */
#include "hd_render.h"
#include "character_json.h"
#include "render_workers.h"
extern "C" {
#include "snes/ppu.h"
}
#include "third_party/stb_image.h"
#include "third_party/stb_image_write.h"
#include <algorithm>
#include <array>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

extern "C" Ppu *g_ppu;
namespace fs = std::filesystem;
namespace {
struct Pack {
    int scale = 0, size = 0;
    std::unordered_map<uint64_t, std::vector<uint32_t>> tiles;
};
Pack pack;
bool initialized = false, enabled = false;
int scale = 10;
unsigned layers = 31, replaced = 0;
std::string directory = "hd_pack", status = "No HD pack loaded";
std::vector<uint32_t> surface;
int frameWidth = 0, frameScale = 0;
uint32_t vramRevision = 0;
std::array<uint16_t, 256> palette;
struct Cached { const std::vector<uint32_t> *tile; };
std::unordered_map<uint32_t, Cached> cache;

uint32_t Rgb(uint16_t c) {
    auto expand = [](unsigned v) { return (v << 3) | (v >> 2); };
    return expand(c & 31) << 16 | expand(c >> 5 & 31) << 8 | expand(c >> 10 & 31);
}
void Persist() {
    std::ofstream f("hd_settings.json");
    f << "{\"enabled\":" << enabled << ",\"scale\":" << scale
      << ",\"layers\":" << layers << ",\"pack\":"
      << character_json::quote(directory) << "}\n";
    f.close();
    if (!f) status = "Could not save hd_settings.json";
}
uint64_t Key(const Ppu *p, const PpuTileSource &s) {
    uint64_t h = 1469598103934665603ull;
    auto mix = [&h](uint8_t b) { h = (h ^ b) * 1099511628211ull; };
    mix(s.bpp);
    const uint16_t *vram = PpuRenderVram(p);
    for (unsigned y = 0; y < 8; ++y) {
        uint16_t a = vram[(s.address + y) & 0x7fff];
        uint16_t b = s.bpp == 4 ? vram[(s.address + y + 8) & 0x7fff] : 0;
        for (int bit = 7; bit >= 0; --bit)
            mix((a >> bit & 1) | (a >> (bit + 8) & 1) << 1 |
                (b >> bit & 1) << 2 | (b >> (bit + 8) & 1) << 3);
    }
    for (unsigned i = 1; i < (1u << s.bpp); ++i) {
        uint16_t c = p->cgram[s.palette + i]; mix(c); mix(c >> 8);
    }
    return h;
}
int Load(const char *path) {
    try {
        fs::path root(path), manifest = root / "pack.json";
        if (fs::file_size(manifest) > 16 * 1024 * 1024) throw std::runtime_error("Manifest too large");
        std::ifstream f(manifest);
        std::string text((std::istreambuf_iterator<char>(f)), {});
        auto j = character_json::Reader(text).read();
        Pack next;
        next.scale = j.at("scale").number(); next.size = j.at("tile_size").number();
        int atlasSize = j.at("atlas_size").number();
        if (j.at("version").number() != 1 || next.scale < 1 || next.scale > 10 ||
            next.size != next.scale * 8 || atlasSize < next.size || atlasSize > 4096)
            throw std::runtime_error("Unsupported pack version, scale or atlas dimensions");
        const auto &entries = j.at("tiles");
        if (entries.kind != '{' || entries.object.empty()) throw std::runtime_error("Pack has no tiles");
        if (entries.object.size() * (size_t)next.size * next.size * 4 > 256u * 1024 * 1024)
            throw std::runtime_error("Pack exceeds 256 MiB tile budget");
        int perRow = atlasSize / next.size;
        /* Load one atlas at a time, bounding decoded memory independently of
         * manifest ordering. Publish only after every entry has validated. */
        std::map<int, std::vector<std::pair<uint64_t, int>>> groups;
        for (const auto &[key, value] : entries.object) {
            if (key.size() != 16 || key.find_first_not_of("0123456789abcdef") != std::string::npos)
                throw std::runtime_error("Invalid tile key");
            const auto &position = value.items();
            if (position.size() != 2) throw std::runtime_error("Invalid atlas position");
            int a = position[0].number(), slot = position[1].number();
            if (a < 0 || a > 4095 || slot < 0 || slot >= perRow * perRow)
                throw std::runtime_error("Atlas position out of bounds");
            groups[a].push_back({std::stoull(key, nullptr, 16), slot});
        }
        for (const auto &[index, slots] : groups) {
            char name[40]; std::snprintf(name, sizeof(name), "atlas_%03d.png", index);
            auto file = (root / name).string();
            int w, h, n;
            if (!stbi_info(file.c_str(), &w, &h, &n) || w != atlasSize || h != atlasSize)
                throw std::runtime_error("Atlas dimensions do not match manifest");
            std::unique_ptr<uint8_t, decltype(&stbi_image_free)> bytes(
                stbi_load(file.c_str(), &w, &h, &n, 4), &stbi_image_free);
            if (!bytes) throw std::runtime_error("Cannot decode atlas");
            for (auto [key, slot] : slots) {
                auto &tile = next.tiles[key]; tile.resize(next.size * next.size);
                int x = slot % perRow * next.size, y = slot / perRow * next.size;
                for (int py = 0; py < next.size; ++py)
                    for (int px = 0; px < next.size; ++px) {
                        auto b = bytes.get() + ((y + py) * w + x + px) * 4;
                        tile[py * next.size + px] = uint32_t(b[3]) << 24 | b[0] << 16 | b[1] << 8 | b[2];
                    }
            }
        }
        pack = std::move(next); cache.clear(); surface.clear(); frameScale = 0; replaced = 0;
        directory = path;
        status = "Loaded " + std::to_string(pack.tiles.size()) + " tiles at " + std::to_string(pack.scale) + "x";
        std::fprintf(stderr, "[HD] %s: %s\n", directory.c_str(), status.c_str());
        return 1;
    } catch (const std::exception &e) {
        status = std::string("Pack not loaded: ") + e.what();
        std::fprintf(stderr, "[HD] %s\n", status.c_str());
        return 0; // A failed reload preserves the previous valid pack.
    }
}
void Init() {
    if (initialized) return;
    initialized = true;
    try {
        if (fs::exists("hd_settings.json")) {
            if (fs::file_size("hd_settings.json") > 16384) throw std::runtime_error("Settings too large");
            std::ifstream f("hd_settings.json");
            std::string text((std::istreambuf_iterator<char>(f)), {});
            auto j = character_json::Reader(text).read();
            int savedScale = j.at("scale").number();
            unsigned savedLayers = j.at("layers").number();
            std::string savedPath = j.at("pack").string();
            bool savedEnabled = j.at("enabled").number() != 0;
            if (savedScale < 1 || savedScale > 10 || savedLayers > 31) throw std::runtime_error("Invalid HD settings");
            scale = savedScale; layers = savedLayers; directory = savedPath; enabled = savedEnabled;
        }
    } catch (const std::exception &e) { status = e.what(); }
    if (auto v = std::getenv("SNESRECOMP_HD_PACK")) directory = v;
    if (auto v = std::getenv("SNESRECOMP_HD_ENABLED")) enabled = std::atoi(v) != 0;
    if (auto v = std::getenv("SNESRECOMP_HD_SCALE")) scale = std::clamp(std::atoi(v), 1, 10);
    if (auto v = std::getenv("SNESRECOMP_HD_LAYERS")) layers = std::strtoul(v, nullptr, 0) & 31;
    std::error_code error;
    if (fs::exists(fs::path(directory) / "pack.json", error)) Load(directory.c_str());
}
struct Sample {
    const std::vector<uint32_t> *tile = nullptr;
    PpuTileSource source = {};
};
struct Pixel {
    Sample main, sub;
    uint32_t native = 0, original = 0, other = 0;
    uint8_t flags = 0, brightness = 0;
    bool math = false, half = false, subtract = false;
};
std::vector<Pixel> pixels;
SnesRenderWorkers *workers = nullptr;
bool workersInitialized = false;
Sample Find(Ppu *p, int x, int line, uint16_t pixel) {
    Sample s;
    unsigned layer = (pixel >> 8) & 15;
    if (layer == 6) layer = 4;
    if (!(layers & (1u << layer)) || !PpuGetTileSource(p, x, line, pixel, &s.source)) return s;
    const auto &r = s.source;
    uint32_t ident = r.address | uint32_t(r.palette) << 15 | uint32_t(r.bpp) << 23;
    auto it = cache.find(ident);
    if (it == cache.end()) {
        auto tile = pack.tiles.find(Key(p, r));
        it = cache.emplace(ident, Cached{tile == pack.tiles.end() ? nullptr : &tile->second}).first;
    }
    s.tile = it->second.tile;
    return s;
}
uint32_t SampleRgb(const Sample &s, int tx, int ty, uint32_t original) {
    if (!s.tile) return original;
    if (s.source.flip & 1) tx = pack.scale - 1 - tx;
    if (s.source.flip & 2) ty = pack.scale - 1 - ty;
    uint32_t c = (*s.tile)[(s.source.py * pack.scale + ty) * pack.size + s.source.px * pack.scale + tx];
    unsigned a = c >> 24;
    if (a == 255) return c & 0xffffff;
    if (!a) return original;
    uint32_t out = 0;
    for (unsigned shift : {0u, 8u, 16u})
        out |= (((c >> shift & 255) * a + (original >> shift & 255) * (255 - a) + 127) / 255) << shift;
    return out;
}
uint32_t Compose(const Pixel &p, uint32_t main, uint32_t other) {
    uint32_t out = 0;
    for (unsigned shift : {0u, 8u, 16u}) {
        int v = p.flags & 1 ? (main >> shift) & 255 : 0;
        if (p.math) {
            int second = (other >> shift) & 255;
            v = std::max(0, v + (p.subtract ? -second : second));
            if (p.half) v /= 2;
        }
        out |= (std::min(255, v) * p.brightness / 15) << shift;
    }
    return out;
}
void RenderRows(void *, size_t begin, size_t end, unsigned) {
    /* Inputs contain the exact scanline state and immutable pack pixels.
     * Workers never read or change a live PPU, palette, cache or CPU. */
    int detail = std::min(scale, pack.scale);
    int artOffset[10], cellOffset[10];
    for (int d = 0; d < detail; ++d) artOffset[d] = d * pack.scale / detail;
    for (int d = 0; d < scale; ++d) cellOffset[d] = d * detail / scale;
    for (size_t y = begin; y < end; ++y) {
        uint32_t *first = surface.data() + y * frameWidth * scale * scale;
        for (int nx = 0; nx < frameWidth; ++nx) {
            const Pixel &p = pixels[y * frameWidth + nx];
            if (!p.main.tile && !p.sub.tile) {
                for (int dy = 0; dy < scale; ++dy)
                    std::fill_n(first + size_t(dy) * frameWidth * scale + nx * scale, scale, p.native);
                continue;
            }
            uint32_t cell[10][10];
            for (int dy = 0; dy < detail; ++dy)
                for (int dx = 0; dx < detail; ++dx) {
                    auto c = SampleRgb(p.main, artOffset[dx], artOffset[dy], p.original);
                    auto b = SampleRgb(p.sub, artOffset[dx], artOffset[dy], p.other);
                    cell[dy][dx] = c == p.original && b == p.other ? p.native :
                        !p.math && (p.flags & 1) && p.brightness == 15 ? c : Compose(p, c, b);
                }
            for (int dy = 0; dy < scale; ++dy) {
                auto row = first + size_t(dy) * frameWidth * scale + nx * scale;
                for (int dx = 0; dx < scale; ++dx) row[dx] = cell[cellOffset[dy]][cellOffset[dx]];
            }
        }
    }
}
} // namespace

extern "C" int Cv4HdEnabled(void) { Init(); return enabled; }
extern "C" void Cv4HdEnable(int v) { Init(); enabled = v != 0; Persist(); }
extern "C" int Cv4HdScale(void) { Init(); return scale; }
extern "C" void Cv4HdSetScale(int v) { Init(); scale = std::clamp(v, 1, 10); Persist(); }
extern "C" unsigned Cv4HdLayerMask(void) { Init(); return layers; }
extern "C" void Cv4HdSetLayerMask(unsigned v) { Init(); layers = v & 31; Persist(); }
extern "C" int Cv4HdLoadPack(const char *p) { Init(); int ok = Load(p); if (ok) Persist(); return ok; }
extern "C" const char *Cv4HdPackPath(void) { Init(); return directory.c_str(); }
extern "C" const char *Cv4HdStatus(void) { Init(); return status.c_str(); }
extern "C" unsigned Cv4HdPackTiles(void) { Init(); return (unsigned)pack.tiles.size(); }
extern "C" int Cv4HdPackScale(void) { Init(); return pack.scale; }
extern "C" unsigned Cv4HdReplacedPixels(void) { return replaced; }
extern "C" int Cv4HdPresentationScale(void) { Init(); return enabled && !pack.tiles.empty() ? scale : 1; }

extern "C" void Cv4HdRenderBegin(Ppu *p) {
    Init();
    p->hdTracking = enabled && !pack.tiles.empty();
    replaced = 0; frameScale = 0;
    if (!p->hdTracking) return;
    frameWidth = 256 + 2 * p->extraLeftRight;
    try {
        surface.resize(size_t(frameWidth) * 224 * scale * scale);
        pixels.resize(size_t(frameWidth) * 224);
    }
    catch (const std::bad_alloc &) { enabled = false; p->hdTracking = false; status = "Not enough memory for HD surface"; return; }
    frameScale = scale; cache.clear(); vramRevision = p->vramWriteCount;
    std::copy(std::begin(p->cgram), std::end(p->cgram), palette.begin());
}
extern "C" void Cv4HdRenderLine(Ppu *p, int line) {
    if (!p->hdTracking || frameScale != scale || line < 1 || line > 224) return;
    if (p->vramWriteCount != vramRevision || std::memcmp(palette.data(), p->cgram, sizeof(p->cgram))) {
        cache.clear(); vramRevision = p->vramWriteCount;
        std::copy(std::begin(p->cgram), std::end(p->cgram), palette.begin());
    }
    auto native = reinterpret_cast<const uint32_t *>(p->renderBuffer + (line - 1) * p->renderPitch);
    for (int nx = 0; nx < frameWidth; ++nx) {
        Pixel &out = pixels[size_t(line - 1) * frameWidth + nx];
        out = Pixel{}; out.native = native[nx];
        int x = nx - p->extraLeftRight, i = x + kPpuExtraLeftRight;
        uint16_t m = p->bgBuffers[0].data[i], sub = p->bgBuffers[1].data[i];
        unsigned flags = p->hdColorFlags[i], layer = m >> 8 & 15;
        bool math = (flags & 2) && (PPU_mathEnabled(p) & (1u << layer));
        bool useSub = math && PPU_addSubscreen(p) && (sub & 255);
        bool half = math && PPU_halfColor(p) && (!PPU_addSubscreen(p) || useSub);
        Sample mainSample, subSample;
        if (!PPU_forcedBlank(p) && x >= -(int)p->extraLeftCur && x < 256 + p->extraRightCur) {
            if (flags & 1) mainSample = Find(p, x, line, m);
            if (useSub) subSample = Find(p, x, line, sub);
        }
        if (!mainSample.tile && !subSample.tile) {
            continue;
        }
        ++replaced;
        uint32_t original = Rgb(PpuPixelColor(p, m, i));
        uint32_t other = Rgb(useSub ? PpuPixelColor(p, sub, i) : p->fixedColor);
        /* Host character colours are RGB24; preserve them when a replaced
         * background participates in their colour math. */
        if (p->hostObjPixels && m == (p->hostObjPriority | 0x80) && (p->hostObjColors[i] >> 24))
            original = p->hostObjColors[i] & 0xffffff;
        out.main = mainSample; out.sub = subSample;
        out.original = original; out.other = other; out.flags = flags;
        out.math = math; out.half = half; out.subtract = PPU_subtractColor(p) != 0;
        out.brightness = PPU_brightness(p);
    }
}
extern "C" void Cv4HdRenderEnd(void) {
    if (!frameScale) return;
    if (!workersInitialized) {
        workers = SnesRenderWorkersCreate(std::getenv("SNESRECOMP_RENDER_WORKERS") ? 0 : 8);
        workersInitialized = true;
    }
    SnesRenderWorkersRun(workers, 224, 8, RenderRows, nullptr);
}
extern "C" void Cv4HdRenderShutdown(void) {
    SnesRenderWorkersDestroy(workers); workers = nullptr; workersInitialized = false;
}
extern "C" void Cv4HdPresent(uint8_t *dst, size_t pitch, int width, int height, int s) {
    if (frameScale == s && frameWidth == width && height == 224 && !surface.empty()) {
        for (int y = 0; y < height * s; ++y)
            std::memcpy(dst + size_t(y) * pitch, surface.data() + size_t(y) * width * s, size_t(width) * s * 4);
    } else if (g_ppu && g_ppu->renderBuffer) {
        for (int y = 0; y < height * s; ++y) {
            auto row = reinterpret_cast<uint32_t *>(dst + size_t(y) * pitch);
            auto src = reinterpret_cast<const uint32_t *>(g_ppu->renderBuffer + size_t(y / s) * g_ppu->renderPitch);
            for (int x = 0; x < width * s; ++x) row[x] = src[x / s];
        }
    }
}
extern "C" int Cv4HdScreenshot(const char *path) {
    if (!enabled || !frameScale || surface.empty()) return 0;
    std::vector<uint8_t> rgb(surface.size() * 3);
    for (size_t i = 0; i < surface.size(); ++i) {
        rgb[i * 3] = surface[i] >> 16; rgb[i * 3 + 1] = surface[i] >> 8; rgb[i * 3 + 2] = surface[i];
    }
    return stbi_write_png(path, frameWidth * frameScale, 224 * frameScale, 3,
                          rgb.data(), frameWidth * frameScale * 3);
}
