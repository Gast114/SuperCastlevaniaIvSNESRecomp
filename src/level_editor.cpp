/* Opt-in custom level playtests. No changes without an explicit project load. */
#include "level_editor.h"
extern "C" {
#include "snes/ppu.h"
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
struct Actor {unsigned type,variant,x,y,flags,hw,hh,hp,trait,add;bool spawned=false;};
struct Door {unsigned x,y,w,h,target,tx,ty,trigger,plane;};
struct Room {unsigned w,h,tileset,sx,sy,base[2],mode,collisionMode;std::vector<unsigned char> video;std::vector<uint32_t> maps[2];std::vector<unsigned short> collision[2];std::vector<Actor> actors;std::vector<Door> doors;};
std::vector<Room> rooms;unsigned current=0;bool active=false,install=false;unsigned cooldown=0;int cx=0,cy=0;
std::vector<std::array<unsigned short,64>> atlas;bool mixed=false;
unsigned streamEnd=0;
unsigned word(unsigned at){return g_ram[at]|unsigned(g_ram[at+1])<<8;}
void put(unsigned at,unsigned value){g_ram[at]=value;g_ram[at+1]=value>>8;}
template<class T> unsigned cell(const Room&r,const std::vector<T>&map,int x,int y,unsigned outside){return x>=0&&y>=0&&x<int(r.w)&&y<int(r.h)?map[y*r.w+x]:outside;}
void enter(unsigned index,unsigned x,unsigned y,unsigned plane){
 current=index;auto&r=rooms[current];install=true;cooldown=30;
 std::fill(g_ram+0x580,g_ram+0xec0,0);std::fill(g_ram+0x1200,g_ram+0x1280,0);
 for(auto&a:r.actors)a.spawned=false;
 put(0x54a,x);put(0x54e,y);put(0x552,0);put(0x542,plane?0:0x8018);
 for(unsigned at=0x558;at<=0x55e;at+=2)put(at,0);
 put(0x13f4,16);put(0xbc,90);put(0xb8,0);put(0x94,streamEnd);put(0x96,streamEnd);
}
}
extern "C" int Cv4LevelLoad(const char *path,char *result,size_t capacity){
 try{
  if(!strcmp(path,"off")){Cv4LevelReset();snprintf(result,capacity,"Custom level disabled");return 1;}
  std::ifstream f(path,std::ios::binary);if(!f)throw std::runtime_error("Cannot open custom level");
  f.seekg(0,std::ios::end);auto size=f.tellg();if(size<14||size>512*1024*1024)throw std::runtime_error("Invalid custom level size");
  f.seekg(0);std::vector<unsigned char> data((size_t)size);if(!f.read((char*)data.data(),data.size()))throw std::runtime_error("Cannot read custom level");
  size_t at=0;auto read=[&](){if(at+2>data.size())throw std::runtime_error("Truncated custom level");unsigned v=data[at]|unsigned(data[at+1])<<8;at+=2;return v;};
  bool newMixed=!memcmp(data.data(),"CV4LVL2\0",8);
  if(!newMixed&&memcmp(data.data(),"CV4LVL1\0",8))throw std::runtime_error("Unknown custom level format");at=8;
  auto read32=[&](){unsigned lo=read();return lo|(read()<<16);};
  unsigned count=read(),start=read(),stop=read();if(!count||count>64||start>=count||stop<0x8000)throw std::runtime_error("Invalid custom room count");
  std::vector<Room> next;
  std::vector<std::array<unsigned short,64>> nextAtlas;
  if(newMixed){
   unsigned tiles=read32();if(!tiles||tiles>1048576||tiles>(data.size()-at)/128)throw std::runtime_error("Invalid custom graphics atlas");
   nextAtlas.resize(tiles);for(auto&tile:nextAtlas)for(auto&pixel:tile)pixel=(unsigned short)read();
  }
  for(unsigned n=0;n<count;++n){
   Room r;r.w=read();r.h=read();r.tileset=read();r.sx=read();r.sy=read();r.base[0]=read();r.base[1]=read();r.mode=read();r.collisionMode=read();unsigned actors=read(),doors=read();
   if(r.w<32||r.w>1024||r.h<28||r.h>512||r.w*r.h>262144||r.sx>=r.w*8||r.sy>=r.h*8||r.tileset>=68||r.base[0]>0x3000||r.base[1]>0x3000||(r.mode&7)!=1||r.collisionMode>3||actors>128||doors>64)
    throw std::runtime_error("Unsupported custom room geometry or graphics");
   if(at+0xd600>data.size())throw std::runtime_error("Missing room graphics");
   r.video.assign(data.begin()+at,data.begin()+at+0xd600);at+=0xd600;
   for(int layer=0;layer<2;++layer)for(unsigned i=0;i<r.w*r.h;++i){
    unsigned value=newMixed?read32():read();
    if(newMixed&&(value&0x7fffffff)>=nextAtlas.size())throw std::runtime_error("Custom tile outside graphics atlas");
    r.maps[layer].push_back(value);
   }
   for(int layer=0;layer<2;++layer)for(unsigned i=0;i<r.w*r.h;++i)r.collision[layer].push_back((unsigned short)read());
   for(unsigned i=0;i<actors;++i){Actor a;a.type=read();a.variant=read();a.x=read();a.y=read();a.flags=read();a.hw=read();a.hh=read();a.hp=read();a.trait=read();a.add=read();
    if(!a.type||a.type>=128||a.variant>255||a.x>=r.w*8||a.y>=r.h*8||a.add>0x1ff)throw std::runtime_error("Invalid custom monster");r.actors.push_back(a);}
   for(unsigned i=0;i<doors;++i){Door d;d.x=read();d.y=read();d.w=read();d.h=read();d.target=read();d.tx=read();d.ty=read();d.trigger=read();d.plane=read();
    if(d.target>=count||d.w<8||d.w>256||d.h<8||d.h>256||d.x>=r.w*8||d.y>=r.h*8||d.trigger>1||d.plane>1)throw std::runtime_error("Invalid custom exit");r.doors.push_back(d);}
   next.push_back(std::move(r));
  }
  for(const auto&r:next)for(const auto&d:r.doors)if(d.tx>=next[d.target].w*8||d.ty>=next[d.target].h*8)throw std::runtime_error("Exit target outside room");
  if(at!=data.size())throw std::runtime_error("Unexpected custom level data");
  rooms=std::move(next);atlas=std::move(nextAtlas);mixed=newMixed;streamEnd=stop;active=true;enter(start,rooms[start].sx,rooms[start].sy,0);
  snprintf(result,capacity,"%u custom rooms ready",count);return 1;
 }catch(const std::exception&e){snprintf(result,capacity,"%s",e.what());return 0;}
}
extern "C" unsigned Cv4LevelRoom(void){return active?current:~0u;}
extern "C" void Cv4LevelReset(void){active=false;install=false;mixed=false;rooms.clear();atlas.clear();}
extern "C" void Cv4LevelBeforeFrame(void){
 if(!active||word(0x32)!=4)return;
 auto*r=&rooms[current];unsigned x=word(0x54a),y=word(0x54e);
 if(cooldown)--cooldown;
 else for(const auto&d:r->doors)if(x>=d.x&&x<d.x+d.w&&y>=d.y&&y<d.y+d.h&&(d.trigger||word(0x28)&0x0800)){
  enter(d.target,d.tx,d.ty,d.plane);r=&rooms[current];x=d.tx;y=d.ty;break;
 }
 put(0x70,5);put(0x86,0);put(0xb8,0);put(0xae,r->collisionMode);
 put(0x94,streamEnd);put(0x96,streamEnd);put(0xa0,0);put(0xa2,r->w*8-256);put(0xa4,0);put(0xa6,r->h*8-224);
 cx=std::clamp(int(x)-128,0,int(r->w*8)-256);cy=std::clamp(int(y)-112,0,int(r->h*8)-224);
 for(unsigned at:{0x1cu,0x1280u,0x12c0u})put(at,cx);
 for(unsigned at:{0x1eu,0x1298u,0x12d8u})put(at,cy);
 for(int yy=cy/8-16;yy<cy/8+48;++yy)for(int xx=cx/8-16;xx<cx/8+48;++xx){
  unsigned px=unsigned(xx*8)&511,py=unsigned(yy*8)&511;
  unsigned index=((px&256)<<2)|((px>>3)&31)|((py&256)<<3)|((py<<2)&0x3e0);
  for(unsigned layer=0;layer<2;++layer)put((layer?0xa000:0x4000)+index*2,cell(*r,r->collision[layer],xx,yy,1));
 }
 for(auto&a:r->actors)if(!a.spawned&&int(a.x)>cx-128&&int(a.x)<cx+384&&int(a.y)>cy-128&&int(a.y)<cy+352){
  for(unsigned slot=0x580;slot<0xec0;slot+=0x40)if(!word(slot+0x10)){
   std::fill(g_ram+slot,g_ram+slot+0x40,0);put(slot+0x10,a.type);put(slot+0x14,a.variant);put(slot+0xa,a.x);put(slot+0xe,a.y);
   put(slot+2,a.flags&0x8000?0x8018:0);put(slot+6,a.hp);put(slot+0x28,a.hw);put(slot+0x2a,a.hh);put(slot+0x2e,a.trait);put(slot+0x26,a.add);a.spawned=true;break;
  }
 }
}
extern "C" void Cv4LevelBeforeDraw(Ppu*p){
 if(!active||word(0x32)!=4)return;auto&r=rooms[current];
 if(install){
  memcpy(p->vram,r.video.data(),0xd400);memcpy(p->cgram,r.video.data()+0xd400,512);
  unsigned shadow=word(0x48);if(shadow>=0x2000&&shadow+512<=0x20000)memcpy(g_ram+shadow,r.video.data()+0xd400,512);
  install=false;
 }
 cx=std::clamp(int(word(0x54a))-128,0,int(r.w*8)-256);cy=std::clamp(int(word(0x54e))-112,0,int(r.h*8)-224);
 for(unsigned at:{0x1cu,0x1280u,0x12c0u})put(at,cx);
 for(unsigned at:{0x1eu,0x1298u,0x12d8u})put(at,cy);
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
