/* Opt-in custom level playtests. No changes without an explicit project load. */
#include "level_editor.h"
extern "C" {
#include "snes/ppu.h"
#include "snes/interp_bridge.h"
#include "cpu_state.h"
}
#include <algorithm>
#include <array>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <vector>
extern "C" unsigned char g_ram[0x20000];
namespace {
struct Actor {unsigned type,variant,x,y,flags,hw,hh,hp,trait,add;unsigned damage=65535,kind=0,boss=0,options=0;bool spawned=false;unsigned slot=0;};
struct Door {unsigned x,y,w,h,target,tx,ty,trigger,plane;};
struct Room {unsigned w,h,tileset,sx,sy,base[2],mode,collisionMode;std::vector<unsigned char> video;std::vector<uint32_t> maps[2];std::vector<unsigned short> collision[2];std::vector<Actor> actors;std::vector<Door> doors;};
struct Boss {unsigned type,x,y,slot,body;std::vector<unsigned char> states[2],video,raster;std::array<unsigned short,9> m7{};};
std::vector<Boss> bosses;int encounter=-1,dx=0,dy=0;unsigned encounterAge=0,deadAge=0;bool encounterVideo=false;
std::array<unsigned char,0x940> suspended;
std::array<unsigned char,0x2b0> suspendedExtras;
std::array<unsigned char,256> suspendedRaster;
std::array<unsigned char,256> suspendedPersistence;
unsigned suspendedBossEffect=0;
constexpr unsigned stateSize=2+0x940+0x80+0x30+0x200;
std::vector<Room> rooms;unsigned current=0;bool active=false,install=false;unsigned cooldown=0;int cx=0,cy=0;
std::vector<std::array<unsigned short,64>> atlas;bool mixed=false;
unsigned streamEnd=0;
bool damageHookInstalled=false;
unsigned word(unsigned at){return g_ram[at]|unsigned(g_ram[at+1])<<8;}
void put(unsigned at,unsigned value){g_ram[at]=value;g_ram[at+1]=value>>8;}
void contactDamage(CpuState*cpu,uint32_t){
 if(!active||current>=rooms.size())return;
 if(encounter>=0){const auto&a=rooms[current].actors[encounter];if(a.damage!=65535){cpu->A=(uint16_t)a.damage;return;}}
 for(const auto&a:rooms[current].actors)if(a.slot==cpu->X&&word(a.slot+0x10)==a.type&&a.damage!=65535){cpu->A=(uint16_t)a.damage;break;}
}
template<class T> unsigned cell(const Room&r,const std::vector<T>&map,int x,int y,unsigned outside){return x>=0&&y>=0&&x<int(r.w)&&y<int(r.h)?map[y*r.w+x]:outside;}
void enter(unsigned index,unsigned x,unsigned y,unsigned plane){
 if(encounter>=0){put(0xef0,suspendedBossEffect);std::copy(suspendedPersistence.begin(),suspendedPersistence.end(),g_ram+0x1500);std::copy(suspendedRaster.begin(),suspendedRaster.end(),g_ram+0x100);unsigned cursor=0;for(auto span:{std::pair<unsigned,unsigned>{0x1200,0x80},{0x13c0,0x30},{0x1e00,0x200}}){memcpy(g_ram+span.first,suspendedExtras.data()+cursor,span.second);cursor+=span.second;}}
 current=index;auto&r=rooms[current];install=true;cooldown=30;encounter=-1;dx=dy=0;
 std::fill(g_ram+0x580,g_ram+0xec0,0);std::fill(g_ram+0x1200,g_ram+0x1280,0);
 for(auto&a:r.actors){a.spawned=false;a.slot=0;}
 put(0x54a,x);put(0x54e,y);put(0x552,0);put(0x542,plane?0:0x8018);
 for(unsigned at=0x558;at<=0x55e;at+=2)put(at,0);
 put(0x13f4,16);put(0xbc,90);put(0xb8,0);put(0x94,streamEnd);put(0x96,streamEnd);
}
void beginEncounter(unsigned index){
 auto&r=rooms[current];auto&a=r.actors[index];const auto&b=bosses[a.boss];
 std::copy(g_ram+0x580,g_ram+0xec0,suspended.begin());
 std::copy(g_ram+0x100,g_ram+0x200,suspendedRaster.begin());memcpy(g_ram+0x100,b.raster.data(),256);
 std::copy(g_ram+0x1500,g_ram+0x1600,suspendedPersistence.begin());
 suspendedBossEffect=word(0xef0);if(b.type==0x8d)put(0xef0,0x200); // Native final-boss initializer $03:C089.
 unsigned cursor=0;for(auto span:{std::pair<unsigned,unsigned>{0x1200,0x80},{0x13c0,0x30},{0x1e00,0x200}}){std::copy(g_ram+span.first,g_ram+span.first+span.second,suspendedExtras.begin()+cursor);cursor+=span.second;}
 const auto&state=b.states[a.options&1?0:1];put(0xb8,state[0]|unsigned(state[1])<<8);cursor=2;
 for(auto span:{std::pair<unsigned,unsigned>{0x580,0x940},{0x1200,0x80},{0x13c0,0x30},{0x1e00,0x200}}){memcpy(g_ram+span.first,state.data()+cursor,span.second);cursor+=span.second;}
 dx=int(b.x)-int(a.x);dy=int(b.y)-int(a.y);put(0x54a,std::max(24,int(word(0x54a))+dx));put(0x54e,word(0x54e)+dy);
 encounter=(int)index;a.spawned=true;a.slot=b.slot;encounterAge=deadAge=0;encounterVideo=true;
 if(a.options&4)put(b.slot+6,a.hp);if(a.options&8)put(b.slot+0x28,a.hw);if(a.options&16)put(b.slot+0x2a,a.hh);
}
void finishEncounter(){
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
   if(r.w<32||r.w>1024||r.h<28||r.h>512||r.w*r.h>262144||r.sx>=r.w*8||r.sy>=r.h*8||r.tileset>=68||r.base[0]>0x3000||r.base[1]>0x3000||(r.mode&7)!=1||r.collisionMode>3||actors>128||doors>64)
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
    if(extended){a.damage=read();a.kind=read();a.boss=read();a.options=read();if((a.damage>255&&a.damage!=65535)||a.kind>2)throw std::runtime_error("Invalid custom actor values");}
    if(!a.type||a.type>0x8d||a.variant>255||a.x>=r.w*8||a.y>=r.h*8||a.add>0x1ff||a.hw>255||a.hh>255||a.hp>32767||a.options>31||(a.type>=128&&(a.kind!=2||a.boss>=nextBosses.size()||nextBosses[a.boss].type!=a.type)))throw std::runtime_error("Invalid custom monster");r.actors.push_back(a);}
   for(unsigned i=0;i<doors;++i){Door d;d.x=read();d.y=read();d.w=read();d.h=read();d.target=read();d.tx=read();d.ty=read();d.trigger=read();d.plane=read();
    if(d.target>=count||d.w<8||d.w>256||d.h<8||d.h>256||d.x>=r.w*8||d.y>=r.h*8||d.trigger>1||d.plane>1)throw std::runtime_error("Invalid custom exit");r.doors.push_back(d);}
   next.push_back(std::move(r));
  }
  for(const auto&r:next)for(const auto&d:r.doors)if(d.tx>=next[d.target].w*8||d.ty>=next[d.target].h*8)throw std::runtime_error("Exit target outside room");
  if(at!=data.size())throw std::runtime_error("Unexpected custom level data");
  if(!damageHookInstalled){damageHookInstalled=interp_bridge_add_pre_opcode_hook(0x00dd12,contactDamage);if(!damageHookInstalled)throw std::runtime_error("Cannot install custom actor hook");}
  rooms=std::move(next);bosses=std::move(nextBosses);atlas=std::move(nextAtlas);mixed=newMixed;streamEnd=stop;active=true;enter(start,rooms[start].sx,rooms[start].sy,0);
  snprintf(result,capacity,"%u custom rooms ready",count);return 1;
 }catch(const std::exception&e){snprintf(result,capacity,"%s",e.what());return 0;}
}
extern "C" unsigned Cv4LevelRoom(void){return active?current:~0u;}
extern "C" void Cv4LevelReset(void){active=false;install=false;mixed=false;rooms.clear();atlas.clear();bosses.clear();encounter=-1;dx=dy=0;}
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
 put(0x94,streamEnd);put(0x96,streamEnd);put(0xa0,dx);put(0xa2,r->w*8-256+dx);put(0xa4,dy);put(0xa6,r->h*8-224+dy);
 cx=std::clamp(int(x)-128,0,int(r->w*8)-256);cy=std::clamp(int(y)-112,0,int(r->h*8)-224);
 if(encounter>=0){const auto&a=r->actors[encounter];cx=std::max(-dx,std::clamp(int(a.x)-128,0,int(r->w*8)-256));cy=std::max(-dy,std::clamp(int(a.y)-96,0,int(r->h*8)-224));put(0xa0,cx+dx);put(0xa2,cx+dx);put(0xa4,cy+dy);put(0xa6,cy+dy);}
 for(unsigned at:{0x1cu,0x1280u,0x12c0u})put(at,cx+dx);
 for(unsigned at:{0x1eu,0x1298u,0x12d8u})put(at,cy+dy);
 for(int yy=(cy+dy)/8-16;yy<(cy+dy)/8+48;++yy)for(int xx=(cx+dx)/8-16;xx<(cx+dx)/8+48;++xx){
  unsigned px=unsigned(xx*8)&511,py=unsigned(yy*8)&511;
  unsigned index=((px&256)<<2)|((px>>3)&31)|((py&256)<<3)|((py<<2)&0x3e0);
  for(unsigned layer=0;layer<2;++layer)put((layer?0xa000:0x4000)+index*2,cell(*r,r->collision[layer],(xx*8-dx)/8,(yy*8-dy)/8,1));
 }
 if(encounter<0)for(auto&a:r->actors)if(a.kind!=2&&!a.spawned&&int(a.x)>cx-128&&int(a.x)<cx+384&&int(a.y)>cy-128&&int(a.y)<cy+352){
  for(unsigned slot=0x580;slot<0xec0;slot+=0x40)if(!word(slot+0x10)){
   std::fill(g_ram+slot,g_ram+slot+0x40,0);put(slot+0x10,a.type);put(slot+0x14,a.variant);put(slot+0xa,a.x);put(slot+0xe,a.y);
   put(slot+2,a.flags&0x8000?0x8018:0);put(slot+6,a.hp);put(slot+0x28,a.hw);put(slot+0x2a,a.hh);put(slot+0x2e,a.trait);put(slot+0x26,a.add);put(slot+0x30,unsigned(&a-r->actors.data())*2);a.spawned=true;a.slot=slot;break;
  }
 }
}
extern "C" void Cv4LevelBeforeDraw(Ppu*p){
 if(!active||word(0x32)!=4)return;auto&r=rooms[current];
 if(install){
  unsigned size=r.video.size()-512;memcpy(p->vram,r.video.data(),size);memcpy(p->cgram,r.video.data()+size,512);
  unsigned shadow=word(0x48);if(shadow>=0x2000&&shadow+512<=0x20000)memcpy(g_ram+shadow,r.video.data()+size,512);
  install=false;
 }
 if(encounter>=0&&encounterVideo){const auto&b=bosses[r.actors[encounter].boss];unsigned start=b.type==0x81?0:0xc000,colors=b.type==0x81?0:256;memcpy((unsigned char*)p->vram+start,b.video.data()+start,0x10000-start);memcpy((unsigned char*)p->cgram+colors,b.video.data()+0x10000+colors,512-colors);unsigned shadow=word(0x48);if(shadow>=0x2000&&shadow+512<=0x20000)memcpy(g_ram+shadow+colors,b.video.data()+0x10000+colors,512-colors);if(b.type==0x81){for(unsigned i=0;i<8;++i)p->m7matrix[i]=(int16_t)b.m7[i];p->m7sel=(uint8_t)b.m7[8];}encounterVideo=false;}
 cx=std::clamp(int(word(0x54a))-dx-128,0,int(r.w*8)-256);cy=std::clamp(int(word(0x54e))-dy-112,0,int(r.h*8)-224);
 if(encounter>=0){const auto&a=r.actors[encounter];cx=std::max(-dx,std::clamp(int(a.x)-128,0,int(r.w*8)-256));cy=std::max(-dy,std::clamp(int(a.y)-96,0,int(r.h*8)-224));}
 for(unsigned at:{0x1cu,0x1280u,0x12c0u})put(at,cx+dx);
 for(unsigned at:{0x1eu,0x1298u,0x12d8u})put(at,cy+dy);
 if(encounter>=0&&r.actors[encounter].type==0x81){p->bgmode=7;p->screenEnabled[0]=0x11;++p->vramWriteCount;return;}
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
 if(!active||encounter<0||word(0x32)!=4||line<32)return;
 if(rooms[current].actors[encounter].type==0x81){p->bgmode=7;p->screenEnabled[0]|=0x11;return;}
 if(mixed){p->bgmode=(uint8_t)rooms[current].mode;p->bgTileAdr=(p->bgTileAdr&0xff00)|0x22;p->bgXsc[0]=0x41;p->bgXsc[1]=0x49;for(unsigned i=0;i<2;++i){p->hScroll[i]=cx;p->vScroll[i]=(cy-1)&1023;}}
}
extern "C" void Cv4LevelRenderLine(Ppu*p,int line){
 if(!active||!mixed||word(0x32)!=4||line<1||line>224||PPU_forcedBlank(p)||!p->renderBuffer)return;
 std::array<PpuLayerSample,kPpuBufWidth> samples[2];
 if(!PpuGetLayerScanline(p,line,0,samples[0].data(),samples[0].size())||!PpuGetLayerScanline(p,line,1,samples[1].data(),samples[1].size()))return;
 const auto&r=rooms[current];auto*row=(uint32_t*)(p->renderBuffer+(line-1)*p->renderPitch);
 for(int x=-int(p->extraLeftCur);x<256+int(p->extraRightCur);++x){
  unsigned i=x+kPpuExtraLeftRight;unsigned depth[2]={p->bgBuffers[0].data[i],p->bgBuffers[1].data[i]};
  unsigned colors[2]={PpuPixelColor(p,(uint16_t)depth[0],i),PpuPixelColor(p,(uint16_t)depth[1],i)};bool changed=false;
  int px=x+cx,py=line-1+cy;
  if(px>=0&&py>=0&&px<int(r.w*8)&&py<int(r.h*8))for(unsigned layer=0;layer<2;++layer){
   unsigned value=r.maps[layer][(py/8)*r.w+px/8],color=atlas[value&0x7fffffff][(py%8)*8+px%8];
   if(!(color&0x8000))continue;
   unsigned z=(value&0x80000000?(layer?0xb100:0xc000):(layer?0x7100:0x8000))|1;
   for(unsigned sub=0;sub<2;++sub)if((samples[layer][i].screens&(1u<<sub))&&z>depth[sub]){depth[sub]=z;colors[sub]=color&0x7fff;changed=true;}
  }
  if(!changed)continue;
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
