/* Standalone synthetic presentation test: no copyrighted ROM or guest code. */
#define STB_IMAGE_IMPLEMENTATION
#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "third_party/stb_image.h"
#include "third_party/stb_image_write.h"
#include "enemy_pack.h"
#include "snes/ppu.h"
#include <array>
#include <cstdio>
#include <cstring>
#include <memory>
#include <vector>
extern "C" int Cv4HdEnabled(void){return 1;}
extern "C" unsigned Cv4HdLayerMask(void){return 31;}
static void set(std::vector<uint8_t>&r,unsigned a,unsigned v){r[a]=v;r[a+1]=v>>8;}
int main(int argc,char**argv){
 std::vector<uint8_t> rom(0x30000),ram(0x20000);auto owner=std::make_unique<Ppu>();Ppu*p=owner.get();memset(p,0,sizeof(*p));
 auto check=[](bool value,const char*label){if(!value){fprintf(stderr,"FAIL: %s\n",label);exit(1);}printf("PASS: %s\n",label);};
 rom[0x20000]=2;rom[0x20001]=0xf8;rom[0x20002]=0xf8;rom[0x20003]=0;rom[0x20004]=0x20;
 rom[0x20005]=8;rom[0x20006]=0xf8;rom[0x20007]=2;rom[0x20008]=0x20;
 ram[0x32]=4;set(ram,0x13de,0xffff);set(ram,0x580,0x8000);set(ram,0x58a,80);set(ram,0x58e,100);set(ram,0x590,0x11);
 p->renderFlags=kPpuRenderFlags_NewRenderer;p->extraRightCur=p->extraLeftCur=48;
 p->oam[20]=72|(92<<8);p->oam[21]=0x2000;p->oam[22]=88|(92<<8);p->oam[23]=0x2002;p->highOam[2]=0xa0;
 p->cgram[129]=31;for(int tile=0;tile<20;++tile)for(int y=0;y<8;++y)p->vram[tile*16+y]=0xff;
 Cv4EnemyInit(rom.data(),(unsigned)rom.size());if(argc>1)check(Cv4EnemyCommand("pack diagnostic"),"load arbitrary-resolution enemy pack");
 Cv4EnemyBegin(p,ram.data());
 if(argc==1){check(Cv4EnemyHdCount()==0,"native fallback while automatically capturing reference");return 0;}
 check(Cv4EnemyHdCount()==1,"complete actor matched");auto f=Cv4EnemyHd(0);check(f&&f->width==387&&f->height==387&&f->displayWidth==96,"4.03125x source kept at original resolution");check(f->x==32&&f->y==52,"native anchor and position");check(p->hostSprites[0].mask[1]==12,"only matching OAM slots 10 and 11 replaced");
 set(ram,0x584,0x4000);p->oam[20]=72|(92<<8);p->oam[21]=0x6000;p->oam[22]=56|(92<<8);p->oam[23]=0x6002;
 Cv4EnemyBegin(p,ram.data());check(Cv4EnemyHdCount()==1&&Cv4EnemyHd(0)->flip==1,"one reference recognizes complete mirrored actor");
 p->oam[23]^=1;Cv4EnemyBegin(p,ram.data());check(Cv4EnemyHdCount()==0,"unmatched sprite part preserves all native parts");
 Cv4EnemyCommand("off");Cv4EnemyBegin(p,ram.data());check(Cv4EnemyHdCount()==0,"disabling enemy pack restores original rendering");
 set(ram,0x584,0);p->oam[20]=72|(92<<8);p->oam[21]=0x2000;p->oam[22]=88|(92<<8);p->oam[23]=0x2002;
 check(Cv4EnemyCommand("pack component"),"load a single native component override");
 Cv4EnemyBegin(p,ram.data());
 check(Cv4EnemyHdCount()==1&&p->hostSprites[0].mask[1]==4,"component replaces only its own OAM slot; neighbouring native part stays intact");
 return 0;
}
