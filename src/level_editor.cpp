/* Opt-in custom level playtests. No changes without an explicit project load. */
#include "level_editor.h"
#include "enemy_pack.h"
extern "C" {
#include "snes/ppu.h"
#include "snes/interp_bridge.h"
#include "cpu_state.h"
}
#include <algorithm>
#include <array>
#include <cstdio>
#include <cstring>
#include <deque>
#include <fstream>
#include <stdexcept>
#include <vector>
extern "C" unsigned char g_ram[0x20000];
namespace {
struct Actor {unsigned type,variant,x,y,flags,hw,hh,hp,trait,add;unsigned damage=65535,kind=0,boss=0,options=0;bool spawned=false,parked=false;unsigned slot=0,persistence=0;std::array<unsigned char,64> saved{};};
struct Door {unsigned x,y,w,h,target,tx,ty,trigger,plane;};
struct Room {unsigned w,h,tileset,sx,sy,base[2],mode,collisionMode;std::vector<unsigned char> video;std::vector<uint32_t> maps[2];std::vector<unsigned short> collision[2];std::vector<Actor> actors;std::vector<Door> doors;};
struct Boss {unsigned type,x,y,slot,body;std::vector<unsigned char> states[2],video,raster;std::array<unsigned short,9> m7{};};
struct Resource {unsigned type,variant,add,pose,w,h,ax,ay;std::vector<unsigned char> video;std::vector<uint32_t> pixels;};
std::vector<Resource> resources;std::vector<unsigned char> spriteRom;
std::vector<PpuHostSprite> virtualSprites;std::deque<std::array<uint32_t,256>> spritePixels;
std::array<unsigned char,0x1400> previousSpriteState{};bool havePreviousSpriteState=false;
std::vector<Boss> bosses;int encounter=-1,dx=0,dy=0;unsigned encounterAge=0,deadAge=0;bool encounterVideo=false;
std::array<unsigned char,0x940> suspended;
std::array<unsigned char,0x2b0> suspendedExtras;
std::array<unsigned char,256> suspendedRaster;
std::array<unsigned char,256> suspendedPersistence;
std::array<unsigned short,128> mode7Colors{};
unsigned gameplaySubscreen=0;
unsigned suspendedBossEffect=0;
constexpr unsigned stateSize=2+0x940+0x80+0x30+0x200;
std::vector<Room> rooms;unsigned current=0;bool active=false,install=false;unsigned cooldown=0;int cx=0,cy=0;
std::vector<std::array<unsigned short,64>> atlas;bool mixed=false;
unsigned streamEnd=0;
bool damageHookInstalled=false;
unsigned sampledLines=0,failedLines=0,requestedFlags=0,failedFlags=0;bool faultRecorded=false;
unsigned word(unsigned at){return g_ram[at]|unsigned(g_ram[at+1])<<8;}
void put(unsigned at,unsigned value){g_ram[at]=value;g_ram[at+1]=value>>8;}
int verticalCameraLimit(const Room&r){return r.h<=32?0:int(r.h*8)-224;}
unsigned bossFloor(const Room&r,const Actor&a){
 unsigned layer=a.flags&0x8000?0:1,column=std::min(r.w-1,a.x/8);
 for(unsigned y=a.y/8;y<r.h;++y){unsigned v=r.collision[layer][y*r.w+column];if(v&&v!=65535)return y*8;}
 return std::clamp(a.y+96,64u,r.h*8-8);
}
void contactDamage(CpuState*cpu,uint32_t){
 if(!active||current>=rooms.size())return;
 if(encounter>=0){const auto&a=rooms[current].actors[encounter];if(a.damage!=65535){cpu->A=(uint16_t)a.damage;return;}}
 for(const auto&a:rooms[current].actors)if(a.slot==cpu->X&&word(a.slot+0x10)==a.type&&a.damage!=65535){cpu->A=(uint16_t)a.damage;break;}
}
template<class T> unsigned cell(const Room&r,const std::vector<T>&map,int x,int y,unsigned outside){return x>=0&&y>=0&&x<int(r.w)&&y<int(r.h)?map[y*r.w+x]:outside;}
void enter(unsigned index,unsigned x,unsigned y,unsigned plane){
 havePreviousSpriteState=false;
 if(encounter>=0){put(0xef0,suspendedBossEffect);std::copy(suspendedPersistence.begin(),suspendedPersistence.end(),g_ram+0x1500);std::copy(suspendedRaster.begin(),suspendedRaster.end(),g_ram+0x100);unsigned cursor=0;for(auto span:{std::pair<unsigned,unsigned>{0x1200,0x80},{0x13c0,0x30},{0x1e00,0x200}}){memcpy(g_ram+span.first,suspendedExtras.data()+cursor,span.second);cursor+=span.second;}}
 current=index;auto&r=rooms[current];install=true;cooldown=30;encounter=-1;dx=dy=0;
 std::fill(g_ram+0x580,g_ram+0xec0,0);std::fill(g_ram+0x1200,g_ram+0x1280,0);
 for(auto&a:r.actors){a.spawned=false;a.parked=false;a.slot=0;a.persistence=0;}
 put(0x54a,x);put(0x54e,y);put(0x552,0);put(0x542,plane?0:0x8018);
 for(unsigned at=0x558;at<=0x55e;at+=2)put(at,0);
 put(0x13f4,16);put(0xbc,90);put(0xb8,0);put(0x94,streamEnd);put(0x96,streamEnd);
}
void beginEncounter(unsigned index){
 havePreviousSpriteState=false;
 auto&r=rooms[current];auto&a=r.actors[index];const auto&b=bosses[a.boss];
 std::copy(g_ram+0x580,g_ram+0xec0,suspended.begin());
 std::copy(g_ram+0x100,g_ram+0x200,suspendedRaster.begin());memcpy(g_ram+0x100,b.raster.data(),256);
 std::copy(g_ram+0x1500,g_ram+0x1600,suspendedPersistence.begin());
 suspendedBossEffect=word(0xef0);if(b.type==0x8d)put(0xef0,0x200); // Native final-boss initializer $03:C089.
 unsigned cursor=0;for(auto span:{std::pair<unsigned,unsigned>{0x1200,0x80},{0x13c0,0x30},{0x1e00,0x200}}){std::copy(g_ram+span.first,g_ram+span.first+span.second,suspendedExtras.begin()+cursor);cursor+=span.second;}
 const auto&state=b.states[a.options&1?0:1];put(0xb8,state[0]|unsigned(state[1])<<8);cursor=2;
 for(auto span:{std::pair<unsigned,unsigned>{0x580,0x940},{0x1200,0x80},{0x13c0,0x30},{0x1e00,0x200}}){memcpy(g_ram+span.first,state.data()+cursor,span.second);cursor+=span.second;}
 // Boss Y records often belong to their invisible scene controller. Align
 // their native arena floor, not that controller's Y, to the custom terrain.
 dx=int(b.x)-int(a.x);dy=192-int(bossFloor(r,a));put(0x54a,std::max(24,int(word(0x54a))+dx));put(0x54e,word(0x54e)+dy);
 encounter=(int)index;a.spawned=true;a.slot=b.slot;encounterAge=deadAge=0;encounterVideo=true;
 if(a.options&4)put(b.slot+6,a.hp);if(a.options&8)put(b.slot+0x28,a.hw);if(a.options&16)put(b.slot+0x2a,a.hh);
}
void finishEncounter(){
 havePreviousSpriteState=false;
 auto&r=rooms[current];auto&a=r.actors[encounter];bool exit=a.options&2;
 put(0x54a,std::clamp(int(word(0x54a))-dx,0,int(r.w*8)-1));put(0x54e,std::clamp(int(word(0x54e))-dy,0,int(r.h*8)-1));
 std::copy(suspended.begin(),suspended.end(),g_ram+0x580);
 std::copy(suspendedRaster.begin(),suspendedRaster.end(),g_ram+0x100);
 std::copy(suspendedPersistence.begin(),suspendedPersistence.end(),g_ram+0x1500);
 put(0xef0,suspendedBossEffect);
 unsigned cursor=0;for(auto span:{std::pair<unsigned,unsigned>{0x1200,0x80},{0x13c0,0x30},{0x1e00,0x200}}){memcpy(g_ram+span.first,suspendedExtras.data()+cursor,span.second);cursor+=span.second;}
 put(0xb8,0);put(0x70,5);put(0x3c,0);put(0xbc,90);put(0x552,0);a.slot=0;encounter=-1;dx=dy=0;install=true;
 if(exit&&!r.doors.empty()){const auto d=r.doors.front();enter(d.target,d.tx,d.ty,d.plane);}
}
}
extern "C" int Cv4LevelLoad(const char *path,char *result,size_t capacity){
 try{
  if(!strcmp(path,"off")){Cv4LevelReset();snprintf(result,capacity,"Custom level disabled");return 1;}
  std::ifstream f(path,std::ios::binary);if(!f)throw std::runtime_error("Cannot open custom level");
  f.seekg(0,std::ios::end);auto size=f.tellg();if(size<14||size>512*1024*1024)throw std::runtime_error("Invalid custom level size");
  f.seekg(0);std::vector<unsigned char> data((size_t)size);if(!f.read((char*)data.data(),data.size()))throw std::runtime_error("Cannot read custom level");
  size_t at=0;auto read=[&](){if(at+2>data.size())throw std::runtime_error("Truncated custom level");unsigned v=data[at]|unsigned(data[at+1])<<8;at+=2;return v;};
  bool extended=!memcmp(data.data(),"CV4LVL3\0",8)||!memcmp(data.data(),"CV4LVL4\0",8);
  bool newMixed=!memcmp(data.data(),"CV4LVL2\0",8)||!memcmp(data.data(),"CV4LVL4\0",8);
  if(!extended&&!newMixed&&memcmp(data.data(),"CV4LVL1\0",8))throw std::runtime_error("Unknown custom level format");at=8;
  auto read32=[&](){unsigned lo=read();return lo|(read()<<16);};
  unsigned count=read(),start=read(),stop=read();if(!count||count>64||start>=count||stop<0x8000)throw std::runtime_error("Invalid custom room count");
  std::vector<Room> next;
  std::vector<std::array<unsigned short,64>> nextAtlas;
  if(newMixed){
   unsigned tiles=read32();if(!tiles||tiles>1048576||tiles>(data.size()-at)/128)throw std::runtime_error("Invalid custom graphics atlas");
   nextAtlas.resize(tiles);for(auto&tile:nextAtlas)for(auto&pixel:tile)pixel=(unsigned short)read();
  }
  std::vector<Boss> nextBosses;
  if(extended){
   unsigned number=read();if(number>14)throw std::runtime_error("Too many boss templates");
   for(unsigned i=0;i<number;++i){Boss b;b.type=read();b.x=read();b.y=read();b.slot=read();b.body=read();
    if(b.type<128||b.type>0x8d||b.slot<0x580||b.slot>=0xec0||(b.slot-0x580)%0x40)throw std::runtime_error("Invalid boss template");
    for(auto&state:b.states){if(at+stateSize>data.size())throw std::runtime_error("Missing boss state");state.assign(data.begin()+at,data.begin()+at+stateSize);at+=stateSize;}
    if(at+0x10300>data.size())throw std::runtime_error("Missing boss graphics");b.video.assign(data.begin()+at,data.begin()+at+0x10200);at+=0x10200;b.raster.assign(data.begin()+at,data.begin()+at+256);at+=256;for(auto&value:b.m7)value=read();nextBosses.push_back(std::move(b));
   }
  }
  for(unsigned n=0;n<count;++n){
   Room r;r.w=read();r.h=read();r.tileset=read();r.sx=read();r.sy=read();r.base[0]=read();r.base[1]=read();r.mode=read();r.collisionMode=read();unsigned actors=read(),doors=read();
   if(r.w<32||r.w>1024||r.h<28||r.h>512||r.w*r.h>262144||r.sx>=r.w*8||r.sy>=r.h*8||r.tileset>=68||r.base[0]>0x3000||r.base[1]>0x3000||(r.mode&7)!=1||r.collisionMode>3||actors>4096||doors>64)
    throw std::runtime_error("Unsupported custom room geometry or graphics");
   unsigned videoSize=extended?0x10200:0xd600;
   if(at+videoSize>data.size())throw std::runtime_error("Missing room graphics");
   r.video.assign(data.begin()+at,data.begin()+at+videoSize);at+=videoSize;
   for(int layer=0;layer<2;++layer)for(unsigned i=0;i<r.w*r.h;++i){
    unsigned value=newMixed?read32():read();
    if(newMixed&&(value&0x7fffffff)>=nextAtlas.size())throw std::runtime_error("Custom tile outside graphics atlas");
    r.maps[layer].push_back(value);
   }
   for(int layer=0;layer<2;++layer)for(unsigned i=0;i<r.w*r.h;++i)r.collision[layer].push_back((unsigned short)read());
   for(unsigned i=0;i<actors;++i){Actor a;a.type=read();a.variant=read();a.x=read();a.y=read();a.flags=read();a.hw=read();a.hh=read();a.hp=read();a.trait=read();a.add=read();
    if(extended){a.damage=read();a.kind=read();a.boss=read();a.options=read();if((a.damage>255&&a.damage!=65535)||a.kind>3)throw std::runtime_error("Invalid custom actor values");}
    if(!a.type||a.type>0x8d||a.variant>255||a.x>=r.w*8||a.y>=r.h*8||a.add>0x1ff||a.hw>255||a.hh>255||a.hp>32767||a.options>31||(a.type>=128&&(a.kind!=2||a.boss>=nextBosses.size()||nextBosses[a.boss].type!=a.type)))throw std::runtime_error("Invalid custom monster");r.actors.push_back(a);}
   for(unsigned i=0;i<doors;++i){Door d;d.x=read();d.y=read();d.w=read();d.h=read();d.target=read();d.tx=read();d.ty=read();d.trigger=read();d.plane=read();
    if(d.target>=count||d.w<8||d.w>256||d.h<8||d.h>256||d.x>=r.w*8||d.y>=r.h*8||d.trigger>1||d.plane>1)throw std::runtime_error("Invalid custom exit");r.doors.push_back(d);}
   next.push_back(std::move(r));
  }
  for(const auto&r:next)for(const auto&d:r.doors)if(d.tx>=next[d.target].w*8||d.ty>=next[d.target].h*8)throw std::runtime_error("Exit target outside room");
  std::vector<Resource> nextResources;std::vector<unsigned char> nextSpriteRom;
  if(at<data.size()){
   if(at+10+32768>data.size()||memcmp(data.data()+at,"CV4VOBJ1",8))throw std::runtime_error("Unexpected custom level data");
   at+=8;unsigned count=read();if(count>1024)throw std::runtime_error("Too many independent actor contexts");
   nextSpriteRom.assign(data.begin()+at,data.begin()+at+32768);at+=32768;
   for(unsigned n=0;n<count;++n){Resource res;res.type=read();res.variant=read();res.add=read();res.pose=read();res.w=read();res.h=read();res.ax=read();res.ay=read();
    if(!res.type||res.type>=128||res.variant>255||res.add>511||res.w>512||res.h>512||bool(res.w)!=bool(res.h)||res.ax>res.w||res.ay>res.h||at+0x10200+size_t(res.w)*res.h*4>data.size())throw std::runtime_error("Invalid independent actor context");
    for(const auto&other:nextResources)if(res.type==other.type&&res.variant==other.variant)throw std::runtime_error("Duplicate independent actor context");
    res.video.assign(data.begin()+at,data.begin()+at+0x10200);at+=0x10200;
    for(unsigned i=0;i<res.w*res.h;++i){res.pixels.push_back(unsigned(data[at+3])<<24|unsigned(data[at])<<16|unsigned(data[at+1])<<8|data[at+2]);at+=4;}
    nextResources.push_back(std::move(res));
   }
  }
  if(at!=data.size())throw std::runtime_error("Unexpected independent actor data");
  if(!damageHookInstalled){damageHookInstalled=interp_bridge_add_pre_opcode_hook(0x00dd12,contactDamage);if(!damageHookInstalled)throw std::runtime_error("Cannot install custom actor hook");}
  rooms=std::move(next);bosses=std::move(nextBosses);resources=std::move(nextResources);spriteRom=std::move(nextSpriteRom);atlas=std::move(nextAtlas);mixed=newMixed;streamEnd=stop;active=true;faultRecorded=false;Cv4EnemySetPixelSource(Cv4LevelSpritePixel);enter(start,rooms[start].sx,rooms[start].sy,0);
  snprintf(result,capacity,"%u custom rooms ready",count);return 1;
 }catch(const std::exception&e){snprintf(result,capacity,"%s",e.what());return 0;}
}
extern "C" unsigned Cv4LevelRoom(void){return active?current:~0u;}
extern "C" void Cv4LevelStatus(char*result,size_t capacity){
 unsigned slots=0;for(unsigned at=0x580;at<0xec0;at+=64)if(word(at+16))++slots;
 snprintf(result,capacity,"{\"active\":%s,\"room\":%u,\"camera_x\":%d,\"camera_y\":%d,\"placements\":%zu,\"resource_contexts\":%zu,\"active_native_slots\":%u,\"native_slot_limit\":37,\"boss_encounter\":%d,\"sampled_lines\":%u,\"failed_lines\":%u,\"requested_render_flags\":%u,\"failed_render_flags\":%u}",active?"true":"false",current,cx,cy,active?rooms[current].actors.size():0,resources.size(),slots,encounter,sampledLines,failedLines,requestedFlags,failedFlags);
}
namespace {
const Resource *resourceFor(unsigned type,unsigned variant){
 const Resource*fallback=nullptr;for(const auto&r:resources)if(r.type==type){if(r.variant==variant)return &r;if(!fallback||r.variant==0)fallback=&r;}return fallback;
}
unsigned dataWord(const std::vector<unsigned char>&v,unsigned at){return v[at]|unsigned(v[at+1])<<8;}
unsigned nativeRgba(unsigned c){auto e=[](unsigned n){return (n<<3)|(n>>2);};return 0xff000000u|e(c&31)<<16|e((c>>5)&31)<<8|e((c>>10)&31);}
struct SpritePart {int x,y,size,slot=-1;unsigned attr;};
bool emittedActor(Ppu*p,const unsigned char*ram,unsigned base,const std::array<bool,128>&claimed,std::vector<SpritePart>&parts,unsigned&type,unsigned&variant,unsigned&add){
 auto read=[&](unsigned at){return unsigned(ram[at])|unsigned(ram[at+1])<<8;};
 type=read(base+16);variant=read(base+20);add=read(base+38);unsigned pose=read(base),flip=read(base+4),priority=read(base+2);
 if(!resourceFor(type,variant)||pose<0x8000||spriteRom.size()!=32768)return false;
 unsigned offset=pose&32767,count=spriteRom[offset];if(!count||count>32||offset+1+count*4>spriteRom.size())return false;
 int ax=(int16_t)(read(base+10)-read(0x1c)),ay=(int16_t)((read(base+14)-read(0x1e))&read(0x13de));
 std::vector<SpritePart> expected;
 for(unsigned i=0;i<count;++i){
  unsigned at=offset+1+i*4,raw=spriteRom[at+2]|unsigned(spriteRom[at+3])<<8;int size=raw&0x2000?16:8;
  int rx=(int8_t)spriteRom[at],ry=(int8_t)spriteRom[at+1];unsigned attr=(raw|0x2000)^flip;
  if(priority&0x8000)attr=(attr&0xcfff)|((priority*2&255)<<8);
  expected.push_back({ax+((flip&0x4000)?-rx-size:rx),ay+((flip&0x8000)?-ry-size:ry),size,-1,(attr+add)&65535});
 }
 auto ox=[&](unsigned n){int x=(p->oam[n*2]&255)|(((p->highOam[n>>2]>>((n&3)*2))&1)<<8);return x>255+int(p->extraRightCur)?x-512:x;};
 auto os=[&](unsigned n){return p->highOam[n>>2]&(2u<<((n&3)*2))?16:8;};
 std::vector<std::pair<int,int>> shifts{{0,0}};
 // Some retail AI emits OAM, then moves itself. Recover only an exact,
 // complete emitted metasprite, never a guessed pose or invented visibility.
 const auto&first=expected.front();
 for(unsigned n=0;n<128;++n)if(!claimed[n]&&p->oam[n*2+1]==first.attr&&os(n)==first.size){
  int sx=ox(n)-first.x,sy=int(p->oam[n*2]>>8)-(first.y&255);if(sy>128)sy-=256;if(sy<-128)sy+=256;
  if(std::abs(sx)<=16&&std::abs(sy)<=16&&std::find(shifts.begin(),shifts.end(),std::pair<int,int>{sx,sy})==shifts.end())shifts.push_back({sx,sy});
 }
 int best=100000;bool ambiguous=false;
 for(auto shift:shifts){
  auto trial=expected;auto used=claimed;bool valid=true;unsigned emitted=0;
  for(auto&part:trial){
   part.x+=shift.first;part.y+=shift.second;
   for(unsigned n=0;n<128;++n)if(!used[n]&&ox(n)==part.x&&(p->oam[n*2]>>8)==(unsigned(part.y)&255)&&p->oam[n*2+1]==part.attr&&os(n)==part.size){part.slot=n;used[n]=true;++emitted;break;}
   if(part.slot<0&&part.x+part.size>-int(p->extraLeftCur)&&part.x<256+int(p->extraRightCur)&&part.y+part.size>0&&part.y<224){valid=false;break;}
  }
  if(!valid||!emitted)continue;int score=shift.first*shift.first+shift.second*shift.second;
  if(score<best){best=score;parts=std::move(trial);ambiguous=false;}else if(score==best)ambiguous=true;
  if(!score)return true;
 }
 return best<100000&&!ambiguous;
}
}
extern "C" int Cv4LevelSpritePixel(unsigned type,unsigned variant,unsigned actualAdd,unsigned attr,int size,int x,int y,unsigned*index,unsigned*rgba){
 if(!active||encounter>=0)return 0;const auto*r=resourceFor(type,variant);if(!r)return 0;
 attr=(attr-actualAdd+r->add)&65535;
 if(attr&0x4000)x=size-1-x;if(attr&0x8000)y=size-1-y;
 unsigned tile=((((attr&255)>>4)+(y>>3))<<4)|(((attr&15)+(x>>3))&15);
 unsigned address=(((attr&256)?0x7000:0x6000)+tile*16+(y&7))&0x7fff,bit=7-(x&7);
 uint32_t value=dataWord(r->video,address*2)|uint32_t(dataWord(r->video,((address+8)&0x7fff)*2))<<16;
 *index=(value>>bit&1)|(value>>(bit+7)&2)|(value>>(bit+14)&4)|(value>>(bit+21)&8);
 *rgba=*index?nativeRgba(dataWord(r->video,0x10000+2*(128+((attr>>9)&7)*16+*index))):0;return 1;
}
extern "C" void Cv4LevelSprites(Ppu*p){
 if(!active||word(0x32)!=4||resources.empty())return;
 virtualSprites.clear();spritePixels.clear();std::array<bool,128> claimed{};
 if(p->hostSprites&&p->hostSpriteCount)virtualSprites.assign(p->hostSprites,p->hostSprites+p->hostSpriteCount);
 for(const auto&s:virtualSprites)for(unsigned n=0;n<128;++n)if(s.mask[n>>3]&(1u<<(n&7)))claimed[n]=true;
 if(p->hostObjPixels)for(unsigned n=0;n<128;++n)if(p->hostObjMask[n>>3]&(1u<<(n&7)))claimed[n]=true;
 if(encounter<0)for(unsigned base=0x580;base<0xec0;base+=64){
  unsigned type=0,variant=0,add=0;std::vector<SpritePart> parts;
  if(!emittedActor(p,g_ram,base,claimed,parts,type,variant,add)&&(!havePreviousSpriteState||!emittedActor(p,previousSpriteState.data(),base,claimed,parts,type,variant,add)))continue;
  for(const auto&part:parts){
   int found=part.slot,x=part.x,y=part.y;unsigned size=part.size,attr=part.attr;if(found<0)continue;
   if(x+int(size)<=-int(p->extraLeftCur)||x>=256+int(p->extraRightCur)||y+int(size)<=0||y>=224)continue;
   spritePixels.emplace_back();auto&pixels=spritePixels.back();pixels.fill(0);
   for(unsigned yy=0;yy<size;++yy)for(unsigned xx=0;xx<size;++xx){unsigned index,color;Cv4LevelSpritePixel(type,variant,add,attr,size,xx,yy,&index,&color);pixels[yy*size+xx]=color;}
   PpuHostSprite host{};host.x=x;host.y=y;host.width=host.height=host.stride=size;host.pixels=pixels.data();host.oamSlot=found<0?127:found;
   host.priority=SPRITE_PRIO_TO_PRIO((attr>>12)&3,(attr&0x800)==0)<<8;
   if(found>=0){host.mask[found>>3]|=1u<<(found&7);claimed[found]=true;}virtualSprites.push_back(host);
  }
 }
 std::copy_n(g_ram,previousSpriteState.size(),previousSpriteState.begin());havePreviousSpriteState=encounter<0;
 // Scene scripts are not ordinary actors. Their measured image is a movable
 // decoration until a safe controller adapter exists, never an arbitrary RTL.
 for(const auto&a:rooms[current].actors)if(a.kind==3){const auto*r=resourceFor(a.type,a.variant);if(!r||r->pixels.empty())continue;
  int x=int(a.x)-cx-int(r->ax),y=int(a.y)-cy-int(r->ay);if(x+int(r->w)<0||x>256||y+int(r->h)<0||y>224)continue;
  PpuHostSprite host{};host.x=x;host.y=y;host.width=host.stride=r->w;host.height=r->h;host.pixels=r->pixels.data();host.oamSlot=126;host.priority=SPRITE_PRIO_TO_PRIO(a.flags&0x8000?3:1,1)<<8;virtualSprites.push_back(host);
 }
 if(!virtualSprites.empty()){p->hostSprites=virtualSprites.data();p->hostSpriteCount=virtualSprites.size();}
}
extern "C" void Cv4LevelReset(void){active=false;install=false;mixed=false;rooms.clear();atlas.clear();bosses.clear();resources.clear();spriteRom.clear();virtualSprites.clear();Cv4EnemySetPixelSource(nullptr);encounter=-1;dx=dy=0;}
extern "C" void Cv4LevelBeforeFrame(void){
 if(!active||word(0x32)!=4)return;
 auto*r=&rooms[current];unsigned x=word(0x54a)-dx,y=word(0x54e)-dy;
 if(encounter>=0){
  ++encounterAge;const auto&a=r->actors[encounter];const auto&b=bosses[a.boss];
  if(!word(0x13f4)||word(0x70)==12){enter(current,r->sx,r->sy,0);put(0x70,5);r=&rooms[current];x=word(0x54a);y=word(0x54e);}
  else {
  if((a.options&4)&&word(b.slot+6)<0x8000&&word(b.slot+6)>a.hp)put(b.slot+6,a.hp);
  if(encounterAge>30&&(word(b.slot+0x10)!=b.body||(int16_t)word(b.slot+6)<=0))++deadAge;else deadAge=0;
  if((encounterAge>30&&word(0x70)!=5)||deadAge>180){finishEncounter();r=&rooms[current];x=word(0x54a);y=word(0x54e);}
  }
 }
 if(cooldown)--cooldown;
 else if(encounter<0)for(const auto&d:r->doors)if(x>=d.x&&x<d.x+d.w&&y>=d.y&&y<d.y+d.h&&(d.trigger||word(0x28)&0x0800)){
  enter(d.target,d.tx,d.ty,d.plane);r=&rooms[current];x=d.tx;y=d.ty;break;
 }
 if(encounter<0)for(unsigned i=0;i<r->actors.size();++i){const auto&a=r->actors[i];if(a.kind==2&&!a.spawned&&std::abs(int(a.x)-int(x))<144&&std::abs(int(a.y)-int(y))<192){beginEncounter(i);break;}}
 put(0x70,5);put(0x86,0);if(encounter<0)put(0xb8,0);put(0xae,encounter>=0?1:r->collisionMode);
 // A horizontal SNES map has 32 storage rows but only 28 visible rows.
 // Scrolling its spare bottom rows into view shifts Simon upward and exposes
 // a blank band. Keep both the native camera bounds and compositor aligned.
 put(0x94,streamEnd);put(0x96,streamEnd);put(0xa0,dx);put(0xa2,r->w*8-256+dx);put(0xa4,dy);put(0xa6,verticalCameraLimit(*r)+dy);
 cx=std::clamp(int(x)-128,0,int(r->w*8)-256);cy=std::clamp(int(y)-112,0,verticalCameraLimit(*r));
 if(encounter>=0){const auto&a=r->actors[encounter];cx=std::max(-dx,std::clamp(int(a.x)-128,0,int(r->w*8)-256));cy=std::max(-dy,std::clamp(-dy,0,verticalCameraLimit(*r)));put(0xa0,cx+dx);put(0xa2,cx+dx);put(0xa4,cy+dy);put(0xa6,cy+dy);}
 for(unsigned at:{0x1cu,0x1280u,0x12c0u})put(at,cx+dx);
 for(unsigned at:{0x1eu,0x1298u,0x12d8u})put(at,cy+dy);
 for(int yy=(cy+dy)/8-16;yy<(cy+dy)/8+48;++yy)for(int xx=(cx+dx)/8-16;xx<(cx+dx)/8+48;++xx){
  unsigned px=unsigned(xx*8)&511,py=unsigned(yy*8)&511;
  unsigned index=((px&256)<<2)|((px>>3)&31)|((py&256)<<3)|((py<<2)&0x3e0);
  for(unsigned layer=0;layer<2;++layer)put((layer?0xa000:0x4000)+index*2,cell(*r,r->collision[layer],(xx*8-dx)/8,(yy*8-dy)/8,1));
 }
 if(encounter<0)for(auto&a:r->actors)if(a.kind==1&&a.slot){
  unsigned offset=word(a.slot+0x30);if(offset<256)a.persistence=word(0x1500+offset);
  if(word(a.slot+0x10)!=a.type)a.slot=0;
 }
 if(encounter<0)for(auto&a:r->actors)if(a.kind<2&&a.slot&&word(a.slot+0x10)!=a.type)a.slot=0;
 if(encounter<0)for(auto&a:r->actors)if(a.kind<2&&a.slot&&word(a.slot+0x10)==a.type){
  int xx=word(a.slot+10),yy=word(a.slot+14);
  // Park before the retail offscreen destructor can consume the placement.
  if(xx<cx-16||xx>cx+272||yy<cy-48||yy>cy+272){
   std::copy_n(g_ram+a.slot,64,a.saved.begin());std::fill_n(g_ram+a.slot,64,0);a.x=xx;a.y=yy;a.slot=0;a.spawned=false;a.parked=true;
  }
 }
 std::vector<Actor*> nearby;
 if(encounter<0)for(auto&a:r->actors)if(a.kind<2&&!a.spawned&&int(a.x)>cx-16&&int(a.x)<cx+272&&int(a.y)>cy-48&&int(a.y)<cy+272)nearby.push_back(&a);
 std::stable_sort(nearby.begin(),nearby.end(),[&](const Actor*a,const Actor*b){return std::abs(int(a->x)-int(x))<std::abs(int(b->x)-int(x));});
 for(auto*actor:nearby){auto&a=*actor;
  for(unsigned slot=0x580;slot<0xec0;slot+=0x40)if(!word(slot+0x10)){
   for(auto&previous:r->actors)if(&previous!=&a&&previous.slot==slot)previous.slot=0;
   if(a.parked){std::copy(a.saved.begin(),a.saved.end(),g_ram+slot);a.parked=false;}
   else {std::fill(g_ram+slot,g_ram+slot+0x40,0);put(slot+0x10,a.type);put(slot+0x14,a.variant);put(slot+0xa,a.x);put(slot+0xe,a.y);
    put(slot+2,a.flags&0x8000?0x8018:0);put(slot+6,a.hp);put(slot+0x28,a.hw);put(slot+0x2a,a.hh);put(slot+0x2e,a.trait);put(slot+0x26,a.add);}
   unsigned offset=(slot-0x580)/0x40*2;put(slot+0x30,offset);if(a.kind==1)put(0x1500+offset,a.persistence);
   a.spawned=true;a.slot=slot;break;
  }
 }
}
extern "C" void Cv4LevelBeforeDraw(Ppu*p){
 if(!active||word(0x32)!=4)return;auto&r=rooms[current];
 // The reference renderer cannot provide host RGB sprite ownership or BG
 // samples. A custom project must never silently turn into raw VRAM tiles.
 requestedFlags=p->renderFlags;p->renderFlags|=kPpuRenderFlags_NewRenderer;
 sampledLines=failedLines=0;
 gameplaySubscreen=p->screenEnabled[1];
 if(install){
  unsigned size=r.video.size()-512;memcpy(p->vram,r.video.data(),size);memcpy(p->cgram,r.video.data()+size,512);
  unsigned shadow=word(0x48);if(shadow>=0x2000&&shadow+512<=0x20000)memcpy(g_ram+shadow,r.video.data()+size,512);
  install=false;
 }
 if(encounter>=0&&encounterVideo){const auto&b=bosses[r.actors[encounter].boss];unsigned start=b.type==0x81?0:0xc000,colors=b.type==0x81?0:256;memcpy((unsigned char*)p->vram+start,b.video.data()+start,0x10000-start);memcpy((unsigned char*)p->cgram+colors,b.video.data()+0x10000+colors,512-colors);unsigned shadow=word(0x48);if(shadow>=0x2000&&shadow+512<=0x20000)memcpy(g_ram+shadow+colors,b.video.data()+0x10000+colors,512-colors);if(b.type==0x81){for(unsigned i=0;i<8;++i)p->m7matrix[i]=(int16_t)b.m7[i];p->m7sel=(uint8_t)b.m7[8];}encounterVideo=false;}
 cx=std::clamp(int(word(0x54a))-dx-128,0,int(r.w*8)-256);cy=std::clamp(int(word(0x54e))-dy-112,0,verticalCameraLimit(r));
 if(encounter>=0){const auto&a=r.actors[encounter];cx=std::max(-dx,std::clamp(int(a.x)-128,0,int(r.w*8)-256));cy=std::max(-dy,std::clamp(-dy,0,verticalCameraLimit(r)));}
 for(unsigned at:{0x1cu,0x1280u,0x12c0u})put(at,cx+dx);
 for(unsigned at:{0x1eu,0x1298u,0x12d8u})put(at,cy+dy);
 if(encounter>=0&&r.actors[encounter].type==0x81){std::copy_n(p->cgram,128,mode7Colors.begin());memcpy(p->vram+0x5000,r.video.data()+0xa000,0x1000);p->bgmode=7;p->screenEnabled[0]=0x11;++p->vramWriteCount;return;}
 p->bgmode=(uint8_t)r.mode;p->bgXsc[0]=0x41;p->bgXsc[1]=0x49;
 p->bgTileAdr=(p->bgTileAdr&0xff00)|(mixed?0x22:(r.base[0]>>12)|((r.base[1]>>12)<<4));
 if(mixed)std::fill(p->vram+0x2000,p->vram+0x2010,0);
 for(unsigned layer=0;layer<2;++layer){
  p->hScroll[layer]=cx;p->vScroll[layer]=(cy-1)&1023;
  for(int yy=cy/8;yy<cy/8+32;++yy)for(int xx=cx/8-16;xx<cx/8+48;++xx){
   unsigned col=unsigned(xx)&63,row=unsigned(yy)&31;
   unsigned target=(layer?0x4800:0x4000)+(col>>5)*1024+row*32+(col&31);
   p->vram[target]=mixed?0:(unsigned short)cell(r,r.maps[layer],xx,yy,0x800);
  }
 }
 ++p->vramWriteCount;
}

