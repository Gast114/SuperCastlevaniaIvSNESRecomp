/* Independent black-box coverage of the expanded workshop renderer. */
#define STB_IMAGE_IMPLEMENTATION
#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "third_party/stb_image.h"
#include "third_party/stb_image_write.h"
#include "enemy_pack.h"
#include "snes/ppu.h"
#include <cstdio>
#include <cstring>
#include <memory>
#include <vector>
extern "C" int Cv4HdEnabled(void){return 1;}
extern "C" unsigned Cv4HdLayerMask(void){return 31;}
static void put(std::vector<uint8_t>&r,unsigned a,unsigned v){r[a]=v;r[a+1]=v>>8;}
int main(int argc,char**argv){
 auto owner=std::make_unique<Ppu>();auto*p=owner.get();memset(p,0,sizeof(*p));
 std::vector<uint8_t>rom(0x30000),ram(0x20000);
 auto check=[](bool v,const char*s){if(!v){fprintf(stderr,"FAIL: %s\n",s);exit(1);}printf("PASS: %s\n",s);};
 rom[0x20000]=2;rom[0x20001]=(uint8_t)-80;rom[0x20002]=(uint8_t)-8;rom[0x20004]=0x20;
 rom[0x20005]=64;rom[0x20006]=(uint8_t)-8;rom[0x20007]=2;rom[0x20008]=0x20;
 ram[0x32]=4;put(ram,0x13de,0xffff);put(ram,0x580,0x8000);put(ram,0x58a,128);put(ram,0x58e,128);put(ram,0x590,0x12);
 p->renderFlags=kPpuRenderFlags_NewRenderer;p->oam[20]=48|(120<<8);p->oam[21]=0x2000;p->oam[22]=192|(120<<8);p->oam[23]=0x2002;p->highOam[2]=0xa0;
 p->cgram[129]=31;for(int tile=0;tile<20;++tile)for(int y=0;y<8;++y)p->vram[tile*16+y]=0xff;
 Cv4EnemyInit(rom.data(),(unsigned)rom.size());Cv4EnemyCommand("workshop on");
 if(argc==1){Cv4EnemyBegin(p,ram.data());check(strstr(Cv4EnemyObservation(),"\"size\":256"),"large native actor promotes capture to 256px canvas");check(Cv4EnemyCommand("flush"),"complete and component references flushed");return 0;}
 check(Cv4EnemyCommand("pack large"),"load 1032px artwork for 256px canvas");Cv4EnemyBegin(p,ram.data());
 check(Cv4EnemyHdCount()==1,"complete large actor replaced once");auto f=Cv4EnemyHd(0);check(f&&f->width==1032&&f->displayWidth==256&&f->x==0&&f->y==0,"4.03125x large artwork keeps exact anchor and extent");
 put(ram,0x584,0x4000);p->oam[20]=192|(120<<8);p->oam[21]=0x6000;p->oam[22]=48|(120<<8);p->oam[23]=0x6002;Cv4EnemyBegin(p,ram.data());
 check(Cv4EnemyHdCount()==1&&Cv4EnemyHd(0)->flip==1,"large mirrored actor reuses normalized capture");
 check(Cv4EnemyCommand("pack part"),"load large-canvas part replacement");Cv4EnemyBegin(p,ram.data());check(Cv4EnemyHdCount()==1&&p->hostSprites[0].mask[1]==4,"large-canvas component consumes only its own native slot");
 check(Cv4EnemyCommand("pack combined"),"load whole and component mappings together");Cv4EnemyBegin(p,ram.data());check(Cv4EnemyHdCount()==1&&p->hostSprites[0].mask[1]==12,"whole replacement takes precedence without double rendering parts");
 p->oam[23]=0x7002;rom[0x20008]=0x30;Cv4EnemyBegin(p,ram.data());check(Cv4EnemyHdCount()==1&&p->hostSprites[0].mask[1]==4,"mixed native priorities reject whole replacement and keep safe component fallback");
 return 0;
}
