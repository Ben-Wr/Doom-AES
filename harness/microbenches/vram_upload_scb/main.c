#include <ngdevkit/neogeo.h>
#include <ngdevkit/ng-fix.h>
#include <ngdevkit/ng-video.h>
#include <stdio.h>

#include "ng_profile.h"

#define HEARTBEAT_SPRITE 1u
#define BENCH_SPRITE_BASE 64u
#define CARD_START_TILE 256u
#define CARD_TILE_COUNT 32u
#define THING_TILE_COUNT 12u
#define WALL_SPRITES 40u
#define THING_SPRITES 24u
#define PROFILE_MIRROR_ADDR 0x10e040u

#define STREAM_CYCLES_PER_WORD 12u
#define ADDR_SET_CYCLES 16u
#define VBLANK_PRACTICAL_WORDS 1664u
#define VBLANK_THEORETICAL_WORDS 2560u
#define VBLANK_CPU_CYCLES 30720u

typedef enum m0b_mode_t {
    MODE_FULL = 0,
    MODE_CTRL = 1,
    MODE_MIXED = 2,
    MODE_ACTIVE = 3
} m0b_mode_t;

typedef struct upload_stats_t {
    u16 words;
    u16 addr_sets;
    u32 cycles_x10;
    u16 cpw_x10;
    u16 frames_to_fit;
    u16 safe_fps;
} upload_stats_t;

typedef struct m0b_state_t {
    m0b_mode_t mode;
    u16 target;
    u8 artifact_observed;
    u8 frame_phase;
} m0b_state_t;

static const char * const mode_names[] = {
    "FULL", "CTRL", "MIXED", "ACTIVE"
};

static m0b_state_t state;
static ng_profile_frame_t profile;
static upload_stats_t stats;
static u16 frame_id;

static u16 max_target_for_mode(m0b_mode_t mode) {
    switch (mode) {
    case MODE_FULL: return 40;
    case MODE_CTRL: return 320;
    case MODE_MIXED: return WALL_SPRITES;
    case MODE_ACTIVE: return 40;
    }
    return 1;
}

static u16 step_for_mode(m0b_mode_t mode) {
    switch (mode) {
    case MODE_FULL: return 1;
    case MODE_CTRL: return 16;
    case MODE_MIXED: return 1;
    case MODE_ACTIVE: return 1;
    }
    return 1;
}

static u16 default_target_for_mode(m0b_mode_t mode) {
    switch (mode) {
    case MODE_FULL: return 24;
    case MODE_CTRL: return 256;
    case MODE_MIXED: return 10;
    case MODE_ACTIVE: return 26;
    }
    return 1;
}

static void reset_state(void) {
    state.mode = MODE_MIXED;
    state.target = default_target_for_mode(state.mode);
    state.artifact_observed = 0;
    state.frame_phase = 0;
}

static void reset_stats(void) {
    stats.words = 0;
    stats.addr_sets = 0;
    stats.cycles_x10 = 0;
    stats.cpw_x10 = 0;
    stats.frames_to_fit = 1;
    stats.safe_fps = 60;
}

static void vram_addr(u16 address, u16 mod) {
    *REG_VRAMMOD = mod;
    *REG_VRAMADDR = address;
    stats.addr_sets++;
    stats.cycles_x10 += ADDR_SET_CYCLES * 10u;
}

static void vram_write(u16 value) {
    *REG_VRAMRW = value;
    stats.words++;
    stats.cycles_x10 += STREAM_CYCLES_PER_WORD * 10u;
}

static void finish_stats(void) {
    if (stats.words != 0) {
        stats.cpw_x10 = stats.cycles_x10 / stats.words;
        stats.frames_to_fit = (u16)((stats.words + VBLANK_PRACTICAL_WORDS - 1u) / VBLANK_PRACTICAL_WORDS);
        if (stats.frames_to_fit == 0) stats.frames_to_fit = 1;
        stats.safe_fps = (u16)(60u / stats.frames_to_fit);
    }
}

