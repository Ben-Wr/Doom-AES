#include <ngdevkit/neogeo.h>
#include <ngdevkit/ng-fix.h>
#include <ngdevkit/ng-video.h>
#include <stdio.h>

#include "ng_profile.h"

#define CARD_SPRITE 1
#define CARD_START_TILE 256
#define CARD_TILE_COUNT 32
#define CARD_SOURCE_HEIGHT_PX 512
#define CARD_SOURCE_WIDTH_PX 16
#define PROFILE_MIRROR_ADDR 0x10e000u

typedef struct m0a_state_t {
    u16 x;
    u16 top;
    u8 y_step;
    u8 x_step;
    u8 palette;
    u8 guard_asserted;
} m0a_state_t;

static const u8 y_shrink_steps[] = {
    0xff, 0xdf, 0xbf, 0x9f, 0x7f, 0x5f, 0x3f, 0x1f, 0x07, 0x00
};

static const u8 x_shrink_steps[] = {
    0x0f, 0x0b, 0x07, 0x03, 0x00
};

static const u16 card_palettes[8][16] = {
    {0x0000, 0x0111, 0x0222, 0x0333, 0x0444, 0x0555, 0x0666, 0x0777,
     0x0888, 0x0999, 0x0aaa, 0x0bbb, 0x0ccc, 0x0ddd, 0x0eee, 0x0fff},
    {0x0000, 0x0200, 0x0300, 0x0400, 0x0500, 0x0600, 0x0700, 0x0800,
     0x0900, 0x0a00, 0x0b00, 0x0c00, 0x0d00, 0x0e00, 0x0f00, 0x0fff},
    {0x0000, 0x0020, 0x0030, 0x0040, 0x0050, 0x0060, 0x0070, 0x0080,
     0x0090, 0x00a0, 0x00b0, 0x00c0, 0x00d0, 0x00e0, 0x00f0, 0x0fff},
    {0x0000, 0x0002, 0x0003, 0x0004, 0x0005, 0x0006, 0x0007, 0x0008,
     0x0009, 0x000a, 0x000b, 0x000c, 0x000d, 0x000e, 0x000f, 0x0fff},
    {0x0000, 0x0210, 0x0320, 0x0430, 0x0540, 0x0650, 0x0760, 0x0870,
     0x0980, 0x0a90, 0x0ba0, 0x0cb0, 0x0dc0, 0x0ed0, 0x0fe0, 0x0fff},
    {0x0000, 0x0202, 0x0303, 0x0404, 0x0505, 0x0606, 0x0707, 0x0808,
     0x0909, 0x0a0a, 0x0b0b, 0x0c0c, 0x0d0d, 0x0e0e, 0x0f0f, 0x0fff},
    {0x0000, 0x0022, 0x0033, 0x0044, 0x0055, 0x0066, 0x0077, 0x0088,
     0x0099, 0x00aa, 0x00bb, 0x00cc, 0x00dd, 0x00ee, 0x00ff, 0x0fff},
    {0x0000, 0x0121, 0x0232, 0x0343, 0x0454, 0x0565, 0x0676, 0x0787,
     0x0898, 0x09a9, 0x0aba, 0x0bcb, 0x0cdc, 0x0ded, 0x0efe, 0x0fff},
};

static m0a_state_t state;
static ng_profile_frame_t profile;
static u16 frame_id;

static u16 y_shrink(void) {
    return y_shrink_steps[state.y_step];
}

static u16 x_shrink(void) {
    return x_shrink_steps[state.x_step];
}

static u16 visible_height_px(void) {
    return (u16)(1u + ((CARD_SOURCE_HEIGHT_PX - 1u) * y_shrink()) / 0xffu);
}

static u16 visible_width_px(void) {
    return (u16)(1u + x_shrink());
}

static u16 scb3_yfield_from_top(u16 top) {
    return (u16)((496u - top) & 0x01ffu);
}

static void copy_profile_to_mirror(void) {
    volatile u16 *dst = (volatile u16 *)PROFILE_MIRROR_ADDR;
    const u16 *src = (const u16 *)&profile;
    for (u16 i = 0; i < sizeof(profile) / sizeof(u16); i++) {
        dst[i] = src[i];
    }
}

static void init_palettes(void) {
    static const u16 fix_palette[16] = {
        0x8000, 0x0fff, 0x0555, 0x0f00, 0x00f0, 0x000f, 0x0ff0, 0x0f0f,
        0x00ff, 0x0222, 0x0444, 0x0666, 0x0888, 0x0aaa, 0x0ccc, 0x0eee
    };

    for (u16 i = 0; i < 16; i++) {
        MMAP_PALBANK1[i] = fix_palette[i];
    }
    for (u16 pal = 0; pal < 8; pal++) {
        for (u16 c = 0; c < 16; c++) {
            MMAP_PALBANK1[((pal + 1u) * 16u) + c] = card_palettes[pal][c];
        }
    }
    profile.palette_words = 16u * 9u;
}

static void write_card_tilemap(u8 palette) {
    *REG_VRAMMOD = 1;
    *REG_VRAMADDR = ADDR_SCB1 + (CARD_SPRITE * 64u);
    for (u16 i = 0; i < CARD_TILE_COUNT; i++) {
        *REG_VRAMRW = CARD_START_TILE + i;
        *REG_VRAMRW = ((u16)palette) << 8;
    }
    profile.scb1_words += CARD_TILE_COUNT * 2u;
}

