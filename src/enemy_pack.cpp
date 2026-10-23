#include "enemy_pack.h"
#include "character_json.h"
#include "hd_render.h"
#include "snes/ppu.h"
#include "third_party/stb_image.h"
#include "third_party/stb_image_write.h"
#include <algorithm>
#include <array>
#include <condition_variable>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <map>
#include <mutex>
#include <set>
#include <sstream>
#include <thread>
#include <vector>

namespace {
namespace fs=std::filesystem;
constexpr int Cell=96,Anchor=48,MaxFrames=4096,MaxActors=128,MaxCell=256;
struct Part {int slot,x,y,size;uint16_t attr;unsigned index;};
struct Capture {std::string id;unsigned type=0,pose=0;int size=Cell,anchor=Anchor;std::vector<uint32_t> pixels=std::vector<uint32_t>(Cell*Cell);};
struct Art {std::string id,image;int w=0,h=0,dw=Cell,dh=Cell,ax=Anchor,ay=Anchor;std::vector<uint32_t> pixels;std::array<std::vector<uint32_t>,4> proxies;fs::file_time_type stamp{};};
struct Pack {std::string directory;std::map<std::string,Art> frames;fs::file_time_type stamp{};};
const uint8_t *rom=nullptr;unsigned romSize=0,ticks=0;bool initialized=false,capture=true;
std::array<uint8_t,0x13e0> previous{};bool havePrevious=false;
Pack active;std::string status="Native enemies; collecting pilot references",selection;
std::set<std::string> captured;
// Native A02 walking skeletons, on the two playable planes. Other actors
// include architecture and ambient effects; do not mislabel those as enemies.
const std::set<unsigned> captureTypes{0x11,0x12};
bool workshop=false;
std::string observation="{\"actors\":[]}";
std::array<Cv4EnemyHdFrame,MaxActors> frames{};
std::array<PpuHostSprite,MaxActors> hosts{};unsigned frameCount=0;uint64_t revision=1;
uint16_t word(const uint8_t*r,unsigned a){return r[a]|uint16_t(r[a+1])<<8;}
uint32_t rgba(uint16_t c){auto e=[](unsigned v){return (v<<3)|(v>>2);};return 0xff000000u|e(c&31)<<16|e(c>>5&31)<<8|e(c>>10&31);}
int ox(const Ppu*p,int slot){int x=(p->oam[slot*2]&255)|(((p->highOam[slot>>2]>>((slot&3)*2))&1)<<8);return x>=256+(int)p->extraRightCur?x-512:x;}
int os(const Ppu*p,int slot){static const int sizes[8][2]={{8,16},{8,32},{8,64},{16,32},{16,64},{32,64},{16,32},{16,32}};return sizes[PPU_objSize(p)][(p->highOam[slot>>2]>>((slot&3)*2+1))&1];}
unsigned texel(const Ppu*p,const Part&a,int x,int y){
 if(a.attr&0x4000)x=a.size-1-x;if(a.attr&0x8000)y=a.size-1-y;
 unsigned tile=((((a.attr&255)>>4)+(y>>3))<<4)|(((a.attr&15)+(x>>3))&15);
 unsigned base=(a.attr&256)?PPU_objTileAdr2(p):PPU_objTileAdr1(p),addr=(base+tile*16+(y&7))&0x7fff,b=7-(x&7);
 uint32_t v=p->vram[addr]|uint32_t(p->vram[(addr+8)&0x7fff])<<16;
 return (v>>b&1)|(v>>(b+7)&2)|(v>>(b+14)&4)|(v>>(b+21)&8);
}
std::string key(unsigned type,unsigned pose,uint64_t hash){std::ostringstream s;s<<(type==0x11||type==0x12?"skelett-":"gegner-")<<std::hex<<std::setfill('0')<<std::setw(4)<<type<<"_pose-"<<std::setw(4)<<pose<<'_'<<std::setw(16)<<hash;return s.str();}
// Small independent PNG jobs never block the game thread. The worker owns its
// snapshots; the manifest is rebuilt from complete saved captures at shutdown.
class Writer {
 std::mutex mutex;std::condition_variable wake;std::vector<Capture> pending;std::map<std::string,Capture> saved;bool stop=false,busy=false;
 std::thread worker{[this]{run();}};
 void manifest(){
  fs::path base="enemy_packs/native-template";fs::create_directories(base);std::ofstream f(base/"enemies.tmp.json");
  f<<"{\n  \"version\": 1,\n  \"name\": \"Native enemy references\",\n  \"frames\": [\n";size_t n=0;
  for(const auto &[id,c]:saved)f<<"    {\"id\": "<<character_json::quote(id)<<", \"actor_type\": "<<c.type<<", \"pose\": "<<c.pose<<", \"reference\": "<<character_json::quote(id+".png")<<", \"display_size\": ["<<c.size<<","<<c.size<<"], \"anchor\": ["<<c.anchor<<","<<c.anchor<<"]}"<<(++n==saved.size()?"\n":",\n");
  f<<"  ]\n}\n";f.close();if(!f)throw std::runtime_error("Cannot save enemy reference manifest");fs::copy_file(base/"enemies.tmp.json",base/"enemies.json",fs::copy_options::overwrite_existing);fs::remove(base/"enemies.tmp.json");
 }
 void run(){for(;;){std::vector<Capture> batch;{std::unique_lock<std::mutex> lock(mutex);wake.wait(lock,[&]{return stop||!pending.empty();});if(pending.empty())return;batch.swap(pending);busy=true;}
   try{for(auto &c:batch){fs::path file=fs::path("enemy_packs/native-template")/(c.id+".png");fs::create_directories(file.parent_path());
    std::vector<uint8_t> bytes(c.pixels.size()*4);for(size_t i=0;i<c.pixels.size();++i){auto v=c.pixels[i];bytes[i*4]=v>>16;bytes[i*4+1]=v>>8;bytes[i*4+2]=v;bytes[i*4+3]=v>>24;}
    // References are never overwritten, so edited art cannot be lost.
    if(!fs::exists(file)&&!stbi_write_png(file.string().c_str(),c.size,c.size,4,bytes.data(),c.size*4))throw std::runtime_error("Cannot save enemy reference PNG");c.pixels.clear();c.pixels.shrink_to_fit();saved.emplace(c.id,std::move(c));}
    manifest();
   }catch(const std::exception&e){fprintf(stderr,"[enemies] reference capture: %s\n",e.what());}
   {std::lock_guard<std::mutex> lock(mutex);busy=false;}wake.notify_all();
  }}
public:
 void existing(const std::vector<Capture>&v){std::lock_guard<std::mutex> lock(mutex);for(const auto&c:v)saved.emplace(c.id,c);}
 void submit(Capture c){{std::lock_guard<std::mutex> lock(mutex);if(pending.size()>=MaxFrames)return;pending.push_back(std::move(c));}wake.notify_one();}
 void flush(){std::unique_lock<std::mutex> lock(mutex);wake.wait(lock,[&]{return pending.empty()&&!busy;});}
 ~Writer(){{std::lock_guard<std::mutex> lock(mutex);stop=true;}wake.notify_one();if(worker.joinable())worker.join();}
} writer;
fs::path directory(const std::string&s){if(s.empty()||s.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")!=std::string::npos)throw std::runtime_error("Enemy pack needs a local directory name");return fs::path("enemy_packs")/s;}
character_json::Value jsonFile(const fs::path&file){if(fs::file_size(file)>2*1024*1024)throw std::runtime_error("Enemy manifest too large");std::ifstream f(file);std::string t((std::istreambuf_iterator<char>(f)),{});return character_json::Reader(t).read();}
Pack load(const std::string&name){
 Pack p;p.directory=name;auto base=directory(name),file=base/"enemies.json";auto j=jsonFile(file);if(j.at("version").number()!=1)throw std::runtime_error("Unsupported enemy pack version");
 if(j.at("frames").items().size()>MaxFrames)throw std::runtime_error("Too many enemy poses");
 size_t pixelBudget=0;
 for(const auto &v:j.at("frames").items()){
  if(!v.object.count("image"))continue;Art a;a.id=v.at("id").string();a.image=v.at("image").string();if(a.id.empty()||a.image.empty()||fs::path(a.image).filename()!=fs::path(a.image))throw std::runtime_error("Enemy PNG must be local to its pack");
  const auto &d=v.at("display_size").items(),&an=v.at("anchor").items();if(d.size()!=2||an.size()!=2)throw std::runtime_error("Enemy display_size and anchor need two numbers");a.dw=d[0].number();a.dh=d[1].number();a.ax=an[0].number();a.ay=an[1].number();
  if(a.dw<1||a.dh<1||a.dw>MaxCell||a.dh>MaxCell||a.ax<0||a.ay<0||a.ax>a.dw||a.ay>a.dh)throw std::runtime_error("Enemy display or anchor outside 256px cell");
  int n;auto png=base/a.image;if(!stbi_info(png.string().c_str(),&a.w,&a.h,&n)||a.w<1||a.h<1||a.w>4096||a.h>4096)throw std::runtime_error("Enemy PNG dimensions invalid");
  pixelBudget+=size_t(a.w)*a.h;if(pixelBudget>64*1024*1024)throw std::runtime_error("Enemy pack exceeds pixel budget");
  unsigned char *bytes=stbi_load(png.string().c_str(),&a.w,&a.h,&n,4);if(!bytes)throw std::runtime_error("Cannot read enemy PNG");
  a.pixels.resize(size_t(a.w)*a.h);for(size_t i=0;i<a.pixels.size();++i)a.pixels[i]=uint32_t(bytes[i*4+3])<<24|uint32_t(bytes[i*4])<<16|uint32_t(bytes[i*4+1])<<8|bytes[i*4+2];stbi_image_free(bytes);
  for(unsigned flip=0;flip<4;++flip){auto &proxy=a.proxies[flip];proxy.resize(a.dw*a.dh);for(int y=0;y<a.dh;++y)for(int x=0;x<a.dw;++x){
   int rx=flip&1?a.dw-1-x:x,ry=flip&2?a.dh-1-y:y;
   // Any covered subpixel must participate in OBJ depth, even a fine strand
   // which misses a native pixel centre. The HD compositor retains its alpha.
   uint64_t sums[3]={};unsigned alpha=0;int x0=rx*a.w/a.dw,x1=std::max(x0+1,(rx+1)*a.w/a.dw),y0=ry*a.h/a.dh,y1=std::max(y0+1,(ry+1)*a.h/a.dh);
   for(int sy=y0;sy<y1;++sy)for(int sx=x0;sx<x1;++sx){auto c=a.pixels[size_t(sy)*a.w+sx];unsigned al=c>>24;alpha+=al;for(int k=0;k<3;++k)sums[k]+=((c>>(k*8))&255)*al;}
   if(alpha)proxy[y*a.dw+x]=0xff000000u|uint32_t(sums[0]/alpha)|uint32_t(sums[1]/alpha)<<8|uint32_t(sums[2]/alpha)<<16;
  }}a.stamp=fs::last_write_time(png);if(!p.frames.emplace(a.id,std::move(a)).second)throw std::runtime_error("Duplicate enemy pose");
 }p.stamp=fs::last_write_time(file);return p;
}
void initialize(){
 fs::create_directories("enemy_packs");initialized=true;std::ifstream selected("enemy_packs/selected.txt");std::getline(selected,selection);
 if(fs::exists("enemy_packs/native-template/enemies.json"))try{auto j=jsonFile("enemy_packs/native-template/enemies.json");std::vector<Capture> old;
  for(const auto&v:j.at("frames").items()){Capture c;c.id=v.at("id").string();c.type=v.at("actor_type").number();c.pose=v.at("pose").number();if(v.object.count("display_size")){const auto &d=v.at("display_size").items(),&a=v.at("anchor").items();if(d.size()!=2||a.size()!=2||d[0].number()!=d[1].number()||a[0].number()!=a[1].number())throw std::runtime_error("Invalid captured enemy canvas");c.size=d[0].number();c.anchor=a[0].number();if(c.size<1||c.size>MaxCell||c.anchor<0||c.anchor>c.size)throw std::runtime_error("Captured enemy canvas outside bounds");}c.pixels.clear();if(captured.size()<MaxFrames){captured.insert(c.id);old.push_back(std::move(c));}}writer.existing(old);
 }catch(const std::exception&e){capture=false;status=std::string("References preserved; capture disabled: ")+e.what();}
 if(!selection.empty()){active=load(selection);status="Loaded enemy pack "+selection;}
}
bool readActor(Ppu*p,const uint8_t*r,unsigned base,const std::set<int>&claimed,Capture&c,std::vector<Part>&parts,int&xbase,int&ybase,unsigned&flip){
 c.type=word(r,base+0x10);c.pose=word(r,base);if(!rom||c.pose<0x8000||!c.type||c.type==0x0e)return false;
 unsigned a=0x20000+(c.pose&0x7fff);if(a>=romSize)return false;unsigned count=rom[a];if(!count||count>32||a+1+count*4>romSize)return false;
 xbase=(int16_t)(word(r,base+0xa)-word(r,0x1c));ybase=(int16_t)((word(r,base+0xe)-word(r,0x1e))&word(r,0x13de));flip=word(r,base+4);
 unsigned add=word(r,base+0x26),priority=word(r,base+2);std::set<int> used=claimed;parts.clear();
 for(unsigned i=0;i<count;++i){unsigned o=a+1+i*4;uint16_t tile=word(rom,o+2);int size=tile&0x2000?16:8,x=(int8_t)rom[o],y=(int8_t)rom[o+1];
  x=xbase+((flip&0x4000)?-x-size:x);y=ybase+((flip&0x8000)?-y-size:y);tile=(tile|0x2000)^flip;if(priority&0x8000)tile=(tile&0xcfff)|((priority*2&255)<<8);tile+=add;
  // Require every component, including clipped offscreen pieces. Partial
  // metasprites must not consume an unrelated matching OBJ or hide originals.
  int found=-1;for(int slot=0;slot<128;++slot)if(!used.count(slot)&&ox(p,slot)==x&&(p->oam[slot*2]>>8)==(y&255)&&p->oam[slot*2+1]==tile&&os(p,slot)==size){found=slot;break;}
  if(found<0||x<-64||x>320)return false;parts.push_back({found,x,y,size,tile,i});used.insert(found);
 }
 for(const auto &part:parts){
  int dx=part.x-xbase,dy=part.y-ybase;
  if(flip&0x4000)dx=-dx-part.size;if(flip&0x8000)dy=-dy-part.size;
  if(dx < -Anchor || dy < -Anchor || dx+part.size>Anchor || dy+part.size>Anchor){c.size=MaxCell;c.anchor=MaxCell/2;}
 }
 c.pixels.assign(c.size*c.size,0);
 std::vector<uint8_t> indices(c.size*c.size);bool visible=false;std::sort(parts.begin(),parts.end(),[](const Part&a,const Part&b){return a.slot>b.slot;});
 for(const auto&a:parts)for(int y=0;y<a.size;++y)for(int x=0;x<a.size;++x){int dx=a.x+x-xbase,dy=a.y+y-ybase;if(flip&0x4000)dx=-dx-1;if(flip&0x8000)dy=-dy-1;dx+=c.anchor;dy+=c.anchor;if(dx<0||dy<0||dx>=c.size||dy>=c.size)return false;
  unsigned v=texel(p,a,x,y);if(v){indices[dy*c.size+dx]=(uint8_t)v;c.pixels[dy*c.size+dx]=rgba(p->cgram[128+((a.attr>>9)&7)*16+v]);if(a.x+x>=0&&a.x+x<256&&a.y+y>=0&&a.y+y<224)visible=true;}}
 if(!visible)return false;uint64_t h=14695981039346656037ull;for(auto v:indices){h^=v;h*=1099511628211ull;}c.id=key(c.type,c.pose,h);return true;
}
}
extern "C" void Cv4EnemyInit(const uint8_t*r,unsigned n){rom=r;romSize=n;havePrevious=false;}
extern "C" void Cv4EnemyBegin(Ppu*p,const uint8_t*r){
 frameCount=0;p->hostSprites=nullptr;p->hostSpriteCount=0;
 try{if(!initialized)initialize();++ticks;
  if(ticks%30==0&&!active.directory.empty())try{bool changed=fs::last_write_time(directory(active.directory)/"enemies.json")!=active.stamp;for(const auto &[id,a]:active.frames)if(fs::last_write_time(directory(active.directory)/a.image)!=a.stamp)changed=true;if(changed){active=load(active.directory);++revision;status="Reloaded enemy artwork";}}catch(const std::exception&e){status=std::string("Keeping last enemy artwork: ")+e.what();}
  bool visible=r[0x32]==4&&!PPU_forcedBlank(p);std::set<int> claimed;
  std::ostringstream observed;observed<<"{\"tick\":"<<ticks<<",\"actors\":[";bool comma=false;
  if(p->hostObjPixels)for(int s=0;s<128;++s)if(p->hostObjMask[s>>3]&(1u<<(s&7)))claimed.insert(s);
  if(visible)for(unsigned base=0x580;base<0xec0&&frameCount<MaxActors;base+=0x40){Capture c;std::vector<Part> parts;int x,y;unsigned flip;
   bool matched=readActor(p,r,base,claimed,c,parts,x,y,flip);if(!matched&&havePrevious){c={};matched=readActor(p,previous.data(),base,claimed,c,parts,x,y,flip);}if(!matched)continue;
   for(const auto&a:parts)claimed.insert(a.slot);
   if(capture&&(workshop||captureTypes.count(c.type)||c.type==2)&&captured.size()<MaxFrames&&captured.insert(c.id).second)writer.submit(c);
   if(workshop) {
    if(comma)observed<<',';comma=true;
    observed<<"{\"slot\":"<<base<<",\"type\":"<<c.type<<",\"pose\":"<<c.pose<<",\"id\":"<<character_json::quote(c.id)<<",\"x\":"<<x<<",\"y\":"<<y<<",\"size\":"<<c.size<<",\"anchor\":"<<c.anchor<<",\"flip\":"<<((flip>>14)&3)<<",\"parts\":[";
    bool pc=false;for(const auto &part:parts) {
     const std::string pieceID=c.id+"__teil-"+std::to_string(part.index);
     if(capture&&captured.size()<MaxFrames&&captured.insert(pieceID).second){
      Capture piece;piece.size=c.size;piece.anchor=c.anchor;piece.pixels.assign(c.pixels.size(),0);piece.type=c.type;piece.pose=c.pose;piece.id=pieceID;
      for(int py=0;py<part.size;++py)for(int px=0;px<part.size;++px) {
       int dx=part.x+px-x,dy=part.y+py-y;if(flip&0x4000)dx=-dx-1;if(flip&0x8000)dy=-dy-1;dx+=c.anchor;dy+=c.anchor;
       unsigned v=texel(p,part,px,py);if(v&&dx>=0&&dy>=0&&dx<c.size&&dy<c.size)piece.pixels[dy*c.size+dx]=rgba(p->cgram[128+((part.attr>>9)&7)*16+v]);
      }writer.submit(std::move(piece));
     }
     if(pc)observed<<',';pc=true;observed<<"{\"id\":"<<character_json::quote(pieceID)<<",\"index\":"<<part.index<<",\"oam\":"<<part.slot<<",\"priority\":"<<((part.attr>>12)&3)<<",\"math\":"<<((part.attr>>11)&1)<<"}";
    }observed<<"]}";
   }
   auto it=active.frames.find(c.id);bool whole=it!=active.frames.end();
   for(const auto &part:parts)if((part.attr&0x3800)!=(parts[0].attr&0x3800))whole=false;
   if(!Cv4HdEnabled()||!(Cv4HdLayerMask()&16)||!(p->renderFlags&kPpuRenderFlags_NewRenderer))continue;
   // Whole-pose artwork takes precedence. Otherwise individual native OAM
   // components may be replaced without consuming their untouched neighbours.
   std::vector<std::pair<const Art*,std::vector<Part>>> replacements;
   if(whole)replacements.push_back({&it->second,parts});
   else for(const auto &part:parts) {
    auto piece=active.frames.find(c.id+"__teil-"+std::to_string(part.index));
    if(piece!=active.frames.end())replacements.push_back({&piece->second,{part}});
   }
   for(const auto &replacement:replacements) {
   if(frameCount>=MaxActors)break;
   const auto &selectedParts=replacement.second;
   const auto&a=*replacement.first;unsigned f=(flip&0x4000?1:0)|(flip&0x8000?2:0);auto &host=hosts[frameCount];host={};host.x=x-(f&1?a.dw-a.ax:a.ax);host.y=y-(f&2?a.dh-a.ay:a.ay);host.width=host.stride=a.dw;host.height=a.dh;host.pixels=a.proxies[f].data();host.oamSlot=127;
   for(const auto&part:selectedParts){host.mask[part.slot>>3]|=1u<<(part.slot&7);host.oamSlot=std::min(host.oamSlot,(uint8_t)part.slot);}auto attr=selectedParts[0].attr;host.priority=SPRITE_PRIO_TO_PRIO((attr>>12)&3,(attr&0x800)==0)<<8;
   frames[frameCount]={a.pixels.data(),host.x,host.y,a.w,a.h,a.dw,a.dh,f,host.priority,(uint16_t)c.type,(uint16_t)c.pose,host.oamSlot,revision,a.id.c_str()};++frameCount;
   }
  }
  std::copy_n(r,previous.size(),previous.begin());havePrevious=visible;
  if(workshop){observed<<"]}";observation=observed.str();}
  if(frameCount){p->hostSprites=hosts.data();p->hostSpriteCount=frameCount;}
 }catch(const std::exception&e){status=e.what();frameCount=0;p->hostSprites=nullptr;p->hostSpriteCount=0;}
}
extern "C" void Cv4EnemyEnd(Ppu*p){p->hostSprites=nullptr;p->hostSpriteCount=0;}
extern "C" const Cv4EnemyHdFrame *Cv4EnemyHd(unsigned n){return n<frameCount?&frames[n]:nullptr;}
extern "C" unsigned Cv4EnemyHdCount(void){return frameCount;}
extern "C" const char *Cv4EnemyStatus(void){return status.c_str();}
extern "C" int Cv4EnemyCapturing(void){return capture;}
extern "C" const char *Cv4EnemySelection(void){return selection.c_str();}
extern "C" const char *Cv4EnemyObservation(void){return observation.c_str();}
extern "C" int Cv4EnemyCommand(const char*s){try{if(!initialized)initialize();std::string c=s?s:"";if(c=="flush"){writer.flush();status="Enemy references saved";}else if(c=="workshop on"){workshop=true;capture=true;status="Native workshop capture enabled";}else if(c=="workshop off"){workshop=false;status="Workshop capture disabled";}else if(c=="capture on"){capture=true;status="Enemy pilot capture enabled";}else if(c=="capture off"){capture=false;status="Enemy capture disabled";}else if(c=="reload"){if(!selection.empty())active=load(selection);++revision;status="Reloaded enemy pack";}else if(c.rfind("pack ",0)==0){auto name=c.substr(5);Pack next=load(name);active=std::move(next);selection=name;++revision;std::ofstream("enemy_packs/selected.txt")<<name;status="Loaded enemy pack "+name;}else if(c=="off"){active={};selection.clear();++revision;std::ofstream("enemy_packs/selected.txt");status="Native enemies";}else if(c!="status")throw std::runtime_error("enemy: status, capture on/off, pack <name>, reload, off");return 1;}catch(const std::exception&e){status=e.what();return 0;}}
