/* Private workshop presentation. Native Mode7 boss pixels, with transparent
 * colour index zero, sampled after each line's IRQ/HDMA and PPU rendering.
 * No guest palette, VRAM, CPU or collision state is changed. */
#include "workshop_capture.h"
#include "enemy_pack.h"
extern "C" {
#include "snes/ppu.h"
}
#include "third_party/stb_image_write.h"
#include <array>

namespace {
bool active=false;
std::array<unsigned char,256*224*4> pixels{};
}
extern "C" void Cv4WorkshopCaptureBegin(Ppu *ppu,const unsigned char *ram) {
 active=Cv4EnemyWorkshop() && ram[0x590]==0x81 && ram[0x591]==0;
 if(active){pixels.fill(0);ppu->hdTracking=true;}
}
extern "C" void Cv4WorkshopCaptureLine(Ppu *ppu,int line) {
 if(!active||line<1||line>224||PPU_mode(ppu)!=7)return;
 std::array<PpuLayerSample,kPpuBufWidth> samples{};
 if(!PpuGetLayerScanline(ppu,line,0,samples.data(),samples.size()))return;
 for(int x=0;x<256;++x) {
  const auto&s=samples[x+kPpuExtraLeftRight];unsigned index=s.pixel&255;
  if(!index||!(s.screens&1))continue;
  unsigned c=ppu->cgram[index];auto*out=&pixels[((line-1)*256+x)*4];
  out[0]=ppu->brightnessMult[c&31];out[1]=ppu->brightnessMult[(c>>5)&31];
  out[2]=ppu->brightnessMult[(c>>10)&31];out[3]=255;
 }
}
extern "C" int Cv4WorkshopCaptureSave(const char *path) {
 return active && path && *path && stbi_write_png(path,256,224,4,pixels.data(),256*4);
}