static void rewrite_card_attrs(u8 palette) {
    *REG_VRAMMOD = 2;
    *REG_VRAMADDR = ADDR_SCB1 + (CARD_SPRITE * 64u) + 1u;
    for (u16 i = 0; i < CARD_TILE_COUNT; i++) {
        *REG_VRAMRW = ((u16)palette) << 8;
    }
    profile.scb1_words += CARD_TILE_COUNT;
}

static void write_card_controls(void) {
    const u16 shrink_word = (u16)((x_shrink() << 8) | y_shrink());
    const u16 y_word = (u16)((scb3_yfield_from_top(state.top) << 7) | CARD_TILE_COUNT);
    const u16 x_word = (u16)((state.x & 0x01ffu) << 7);

    *REG_VRAMMOD = 0x200;
    *REG_VRAMADDR = ADDR_SCB2 + CARD_SPRITE;
    *REG_VRAMRW = shrink_word;
    *REG_VRAMRW = y_word;
    *REG_VRAMRW = x_word;
    profile.scb_control_words += 3;
}

static void assert_shrink_only(u16 requested_height_px) {
    if (requested_height_px > CARD_SOURCE_HEIGHT_PX) {
        state.guard_asserted = 1;
    }
}

static void reset_state(void) {
    state.x = 152;
    state.top = 16;
    state.y_step = 0;
    state.x_step = 0;
    state.palette = 1;
    state.guard_asserted = 0;
}

static void init_sprite(void) {
    bios_lsp_1st();
    write_card_tilemap(state.palette);
    write_card_controls();
}

static void update_controls(void) {
    if (bios_p1current & CNT_LEFT) {
        if (state.x > 0) state.x--;
    }
    if (bios_p1current & CNT_RIGHT) {
        if (state.x < 319) state.x++;
    }
    if (bios_p1current & CNT_UP) {
        if (state.top > 0) state.top--;
    }
    if (bios_p1current & CNT_DOWN) {
        if (state.top < 223) state.top++;
    }

    if (bios_p1change & CNT_A) {
        state.y_step = (u8)((state.y_step + 1u) % (sizeof(y_shrink_steps) / sizeof(y_shrink_steps[0])));
    }
    if (bios_p1change & CNT_B) {
        state.x_step = (u8)((state.x_step + 1u) % (sizeof(x_shrink_steps) / sizeof(x_shrink_steps[0])));
    }
    if (bios_p1change & CNT_C) {
        state.palette++;
        if (state.palette > 8) state.palette = 1;
        rewrite_card_attrs(state.palette);
    }
    if (bios_p1change & CNT_D) {
        assert_shrink_only(CARD_SOURCE_HEIGHT_PX + 1u);
    }
    if (bios_statchange & CNT_START1) {
        reset_state();
        rewrite_card_attrs(state.palette);
    }

    assert_shrink_only(visible_height_px());
}

static void put_overlay_line(u8 row, const char *text) {
    char line[38];
    u8 i = 0;
    while (text[i] && i < 37) {
        line[i] = text[i];
        i++;
    }
    while (i < 37) {
        line[i++] = ' ';
    }
    line[i] = 0;
    ng_text(1, row, 0, line);
    profile.fix_words += 37;
}

static void draw_overlay(void) {
    char line[38];
    const u16 yfield = scb3_yfield_from_top(state.top);

    put_overlay_line(2, "DOOM AES M0A SPRITE PATH");
    put_overlay_line(3, "DPAD MOVE  A:Y  B:X  C:PAL  D:GUARD");

    snprintf(line, sizeof(line), "HEIGHT %3uPX  WIDTH %2uPX", visible_height_px(), visible_width_px());
    put_overlay_line(5, line);
    snprintf(line, sizeof(line), "YSHR $%02X  XSHR $%01X  PAL %u", y_shrink(), x_shrink(), state.palette);
    put_overlay_line(6, line);
    snprintf(line, sizeof(line), "TOP %3u  X %3u  YFIELD $%03X", state.top, state.x, yfield);
    put_overlay_line(7, line);
    snprintf(line, sizeof(line), "SPR/LINE %u  SCB1 %u  CTRL %u", profile.max_sprites_scanline, profile.scb1_words, profile.scb_control_words);
    put_overlay_line(9, line);
    snprintf(line, sizeof(line), "FPS 60V  RAM %u  DEG $%04X", profile.ram_high_water_bytes, profile.degrade_flags);
    put_overlay_line(10, line);
    snprintf(line, sizeof(line), "GUARD %s  MIRROR $%06lX", state.guard_asserted ? "ASSERT" : "OK", (unsigned long)PROFILE_MIRROR_ADDR);
    put_overlay_line(11, line);
}

int main(void) {
    ng_cls();
    reset_state();
    ng_profile_reset(&profile, frame_id);
    init_palettes();
    init_sprite();

    for (;;) {
        ng_profile_reset(&profile, frame_id++);
        profile.sprites_emitted = 1;
        profile.max_sprites_scanline = 1;

        update_controls();
        write_card_controls();
        draw_overlay();
        copy_profile_to_mirror();

        ng_wait_vblank();
    }
    return 0;
}
