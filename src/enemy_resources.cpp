#include "enemy_resources.h"
extern "C" {
#include "snes/ppu.h"
}
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iterator>
#include <vector>

extern "C" int Cv4EnemyResources(Ppu *ppu,unsigned char *ram,const char *path,char *error,size_t capacity) {
 auto fail=[&](const char *message){snprintf(error,capacity,"%s",message);return 0;};
 if(!ppu||!ram||!path||!*path)return fail("Missing monster resource target");
 std::ifstream file(path,std::ios::binary);if(!file)return fail("Cannot open monster resource bundle");
 file.seekg(0,std::ios::end);auto length=file.tellg();
 if(length<12||length>0x8000)return fail("Invalid monster resource bundle size");
 file.seekg(0);std::vector<unsigned char> data((size_t)length);
 if(!file.read((char*)data.data(),data.size()))return fail("Cannot read monster resource bundle");
 auto word=[&](size_t at){return unsigned(data[at])|(unsigned(data[at+1])<<8);};
 if(memcmp(data.data(),"CV4OBJ1\0",8))return fail("Unsupported monster resource bundle");
 unsigned full=word(8),count=word(10);size_t at=12;
 if(full>1||count>11)return fail("Invalid monster resource declaration");
 if(count&&(PPU_objTileAdr1(ppu)!=0x6000||PPU_objTileAdr2(ppu)!=0x7000||PPU_objSize(ppu)!=0))
  return fail("Monster graphics require the original 8/16px OBJ layout");
 struct Block {unsigned address,length;size_t offset;};std::vector<Block> blocks;
 std::vector<bool> occupied(0x1600);
 for(unsigned i=0;i<count;++i){
  if(at+4>data.size())return fail("Truncated monster resource header");
  unsigned address=word(at),size=word(at+2);at+=4;
  if(address<0x6a00||address>=0x8000||!size||(size&1)||size>2*(0x8000-address)||at+size>data.size())
   return fail("Monster graphics exceed reserved OBJ region");
  for(unsigned w=address;w<address+size/2;++w){if(occupied[w-0x6a00])return fail("Overlapping monster graphics");occupied[w-0x6a00]=true;}
  blocks.push_back({address,size,at});at+=size;
 }
 unsigned paletteBytes=full?512:256;
 unsigned shadow=unsigned(ram[0x48])|(unsigned(ram[0x49])<<8);
 if(at+paletteBytes!=data.size()||shadow<0x2000||shadow+512>0x20000)
  return fail("Invalid monster palette or native palette shadow");
 // Validate every span before touching any guest or PPU memory.
 for(const auto&b:blocks)memcpy(ppu->vram+b.address,data.data()+b.offset,b.length);
 unsigned first=full?0:128;
 memcpy(ppu->cgram+first,data.data()+at,paletteBytes);
 memcpy(ram+shadow+first*2,data.data()+at,paletteBytes);
 ++ppu->vramWriteCount;
 snprintf(error,capacity,"Original monster graphics and palette installed; no level loaded");return 1;
}
