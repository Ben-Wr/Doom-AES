#include <ngdevkit/neogeo.h>
#include <ngdevkit/ng-fix.h>
#include <ngdevkit/ng-video.h>
#include <stdint.h>
#include <stdio.h>

#include "ng_profile.h"

#define CARD_START_TILE 256u
#define CARD_TILE_COUNT 32u
#define CARD_SOURCE_HEIGHT_PX 512u
#define SPRITE_BASE 32u
#define MAX_CMDS 96u
#define PROFILE_MIRROR_ADDR 0x10e080u

#define SCREEN_W 320
#define SCREEN_H 224
#define VIEW_TOP 88
#define VIEW_BOTTOM 224
#define HORIZON_Y 152
#define FOCAL 172
#define PROJ_SCALE 190
#define NEAR_Z 32
#define PLAYER_EYE 48
#define MOVE_STEP 8
#define STRAFE_STEP 7
#define TURN_STEP 2
#define COLLISION_RADIUS 42
#define DOOR_CLOSED_CEIL 24
#define DOOR_OPEN_CEIL 128
#define DOOR_SPEED 2
#define VBLANK_PRACTICAL_WORDS 1664u
#define STREAM_CYCLES_PER_WORD 12u
#define ADDR_SET_CYCLES 16u
#define RAM_HWM_BYTES 5376u

typedef enum wall_role_t {
    ROLE_MIDDLE = 0,
    ROLE_UPPER = 1,
    ROLE_LOWER = 2
} wall_role_t;

typedef struct vertex_t {
    int16_t x;
    int16_t y;
} vertex_t;

typedef struct sector_base_t {
    int16_t floor;
    int16_t ceil;
} sector_base_t;

typedef struct line_t {
    uint8_t v0;
    uint8_t v1;
    int8_t front;
    int8_t back;
    uint8_t material;
    uint8_t door;
} line_t;

typedef struct sprite_cmd_t {
    uint16_t card_id;
    int16_t x;
    int16_t y;
    uint16_t height;
    uint16_t depth;
    uint8_t width;
    uint8_t x_shrink;
    uint8_t y_shrink;
    uint8_t size_tiles;
    uint8_t palette;
    uint8_t role;
} sprite_cmd_t;

typedef struct player_t {
    int16_t x;
    int16_t y;
    uint8_t angle;
} player_t;

typedef struct door_t {
    int16_t ceil;
    uint8_t target_open;
} door_t;

static const int16_t sin_q8_table[64] = {
    0, 25, 50, 74, 98, 121, 142, 162, 181, 198, 213, 226, 237, 245, 251, 255,
    256, 255, 251, 245, 237, 226, 213, 198, 181, 162, 142, 121, 98, 74, 50, 25,
    0, -25, -50, -74, -98, -121, -142, -162, -181, -198, -213, -226, -237, -245, -251, -255,
    -256, -255, -251, -245, -237, -226, -213, -198, -181, -162, -142, -121, -98, -74, -50, -25
};

static const vertex_t vertices[] = {
    { 0, 0 }, { 1024, 0 }, { 1024, 256 }, { 1024, 512 }, { 1024, 768 },
    { 0, 768 }, { 1280, 256 }, { 1280, 512 }
};

static const sector_base_t sector_bases[] = {
    { 0, 128 },
    { 24, 128 }
};

static const line_t lines[] = {
    { 0, 1, 0, -1, 0, 0 },
    { 1, 2, 0, -1, 1, 0 },
    { 2, 3, 0, 1,  2, 1 },
    { 3, 4, 0, -1, 1, 0 },
    { 4, 5, 0, -1, 0, 0 },
    { 5, 0, 0, -1, 1, 0 },
    { 2, 6, 1, -1, 2, 0 },
    { 6, 7, 1, -1, 2, 0 },
    { 7, 3, 1, -1, 2, 0 }
};