static void copy_profile_to_mirror(void) {
    volatile u16 *dst = (volatile u16 *)PROFILE_MIRROR_ADDR;
    const u16 *src = (const u16 *)&profile;
    for (u16 i = 0; i < sizeof(profile) / sizeof(u16); i++) {
        dst[i] = src[i];
    }
}

static void init_palettes(void) {
    static const u16 clut[32] = {
        0x8000, 0x0fff, 0x0555, 0x0f00, 0x00f0, 0x000f, 0x0ff0, 0x0f0f,
        0x00ff, 0x0222, 0x0444, 0x0666, 0x0888, 0x0aaa, 0x0ccc, 0x0eee,
        0x0000, 0x0111, 0x0333, 0x0555, 0x0777, 0x0999, 0x0bbb, 0x0ddd,
        0x0fff, 0x0f80, 0x08f0, 0x008f, 0x0ff0, 0x0f0f, 0x00ff, 0x0fff
    };
    for (u16 i = 0; i < 32; i++) {
        MMAP_PALBANK1[i] = clut[i];
    }
    profile.palette_words = 32;
}

static void write_full_tilemap(u16 sprite, u16 attr_seed) {
    vram_addr((u16)(ADDR_SCB1 + (sprite * 64u)), 1);
    for (u16 i = 0; i < CARD_TILE_COUNT; i++) {
        vram_write((u16)(CARD_START_TILE + i));
        vram_write((u16)(0x0100u | ((attr_seed + i) & 0x000fu)));
    }
    profile.scb1_words += CARD_TILE_COUNT * 2u;
}

static void write_thing_tilemap(u16 sprite, u16 attr_seed) {
    vram_addr((u16)(ADDR_SCB1 + (sprite * 64u)), 1);
    for (u16 i = 0; i < THING_TILE_COUNT; i++) {
        vram_write((u16)(CARD_START_TILE + i));
        vram_write((u16)(0x0100u | ((attr_seed + i) & 0x000fu)));
    }
    profile.scb1_words += THING_TILE_COUNT * 2u;
}

static void write_controls_batched(u16 base_sprite, u16 count, u16 size_tiles) {
    vram_addr((u16)(ADDR_SCB2 + base_sprite), 1);
    for (u16 i = 0; i < count; i++) {
        vram_write(0x0fff);
    }

    vram_addr((u16)(ADDR_SCB3 + base_sprite), 1);
    for (u16 i = 0; i < count; i++) {
        vram_write((u16)((0x01e0u << 7) | (size_tiles & 0x003fu)));
    }

    vram_addr((u16)(ADDR_SCB4 + base_sprite), 1);
    for (u16 i = 0; i < count; i++) {
        vram_write((u16)(((i * 17u) & 0x01ffu) << 7));
    }

    profile.scb_control_words += count * 3u;
}

static void init_heartbeat_sprite(void) {
    *REG_VRAMMOD = 1;
    *REG_VRAMADDR = ADDR_SCB1 + (HEARTBEAT_SPRITE * 64u);
    for (u16 i = 0; i < CARD_TILE_COUNT; i++) {
        *REG_VRAMRW = CARD_START_TILE + i;
        *REG_VRAMRW = 0x0100;
    }

    *REG_VRAMMOD = 0x200;
    *REG_VRAMADDR = ADDR_SCB2 + HEARTBEAT_SPRITE;
    *REG_VRAMRW = 0x0fff;
    *REG_VRAMRW = (u16)((0x01e0u << 7) | CARD_TILE_COUNT);
    *REG_VRAMRW = (u16)(296u << 7);
}

static void active_delay(void) {
    for (volatile u16 i = 0; i < 7000; i++) {
        __asm__ volatile ("nop");
    }
}

