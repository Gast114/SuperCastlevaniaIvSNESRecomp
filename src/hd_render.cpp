/* Optional tile detail and registered scene planes. Legacy tile packs retain
 * native visibility. Scene packs compose HD alpha before visibility using
 * read-only scanline snapshots, native priorities/windows and Mode 7 transforms.
 * Guest picture memory, collision and save states are never modified. */
#include "hd_render.h"
#include "character_json.h"
#include "render_workers.h"
extern "C" {
#include "snes/ppu.h"
#include "snes/mode7_hd.h"
}
#include "third_party/stb_image.h"
#include "third_party/stb_image_write.h"
#include <algorithm>
#include <array>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstddef>
#include <filesystem>
#include <fstream>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>
#include <chrono>

extern "C" Ppu *g_ppu;
extern "C" unsigned char g_ram[0x20000];
namespace fs = std::filesystem;
namespace {
struct Neighbor { int dx, dy, flip; uint64_t key; };
struct Context { uint64_t image; int flip; std::vector<Neighbor> neighbors; };
struct Region {
    int layer, x, y, w, h, stride, wrapX, wrapY;
    bool world;
    std::vector<uint32_t> rgba;
    std::vector<uint8_t> coverage;
    int sourcePalette = -1, selectAddress = 0;
    std::vector<uint64_t> selectKeys;
    unsigned modes=(1u<<1)|(1u<<7);
    bool stationary=false;
    bool screen=false;
    int priority=0xa300;
    std::vector<uint64_t> maskKeys;
    int framePeriod=0,frameCount=1,framePhase=0;
};
struct Pack {
    int scale = 0, size = 0;
    std::unordered_map<uint64_t, std::vector<uint32_t>> tiles;
    std::unordered_map<uint64_t, std::vector<Context>> contexts;
    std::vector<Region> regions;
    int block = -1;
    int objectMaskPalette = -1;
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
struct Cached { const std::vector<uint32_t> *tile; uint64_t key; };
thread_local std::unordered_map<uint32_t, Cached> cache;
struct ContextCell {
    int position;
    uint64_t key;
    bool operator==(const ContextCell &b) const { return position == b.position && key == b.key; }
};
struct ContextCellHash {
    size_t operator()(const ContextCell &c) const { return size_t(c.key ^ (uint64_t(c.position) * 0x9e3779b97f4a7c15ull)); }
};
std::unordered_map<ContextCell, const std::vector<uint32_t> *, ContextCellHash> contextCache;
constexpr size_t contextRegisterBytes = offsetof(Ppu, cgwsel) + sizeof(Ppu::cgwsel) - offsetof(Ppu, inidisp);
constexpr size_t contextPolicyBytes = offsetof(Ppu, wsViewportInsetL) - offsetof(Ppu, wsLayerClamp);
std::array<uint8_t, contextRegisterBytes> contextRegisters;
std::array<uint8_t, contextPolicyBytes> contextPolicies;
unsigned contextBoundaries = 255, contextHudSplit = 0;
bool HasArt() { return !pack.tiles.empty() || !pack.regions.empty(); }
bool SceneActive() { return pack.block < 0 || (g_ram[0x32] == 4 && g_ram[0x70] == 5 && g_ram[0x86] == pack.block); }

void ContextScanline(Ppu *p, int line) {
    if (pack.contexts.empty()) return;
    bool changed = std::memcmp(contextRegisters.data(), &p->inidisp, contextRegisterBytes) ||
                   std::memcmp(contextPolicies.data(), &p->wsLayerClamp, contextPolicyBytes) ||
                   contextHudSplit != p->wsHudSplitHeight;
    if (changed) {
        std::memcpy(contextRegisters.data(), &p->inidisp, contextRegisterBytes);
        std::memcpy(contextPolicies.data(), &p->wsLayerClamp, contextPolicyBytes);
        contextHudSplit = p->wsHudSplitHeight;
        // Neighbors are offset by whole tiles. A scanline band can change a
        // neighbor's interpretation only at its boundary modulo eight. Clear
        // there, even when that boundary is outside the visible current row.
        contextBoundaries = 1u | (1u << ((contextHudSplit & 127) & 7));
        auto bands = [](const auto &a, const auto &b) {
            const auto *first = reinterpret_cast<const uint8_t *>(&a);
            const auto *last = reinterpret_cast<const uint8_t *>(&b);
            for (size_t i = 0; i < sizeof(a); ++i)
                if (last[i] > first[i]) contextBoundaries |= (1u << (first[i] & 7)) | (1u << (last[i] & 7));
        };
        bands(p->wsRepeatY0, p->wsRepeatY1);
        bands(p->wsStretchY0, p->wsStretchY1);
        bands(p->wsAnchorY0, p->wsAnchorY1);
        bands(p->wsWorldY0, p->wsWorldY1);
        bands(p->wsElasticY0, p->wsElasticY1);
    }
    if (changed || (contextBoundaries & (1u << (line & 7)))) contextCache.clear();
}

uint64_t ParseKey(const std::string &key) {
    if (key.size() != 16 || key.find_first_not_of("0123456789abcdef") != std::string::npos)
        throw std::runtime_error("Invalid tile key");
    return std::stoull(key, nullptr, 16);
}

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
        if (auto required = j.object.find("requires"); required != j.object.end())
            for (const auto &feature : required->second.items())
                if (feature.string() != "tile-context-v1" && feature.string() != "scene-regions-v1")
                    throw std::runtime_error("Unsupported pack feature");
        Pack next;
        next.scale = j.at("scale").number(); next.size = j.at("tile_size").number();
        int atlasSize = j.at("atlas_size").number();
        if (j.at("version").number() != 1 || next.scale < 1 || next.scale > 10 ||
            next.size != next.scale * 8 || atlasSize < next.size || atlasSize > 4096)
            throw std::runtime_error("Unsupported pack version, scale or atlas dimensions");
        const auto &entries = j.at("tiles");
        if (entries.kind != '{') throw std::runtime_error("Expected tile object");
        if (entries.object.size() * (size_t)next.size * next.size * 4 > 256u * 1024 * 1024)
            throw std::runtime_error("Pack exceeds 256 MiB tile budget");
        int perRow = atlasSize / next.size;
        /* Load one atlas at a time, bounding decoded memory independently of
         * manifest ordering. Publish only after every entry has validated. */
        std::map<int, std::vector<std::pair<uint64_t, int>>> groups;
        for (const auto &[key, value] : entries.object) {
            uint64_t parsedKey = ParseKey(key);
            const auto &position = value.items();
            if (position.size() != 2) throw std::runtime_error("Invalid atlas position");
            int a = position[0].number(), slot = position[1].number();
            if (a < 0 || a > 4095 || slot < 0 || slot >= perRow * perRow)
                throw std::runtime_error("Atlas position out of bounds");
            groups[a].push_back({parsedKey, slot});
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
        if (auto contexts = j.object.find("contexts"); contexts != j.object.end()) {
            if (contexts->second.kind != '{') throw std::runtime_error("Expected contexts object");
            size_t count = 0;
            for (const auto &[key, choices] : contexts->second.object) {
                auto &dest = next.contexts[ParseKey(key)];
                for (const auto &choice : choices.items()) {
                    Context c{ParseKey(choice.at("image").string()), choice.at("flip").number(), {}};
                    if (++count > 16384 || !next.tiles.count(c.image) || c.flip < 0 || c.flip > 3)
                        throw std::runtime_error("Invalid context image, flip or count");
                    for (const auto &item : choice.at("neighbors").items()) {
                        const auto &n = item.items();
                        if (n.size() != 4) throw std::runtime_error("Invalid context neighbor");
                        Neighbor v{n[0].number(), n[1].number(), n[3].number(), ParseKey(n[2].string())};
                        if (v.dx < -16 || v.dx > 16 || v.dy < -16 || v.dy > 16 || (!v.dx && !v.dy) ||
                            v.flip < 0 || v.flip > 3 || c.neighbors.size() >= 32)
                            throw std::runtime_error("Context neighbor out of bounds");
                        c.neighbors.push_back(v);
                    }
                    if (c.neighbors.empty()) throw std::runtime_error("Context needs neighbors");
                    dest.push_back(std::move(c));
                }
                if (dest.empty()) throw std::runtime_error("Context needs images");
            }
        }
        if (auto scene = j.object.find("scene_block"); scene != j.object.end()) {
            next.block = scene->second.number();
            if (next.block < 0 || next.block > 255) throw std::runtime_error("Invalid scene block");
        }
        if (auto mask = j.object.find("object_mask_palette"); mask != j.object.end()) {
            next.objectMaskPalette = mask->second.number();
            if (next.objectMaskPalette < 128 || next.objectMaskPalette > 240 || next.objectMaskPalette%16)
                throw std::runtime_error("Invalid object palette mask");
        }
        if (auto regions = j.object.find("regions"); regions != j.object.end()) {
            if (next.block < 0) throw std::runtime_error("Regions need an explicit scene block");
            size_t bytesTotal = entries.object.size() * size_t(next.size) * next.size * 4;
            for (const auto &item : regions->second.items()) {
                Region r{};
                r.layer = item.at("layer").number(); r.x = item.at("x").number(); r.y = item.at("y").number();
                r.wrapX = item.at("wrap_x").number(); r.wrapY = item.at("wrap_y").number();
                auto coordinates = item.at("coordinates").string();
                if (coordinates != "world" && coordinates != "map" && coordinates != "screen") throw std::runtime_error("Invalid region coordinates");
                r.world = coordinates == "world";
                r.screen = coordinates == "screen";
                if(auto v=item.object.find("priority");v!=item.object.end()) {
                    r.priority=v->second.number();if(r.priority<0x100||r.priority>0xe600)throw std::runtime_error("Invalid object priority");
                }
                if(auto v=item.object.find("mask_keys");v!=item.object.end()) {
                    for(const auto &key:v->second.items())r.maskKeys.push_back(ParseKey(key.string()));
                    if(r.maskKeys.size()>128)throw std::runtime_error("Too many object mask keys");
                }
                if(auto v=item.object.find("stationary");v!=item.object.end())r.stationary=v->second.number()!=0;
                if(auto value=item.object.find("modes");value!=item.object.end()) {
                    r.modes=0;for(const auto &v:value->second.items()) {
                        unsigned mode=v.number();if(mode!=1&&mode!=7)throw std::runtime_error("Invalid region mode");
                        r.modes|=1u<<mode;
                    }
                }
                if(auto value=item.object.find("source_palette");value!=item.object.end()) {
                    r.sourcePalette=value->second.number();r.selectAddress=item.at("select_address").number();
                    if(r.sourcePalette<0||r.sourcePalette>240||r.sourcePalette%16||r.selectAddress<0||r.selectAddress>32767)
                        throw std::runtime_error("Invalid animation selector");
                    for(const auto &key:item.at("select_keys").items())r.selectKeys.push_back(ParseKey(key.string()));
                    if(r.selectKeys.size()>128)throw std::runtime_error("Too many animation selector keys");
                }
                if(auto value=item.object.find("frame_period");value!=item.object.end()) {
                    r.framePeriod=value->second.number();r.frameCount=item.at("frame_count").number();r.framePhase=item.at("frame_phase").number();
                    if(r.framePeriod<1||r.framePeriod>256||r.frameCount<1||r.frameCount>64||r.framePhase<0||r.framePhase>=r.frameCount)
                        throw std::runtime_error("Invalid animation clock");
                }
                fs::path relative(item.at("image").string());
                if (next.regions.size() >= 16 || (r.layer != 0 && r.layer != 1 && r.layer != 4) ||
                    std::abs(r.x) > 65536 || std::abs(r.y) > 65536 ||
                    r.wrapX < 0 || r.wrapX > 2048 || r.wrapY < 0 || r.wrapY > 2048 ||
                    relative.is_absolute() || relative.has_parent_path()) throw std::runtime_error("Invalid region bounds or filename");
                auto file = (root / relative).string();
                int w, h, channels;
                if (!stbi_info(file.c_str(), &w, &h, &channels) || w < 1 || h < 1 || w > 4096 || h > 4096 ||
                    w % next.scale || h % next.scale) throw std::runtime_error("Invalid scene image dimensions");
                bytesTotal += size_t(w) * h * 4;
                if (bytesTotal > 256u * 1024 * 1024) throw std::runtime_error("Scene pack exceeds 256 MiB budget");
                std::unique_ptr<uint8_t, decltype(&stbi_image_free)> pixels(stbi_load(file.c_str(), &w, &h, &channels, 4), &stbi_image_free);
                if (!pixels) throw std::runtime_error("Cannot decode scene image");
                r.w = w / next.scale; r.h = h / next.scale; r.stride = w;
                r.rgba.resize(size_t(w) * h);
                for (size_t i = 0; i < r.rgba.size(); ++i) {
                    const auto *p = pixels.get() + i * 4;
                    r.rgba[i] = uint32_t(p[3]) << 24 | p[0] << 16 | p[1] << 8 | p[2];
                }
                next.regions.push_back(std::move(r));
            }
        }
        // Reassemble decoder-sized pieces into their original continuous CPU
        // plane. Affine samples can then cross a file boundary without seams.
        for (size_t i = 0; i+1 < next.regions.size();) {
            auto &a = next.regions[i]; const auto &b = next.regions[i+1];
            if (a.screen==b.screen && a.maskKeys==b.maskKeys && a.priority==b.priority && a.stationary==b.stationary && a.modes==b.modes && a.sourcePalette<0 && b.sourcePalette<0 && a.layer == b.layer && a.world == b.world && a.wrapX == b.wrapX && a.wrapY == b.wrapY &&
                a.y == b.y && a.h == b.h && a.x+a.w == b.x && (a.w+b.w)*next.scale <= 8192) {
                int stride = a.stride+b.stride;
                std::vector<uint32_t> joined(size_t(stride)*a.h*next.scale);
                for (int y=0; y<a.h*next.scale; ++y) {
                    std::copy_n(a.rgba.data()+size_t(y)*a.stride,a.stride,joined.data()+size_t(y)*stride);
                    std::copy_n(b.rgba.data()+size_t(y)*b.stride,b.stride,joined.data()+size_t(y)*stride+a.stride);
                }
                a.w += b.w; a.stride = stride; a.rgba=std::move(joined);
                next.regions.erase(next.regions.begin()+i+1);
            } else ++i;
        }
        for (auto &r : next.regions) {
            r.coverage.resize(size_t(r.w)*r.h);
            for (int y=0;y<r.h;++y) for (int x=0;x<r.w;++x) {
                unsigned lo=255,hi=0;
                for(int dy=0;dy<next.scale;++dy) for(int dx=0;dx<next.scale;++dx) {
                    unsigned a=r.rgba[size_t(y*next.scale+dy)*r.stride+x*next.scale+dx]>>24;
                    lo=std::min(lo,a);hi=std::max(hi,a);
                }
                r.coverage[size_t(y)*r.w+x]=hi==0?0:lo==255?1:2;
            }
        }
        if(!next.regions.empty()&&!next.contexts.empty())throw std::runtime_error("Scene regions cannot contain context tiles");
        if (next.tiles.empty() && next.regions.empty()) throw std::runtime_error("Pack has no artwork");
        pack = std::move(next); cache.clear(); contextCache.clear(); surface.clear(); frameScale = 0; replaced = 0;
        directory = path;
        status = "Loaded " + std::to_string(pack.tiles.size()) + " tiles, " + std::to_string(pack.regions.size()) + " regions at " + std::to_string(pack.scale) + "x";
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
    const uint32_t *region = nullptr;
    int stride = 0;
    const Region *affine = nullptr;
    int ax = 0, ay = 0, xx = 0, xy = 0, yx = 0, yy = 0;
    uint8_t coverage = 2;
    const Region *owner=nullptr;
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
Cached Lookup(Ppu *p, const PpuTileSource &r) {
    uint32_t ident = r.address | uint32_t(r.palette) << 15 | uint32_t(r.bpp) << 23;
    auto it = cache.find(ident);
    if (it == cache.end()) {
        auto key = Key(p, r);
        auto tile = pack.tiles.find(key);
        it = cache.emplace(ident, Cached{tile == pack.tiles.end() ? nullptr : &tile->second, key}).first;
    }
    return it->second;
}
Sample FindSource(Ppu *p, int x, int line, unsigned layer, const PpuTileSource &source) {
    Sample s; s.source = source;
    if (!(layers & (1u << layer)) || !source.valid) return s;
    auto lookup = Lookup(p, s.source);
    s.tile = lookup.tile;
    auto choices = pack.contexts.find(lookup.key);
    if (layer >= 3 || choices == pack.contexts.end()) return s;
    // Reuse across a tile's rows, but never across register/memory/band changes.
    int left = x - (s.source.flip & 1 ? 7 - s.source.px : s.source.px);
    int top = line - (s.source.flip & 2 ? 7 - s.source.py : s.source.py);
    ContextCell id{int(((top + 16) * 2048 + left + 1024) * 16 + layer * 4 + s.source.flip), lookup.key};
    auto cached = contextCache.find(id);
    if (cached != contextCache.end()) { s.tile = cached->second; return s; }
    // Context entries are opt-in: no match must not leak a fragment elsewhere.
    s.tile = nullptr;
    for (const auto &c : choices->second) {
        int reflect = c.flip ^ s.source.flip;
        bool match = true;
        for (const auto &n : c.neighbors) {
            PpuTileSource other = {};
            int dx = n.dx * 8 * (reflect & 1 ? -1 : 1);
            int dy = n.dy * 8 * (reflect & 2 ? -1 : 1);
            if (line + dy < 0 || !PpuGetBackgroundTileSource(p, x + dx, line + dy, layer, &other) ||
                other.flip != (n.flip ^ reflect) || Lookup(p, other).key != n.key) {
                match = false; break;
            }
        }
        if (match) { s.tile = &pack.tiles.at(c.image); break; }
    }
    contextCache.emplace(id, s.tile);
    return s;
}
Sample Find(Ppu *p, int x, int line, uint16_t pixel) {
    unsigned layer = (pixel >> 8) & 15;
    if (layer == 6) layer = 4;
    PpuTileSource source{};
    if (!PpuGetTileSource(p, x, line, pixel, &source)) return {};
    return FindSource(p, x, line, layer, source);
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
struct Candidate {
    Sample art;
    uint32_t rgba = 0;
    uint16_t priority = 0;
    uint8_t screens = 0, layer = 0;
};
struct ScenePixel {
    std::array<Candidate, 6> candidates;
    std::array<uint8_t,6> order{};
    uint8_t count=0;
    Pixel colour;
    uint32_t backdrop = 0, fixed = 0;
    uint8_t mathMask = 0, mainLayer = 5;
    bool addSub = false, halfFlag = false;
    int8_t fast = -1;
};
std::vector<ScenePixel> scenePixels;
struct SceneLine { Ppu ppu; int cameraX=0,cameraY=0,clock=0; bool valid=false; };
std::vector<SceneLine> sceneLines;
std::array<const uint32_t *,224> sceneNativeRows{};
std::array<unsigned,224> sceneMatches{};
uint64_t sceneEpoch=0;
thread_local int sceneCameraX=0,sceneCameraY=0,sceneClock=0;
bool sceneFrame = false;
bool timing = std::getenv("SCIV_HD_TIMINGS") != nullptr;
double gatherSeconds=0, composeSeconds=0;
unsigned timingFrames=0;
using HdClock=std::chrono::steady_clock;
int Wrap(int n, int width) { return (n % width + width) % width; }
Sample RegionAt(Ppu *p, int x, int line, unsigned layer, const PpuTileSource *native=nullptr, bool stationary=false) {
    if (!(layers & (1u << layer))) return {};
    for (const auto &r : pack.regions) {
        if (r.layer != int(layer)) continue;
        if(r.stationary!=stationary)continue;
        if(!(r.modes&(1u<<PPU_mode(p))))continue;
        if(r.framePeriod && (sceneClock/r.framePeriod)%r.frameCount!=r.framePhase)continue;
        if(r.sourcePalette>=0) {
            if(!native||!native->valid||native->palette!=r.sourcePalette)continue;
            if(!r.framePeriod&&!r.selectKeys.empty()) {
                PpuTileSource watch{};watch.address=r.selectAddress;watch.palette=r.sourcePalette;watch.bpp=4;watch.valid=1;
                auto key=Lookup(p,watch).key;
                if(std::find(r.selectKeys.begin(),r.selectKeys.end(),key)==r.selectKeys.end())continue;
            }
        }
        if (PPU_mode(p) == 7 && layer < 2 && !stationary) {
            if (layer != 0 || !r.world) continue;
            auto t = SnesMode7HdMakeTransform(p->m7matrix, p->m7sel, line);
            double px = (t.origin_x+x*t.step_x-r.x)*pack.scale;
            double py = (t.origin_y+x*t.step_y-r.y)*pack.scale;
            // One native cell may cross an image edge during the rotation.
            if (px < -pack.scale*2 || py < -pack.scale*2 || px >= r.stride+pack.scale*2 ||
                py >= r.h*pack.scale+pack.scale*2) continue;
            Sample s; s.affine = &r;
            s.ax = int(px*65536); s.ay = int(py*65536);
            s.xx = int(t.step_x*65536); s.xy = int(t.step_y*65536);
            s.yx = int(t.row_x*65536); s.yy = int(t.row_y*65536);
            int minx=INT_MAX,miny=INT_MAX,maxx=INT_MIN,maxy=INT_MIN;
            for (int dx : {0,pack.scale-1}) for (int dy : {0,pack.scale-1}) {
                int qx=(s.ax+dx*s.xx+dy*s.yx)>>16,qy=(s.ay+dx*s.xy+dy*s.yy)>>16;
                minx=std::min(minx,qx);maxx=std::max(maxx,qx);miny=std::min(miny,qy);maxy=std::max(maxy,qy);
            }
            if (minx>=0 && miny>=0 && maxx<r.stride && maxy<r.h*pack.scale &&
                maxx/pack.scale-minx/pack.scale<=3 && maxy/pack.scale-miny/pack.scale<=3) {
                int kind=r.coverage[size_t(miny/pack.scale)*r.w+minx/pack.scale];
                for (int yy=miny/pack.scale;yy<=maxy/pack.scale;++yy)
                    for (int xx=minx/pack.scale;xx<=maxx/pack.scale;++xx)
                        if (r.coverage[size_t(yy)*r.w+xx]!=kind) kind=2;
                s.coverage=kind;
            }
            return s;
        }
        int wx, wy, flip = 0;
        if(r.screen) { wx=x;wy=line-1; }
        else if (layer == 4 || stationary) {
            wx = x + sceneCameraX;
            wy = line-1 + sceneCameraY;
        } else if (r.world) {
            int cx = sceneCameraX, cy = sceneCameraY;
            wx = x + cx + Wrap(int(p->hScroll[layer]) - cx + 512, 1024) - 512;
            wy = line + cy + Wrap(int(p->vScroll[layer]) - cy + 512, 1024) - 512;
        } else {
            wx = x + p->hScroll[layer]; wy = line + p->vScroll[layer];
            int band = PpuWidescreenLayerWorldBandAt(p, layer, line);
            if (band >= 0 && wx < p->wsWorldLeft[band][layer]) {
                wx = 2 * p->wsWorldLeft[band][layer] - 1 - wx; flip = 1;
            }
            if (r.wrapX) wx = Wrap(wx, r.wrapX);
            if (r.wrapY) wy = Wrap(wy, r.wrapY);
        }
        int px = wx - r.x, py = wy - r.y;
        if (px < 0 || py < 0 || px >= r.w || py >= r.h) continue;
        Sample sample; sample.region = r.rgba.data() + size_t(py * pack.scale) * r.stride + px * pack.scale;
        sample.stride = r.stride; sample.source.flip = flip;
        sample.coverage = r.coverage[size_t(py)*r.w+px];
        sample.owner=&r;
        return sample;
    }
    return {};
}
uint32_t ArtRgba(const Candidate &c, int dx, int dy) {
    const auto &s = c.art;
    if (s.affine) {
        int x = (s.ax+dx*s.xx+dy*s.yx)>>16, y = (s.ay+dx*s.xy+dy*s.yy)>>16;
        const auto &r = *s.affine;
        if (x<0 || y<0 || x>=r.stride || y>=r.h*pack.scale) return 0;
        return r.rgba[size_t(y)*r.stride+x];
    }
    if (!s.tile && !s.region) return c.rgba;
    if (s.source.flip & 1) dx = pack.scale - 1 - dx;
    if (s.source.flip & 2) dy = pack.scale - 1 - dy;
    if (s.region) return s.region[size_t(dy) * s.stride + dx];
    return (*s.tile)[(s.source.py * pack.scale + dy) * pack.size + s.source.px * pack.scale + dx];
}
uint32_t Over(uint32_t foreground, uint32_t background) {
    unsigned a = foreground >> 24;
    if (a == 255) return foreground & 0xffffff;
    if (!a) return background;
    uint32_t out = 0;
    for (unsigned shift : {0u, 8u, 16u})
        out |= ((((foreground >> shift & 255) * a + (background >> shift & 255) * (255-a) + 127) / 255) << shift);
    return out;
}
struct ScreenColour { uint32_t rgb; unsigned layer; bool opaque; };
ScreenColour SceneScreen(const ScenePixel &p, unsigned screen, int dx, int dy) {
    uint32_t translucent[6]; unsigned count = 0;
    ScreenColour result{p.backdrop, 5, false};
    // Front to back: an opaque sample avoids fetching all hidden images.
    for (int n = p.count-1; n >= 0; --n) {
        const auto &c = p.candidates[p.order[n]];
        if (!(c.screens & screen)) continue;
        uint32_t rgba = ArtRgba(c, dx, dy);
        if (!(rgba >> 24)) continue;
        if (!result.opaque) { result.layer = c.layer; result.opaque = true; }
        if ((rgba >> 24) == 255) { result.rgb = rgba & 0xffffff; break; }
        translucent[count++] = rgba;
    }
    while (count) result.rgb = Over(translucent[--count], result.rgb);
    return result;
}
uint32_t SceneColour(const ScenePixel &p, int dx, int dy) {
    auto main = SceneScreen(p, 1, dx, dy);
    Pixel colour = p.colour;
    colour.math = (colour.flags & 2) && (p.mathMask & (1u << main.layer));
    if (!colour.math && (colour.flags & 1) && colour.brightness == 15) return main.rgb;
    auto sub = colour.math && p.addSub ? SceneScreen(p, 2, dx, dy) : ScreenColour{p.backdrop,5,false};
    bool useSub = colour.math && p.addSub && sub.opaque;
    colour.half = colour.math && p.halfFlag && (!p.addSub || useSub);
    uint32_t other = useSub ? sub.rgb : p.fixed;
    if (main.rgb == colour.original && main.layer == p.mainLayer &&
        (!colour.math || other == colour.other)) return colour.native;
    return Compose(colour, main.rgb, other);
}
bool GatherSceneLine(Ppu *p, int line) {
    if ((PPU_mode(p) != 1 && PPU_mode(p) != 7) || PPU_forcedBlank(p) || line <= std::max(32, int(p->wsHudSplitHeight & 127))) return false;
    // Unsupported host transforms/mosaic keep the ordinary picture.
    for (const auto &r : pack.regions) {
        if (r.layer == 4) continue;
        if(!(r.modes&(1u<<PPU_mode(p))))continue;
        if (PPU_mode(p) == 7) break;
        PpuTileSource probe{};
        if (!PpuGetBackgroundTileSource(p, 0, line, r.layer, &probe)) return false;
    }
    PpuLayerSample samples[4][kPpuBufWidth];
    for (unsigned layer = 0; layer < 4; ++layer)
        if (!PpuGetLayerScanline(p, line, layer == 3 ? 4 : layer, samples[layer], kPpuBufWidth)) return false;
    const auto *native = reinterpret_cast<const uint32_t *>(p->renderBuffer + (line-1)*p->renderPitch);
    for (int nx = 0; nx < frameWidth; ++nx) {
        int x = nx - p->extraLeftRight, i = x + kPpuExtraLeftRight;
        auto &out = scenePixels[size_t(line-1)*frameWidth+nx];
        out = {}; out.colour.native = native[nx];
        if (x < -(int)p->extraLeftCur || x >= 256+p->extraRightCur) continue;
        uint16_t main = p->bgBuffers[0].data[i], sub = p->bgBuffers[1].data[i];
        out.mainLayer = main >> 8 & 15; out.backdrop = Rgb(p->cgram[0]);
        out.colour.original = Rgb(PpuPixelColor(p, main, i));
        out.fixed = Rgb(p->fixedColor);
        out.colour.flags = p->hdColorFlags[i]; out.colour.brightness = PPU_brightness(p);
        out.colour.subtract = PPU_subtractColor(p); out.mathMask = PPU_mathEnabled(p);
        out.addSub = PPU_addSubscreen(p); out.halfFlag = PPU_halfColor(p);
        bool nativeMath = (out.colour.flags & 2) && (out.mathMask & (1u << out.mainLayer));
        out.colour.other = nativeMath && out.addSub && (sub & 255) ? Rgb(PpuPixelColor(p,sub,i)) : out.fixed;
        auto tower = RegionAt(p,x,line,4);
        for (unsigned n = 0; n < 4; ++n) {
            const auto &s = samples[n][i]; auto &c = out.candidates[n];
            unsigned layer = n == 3 ? 4 : n;
            c.screens = s.screens; c.layer = s.pixel >> 8 & 15; c.priority = s.pixel & 0xff00;
            bool opaque = layer == 4 || PPU_mode(p) == 7 ? (s.pixel & 255) != 0 : s.source.valid && ((s.pixel & ((1u<<s.source.bpp)-1)) != 0);
            c.rgba = opaque ? 0xff000000u | Rgb(PpuPixelColor(p, s.pixel, i)) : 0;
            if (layer == 4 && p->hostObjPixels && s.pixel == (p->hostObjPriority|0x80) && (p->hostObjColors[i]>>24))
                c.rgba = p->hostObjColors[i];
            if (layer == 4 && tower.region && s.source.valid) {
                const auto &masks=tower.owner->maskKeys;
                bool hide=masks.empty()?s.source.palette==pack.objectMaskPalette:
                    std::find(masks.begin(),masks.end(),Lookup(p,s.source).key)!=masks.end();
                if(hide) { c.rgba=0;c.screens=0;continue; }
            }
            c.art = layer < 2 ? RegionAt(p, x, line, layer, &s.source) : Sample{};
            if (!c.art.region && !c.art.affine && s.source.valid) {
                // OBJ provenance must still identify the real winning object.
                if (layer < 3 || PpuGetTileSource(p,x,line,s.pixel,&c.art.source))
                    c.art = FindSource(p,x,line,layer,s.source);
            }
            if (c.art.tile || c.art.region || c.art.affine) ++sceneMatches[line-1];
            else if (!(c.rgba >> 24)) c.screens = 0;
            if ((c.art.region || c.art.affine) && c.art.coverage==0) {
                c.art={};c.rgba=0;c.screens=0;
            }
        }
        if (tower.region) {
            auto &c = out.candidates[4]; c.art=tower; c.layer=4;
            // The castle uses OBJ priority 2, behind earlier native OBJs at
            // the same priority (Simon). Its guest OBJ palette is masked only
            // within this authored replacement's bounds.
            c.priority=tower.owner->priority; c.screens=samples[3][i].screens;
            if(tower.coverage==0)c.screens=0;
            ++sceneMatches[line-1];
        }
        auto shoreline=RegionAt(p,x,line,0,nullptr,true);
        if(shoreline.region&&shoreline.coverage!=0) {
            auto &c=out.candidates[5];c.art=shoreline;c.layer=0;c.priority=0x4000;
            c.screens=samples[0][i].screens;++sceneMatches[line-1];
        }
        // Sort small indices, not the large immutable sampling descriptors.
        for(unsigned n=0;n<out.candidates.size();++n) if(out.candidates[n].screens) {
            unsigned j=out.count++;
            while(j && out.candidates[out.order[j-1]].priority>out.candidates[n].priority) {
                out.order[j]=out.order[j-1];--j;
            }
            out.order[j]=n;
        }
        bool varies=false, hasSub=false;
        for(const auto &c:out.candidates) {
            hasSub |= (c.screens&2)!=0;
            varies |= c.screens && (c.art.tile || c.art.region || c.art.affine);
        }
        if(!varies) out.fast=-2;
        else if((out.colour.flags&1) && out.colour.brightness==15) {
            for(int j=out.count-1;j>=0;--j) {
                int n=out.order[j];const auto &c=out.candidates[n];if(!(c.screens&1))continue;
                bool opaque = c.art.tile ? false : c.art.region||c.art.affine ? c.art.coverage==1 : (c.rgba>>24)==255;
                bool math=(out.colour.flags&2) && (out.mathMask&(1u<<c.layer));
                if(opaque && (!math || (out.addSub && !hasSub && !out.fixed))) out.fast=n;
                break;
            }
        }
    }
    return true;
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
        bool sceneValid=false;
        if(sceneFrame) {
            auto &line=sceneLines[y];
            if(line.valid) {
                thread_local uint64_t epoch=0;
                thread_local uint32_t revision=0;
                thread_local std::array<uint16_t,256> colours{};
                if(epoch!=sceneEpoch||revision!=line.ppu.vramWriteCount||std::memcmp(colours.data(),line.ppu.cgram,sizeof(line.ppu.cgram))) {
                    cache.clear();epoch=sceneEpoch;revision=line.ppu.vramWriteCount;
                    std::copy(std::begin(line.ppu.cgram),std::end(line.ppu.cgram),colours.begin());
                }
                sceneCameraX=line.cameraX;sceneCameraY=line.cameraY;sceneClock=line.clock;
                sceneValid=GatherSceneLine(&line.ppu,int(y)+1);
            }
        }
        for (int nx = 0; nx < frameWidth; ++nx) {
            if (sceneFrame) {
                if(!sceneValid) {
                    for(int dy=0;dy<scale;++dy)std::fill_n(first+size_t(dy)*frameWidth*scale+nx*scale,scale,sceneNativeRows[y][nx]);
                    continue;
                }
                const auto &p = scenePixels[y*frameWidth+nx];
                if (!p.colour.brightness || p.fast==-2) {
                    auto rgb=p.colour.brightness?SceneColour(p,0,0):p.colour.native;
                    for(int dy=0;dy<scale;++dy)std::fill_n(first+size_t(dy)*frameWidth*scale+nx*scale,scale,rgb);
                    continue;
                }
                if(p.fast>=0) {
                    const auto &c=p.candidates[p.fast];
                    for(int dy=0;dy<scale;++dy) {
                        auto row=first+size_t(dy)*frameWidth*scale+nx*scale;
                        if(!c.art.region&&!c.art.affine)std::fill_n(row,scale,c.rgba&0xffffff);
                        else if(c.art.region && !c.art.source.flip && pack.scale==scale) {
                            const auto *src=c.art.region+size_t(dy)*c.art.stride;
                            for(int dx=0;dx<scale;++dx)row[dx]=src[dx]&0xffffff;
                        } else for(int dx=0;dx<scale;++dx)row[dx]=ArtRgba(c,artOffset[cellOffset[dx]],artOffset[cellOffset[dy]])&0xffffff;
                    }
                    continue;
                }
                for (int dy = 0; dy < scale; ++dy) {
                    auto *row = first + size_t(dy)*frameWidth*scale + nx*scale;
                    for (int dx = 0; dx < scale; ++dx)
                        row[dx] = SceneColour(p,artOffset[cellOffset[dx]],artOffset[cellOffset[dy]]);
                }
                continue;
            }
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
extern "C" int Cv4HdPresentationScale(void) { Init(); return enabled && HasArt() ? scale : 1; }

extern "C" void Cv4HdRenderBegin(Ppu *p) {
    Init();
    p->hdTracking = enabled && HasArt();
    replaced = 0; frameScale = 0;
    if (!p->hdTracking) return;
    frameWidth = 256 + 2 * p->extraLeftRight;
    try {
        surface.resize(size_t(frameWidth) * 224 * scale * scale);
        pixels.resize(size_t(frameWidth) * 224);
        sceneFrame = !pack.regions.empty();
        if (sceneFrame) {
            scenePixels.resize(size_t(frameWidth)*224);sceneLines.resize(224);
            for(auto &line:sceneLines)line.valid=false;
            sceneMatches.fill(0);++sceneEpoch;
        }
    }
    catch (const std::bad_alloc &) { enabled = false; p->hdTracking = false; status = "Not enough memory for HD surface"; return; }
    frameScale = scale; cache.clear(); contextCache.clear(); vramRevision = p->vramWriteCount;
    std::copy(std::begin(p->cgram), std::end(p->cgram), palette.begin());
}
extern "C" void Cv4HdRenderLine(Ppu *p, int line) {
    if (!p->hdTracking || frameScale != scale || line < 1 || line > 224) return;
    ContextScanline(p, line);
    if (p->vramWriteCount != vramRevision || std::memcmp(palette.data(), p->cgram, sizeof(p->cgram))) {
        cache.clear(); contextCache.clear(); vramRevision = p->vramWriteCount;
        std::copy(std::begin(p->cgram), std::end(p->cgram), palette.begin());
    }
    auto native = reinterpret_cast<const uint32_t *>(p->renderBuffer + (line - 1) * p->renderPitch);
    if (sceneFrame) {
        auto t=timing?HdClock::now():HdClock::time_point{};
        sceneNativeRows[line-1]=native;
        auto &copy=sceneLines[line-1];copy.valid=false;
        if(SceneActive()&&!PPU_forcedBlank(p)&&(PPU_mode(p)==1||PPU_mode(p)==7)&&line>std::max(32,int(p->wsHudSplitHeight&127))) {
            copy.ppu=*p;
            if(p->renderVram)std::copy_n(p->renderVram,32768,copy.ppu.vram);
            copy.ppu.renderVram=nullptr;
            copy.cameraX=g_ram[0x1c]|g_ram[0x1d]<<8;copy.cameraY=g_ram[0x1e]|g_ram[0x1f]<<8;
            copy.clock=g_ram[0x3a];
            copy.valid=true;
        }
        if(timing)gatherSeconds+=std::chrono::duration<double>(HdClock::now()-t).count();
        return;
    }
    if (!SceneActive()) {
        for (int nx=0; nx<frameWidth; ++nx) { auto &out=pixels[size_t(line-1)*frameWidth+nx];out={};out.native=native[nx]; }
        return;
    }
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
    auto t=timing?HdClock::now():HdClock::time_point{};
    SnesRenderWorkersRun(workers, 224, 8, RenderRows, nullptr);
    if(sceneFrame) { replaced=0;for(auto n:sceneMatches)replaced+=n; }
    if(timing) {
        composeSeconds+=std::chrono::duration<double>(HdClock::now()-t).count();
        if(++timingFrames==120) {
            std::fprintf(stderr,"[HD timing] capture %.3f ms, workers %.3f ms/frame\n",gatherSeconds*1000/timingFrames,composeSeconds*1000/timingFrames);
            std::fflush(stderr);gatherSeconds=composeSeconds=0;timingFrames=0;
        }
    }
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