static sprite_cmd_t cmds[MAX_CMDS];
static uint16_t shadow_card_id[MAX_CMDS];
static uint8_t shadow_valid[MAX_CMDS];
static uint16_t ctrl_scb2[MAX_CMDS];
static uint16_t ctrl_scb3[MAX_CMDS];
static uint16_t ctrl_scb4[MAX_CMDS];
static player_t player;
static door_t door;
static ng_profile_frame_t profile;
static uint16_t frame_id;
static uint8_t cmd_count;
static uint8_t last_cmd_count;
static uint8_t guard_asserted;

static int16_t sin_q8(uint8_t angle) {
    return sin_q8_table[angle & 63u];
}

static int16_t cos_q8(uint8_t angle) {
    return sin_q8_table[(angle + 16u) & 63u];
}

static int16_t sector_ceil(int8_t sector) {
    if (sector == 1) {
        return door.ceil;
    }
    return sector_bases[(uint8_t)sector].ceil;
}

static int16_t sector_floor(int8_t sector) {
    return sector_bases[(uint8_t)sector].floor;
}

static int16_t clamp_i16(int16_t value, int16_t lo, int16_t hi) {
    if (value < lo) return lo;
    if (value > hi) return hi;
    return value;
}

static uint16_t scb3_yfield_from_top(int16_t top) {
    return (uint16_t)((496 - top) & 0x01ff);
}

static uint8_t y_shrink_for_height(uint16_t height) {
    if (height > CARD_SOURCE_HEIGHT_PX) {
        guard_asserted = 1;
        return 0xff;
    }
    if (height <= 1) {
        return 0;
    }
    return (uint8_t)(((uint32_t)(height - 1u) * 255u) / (CARD_SOURCE_HEIGHT_PX - 1u));
}

static void copy_profile_to_mirror(void) {
    volatile uint16_t *dst = (volatile uint16_t *)PROFILE_MIRROR_ADDR;
    const uint16_t *src = (const uint16_t *)&profile;
    for (uint16_t i = 0; i < sizeof(profile) / sizeof(uint16_t); i++) {
        dst[i] = src[i];
    }
}