static void run_upload(void) {
    reset_stats();

    if (state.mode == MODE_ACTIVE) {
        active_delay();
    }

    switch (state.mode) {
    case MODE_FULL:
        for (u16 i = 0; i < state.target; i++) {
            write_full_tilemap((u16)(BENCH_SPRITE_BASE + i), (u16)(frame_id + i));
        }
        write_controls_batched(BENCH_SPRITE_BASE, state.target, 0);
        break;

    case MODE_CTRL:
        write_controls_batched(BENCH_SPRITE_BASE, state.target, 0);
        break;

    case MODE_MIXED:
        write_controls_batched(BENCH_SPRITE_BASE, (u16)(WALL_SPRITES + THING_SPRITES), 0);
        for (u16 i = 0; i < state.target; i++) {
            write_full_tilemap((u16)(BENCH_SPRITE_BASE + i), (u16)(frame_id + i));
        }
        for (u16 i = 0; i < THING_SPRITES; i++) {
            write_thing_tilemap((u16)(BENCH_SPRITE_BASE + WALL_SPRITES + i), (u16)(frame_id + i));
        }
        break;

    case MODE_ACTIVE:
        for (u16 i = 0; i < state.target; i++) {
            write_full_tilemap((u16)(BENCH_SPRITE_BASE + i), (u16)(frame_id + i));
        }
        write_controls_batched(BENCH_SPRITE_BASE, state.target, 0);
        break;
    }

    finish_stats();
}

static void update_controls(void) {
    if (bios_p1change & CNT_A) {
        state.mode = (m0b_mode_t)((state.mode + 1u) & 3u);
        state.target = default_target_for_mode(state.mode);
    }
    if (bios_p1change & CNT_B) {
        const u16 step = step_for_mode(state.mode);
        const u16 max = max_target_for_mode(state.mode);
        if (state.target + step <= max) {
            state.target += step;
        } else {
            state.target = max;
        }
    }
    if (bios_p1change & CNT_C) {
        const u16 step = step_for_mode(state.mode);
        if (state.target > step) {
            state.target -= step;
        } else {
            state.target = 1;
        }
    }
    if (bios_p1change & CNT_D) {
        state.artifact_observed ^= 1u;
    }
    if (bios_statchange & CNT_START1) {
        reset_state();
    }
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
    const u16 over_practical = stats.words > VBLANK_PRACTICAL_WORDS;
    const u16 over_theoretical = stats.words > VBLANK_THEORETICAL_WORDS;

    put_overlay_line(2, "DOOM AES M0B VRAM UPLOAD");
    put_overlay_line(3, "A:MODE B:+ C:- D:ART START:RST");

    snprintf(line, sizeof(line), "MODE %-6s TARGET %3u", mode_names[state.mode], state.target);
    put_overlay_line(5, line);
    snprintf(line, sizeof(line), "WORDS %4u SCB1 %4u CTRL %4u", stats.words, profile.scb1_words, profile.scb_control_words);
    put_overlay_line(6, line);
    snprintf(line, sizeof(line), "ADDR %3u  CYC %5lu  C/W %2u.%u", stats.addr_sets, (unsigned long)(stats.cycles_x10 / 10u), stats.cpw_x10 / 10u, stats.cpw_x10 % 10u);
    put_overlay_line(7, line);
    snprintf(line, sizeof(line), "VB PRACT %4u THEO %4u", VBLANK_PRACTICAL_WORDS, VBLANK_THEORETICAL_WORDS);
    put_overlay_line(9, line);
    snprintf(line, sizeof(line), "OVER P:%u T:%u  FIT %uF FPS %2u", over_practical, over_theoretical, stats.frames_to_fit, stats.safe_fps);
    put_overlay_line(10, line);
    snprintf(line, sizeof(line), "ART %s  MIRROR $%06lX", state.artifact_observed ? "OBSERVED" : "CLEAR", (unsigned long)PROFILE_MIRROR_ADDR);
    put_overlay_line(11, line);
}

int main(void) {
    ng_cls();
    reset_state();
    ng_profile_reset(&profile, frame_id);
    init_palettes();
    bios_lsp_1st();
    init_heartbeat_sprite();

    for (;;) {
        ng_wait_vblank();

        ng_profile_reset(&profile, frame_id++);
        profile.sprites_emitted = 1;
        profile.max_sprites_scanline = 1;

        update_controls();
        run_upload();

        profile.upload_ticks = (u16)(stats.cycles_x10 / 10u);
        profile.degrade_flags = state.artifact_observed ? 1u : 0u;

        draw_overlay();
        copy_profile_to_mirror();
    }
    return 0;
}
