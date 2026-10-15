/* NEW GAME+ is a host-authored sandbox campaign, chosen from the native title
 * menu entry that title_menu.c adds. The unused WRAM tag follows quick
 * saves/rewind. All room overrides are gated by it; selecting ordinary START
 * leaves the original campaign untouched. */
#include "campaign2.h"
#include "common_rtl.h"
#include "snes/ppu.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
extern unsigned char g_ram[0x20000];
extern Ppu *g_ppu;
enum { CAMPAIGN_TAG=0x11e0, CAMPAIGN_MAGIC=0xc402, FLOOR_Y=192 };
static int pending;
static unsigned word(unsigned a){return g_ram[a]|g_ram[a+1]<<8;}
static void put(unsigned a,unsigned v){g_ram[a]=(unsigned char)v;g_ram[a+1]=(unsigned char)(v>>8);}
static int room(void){return word(0x32)==4 && word(0x70)==5 && word(CAMPAIGN_TAG)==CAMPAIGN_MAGIC;}
static void roomPhysics(void){
    /* Four 256px quadrants of native 8px collision cells. */
    for(unsigned y=0;y<512;y+=8)for(unsigned x=0;x<512;x+=8){
        unsigned offset=2*(((x&256)<<2)|((x>>3)&31)|((y&256)<<3)|((y<<2)&0x3e0));
        put(0x4000+offset,y>=FLOOR_Y?1:0);
    }
    put(0xae,0);put(0x1c,0);put(0x1e,0);
    put(0xa0,0);put(0xa2,0);put(0xa4,0);put(0xa6,0);
    /* Keep player/whip/subweapon slots, discard retail room actors. */
    memset(g_ram+0x580,0,0xf00-0x580);
    if(word(0x54a)<16 || word(0x54a)>0xff00)put(0x54a,16);
    if(word(0x54a)>240)put(0x54a,240);
    put(0x13f0,0x400);
}
void Cv4CampaignBeforeFrame(void){
    unsigned phase=word(0x32);
    /* Logo, title menu: nothing is chosen (yet). */
    if(phase==0 || phase==1){pending=0;put(CAMPAIGN_TAG,0);}
    /* The confirmation ($00:8715) branches on the retail entries only. Once
     * NEW GAME+ (entry 3) has blinked, let it start like START and remember
     * the campaign for the first room. */
    if(phase==3 && g_ram[0x34]>=2 && word(0x1e02)==3){pending=1;put(0x1e02,0);}
    if(pending && phase==4 && word(0x70)==5){
        put(CAMPAIGN_TAG,CAMPAIGN_MAGIC);pending=0;
        put(0x54a,128);put(0x54e,FLOOR_Y-27);
        put(0x558,0);put(0x55a,0);put(0x55c,0);put(0x55e,0);
    }
    if(room())roomPhysics();
    if(getenv("SNESRECOMP_CAMPAIGN_PROBE")){
        static unsigned frame,old=~0u;
        unsigned state=phase|(word(0x70)<<8)|(word(0x1e02)<<16);
        if(state!=old){fprintf(stderr,"[campaign] frame=%u phase=%u/%u choice=%u pending=%d active=%d\n",frame,phase,word(0x70),word(0x1e02),pending,room());old=state;}
        if(room() && frame%20==0)fprintf(stderr,"[campaign_room] frame=%u x=%u y=%u\n",frame,word(0x54a),word(0x54e));
        if(++frame==1300){FILE*f=fopen("campaign-ram.bin","wb");if(f){fwrite(g_ram,1,sizeof(g_ram),f);fclose(f);}}
    }
}
void Cv4CampaignRasterLine(int line){
    if(!room())return;
    Ppu*p=g_ppu;
    if(line==0){
        /* This authored room has valid floor across both widescreen margins. */
        PpuSetExtraSideSpace(p,p->extraLeftRight,p->extraLeftRight,0);
        /* Empty tile and bevelled floor block, authored here rather than ROM. */
        memset(p->vram,0,64);
        for(int y=0;y<8;y++){p->vram[16+y]=y==0?0xff00:y==7?0x00ff:0x817e;p->vram[24+y]=0;}
        p->cgram[0]=0;p->cgram[113]=0x18c6;p->cgram[114]=0x4631;p->cgram[115]=0x294a;
        for(int y=0;y<32;y++)for(int x=0;x<32;x++)p->vram[0x5800+y*32+x]=(7<<10)|(y>=FLOOR_Y/8?1:0);
    }
    p->bgmode=1;p->bgTileAdr&=0xfff0;p->bgXsc[0]=0x58;
    p->hScroll[0]=0;p->vScroll[0]=0xffff;
    p->screenEnabled[0]=0x11;p->screenEnabled[1]=0;
    p->screenWindowed[0]=p->screenWindowed[1]=0;p->cgadsub=0;p->cgwsel=0;
}