static void put_overlay_line(uint8_t row, const char *text) {
    char line[38];
    uint8_t i = 0;
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

static void init_palettes(void) {
    static const uint16_t clut[80] = {
        0x8000, 0x0fff, 0x0555, 0x0f00, 0x00f0, 0x000f, 0x0ff0, 0x0f0f,
        0x00ff, 0x0222, 0x0444, 0x0666, 0x0888, 0x0aaa, 0x0ccc, 0x0eee,
        0x0000, 0x0211, 0x0322, 0x0433, 0x0544, 0x0655, 0x0766, 0x0877,
        0x0988, 0x0a99, 0x0baa, 0x0cbb, 0x0dcc, 0x0edd, 0x0fee, 0x0fff,
        0x0000, 0x0002, 0x0014, 0x0026, 0x0038, 0x004a, 0x005c, 0x006e,
        0x008f, 0x028f, 0x048f, 0x068f, 0x089f, 0x0aaf, 0x0ccf, 0x0fff,
        0x0000, 0x0200, 0x0420, 0x0640, 0x0860, 0x0a80, 0x0ca0, 0x0ec0,
        0x0fe0, 0x0fd0, 0x0fb0, 0x0f90, 0x0f70, 0x0f50, 0x0f30, 0x0fff,
        0x0000, 0x0111, 0x0222, 0x0333, 0x0444, 0x0555, 0x0666, 0x0777,
        0x0888, 0x0999, 0x0aaa, 0x0bbb, 0x0ccc, 0x0ddd, 0x0eee, 0x0fff
    };
    for (uint16_t i = 0; i < 80; i++) {
        MMAP_PALBANK1[i] = clut[i];
    }
    MMAP_PALBANK1[255] = 0x0001;
    profile.palette_words = 81;
}

static void reset_state(void) {
    player.x = 512;
    player.y = 384;
    player.angle = 0;
    door.ceil = DOOR_CLOSED_CEIL;
    door.target_open = 0;
    cmd_count = 0;
    last_cmd_count = 0;
    guard_asserted = 0;
    for (uint8_t i = 0; i < MAX_CMDS; i++) {
        shadow_card_id[i] = 0xffffu;
        shadow_valid[i] = 0;
    }
}

static uint8_t line_is_solid(const line_t *line) {
    if (line->back < 0) {
        return 1;
    }
    if (line->door && door.ceil < 112) {
        return 1;
    }
    return 0;
}

static uint8_t point_near_segment(int16_t px, int16_t py, const line_t *line) {
    const vertex_t *a = &vertices[line->v0];
    const vertex_t *b = &vertices[line->v1];
    int32_t vx = b->x - a->x;
    int32_t vy = b->y - a->y;
    int32_t wx = px - a->x;
    int32_t wy = py - a->y;
    int32_t len2 = vx * vx + vy * vy;
    int32_t t;
    int32_t cx;
    int32_t cy;
    int32_t dx;
    int32_t dy;

    if (len2 == 0) {
        return 0;
    }
    t = ((wx * vx + wy * vy) * 256) / len2;
    if (t < 0 || t > 256) {
        return 0;
    }
    cx = a->x + ((vx * t) >> 8);
    cy = a->y + ((vy * t) >> 8);
    dx = px - cx;
    dy = py - cy;
    return (uint8_t)((dx * dx + dy * dy) < (COLLISION_RADIUS * COLLISION_RADIUS));
}

static uint8_t blocked_position(int16_t x, int16_t y) {
    if (x < COLLISION_RADIUS || y < COLLISION_RADIUS || x > 1280 - COLLISION_RADIUS || y > 768 - COLLISION_RADIUS) {
        return 1;
    }
    for (uint8_t i = 0; i < sizeof(lines) / sizeof(lines[0]); i++) {
        if (line_is_solid(&lines[i]) && point_near_segment(x, y, &lines[i])) {
            return 1;
        }
    }
    return 0;
}

static void try_move(int16_t dx, int16_t dy) {
    int16_t nx = player.x + dx;
    int16_t ny = player.y + dy;
    if (!blocked_position(nx, player.y)) {
        player.x = nx;
    }
    if (!blocked_position(player.x, ny)) {
        player.y = ny;
    }
}

static void update_controls(void) {
    int16_t fx = cos_q8(player.angle);
    int16_t fy = sin_q8(player.angle);
    int16_t rx = -fy;
    int16_t ry = fx;

    if (bios_p1current & CNT_LEFT) {
        player.angle = (uint8_t)((player.angle - TURN_STEP) & 63u);
    }
    if (bios_p1current & CNT_RIGHT) {
        player.angle = (uint8_t)((player.angle + TURN_STEP) & 63u);
    }
    if (bios_p1current & CNT_UP) {
        try_move((int16_t)((fx * MOVE_STEP) >> 8), (int16_t)((fy * MOVE_STEP) >> 8));
    }
    if (bios_p1current & CNT_DOWN) {
        try_move((int16_t)(-((fx * MOVE_STEP) >> 8)), (int16_t)(-((fy * MOVE_STEP) >> 8)));
    }
    if (bios_p1current & CNT_A) {
        try_move((int16_t)(-((rx * STRAFE_STEP) >> 8)), (int16_t)(-((ry * STRAFE_STEP) >> 8)));
    }
    if (bios_p1current & CNT_B) {
        try_move((int16_t)((rx * STRAFE_STEP) >> 8), (int16_t)((ry * STRAFE_STEP) >> 8));
    }
    if (bios_p1change & CNT_C) {
        door.target_open ^= 1u;
    }
    if (bios_p1change & CNT_D || bios_statchange & CNT_START1) {
        reset_state();
    }

    if (door.target_open && door.ceil < DOOR_OPEN_CEIL) {
        door.ceil += DOOR_SPEED;
    } else if (!door.target_open && door.ceil > DOOR_CLOSED_CEIL) {
        door.ceil -= DOOR_SPEED;
    }
}

static void add_cmd(sprite_cmd_t cmd) {
    if (cmd_count >= MAX_CMDS) {
        profile.degrade_flags |= NG_DEGRADE_PANIC_CHUNKS;
        return;
    }
    cmds[cmd_count++] = cmd;
}

static void emit_chunk(uint8_t material, wall_role_t role, int16_t x, int16_t top, uint16_t height, uint16_t depth, uint8_t width) {
    sprite_cmd_t cmd;
    if (height < 2 || width == 0) {
        return;
    }
    int16_t bot = top + (int16_t)height;
    if (top < VIEW_TOP) top = VIEW_TOP;
    if (bot > VIEW_BOTTOM) bot = VIEW_BOTTOM;
    if (bot <= top + 1) return;
    height = (uint16_t)(bot - top);

    cmd.card_id = (uint16_t)(material * 32u + role * 8u + ((uint8_t)(x >> 4) & 7u));
    cmd.x = x;
    cmd.y = top;
    cmd.height = height;
    cmd.depth = depth;
    cmd.width = width;
    cmd.x_shrink = (uint8_t)(width >= 16 ? 0x0f : (width - 1u));
    cmd.y_shrink = y_shrink_for_height(height);
    cmd.size_tiles = (uint8_t)((height + 15u) / 16u);
    if (cmd.size_tiles == 0) cmd.size_tiles = 1;
    if (cmd.size_tiles > CARD_TILE_COUNT) cmd.size_tiles = CARD_TILE_COUNT;
    cmd.palette = (uint8_t)(1u + role);
    cmd.role = (uint8_t)role;
    add_cmd(cmd);
}

static void emit_wall_role(const line_t *line, wall_role_t role, int16_t floor, int16_t ceil) {
    const vertex_t *v0 = &vertices[line->v0];
    const vertex_t *v1 = &vertices[line->v1];
    int16_t c = cos_q8(player.angle);
    int16_t s = sin_q8(player.angle);
    int16_t right_x = -s;
    int16_t right_y = c;
    int32_t dx0 = v0->x - player.x;
    int32_t dy0 = v0->y - player.y;
    int32_t dx1 = v1->x - player.x;
    int32_t dy1 = v1->y - player.y;
    int32_t z0 = (dx0 * c + dy0 * s) >> 8;
    int32_t z1 = (dx1 * c + dy1 * s) >> 8;
    int32_t sx0;
    int32_t sx1;
    int16_t x0;
    int16_t x1;
    uint16_t depth;
    int16_t top;
    int16_t bot;
    int16_t left;
    int16_t right;

    if (ceil <= floor || (z0 <= NEAR_Z && z1 <= NEAR_Z)) {
        return;
    }
    if (z0 <= NEAR_Z || z1 <= NEAR_Z) {
        return;
    }

    sx0 = ((dx0 * right_x + dy0 * right_y) >> 8);
    sx1 = ((dx1 * right_x + dy1 * right_y) >> 8);
    x0 = (int16_t)(SCREEN_W / 2 + (sx0 * FOCAL) / z0);
    x1 = (int16_t)(SCREEN_W / 2 + (sx1 * FOCAL) / z1);

    if (x0 == x1) {
        return;
    }
    if (x0 < x1) {
        left = x0;
        right = x1;
    } else {
        left = x1;
        right = x0;
    }
    if (right < 0 || left >= SCREEN_W) {
        return;
    }
    left = clamp_i16(left, 0, SCREEN_W - 1);
    right = clamp_i16(right, 0, SCREEN_W);
    if (right <= left) {
        return;
    }

    depth = (uint16_t)((z0 + z1) / 2);
    if (depth < NEAR_Z) {
        depth = NEAR_Z;
    }
    top = (int16_t)(HORIZON_Y - (((int32_t)(ceil - PLAYER_EYE) * PROJ_SCALE) / depth));
    bot = (int16_t)(HORIZON_Y - (((int32_t)(floor - PLAYER_EYE) * PROJ_SCALE) / depth));
    if (bot <= top) {
        return;
    }

    for (int16_t x = left; x < right; x += 16) {
        uint8_t width = (uint8_t)((right - x) >= 16 ? 16 : (right - x));
        emit_chunk(line->material, role, x, top, (uint16_t)(bot - top), depth, width);
    }
}

static void emit_line(const line_t *line) {
    int16_t front_floor = sector_floor(line->front);
    int16_t front_ceil = sector_ceil(line->front);
    if (line->back < 0) {
        emit_wall_role(line, ROLE_MIDDLE, front_floor, front_ceil);
    } else {
        int16_t back_floor = sector_floor(line->back);
        int16_t back_ceil = sector_ceil(line->back);
        if (back_ceil < front_ceil) {
            emit_wall_role(line, ROLE_UPPER, back_ceil, front_ceil);
        }
        if (back_floor > front_floor) {
            emit_wall_role(line, ROLE_LOWER, front_floor, back_floor);
        }
    }
}

static void sort_cmds_back_to_front(void) {
    for (uint8_t i = 1; i < cmd_count; i++) {
        sprite_cmd_t key = cmds[i];
        int8_t j = (int8_t)i - 1;
        while (j >= 0 && cmds[(uint8_t)j].depth < key.depth) {
            cmds[(uint8_t)(j + 1)] = cmds[(uint8_t)j];
            j--;
        }
        cmds[(uint8_t)(j + 1)] = key;
    }
}

static uint8_t compute_peak_scanline(void) {
    uint8_t peak = 0;
    for (uint16_t y = 0; y < SCREEN_H; y++) {
        uint8_t count = 0;
        for (uint8_t i = 0; i < cmd_count; i++) {
            int16_t top = cmds[i].y;
            int16_t bot = (int16_t)(cmds[i].y + cmds[i].height);
            if ((int16_t)y >= top && (int16_t)y < bot) {
                count++;
            }
        }
        if (count > peak) {
            peak = count;
        }
    }
    return peak;
}

static void render_scene(void) {
    cmd_count = 0;
    guard_asserted = 0;
    for (uint8_t i = 0; i < sizeof(lines) / sizeof(lines[0]); i++) {
        emit_line(&lines[i]);
    }
    sort_cmds_back_to_front();
    profile.sprites_emitted = cmd_count;
    profile.max_sprites_scanline = compute_peak_scanline();
    if (profile.max_sprites_scanline > 84u) {
        profile.degrade_flags |= NG_DEGRADE_PANIC_CHUNKS;
    }
}

static void write_tilemap(uint16_t sprite, const sprite_cmd_t *cmd) {
    *REG_VRAMMOD = 1;
    *REG_VRAMADDR = ADDR_SCB1 + (sprite * 64u);
    for (uint16_t i = 0; i < CARD_TILE_COUNT; i++) {
        *REG_VRAMRW = CARD_START_TILE + ((cmd->card_id + i) & 31u);
        *REG_VRAMRW = ((uint16_t)cmd->palette) << 8;
    }
    profile.scb1_words += CARD_TILE_COUNT * 2u;
}

static void upload_controls(uint8_t count) {
    *REG_VRAMMOD = 1;
    *REG_VRAMADDR = ADDR_SCB2 + SPRITE_BASE;
    for (uint8_t i = 0; i < count; i++) {
        *REG_VRAMRW = ctrl_scb2[i];
    }
    *REG_VRAMADDR = ADDR_SCB3 + SPRITE_BASE;
    for (uint8_t i = 0; i < count; i++) {
        *REG_VRAMRW = ctrl_scb3[i];
    }
    *REG_VRAMADDR = ADDR_SCB4 + SPRITE_BASE;
    for (uint8_t i = 0; i < count; i++) {
        *REG_VRAMRW = ctrl_scb4[i];
    }
    profile.scb_control_words += (uint16_t)count * 3u;
}

static void upload_scene(void) {
    uint8_t active_count = cmd_count > last_cmd_count ? cmd_count : last_cmd_count;
    if (active_count > MAX_CMDS) {
        active_count = MAX_CMDS;
    }

    for (uint8_t i = 0; i < active_count; i++) {
        if (i < cmd_count) {
            sprite_cmd_t *cmd = &cmds[i];
            uint16_t sprite = SPRITE_BASE + i;
            ctrl_scb2[i] = (uint16_t)((cmd->x_shrink << 8) | cmd->y_shrink);
            ctrl_scb3[i] = (uint16_t)((scb3_yfield_from_top(cmd->y) << 7) | (cmd->size_tiles & 0x3fu));
            ctrl_scb4[i] = (uint16_t)(((uint16_t)(cmd->x & 0x01ff)) << 7);
            if (!shadow_valid[i] || shadow_card_id[i] != cmd->card_id) {
                write_tilemap(sprite, cmd);
                shadow_card_id[i] = cmd->card_id;
                shadow_valid[i] = 1;
            }
        } else {
            ctrl_scb2[i] = 0;
            ctrl_scb3[i] = 0;
            ctrl_scb4[i] = 0;
            shadow_valid[i] = 0;
        }
    }
    upload_controls(active_count);
    last_cmd_count = cmd_count;

    profile.upload_ticks = (uint16_t)((profile.scb1_words + profile.scb_control_words) * STREAM_CYCLES_PER_WORD + ADDR_SET_CYCLES * 4u);
    if (profile.scb1_words + profile.scb_control_words > VBLANK_PRACTICAL_WORDS) {
        profile.degrade_flags |= NG_DEGRADE_PANIC_CHUNKS;
    }
}

static void draw_overlay(void) {
    char line[38];
    uint16_t scb_words = profile.scb1_words + profile.scb_control_words;
    uint16_t fit_frames = (uint16_t)((scb_words + VBLANK_PRACTICAL_WORDS - 1u) / VBLANK_PRACTICAL_WORDS);
    if (fit_frames == 0) fit_frames = 1;

    put_overlay_line(1, "DOOM AES M1 ONE ROOM");
    put_overlay_line(2, "DOOM AES M1  DPAD MOVE/TURN");
    snprintf(line, sizeof(line), "POS %4d,%4d ANG %02u DOOR %3d", player.x, player.y, player.angle, door.ceil);
    put_overlay_line(4, line);
    snprintf(line, sizeof(line), "SPR %2u PEAK %2u SCB %4u FIT %u", profile.sprites_emitted, profile.max_sprites_scanline, scb_words, fit_frames);
    put_overlay_line(5, line);
    snprintf(line, sizeof(line), "SCB1 %4u CTRL %3u RAM %5u", profile.scb1_words, profile.scb_control_words, profile.ram_high_water_bytes);
    put_overlay_line(6, line);
    snprintf(line, sizeof(line), "FPS %2u MIN12 %s BUD %s", (uint16_t)(60u / fit_frames),
             (60u / fit_frames) >= 12u ? "OK" : "FAIL",
             scb_words <= VBLANK_PRACTICAL_WORDS ? "OK" : "OVER");
    put_overlay_line(7, line);
    snprintf(line, sizeof(line), "MID/UP/LOW LIVE  ART %s", guard_asserted ? "GUARD" : "CLEAR");
    put_overlay_line(8, line);
    snprintf(line, sizeof(line), "DEG $%04X MIRROR $%06lX", profile.degrade_flags, (unsigned long)PROFILE_MIRROR_ADDR);
    put_overlay_line(9, line);
}

int main(void) {
    ng_cls();
    reset_state();
    ng_profile_reset(&profile, frame_id);
    init_palettes();
    bios_lsp_1st();

    for (;;) {
        ng_wait_vblank();
        ng_profile_reset(&profile, frame_id++);
        profile.ram_high_water_bytes = RAM_HWM_BYTES;

        update_controls();
        render_scene();
        upload_scene();
        draw_overlay();
        copy_profile_to_mirror();
    }
    return 0;
}
