/* Select the cartridge's second quest from the extra title-menu entry.
 * The ending at $03:FCAE writes $0088 = 1 before restarting block zero.
 * Native room setup ($00:D3FA) and actor spawning ($00:D6F0) consume it.
 * All subsequent gameplay, collisions, damage and graphics remain native. */
#include "campaign2.h"
#include <stdio.h>
#include <stdlib.h>

extern unsigned char g_ram[0x20000];

/* A short-lived request in unused WRAM follows save states and rewind. The
 * native confirmation clears $0070..$00BD, including the quest flag, and
 * $0200..$0EFF, but preserves this address. No host-static pending state. */
enum { REQUEST = 0x11e0, SECOND_QUEST_REQUEST = 0xc402, QUEST = 0x88 };
static unsigned word(unsigned a) { return g_ram[a] | g_ram[a + 1] << 8; }
static void put(unsigned a, unsigned v) {
    g_ram[a] = (unsigned char)v;
    g_ram[a + 1] = (unsigned char)(v >> 8);
}

void Cv4CampaignBeforeFrame(void) {
    unsigned phase = word(0x32), level = word(0x70);
    if (phase <= 1) put(REQUEST, 0);
    /* Let the original START path handle the name and new-game setup. */
    if (phase == 3 && word(0x34) >= 2 && word(0x1e02) == 3) {
        put(REQUEST, SECOND_QUEST_REQUEST);
        put(0x1e02, 0);
    }
    /* Phase 3 is the first room-load phase, before difficulty and spawn
     * tables are read. The request is consumed once, never every frame. */
    if (phase == 4 && level >= 3 && level <= 5 &&
        word(REQUEST) == SECOND_QUEST_REQUEST) {
        put(QUEST, 1);
        put(REQUEST, 0);
    }
    if (getenv("SNESRECOMP_CAMPAIGN_PROBE")) {
        static unsigned previous = ~0u;
        unsigned state = phase | (level << 4) | (word(QUEST) << 8) |
                         (word(0x1e02) << 16);
        if (state != previous) {
            fprintf(stderr, "[campaign] phase=%u/%u choice=%u quest=%u request=%u\n",
                    phase, level, word(0x1e02), word(QUEST), word(REQUEST));
            previous = state;
        }
    }
}

/* Kept for the existing scanline-hook ABI; second quest uses the retail PPU. */
void Cv4CampaignRasterLine(int line) { (void)line; }
