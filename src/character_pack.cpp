#include "character_pack.h"
#include "character_json.h"
#include "character_tuning.h"
#include "hd_render.h"
#include "snes/ppu.h"
#include "snes/cart.h"
#include "third_party/stb_image.h"
#include "third_party/stb_image_write.h"
#include "imgui.h"
#include <algorithm>
#include <array>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <set>
#include <condition_variable>
#include <mutex>
#include <optional>
#include <thread>
#include <cstdio>
#include <cstdlib>
#include <cstring>
extern "C" { extern Snes *g_snes; }

namespace {
namespace fs = std::filesystem;
constexpr int Cell=96, Columns=8, Rows=32, Width=Cell*Columns, Height=Cell*Rows;
struct Frame {
  std::string id, label; int cell=0, ax=48, ay=48, hx=48, hy=48;
  std::string hdImage;int hdScale=10,hdX=0,hdY=0,hdW=0,hdH=0;
  int displayW=0,displayH=0;
  std::array<std::vector<uint32_t>,4> hdPixels;
  fs::file_time_type hdTime{};
};
struct Pack {
  cv4tuning::Values gameplay;
  std::string directory, name;
  std::vector<Frame> frames;
  std::vector<uint32_t> pixels;
  fs::file_time_type imageTime{}, manifestTime{};
};
struct Part { int slot,x,y,size; uint16_t attr; };
Pack reference, active;
const uint8_t* rom;
unsigned romSize;
const uint8_t *tuningRom=nullptr;
bool initialized=false, enabled=false, capture=true, overlay=false, previewFlip=false, playing=false;
int selected=0, currentIndex=-1, originX=0, originY=0;
std::string currentId, status="Native Simon", selectedDirectory;
std::vector<Part> parts;
std::array<uint32_t,Cell*Cell> body{}, rendered{};
std::array<uint8_t,Cell*Cell> indices{};
unsigned ticks=0;
unsigned matchedFlip=0;
bool edgeClipped=false;
std::array<uint8_t,0x13e0> previousPoseRam{};
bool havePreviousPose=false;
Cv4CharacterHdFrame hdFrame{};
uint64_t hdRevision=0;
uint16_t word(const uint8_t*r,unsigned a){return r[a]|uint16_t(r[a+1])<<8;}
int oamX(const Ppu*p,int s){int x=(p->oam[s*2]&255)|(((p->highOam[s>>2]>>((s&3)*2))&1)<<8);return x>=256+(int)p->extraRightCur?x-512:x;}
int oamSize(const Ppu*p,int s){static const int sizes[8][2]={{8,16},{8,32},{8,64},{16,32},{16,64},{32,64},{16,32},{16,32}};return sizes[PPU_objSize(p)][(p->highOam[s>>2]>>((s&3)*2+1))&1];}
uint32_t rgba(uint16_t c){auto expand=[](unsigned n){return (n<<3)|(n>>2);};return 0xff000000u|(expand(c&31)<<16)|(expand((c>>5)&31)<<8)|expand((c>>10)&31);}
unsigned pixel(const Ppu*p,const Part&part,int x,int y){
  if(part.attr&0x4000)x=part.size-1-x;if(part.attr&0x8000)y=part.size-1-y;
  unsigned tile=((((part.attr&255)>>4)+(y>>3))<<4)|(((part.attr&15)+(x>>3))&15);
  unsigned base=(part.attr&256)?PPU_objTileAdr2(p):PPU_objTileAdr1(p);
  unsigned a=(base+tile*16+(y&7))&0x7fff,b=7-(x&7);
  uint32_t planes=p->vram[a]|uint32_t(p->vram[(a+8)&0x7fff])<<16;
  return (planes>>b&1)|(planes>>(b+7)&2)|(planes>>(b+14)&4)|(planes>>(b+21)&8);
}
fs::path path(const Pack&p,const char*name){return fs::path("characters")/p.directory/name;}
int find(const Pack&p,const std::string&id){for(size_t i=0;i<p.frames.size();++i)if(p.frames[i].id==id)return (int)i;return -1;}
int findBodyFrame(const Pack&p,const std::string&id){
  int exact=find(p,id);if(exact>=0)return exact;
  // DMA and the metasprite pointer can change on different fields. Several
  // pointers describe the very same normalized body. Reuse its artwork only
  // for an unambiguous full-body hash, never a similar/previous pose.
  if(id.size()!=21||id[4]!='-')return -1;
  int match=-1;
  for(size_t i=0;i<p.frames.size();++i){const auto&key=p.frames[i].id;
    if(key.size()==id.size()&&key.compare(4,17,id,4,17)==0){
      if(match>=0)return -1;
      match=(int)i;
    }
  }
  return match;
}
void stamp(Pack&p){p.imageTime=fs::last_write_time(path(p,"body.png"));p.manifestTime=fs::last_write_time(path(p,"character.json"));}
void save(Pack&p,bool image){
  fs::create_directories(path(p,""));
  if(image){
    std::vector<uint8_t> bytes(p.pixels.size()*4);
    for(size_t i=0;i<p.pixels.size();++i){uint32_t c=p.pixels[i];bytes[i*4]=c>>16;bytes[i*4+1]=c>>8;bytes[i*4+2]=c;bytes[i*4+3]=c>>24;}
    auto temporary=path(p,"body.tmp.png");
    if(!stbi_write_png(temporary.string().c_str(),Width,Height,4,bytes.data(),Width*4))throw std::runtime_error("Cannot save body.png");
    fs::copy_file(temporary,path(p,"body.png"),fs::copy_options::overwrite_existing);fs::remove(temporary);
  }
  std::ofstream f(path(p,"character.json"));
  f<<"{\n  \"version\": 1,\n  \"name\": "<<character_json::quote(p.name)<<",\n  \"cell_size\": 96,\n  \"gameplay\": {\n";
  for(int i=0;i<cv4tuning::Count;i++)
    f<<"    "<<character_json::quote(cv4tuning::definitions[i].key)<<": "<<p.gameplay.value[i]<<(i+1==cv4tuning::Count?"\n":",\n");
  f<<"  },\n  \"frames\": [\n";
  for(size_t i=0;i<p.frames.size();++i){const auto&a=p.frames[i];f<<"    {\"id\": "<<character_json::quote(a.id)<<", \"label\": "<<character_json::quote(a.label)<<", \"cell\": "<<a.cell<<", \"anchor\": ["<<a.ax<<", "<<a.ay<<"], \"hand\": ["<<a.hx<<", "<<a.hy<<"]";
    if(!a.hdImage.empty()){f<<", \"hd\": {\"image\": "<<character_json::quote(a.hdImage)<<", \"scale\": "<<a.hdScale<<", \"offset\": ["<<a.hdX<<", "<<a.hdY<<"]";
      if(a.displayW)f<<", \"display_size\": ["<<a.displayW<<", "<<a.displayH<<"]";
      f<<"}";}
    f<<"}"<<(i+1==p.frames.size()?"\n":",\n");}
  f<<"  ]\n}\n";f.close();if(!f)throw std::runtime_error("Cannot save manifest");
  p.manifestTime=fs::last_write_time(path(p,"character.json"));
  if(image)p.imageTime=fs::last_write_time(path(p,"body.png"));
}
// Writing the 768x3072 template PNG takes hundreds of milliseconds; doing it
// on the game thread froze play on every newly collected pose. Captures mark
// the template dirty, at most one snapshot per second goes to this writer
// thread, and the newest snapshot replaces an unwritten older one.
class TemplateWriter {
  std::mutex mutex; std::condition_variable wake; std::optional<Pack> next; bool stopping=false;
  std::thread thread{[this]{run();}};
  void run(){
    for(;;){
      Pack p;
      {std::unique_lock<std::mutex> lock(mutex);wake.wait(lock,[&]{return next.has_value()||stopping;});
       if(!next)return;p=std::move(*next);next.reset();}
      try{save(p,true);}catch(const std::exception&e){fprintf(stderr,"[characters] template not saved: %s\n",e.what());}
    }
  }
public:
  void submit(const Pack&p){{std::lock_guard<std::mutex> lock(mutex);next=p;}wake.notify_one();}
  void finish(){{std::lock_guard<std::mutex> lock(mutex);stopping=true;}wake.notify_one();if(thread.joinable())thread.join();}
  ~TemplateWriter(){finish();}
};
TemplateWriter templateWriter;
bool templateDirty=false;
unsigned templateSubmitted=0;
void flushTemplate(bool force){
  if(!templateDirty||(!force&&ticks-templateSubmitted<60))return;
  templateWriter.submit(reference);templateDirty=false;templateSubmitted=ticks;
}
// Destroyed before `reference` and the writer's own state: queue the last
// unsaved poses and wait for them, so a session's captures survive exit.
struct TemplateFlushAtExit{~TemplateFlushAtExit(){flushTemplate(true);templateWriter.finish();}} templateFlushAtExit;
Pack load(const std::string&directory){
  Pack p;p.directory=directory;
  auto file=path(p,"character.json");if(fs::file_size(file)>1024*1024)throw std::runtime_error("Manifest too large");
  std::ifstream f(file);std::string text((std::istreambuf_iterator<char>(f)),{});auto j=character_json::Reader(text).read();
  if(j.at("version").number()!=1||j.at("cell_size").number()!=Cell)throw std::runtime_error("Unsupported character format");
  p.name=j.at("name").string();std::set<std::string> ids;std::set<int> cells;
  if(auto it=j.object.find("gameplay");it!=j.object.end()) {
    if(it->second.kind!='{')throw std::runtime_error("Gameplay must be an object");
    for(int i=0;i<cv4tuning::Count;i++) {
      const auto &d=cv4tuning::definitions[i];
      auto field=it->second.object.find(d.key);
      if(field==it->second.object.end())continue; // Older packs retain Simon defaults.
      int value=field->second.number();
      if(value<d.minimum||value>d.maximum)throw std::runtime_error(std::string("Gameplay value out of range: ")+d.key);
      p.gameplay.value[i]=value;
    }
  }
  for(const auto&v:j.at("frames").items()){Frame a;a.id=v.at("id").string();a.label=v.at("label").string();a.cell=v.at("cell").number();
    const auto&anchor=v.at("anchor").items();const auto&hand=v.at("hand").items();
    if(anchor.size()!=2||hand.size()!=2)throw std::runtime_error("Invalid anchor");
    a.ax=anchor[0].number();a.ay=anchor[1].number();a.hx=hand[0].number();a.hy=hand[1].number();
    if(a.id.empty()||a.cell<0||a.cell>=Columns*Rows||!ids.insert(a.id).second||!cells.insert(a.cell).second||
       a.ax<0||a.ax>=Cell||a.ay<0||a.ay>=Cell||a.hx<0||a.hx>=Cell||a.hy<0||a.hy>=Cell)throw std::runtime_error("Invalid/duplicate frame mapping");
    if(auto it=v.object.find("hd");it!=v.object.end()) {
      const auto &hd=it->second;a.hdImage=hd.at("image").string();a.hdScale=hd.at("scale").number();
      const auto &offset=hd.at("offset").items();
      if(offset.size()!=2||a.hdScale!=10||a.hdImage.empty()||fs::path(a.hdImage).filename()!=fs::path(a.hdImage))throw std::runtime_error("HD pose needs a local PNG, scale 10 and two offsets");
      a.hdX=offset[0].number();a.hdY=offset[1].number();
      int channels;
      auto image=path(p,a.hdImage.c_str());
      if(!stbi_info(image.string().c_str(),&a.hdW,&a.hdH,&channels)||a.hdW<=0||a.hdH<=0||a.hdW%10||a.hdH%10||a.hdX<0||a.hdY<0||a.hdX+a.hdW/10>Cell||a.hdY+a.hdH/10>Cell)throw std::runtime_error("HD pose exceeds its 96 x 96 native cell");
      uint8_t *bytes=stbi_load(image.string().c_str(),&a.hdW,&a.hdH,&channels,4);
      if(!bytes)throw std::runtime_error("Cannot load HD pose PNG");
      int sourceW=a.hdW,sourceH=a.hdH;
      if(auto display=hd.object.find("display_size");display!=hd.object.end()) {
        const auto &size=display->second.items();
        if(size.size()!=2){stbi_image_free(bytes);throw std::runtime_error("Invalid HD display size");}
        a.displayW=size[0].number();a.displayH=size[1].number();
        if(a.displayW<1||a.displayH<1||a.hdX+a.displayW>Cell||a.hdY+a.displayH>Cell){stbi_image_free(bytes);throw std::runtime_error("HD display size exceeds cell");}
        a.hdW=a.displayW*10;a.hdH=a.displayH*10;
      }
      for(unsigned flip=0;flip<4;++flip) {
        auto &dst=a.hdPixels[flip];dst.resize(size_t(a.hdW)*a.hdH);
        for(int y=0;y<a.hdH;++y)for(int x=0;x<a.hdW;++x) {
          int sx=(flip&1?a.hdW-1-x:x)*sourceW/a.hdW,sy=(flip&2?a.hdH-1-y:y)*sourceH/a.hdH;
          size_t q=(size_t(sy)*sourceW+sx)*4;
          dst[size_t(y)*a.hdW+x]=uint32_t(bytes[q+3])<<24|uint32_t(bytes[q])<<16|uint32_t(bytes[q+1])<<8|bytes[q+2];
        }
      }
      stbi_image_free(bytes);a.hdTime=fs::last_write_time(image);
    }
    p.frames.push_back(std::move(a));
  }
  int w,h,n;if(!stbi_info(path(p,"body.png").string().c_str(),&w,&h,&n)||w!=Width||h!=Height)throw std::runtime_error("body.png must be 768 x 3072");
  uint8_t*bytes=stbi_load(path(p,"body.png").string().c_str(),&w,&h,&n,4);if(!bytes)throw std::runtime_error("Cannot read body.png");
  p.pixels.resize(Width*Height);for(size_t i=0;i<p.pixels.size();++i)p.pixels[i]=uint32_t(bytes[i*4+3])<<24|uint32_t(bytes[i*4])<<16|uint32_t(bytes[i*4+1])<<8|bytes[i*4+2];stbi_image_free(bytes);stamp(p);return p;
}
void selectPack(const std::string&directory){active=load(directory);++hdRevision;selectedDirectory=directory;selected=0;std::ofstream("characters/selected.txt")<<directory;status="Loaded "+active.name;}
void initialize(){
  fs::create_directories("characters");
  reference.directory="simon-template";reference.name="Simon template";
  reference.pixels.resize(Width*Height);
  try{if(fs::exists(path(reference,"character.json")))reference=load(reference.directory);}
  catch(const std::exception&e){capture=false;status=std::string("Template not loaded; capture disabled: ")+e.what();}
  std::ifstream f("characters/selected.txt");std::string s;std::getline(f,s);
  initialized=true;
  if(!s.empty()&&s!="simon-template"&&s.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")==std::string::npos){selectPack(s);enabled=true;}
}

// Reproduce the ROM's $008E56/$008E8F OAM assembly for the player slot only.
// Every selected OAM entry must match all position, tile, size and attribute bits.
// Missing OAM pieces fall back to native rendering rather than guessing ownership.
// Offscreen portions remain part of a complete pose; the PPU clips their pixels.
bool readBody(Ppu*p,const uint8_t*r){
  parts.clear();unsigned id=word(r,0x540);if(!rom||id<0x8000)return false;
  unsigned a=0x20000+(id&0x7fff);if(a>=romSize)return false;
  unsigned count=rom[a];if(count==0||count>32||a+1+count*4>romSize)return false;
  int xbase=(int16_t)(word(r,0x54a)-word(r,0x1c));int ybase=(word(r,0x54e)-word(r,0x1e))&word(r,0x13de);
  unsigned flip=word(r,0x544),add=word(r,0x566),priority=word(r,0x542);
  std::set<int> used;
  for(unsigned i=0;i<count;++i){unsigned o=a+1+i*4;uint16_t tile=word(rom,o+2);int size=(tile&0x2000)?16:8;
    int x=(int8_t)rom[o],y=(int8_t)rom[o+1];x=xbase+((flip&0x4000)?-x-size:x);y=ybase+((flip&0x8000)?-y-size:y);
    tile=(tile|0x2000)^flip;if(priority&0x8000)tile=(tile&0xcfff)|((priority*2&255)<<8);tile+=add;
    int found=-1;for(int s=0;s<128;++s){if(used.count(s))continue;if(oamX(p,s)==x&&(p->oam[s*2]>>8)==(y&255)&&p->oam[s*2+1]==tile&&oamSize(p,s)==size){found=s;break;}}
    if(found<0||x<-64||x>320){
      static std::set<unsigned> reported;
      if(std::getenv("SNESRECOMP_CHARACTER_DIAG")&&reported.insert(id).second){
        fprintf(stderr,"[characters] unmatched id=%04x part=%u xy=%d,%d size=%d attr=%04x base=%d,%d flip=%04x\n",id,i,x,y,size,tile,xbase,ybase,flip);
        for(int s=0;s<24;++s)fprintf(stderr," slot=%d xy=%d,%u size=%d attr=%04x\n",s,oamX(p,s),p->oam[s*2]>>8,oamSize(p,s),p->oam[s*2+1]);
      }
      return false;
    }
    parts.push_back({found,x,y,size,tile});used.insert(found);
  }
  body.fill(0);indices.fill(0);
  edgeClipped=std::any_of(parts.begin(),parts.end(),[](const Part&a){return a.y<0||a.y+a.size>224;});
  // Lower OAM slots win. Normalize only the player's global mirroring.
  std::sort(parts.begin(),parts.end(),[](const Part&a,const Part&b){return a.slot>b.slot;});
  for(const auto&part:parts)for(int y=0;y<part.size;++y)for(int x=0;x<part.size;++x){
    int dx=part.x+x-xbase,dy=part.y+y-ybase;if(flip&0x4000)dx=-dx-1;if(flip&0x8000)dy=-dy-1;dx+=48;dy+=48;
    if(dx<0||dx>=Cell||dy<0||dy>=Cell)return false;
    unsigned c=pixel(p,part,x,y);if(c){indices[dy*Cell+dx]=(uint8_t)c;body[dy*Cell+dx]=rgba(p->cgram[128+((part.attr>>9)&7)*16+c]);}
  }
  // Exact fingerprint of the unmodified body pixels; independent of palette,
  // camera motion, OAM allocation, user artwork, and facing direction.
  uint64_t hash=14695981039346656037ull;for(auto c:indices){hash^=c;hash*=1099511628211ull;}
  std::ostringstream key;key<<std::hex<<std::setfill('0')<<std::setw(4)<<id<<'-'<<std::setw(16)<<hash;currentId=key.str();originX=xbase;originY=ybase;matchedFlip=flip;
  return true;
}
void captureFrame(const uint8_t*r){
  if(!capture||find(reference,currentId)>=0||reference.frames.size()>=Columns*Rows)return;
  Frame f;f.id=currentId;std::set<int> used;for(const auto&a:reference.frames)used.insert(a.cell);while(used.count(f.cell))++f.cell;
  f.label="Pose "+currentId.substr(0,4)+" state "+std::to_string(word(r,0x552));
  int bx=f.cell%Columns*Cell,by=f.cell/Columns*Cell;
  for(int y=0;y<Cell;++y)std::copy_n(body.data()+y*Cell,Cell,reference.pixels.data()+(by+y)*Width+bx);
  reference.frames.push_back(f);templateDirty=true;
  fprintf(stderr,"[characters] captured %s (%zu body frames)\n",f.id.c_str(),reference.frames.size());
}
void publish(Ppu*p,const uint8_t*r){
  currentIndex=findBodyFrame(active,currentId);if(!enabled||currentIndex<0||!(p->renderFlags&kPpuRenderFlags_NewRenderer))return;
  const Frame&f=active.frames[currentIndex];int bx=f.cell%Columns*Cell,by=f.cell/Columns*Cell;
  if(!f.hdImage.empty()&&(!Cv4HdEnabled()||!(Cv4HdLayerMask()&16)))return;
  unsigned flip=matchedFlip;bool fx=(flip&0x4000)!=0,fy=(flip&0x8000)!=0;
  for(int y=0;y<Cell;++y)for(int x=0;x<Cell;++x)rendered[y*Cell+x]=active.pixels[(by+(fy?Cell-1-y:y))*Width+bx+(fx?Cell-1-x:x)];
  p->hostObjX=originX-(fx?Cell-f.ax:f.ax);p->hostObjY=originY-(fy?Cell-f.ay:f.ay);
  p->hostObjWidth=p->hostObjHeight=p->hostObjStride=Cell;
  if(!f.hdImage.empty()) {
    // The PPU uses a small coverage proxy for native OBJ priority/windows.
    // The compositor samples the immutable full-resolution image instead.
    rendered.fill(0);
    int ox=fx?Cell-f.hdX-f.hdW/10:f.hdX,oy=fy?Cell-f.hdY-f.hdH/10:f.hdY;
    const auto &image=f.hdPixels[(fx?1:0)|(fy?2:0)];
    for(int y=0;y<f.hdH/10;++y)for(int x=0;x<f.hdW/10;++x) {
      uint64_t sums[3]={};unsigned alpha=0;
      for(int dy=0;dy<10;++dy)for(int dx=0;dx<10;++dx) {
        uint32_t c=image[size_t(y*10+dy)*f.hdW+x*10+dx];unsigned a=c>>24;alpha+=a;
        for(int k=0;k<3;++k)sums[k]+=((c>>(k*8))&255)*a;
      }
      if(alpha)rendered[(oy+y)*Cell+ox+x]=0xff000000u|uint32_t(sums[0]/alpha)|uint32_t(sums[1]/alpha)<<8|uint32_t(sums[2]/alpha)<<16;
    }
    hdFrame={image.data(),p->hostObjX+ox,p->hostObjY+oy,f.hdW,f.hdH,10,hdRevision};
  }
  p->hostObjSlot=127;memset(p->hostObjMask,0,sizeof(p->hostObjMask));
  for(const auto&part:parts){p->hostObjMask[part.slot>>3]|=1u<<(part.slot&7);p->hostObjSlot=std::min(p->hostObjSlot,(uint8_t)part.slot);}
  auto attr=parts.back().attr;p->hostObjPriority=SPRITE_PRIO_TO_PRIO((attr>>12)&3,(attr&0x800)==0)<<8;p->hostObjPixels=rendered.data();
}
void preview(const Pack&p,const Frame&f,ImVec2 pos,float scale,ImU32 tint=0xffffffff){
  if(p.pixels.empty())return;auto*d=ImGui::GetWindowDrawList();int bx=f.cell%Columns*Cell,by=f.cell/Columns*Cell;
  for(int y=0;y<Cell;++y)for(int x=0;x<Cell;++x){uint32_t c=p.pixels[(by+y)*Width+bx+(previewFlip?Cell-1-x:x)];if(!(c>>24))continue;
    ImU32 col=IM_COL32(c>>16&255,c>>8&255,c&255,(c>>24)*(tint>>24)/255);d->AddRectFilled({pos.x+x*scale,pos.y+y*scale},{pos.x+(x+1)*scale,pos.y+(y+1)*scale},col);}
}
}
extern "C" void Cv4CharacterInit(const uint8_t*r,unsigned n){rom=r;romSize=n;tuningRom=nullptr;}
extern "C" void Cv4CharacterBeforeFrame(void){
  try {
    // on_rom_loaded precedes cart_load, which copies the source image.
    // Bind only after SnesInit, to the actual executable cartridge bytes.
    if(g_snes && g_snes->cart && tuningRom!=g_snes->cart->rom) {
      tuningRom=g_snes->cart->rom;
      cv4tuning::init(tuningRom,g_snes->cart->romSize);
    }
    if(!initialized)initialize();
    if(!cv4tuning::apply(enabled?active.gameplay:cv4tuning::Values()))
      status="Gameplay tuning unavailable: original game bytes did not match";
    if(std::getenv("SNESRECOMP_TUNING_TRACE") && tuningRom && ticks%10==0) {
      extern uint8_t g_ram[];
      fprintf(stderr,"[tuning] frame=%u enabled=%d x=%u y=%u state=%u whip=%u cross=%u cost=%u links=%u\n",
              ticks,enabled,word(g_ram,0x54a),word(g_ram,0x54e),word(g_ram,0x552),
              word(tuningRom,0xa6ec),word(tuningRom,0xa700),word(tuningRom,0x925d),word(tuningRom,0x9261));
    }
  }catch(const std::exception&e){status=e.what();cv4tuning::apply(cv4tuning::Values());}
}
extern "C" void Cv4CharacterBegin(Ppu*p,const uint8_t*r){
  p->hostObjPixels=nullptr;currentIndex=-1;hdFrame={};
  try{
    if(!initialized)initialize();
    // An art program can briefly leave an incomplete file while saving.
    // Keep rendering the last valid pack, then retry on the next poll.
    if(++ticks%30==0&&!active.directory.empty())try{
      bool changed=active.imageTime!=fs::last_write_time(path(active,"body.png"))||active.manifestTime!=fs::last_write_time(path(active,"character.json"));
      for(const auto &f:active.frames)if(!f.hdImage.empty()&&f.hdTime!=fs::last_write_time(path(active,f.hdImage.c_str())))changed=true;
      if(changed){active=load(active.directory);++hdRevision;status="Reloaded "+active.name;}
    }catch(const std::exception&e){status=std::string("Keeping last loaded art: ")+e.what();}
    bool visible=r[0x32]==4&&!PPU_forcedBlank(p);
    // The guest can advance its object state after assembling OAM. In that
    // case the previous object's exact pose/position is what is on screen.
    // Both paths still require every OAM piece to match, with no tolerance.
    bool matched=visible&&readBody(p,r);
    if(!matched&&visible&&havePreviousPose)matched=readBody(p,previousPoseRam.data());
    std::copy_n(r,previousPoseRam.size(),previousPoseRam.begin());
    havePreviousPose=visible;
    if(matched){captureFrame(r);publish(p,r);}
    flushTemplate(false);
    if(visible&&std::getenv("SNESRECOMP_CHARACTER_TRACE"))fprintf(stderr,"[character_frame] %u matched=%d replaced=%d id=%s clipped=%d\n",ticks,matched,p->hostObjPixels!=nullptr,matched?currentId.c_str():"unknown",matched&&edgeClipped);
  }catch(const std::exception&e){status=e.what();p->hostObjPixels=nullptr;hdFrame={};}
}
extern "C" void Cv4CharacterEnd(Ppu*p){p->hostObjPixels=nullptr;}
extern "C" const Cv4CharacterHdFrame *Cv4CharacterHd(void){return hdFrame.pixels?&hdFrame:nullptr;}
extern "C" const char *Cv4CharacterPose(void){return currentId.c_str();}
extern "C" void Cv4CharacterEditor(){
  if(!initialized)return;
  auto display=ImGui::GetIO().DisplaySize;
  ImGui::SetNextWindowPos({24,76},ImGuiCond_Always);
  ImGui::SetNextWindowSize({std::min(600.f,display.x-48),std::min(760.f,display.y-92)},ImGuiCond_Always);
  if(!ImGui::Begin("Character workshop")){ImGui::End();return;}
  ImGui::TextWrapped("%s",status.c_str());
  if(ImGui::Checkbox("Use character pack",&enabled))std::ofstream("characters/selected.txt")<<(enabled?active.directory:"");
  ImGui::SameLine();ImGui::Checkbox("Collect Simon poses",&capture);
  try{
    if(ImGui::BeginCombo("Character",active.name.empty()?"Native Simon":active.name.c_str())){
      for(const auto&e:fs::directory_iterator("characters"))if(e.is_directory()&&e.path().filename()!="simon-template"&&fs::exists(e.path()/"character.json")){
        auto name=e.path().filename().string();if(ImGui::Selectable(name.c_str(),name==active.directory)){selectPack(name);enabled=true;}}
      ImGui::EndCombo();
    }
    ImGui::BeginDisabled(reference.frames.empty());
    if(ImGui::Button("Create character copy")){
      Pack p=reference;int n=1;while(fs::exists(fs::path("characters")/("custom-"+std::to_string(n))))++n;
      p.directory="custom-"+std::to_string(n);p.name="Custom character "+std::to_string(n);save(p,true);selectPack(p.directory);enabled=true;
    }
    ImGui::EndDisabled();
    ImGui::SameLine();if(ImGui::Button("Reload")&&!active.directory.empty()){active=load(active.directory);++hdRevision;status="Reloaded "+active.name;}
    if(!active.directory.empty()&&ImGui::Button("Add newly collected poses")){
      active=load(active.directory);++hdRevision;int added=0;
      for(const auto&f:reference.frames)if(find(active,f.id)<0&&active.frames.size()<Columns*Rows){std::set<int> used;for(auto&a:active.frames)used.insert(a.cell);int cell=0;while(used.count(cell))++cell;
        Frame copy=f;copy.cell=cell;for(int y=0;y<Cell;++y)std::copy_n(reference.pixels.data()+(f.cell/Columns*Cell+y)*Width+f.cell%Columns*Cell,Cell,active.pixels.data()+(cell/Columns*Cell+y)*Width+cell%Columns*Cell);active.frames.push_back(copy);++added;}
      save(active,true);status="Added "+std::to_string(added)+" poses";
    }
  }catch(const std::exception&e){status=e.what();}
  Pack&shown=active.directory.empty()?reference:active;
  if(ImGui::CollapsingHeader("Character gameplay",ImGuiTreeNodeFlags_DefaultOpen)) {
    ImGui::TextWrapped("Live per-character settings. Save gameplay to keep them. Disabling the pack restores Simon defaults.");
    ImGui::BeginDisabled(active.directory.empty()||!cv4tuning::available());
    if(ImGui::Button("Save gameplay"))try{save(active,false);status="Gameplay saved for "+active.name;}catch(const std::exception&e){status=e.what();}
    ImGui::SameLine();
    if(ImGui::Button("Reset to Simon defaults"))active.gameplay=cv4tuning::Values();
    auto sliders=[](int first,int last) {
      for(int i=first;i<last;i++) {
        const auto &d=cv4tuning::definitions[i];
        ImGui::SetNextItemWidth(ImGui::GetContentRegionAvail().x*0.45f);
        ImGui::SliderInt(d.label,&active.gameplay.value[i],d.minimum,d.maximum);
      }
    };
    if(ImGui::TreeNodeEx("Movement",ImGuiTreeNodeFlags_DefaultOpen)) {
      sliders(cv4tuning::Walk,cv4tuning::LeatherDamage);
      ImGui::TextWrapped("Crouch speed also affects the native slow movement in mud.");
      ImGui::TreePop();
    }
    if(ImGui::TreeNode("Weapon attack points")) {
      sliders(cv4tuning::LeatherDamage,cv4tuning::LeatherLength);
      ImGui::TextWrapped("Internal damage units, not HUD bars. Holy water can hit repeatedly.");
      ImGui::TreePop();
    }
    if(ImGui::TreeNode("Whip lengths")) {
      sliders(cv4tuning::LeatherLength,cv4tuning::DaggerCost);
      ImGui::TextWrapped("Native 1-7 link range. Ring-swing rope length is unchanged.");
      ImGui::TreePop();
    }
    if(ImGui::TreeNode("Subweapon heart costs")) {
      sliders(cv4tuning::DaggerCost,cv4tuning::Count);
      ImGui::TreePop();
    }
    ImGui::EndDisabled();
  }
  ImGui::TextWrapped("Collected: %zu | Pack: %zu | Missing collected poses: %zu",reference.frames.size(),shown.frames.size(),reference.frames.size()-std::count_if(reference.frames.begin(),reference.frames.end(),[&](const Frame&f){return find(shown,f.id)>=0;}));
  ImGui::TextWrapped("Edit characters/%s/body.png in your art program. Each 96 x 96 cell is independent. PNG changes reload while playing.",shown.directory.c_str());
  auto hdCount=std::count_if(shown.frames.begin(),shown.frames.end(),[](const Frame &f){return !f.hdImage.empty();});
  if(hdCount)ImGui::TextWrapped("%zu HD poses: individual 10x PNGs render while HD graphics and Sprites are enabled. body.png is their native alignment preview. Ctrl+H restores original Simon for these poses.",size_t(hdCount));
  ImGui::TextWrapped("Unseen or missing poses use native Simon. Collect poses by walking, jumping, crouching, attacking and using stairs.");
  if(!currentId.empty())ImGui::Text("Last game pose: %s (%s)",currentId.c_str(),enabled&&currentIndex>=0?"in pack":"native fallback");
  if(!shown.frames.empty()){
    selected=std::clamp(selected,0,(int)shown.frames.size()-1);
    ImGui::Checkbox("Play collected frames",&playing);ImGui::SameLine();ImGui::Checkbox("Flip preview",&previewFlip);ImGui::SameLine();ImGui::Checkbox("Simon overlay",&overlay);
    if(playing)selected=(int)(ImGui::GetTime()*8)%shown.frames.size();
    ImGui::SliderInt("Frame",&selected,0,(int)shown.frames.size()-1);Frame&f=shown.frames[selected];
    ImGui::TextWrapped("%s | %s | Cell %d",f.label.c_str(),f.id.c_str(),f.cell);
    ImVec2 pos=ImGui::GetCursorScreenPos();float scale=3;auto*d=ImGui::GetWindowDrawList();
    for(int y=0;y<12;++y)for(int x=0;x<12;++x)d->AddRectFilled({pos.x+x*24,pos.y+y*24},{pos.x+(x+1)*24,pos.y+(y+1)*24},((x+y)&1)?IM_COL32(38,40,48,255):IM_COL32(55,58,68,255));
    preview(shown,f,pos,scale);int rf=find(reference,f.id);if(overlay&&rf>=0)preview(reference,reference.frames[rf],pos,scale,0x60ffffff);
    auto mark=[&](int x,int y,ImU32 c){float xx=pos.x+(previewFlip?Cell-x:x)*scale,yy=pos.y+y*scale;d->AddLine({xx-6,yy},{xx+6,yy},c,2);d->AddLine({xx,yy-6},{xx,yy+6},c,2);};
    mark(f.ax,f.ay,IM_COL32(0,255,120,255));mark(f.hx,f.hy,IM_COL32(255,190,40,255));ImGui::Dummy({Cell*scale,Cell*scale});
    ImGui::BeginDisabled(active.directory.empty());
    ImGui::SliderInt("Origin X",&f.ax,0,Cell-1);ImGui::SliderInt("Origin Y",&f.ay,0,Cell-1);
    ImGui::SliderInt("Hand guide X",&f.hx,0,Cell-1);ImGui::SliderInt("Hand guide Y",&f.hy,0,Cell-1);
    ImGui::TextWrapped("Green: engine origin. Gold: hand guide (whip keeps its original attachment). Keep the hand aligned with Simon's overlay.");
    if(ImGui::Button("Save anchors")&&!active.directory.empty())try{save(active,false);status="Anchors saved";}catch(const std::exception&e){status=e.what();}
    ImGui::EndDisabled();
  }
  ImGui::End();
}