/* Mixed backgrounds own RGB555 texels rather than a shared SNES palette.
 * The transparent native BG1/2 leave real OBJ/HUD priority candidates intact.
 * Resolve against those candidates after raster windows/math flags exist;
 * source palette changes can never recolour another section's artwork. */
extern "C" void Cv4LevelTrack(Ppu*p){if(active&&mixed&&word(0x32)==4)p->hdTracking=true;}
extern "C" void Cv4LevelBeforeLine(Ppu*p,int line){
 if(!active||word(0x32)!=4)return;
 bool mode7=encounter>=0&&rooms[current].actors[encounter].type==0x81;
 if(mode7&&line<32){const auto&video=rooms[current].video;for(unsigned n=0;n<128;++n)p->cgram[n]=dataWord(video,0x10000+n*2);}
 if(line<32){
  p->bgmode=9;p->bgTileAdr=(p->bgTileAdr&255)|0x5500;p->bgXsc[2]=0x59;p->hScroll[2]=0;p->vScroll[2]=1023;
  p->screenEnabled[0]=0x14;p->screenEnabled[1]=0;p->windowsel=0;return;
 }
 // Boss IRQ/HDMA may change its body, never the project's layer visibility.
 p->screenEnabled[0]=0x13;p->windowsel=0;
 if(line==32)p->screenEnabled[1]=gameplaySubscreen;
 if(mode7){if(line==32)std::copy(mode7Colors.begin(),mode7Colors.end(),p->cgram);p->cgram[0]=(unsigned short)dataWord(rooms[current].video,0x10000);p->bgmode=7;return;}
 p->cgram[0]=(unsigned short)dataWord(rooms[current].video,0x10000);
 if(mixed){p->bgmode=(uint8_t)rooms[current].mode;p->bgTileAdr=(p->bgTileAdr&0xff00)|0x22;p->bgXsc[0]=0x41;p->bgXsc[1]=0x49;for(unsigned i=0;i<2;++i){p->hScroll[i]=cx;p->vScroll[i]=(cy-1)&1023;}}
}
extern "C" void Cv4LevelRenderLine(Ppu*p,int line){
 if(!active||!mixed||word(0x32)!=4||line<33||line>224||PPU_forcedBlank(p)||!p->renderBuffer)return;
 const auto&r=rooms[current];auto*row=(uint32_t*)(p->renderBuffer+(line-1)*p->renderPitch);
 bool mode7=encounter>=0&&r.actors[encounter].type==0x81;
 std::array<PpuLayerSample,kPpuBufWidth> body{};
 bool bodyAvailable=!mode7||PpuGetLayerScanline(p,line,0,body.data(),body.size());
 if(!bodyAvailable){
  ++failedLines;failedFlags=p->renderFlags;
  if(!faultRecorded){
   std::ofstream f("level_render_fault.json");f<<"{\"line\":"<<line<<",\"flags\":"<<p->renderFlags<<",\"tracking\":"<<p->hdTracking<<",\"mode\":"<<unsigned(p->bgmode)<<",\"setini\":"<<unsigned(p->setini)<<",\"color_control\":"<<unsigned(p->cgwsel)<<",\"line_enhancer\":"<<(p->widescreenLineEnhancer?1:0)<<",\"camera\":["<<cx<<","<<cy<<"]}\n";faultRecorded=true;
  }
 }else ++sampledLines;
 for(int x=-int(p->extraLeftCur);x<256+int(p->extraRightCur);++x){
  unsigned i=x+kPpuExtraLeftRight;
  // Only native OBJ belongs in the custom playfield. The guest BG buffers
  // can contain arbitrary CHR/HUD fragments after another actor's DMA; they
  // must never occlude the immutable project atlas, even in transparent air.
  unsigned depth[2]={0x500,0x500},colors[2]={p->cgram[0],p->cgram[0]};
  for(unsigned sub=0;sub<2;++sub){
   unsigned obj=p->objBuffer.data[i];
   if(IS_SCREEN_ENABLED(p,sub,4)&&(obj&255)){depth[sub]=obj;colors[sub]=PpuPixelColor(p,(uint16_t)obj,i);}
   if(mode7&&bodyAvailable&&(body[i].screens&(1u<<sub))&&(body[i].pixel&255)){
    unsigned z=SPRITE_PRIO_TO_PRIO(r.actors[encounter].flags&0x8000?3:2,1)<<8;
    if(z>depth[sub]){depth[sub]=z;colors[sub]=p->cgram[body[i].pixel&255];}
   }
  }
  int px=x+cx,py=line-1+cy;
  if(px>=0&&py>=0&&px<int(r.w*8)&&py<int(r.h*8))for(unsigned layer=0;layer<2;++layer){
   unsigned value=r.maps[layer][(py/8)*r.w+px/8],color=atlas[value&0x7fffffff][(py%8)*8+px%8];
   if(!(color&0x8000))continue;
   unsigned z=(value&0x80000000?(layer?0xb100:0xc000):(layer?0x7100:0x8000))|1;
   for(unsigned sub=0;sub<2;++sub)if(IS_SCREEN_ENABLED(p,sub,layer)&&z>depth[sub]){depth[sub]=z;colors[sub]=color&0x7fff;}
  }
  unsigned flags=p->hdColorFlags[i],layer=(depth[0]>>8)&15;
  bool math=(flags&2)&&(PPU_mathEnabled(p)&(1u<<layer)),half=math&&PPU_halfColor(p);
  unsigned other=p->fixedColor;
  if(math&&PPU_addSubscreen(p)){if(depth[1]&255)other=colors[1];else half=false;}
  uint32_t output=0;
  for(unsigned channel=0;channel<3;++channel){
   int value=flags&1?(colors[0]>>(channel*5))&31:0;
   if(math){int second=(other>>(channel*5))&31;value=std::max(0,value+(PPU_subtractColor(p)?-second:second));}
   unsigned component=half?p->brightnessMultHalf[value]:p->brightnessMult[std::min(31,value)];
   output|=component<<(16-channel*8);
  }
  row[x+p->extraLeftRight]=output;
 }
}
