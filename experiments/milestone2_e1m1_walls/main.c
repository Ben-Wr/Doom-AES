#include <ngdevkit/neogeo.h>
#include <ngdevkit/ng-fix.h>
#include <ngdevkit/ng-video.h>
#include <stdint.h>
#include <stdio.h>

#include "ng_profile.h"

#ifndef M2_MAP_HEADER
#define M2_MAP_HEADER "e1m1_map_data.h"
#endif
#ifndef M2_WALL_CARDS_HEADER
#define M2_WALL_CARDS_HEADER "e1m1_wall_cards.h"
#endif

#include M2_MAP_HEADER
#include M2_WALL_CARDS_HEADER

#define CARD_START_TILE 256u
#define CARD_TILE_COUNT 32u
#define CARD_SOURCE_HEIGHT_PX 512u
#define SPRITE_BASE 32u
#define MAX_CMDS 96u
#define PROFILE_MIRROR_ADDR 0x10e080u

#define SCREEN_W 320
#define SCREEN_H 224
#define VIEW_TOP 96
#define VIEW_BOTTOM 224
#define HORIZON_Y 154
#define FOCAL 184
#define PROJ_SCALE 220
#define NEAR_Z 28
#define PLAYER_EYE 41
#define MOVE_STEP 10
#define STRAFE_STEP 8
#define TURN_STEP 2
#define COLLISION_RADIUS 36
#define VBLANK_PRACTICAL_WORDS 1664u
#define STREAM_CYCLES_PER_WORD 12u
#define ADDR_SET_CYCLES 16u
#define RAM_START_ADDR 0x100000u
#define RAM_STACK_TOP_ADDR 0x10f300u
#define BSP_MAX_DEPTH 64u
#define OCC_BUCKETS 32u
#define DEMO_CYCLE_FRAMES 960u
#define RENDER_PASS_COUNT 6u
#define TARGET_SPRITES 92u
#define TARGET_PEAK 94u
#define MAX_SCB1_REWRITES 20u
#define TEXTURE_COARSE_Z 260u
#define FAMILY_TEXTURE_LOD 5u
#define FAMILY_TEXTURE_Z 760u
#define FRUSTUM_MARGIN_PX 64
#define WALL_STRIP_WIDTH 16u
#define OVERLAY_UPDATE_MASK 3u

typedef enum wall_role_t {
    ROLE_MIDDLE = 0,
    ROLE_UPPER = 1,
    ROLE_LOWER = 2
} wall_role_t;

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
    uint8_t role;
} sprite_cmd_t;

typedef struct player_t {
    int16_t x;
    int16_t y;
    uint8_t angle;
} player_t;

static const int16_t sin_q8_table[64] = {
    0, 25, 50, 74, 98, 121, 142, 162, 181, 198, 213, 226, 237, 245, 251, 255,
    256, 255, 251, 245, 237, 226, 213, 198, 181, 162, 142, 121, 98, 74, 50, 25,
    0, -25, -50, -74, -98, -121, -142, -162, -181, -198, -213, -226, -237, -245, -251, -255,
    -256, -255, -251, -245, -237, -226, -213, -198, -181, -162, -142, -121, -98, -74, -50, -25
};

static sprite_cmd_t cmds[MAX_CMDS];
static uint16_t shadow_card_id[MAX_CMDS];
static uint8_t shadow_valid[MAX_CMDS];
static uint16_t ctrl_scb2[MAX_CMDS];
static uint16_t ctrl_scb3[MAX_CMDS];
static uint16_t ctrl_scb4[MAX_CMDS];
static uint16_t bucket_depth[OCC_BUCKETS];
static uint8_t bucket_filled[OCC_BUCKETS];
static player_t player;
static ng_profile_frame_t profile;
static uint16_t frame_id;
static uint8_t cmd_count;
static uint8_t last_cmd_count;
static uint8_t global_lod;
static uint8_t bucket_size;
static uint8_t auto_demo;
static uint16_t demo_frame;
static uint8_t pass_overflow;
static uint8_t scb1_rewrites;
static uint8_t scb1_deferred;
static uint8_t max_scb1_rewrites;
static uint8_t max_scb1_deferred;
static uint8_t role_counts[3];
static uint8_t max_roles[3];
static uint8_t max_peak;
static uint8_t max_sprites;
static uint16_t max_scb_words;
static uint8_t min_fps;
static uint16_t ram_high_water_bytes;
static uint16_t segs_visited;
static uint16_t subsectors_visited;
static uint16_t nodes_visited;
static uint16_t nodes_culled;
static uint8_t guard_asserted;

extern uint8_t _end;

static const uint8_t lod_bucket_sizes[RENDER_PASS_COUNT] = {
    16, 24, 32, 48, 64, 80
};

static int16_t sin_q8(uint8_t angle) {
    return sin_q8_table[angle & 63u];
}

static int16_t cos_q8(uint8_t angle) {
    return sin_q8_table[(angle + 16u) & 63u];
}

static int16_t vertex_x(uint16_t index) {
    return (int16_t)(m2_vertices[index].x >> 16);
}

static int16_t vertex_y(uint16_t index) {
    return (int16_t)(m2_vertices[index].y >> 16);
}

static int16_t clamp_i16(int16_t value, int16_t lo, int16_t hi) {
    if (value < lo) return lo;
    if (value > hi) return hi;
    return value;
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

static uint16_t scb3_yfield_from_top(int16_t top) {
    return (uint16_t)((496 - top) & 0x01ff);
}

static void copy_profile_to_mirror(void) {
    volatile uint16_t *dst = (volatile uint16_t *)PROFILE_MIRROR_ADDR;
    const uint16_t *src = (const uint16_t *)&profile;
    for (uint16_t i = 0; i < sizeof(profile) / sizeof(uint16_t); i++) {
        dst[i] = src[i];
    }
}

static uint32_t current_stack_pointer(void) {
#if defined(__m68k__)
    uint32_t sp;
    __asm__ volatile("move.l %%sp,%0" : "=r"(sp));
    return sp;
#else
    uint16_t stack_probe;
    return (uint32_t)(uintptr_t)&stack_probe;
#endif
}

static uint16_t current_ram_used_bytes(void) {
    uint32_t static_end = (uint32_t)(uintptr_t)&_end;
    uint32_t sp = current_stack_pointer();
    uint32_t static_bytes = 0;
    uint32_t stack_bytes = 0;
    uint32_t used;

    if (static_end > RAM_START_ADDR) {
        static_bytes = static_end - RAM_START_ADDR;
    }
    if (static_end > RAM_STACK_TOP_ADDR) {
        static_bytes = RAM_STACK_TOP_ADDR - RAM_START_ADDR;
    }
    if (sp < RAM_STACK_TOP_ADDR && sp > RAM_START_ADDR) {
        stack_bytes = RAM_STACK_TOP_ADDR - sp;
    } else if (sp <= RAM_START_ADDR) {
        stack_bytes = RAM_STACK_TOP_ADDR - RAM_START_ADDR;
    }

    used = static_bytes + stack_bytes;
    if (used > 0xffffu) {
        used = 0xffffu;
    }
    return (uint16_t)used;
}

static void update_ram_high_water(void) {
    uint16_t used = current_ram_used_bytes();
    if (used > ram_high_water_bytes) {
        ram_high_water_bytes = used;
    }
    profile.ram_high_water_bytes = ram_high_water_bytes;
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
        0x0000, 0x0eed, 0x0556, 0x0b33, 0x0ea4, 0x0596, 0x048b, 0x085a,
        0x0dd8, 0x0223, 0x0643, 0x0853, 0x0b74, 0x0575, 0x0478, 0x0eeb,
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
}

static void reset_state(void) {
    player.x = M2_PLAYER_START_X;
    player.y = M2_PLAYER_START_Y;
    player.angle = (uint8_t)(((uint32_t)M2_PLAYER_START_ANGLE * 64u) / 360u);
    cmd_count = 0;
    global_lod = 0;
    bucket_size = 16;
    auto_demo = 1;
    demo_frame = 0;
    max_peak = 0;
    max_sprites = 0;
    max_scb_words = 0;
    max_scb1_rewrites = 0;
    max_scb1_deferred = 0;
    min_fps = 60;
    last_cmd_count = MAX_CMDS;
    for (uint8_t i = 0; i < 3; i++) {
        max_roles[i] = 0;
        role_counts[i] = 0;
    }
    for (uint8_t i = 0; i < MAX_CMDS; i++) {
        shadow_card_id[i] = 0;
        shadow_valid[i] = 0;
    }
}

static uint8_t line_is_solid(uint16_t linedef_index) {
    const m2_linedef_t *line = &m2_linedefs[linedef_index];
    return (uint8_t)(line->left < 0 || line->right < 0);
}

static uint8_t point_near_linedef(int16_t px, int16_t py, uint16_t linedef_index) {
    const m2_linedef_t *line = &m2_linedefs[linedef_index];
    int16_t ax = vertex_x(line->v1);
    int16_t ay = vertex_y(line->v1);
    int16_t bx = vertex_x(line->v2);
    int16_t by = vertex_y(line->v2);
    int32_t vx = bx - ax;
    int32_t vy = by - ay;
    int32_t wx = px - ax;
    int32_t wy = py - ay;
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
    cx = ax + ((vx * t) >> 8);
    cy = ay + ((vy * t) >> 8);
    dx = px - cx;
    dy = py - cy;
    return (uint8_t)((dx * dx + dy * dy) < (COLLISION_RADIUS * COLLISION_RADIUS));
}

static uint8_t blocked_position(int16_t x, int16_t y) {
    if (x < M2_BOUNDS_MIN_X - 64 || x > M2_BOUNDS_MAX_X + 64 || y < M2_BOUNDS_MIN_Y - 64 || y > M2_BOUNDS_MAX_Y + 64) {
        return 1;
    }
    for (uint16_t i = 0; i < M2_LINEDEF_COUNT; i++) {
        if (line_is_solid(i) && point_near_linedef(x, y, i)) {
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

static uint8_t manual_input_active(void) {
    uint16_t held = bios_p1current & (CNT_UP | CNT_DOWN | CNT_LEFT | CNT_RIGHT | CNT_A | CNT_B);
    uint16_t changed = bios_p1change & CNT_D;
    return (uint8_t)(held || changed || (bios_statchange & CNT_START1));
}

static void update_auto_demo(void) {
    uint16_t phase = demo_frame % DEMO_CYCLE_FRAMES;
    int16_t fx = cos_q8(player.angle);
    int16_t fy = sin_q8(player.angle);
    int16_t rx = -fy;
    int16_t ry = fx;

    if (phase == 0) {
        player.x = M2_PLAYER_START_X;
        player.y = M2_PLAYER_START_Y;
        player.angle = (uint8_t)(((uint32_t)M2_PLAYER_START_ANGLE * 64u) / 360u);
    } else if (phase < 160) {
        if ((phase & 3u) == 0) {
            player.angle = (uint8_t)((player.angle + 1u) & 63u);
        }
    } else if (phase < 360) {
        try_move((int16_t)((fx * MOVE_STEP) >> 8), (int16_t)((fy * MOVE_STEP) >> 8));
    } else if (phase < 560) {
        if ((phase & 7u) == 0) {
            player.angle = (uint8_t)((player.angle - 1u) & 63u);
        }
        try_move((int16_t)((rx * STRAFE_STEP) >> 8), (int16_t)((ry * STRAFE_STEP) >> 8));
    } else if (phase < 760) {
        try_move((int16_t)(-((fx * MOVE_STEP) >> 8)), (int16_t)(-((fy * MOVE_STEP) >> 8)));
    } else {
        if ((phase & 3u) == 0) {
            player.angle = (uint8_t)((player.angle + 1u) & 63u);
        }
    }
    demo_frame++;
}

static void update_controls(void) {
    int16_t fx = cos_q8(player.angle);
    int16_t fy = sin_q8(player.angle);
    int16_t rx = -fy;
    int16_t ry = fx;

    if (auto_demo && manual_input_active()) {
        auto_demo = 0;
    }
    if (auto_demo) {
        update_auto_demo();
        return;
    }

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
    if (bios_p1change & CNT_D || bios_statchange & CNT_START1) {
        reset_state();
    }
}

static void reset_occlusion(void) {
    for (uint8_t i = 0; i < OCC_BUCKETS; i++) {
        bucket_filled[i] = 0;
        bucket_depth[i] = 0xffffu;
    }
}

static uint8_t bucket_for_x(int16_t x) {
    int16_t clamped = clamp_i16(x, 0, SCREEN_W - 1);
    uint8_t bucket = (uint8_t)(clamped / bucket_size);
    if (bucket >= OCC_BUCKETS) {
        bucket = OCC_BUCKETS - 1;
    }
    return bucket;
}

static uint8_t bucket_occluded(int16_t x, uint16_t depth) {
    uint8_t bucket = bucket_for_x(x);
    if (!bucket_filled[bucket]) {
        return 0;
    }
    return (uint8_t)(depth > bucket_depth[bucket] + 16u);
}

static uint8_t bbox_visible(const int16_t bbox[4]) {
    enum { BBOX_TOP = 0, BBOX_BOTTOM = 1, BBOX_LEFT = 2, BBOX_RIGHT = 3 };
    int16_t c = cos_q8(player.angle);
    int16_t s = sin_q8(player.angle);
    int16_t right_x = -s;
    int16_t right_y = c;
    int16_t xs[4] = { bbox[BBOX_LEFT], bbox[BBOX_RIGHT], bbox[BBOX_LEFT], bbox[BBOX_RIGHT] };
    int16_t ys[4] = { bbox[BBOX_TOP], bbox[BBOX_TOP], bbox[BBOX_BOTTOM], bbox[BBOX_BOTTOM] };
    int16_t min_x = SCREEN_W + FRUSTUM_MARGIN_PX;
    int16_t max_x = -FRUSTUM_MARGIN_PX;
    uint8_t front_corners = 0;

    if (player.x >= bbox[BBOX_LEFT] - 64 && player.x <= bbox[BBOX_RIGHT] + 64 &&
        player.y >= bbox[BBOX_BOTTOM] - 64 && player.y <= bbox[BBOX_TOP] + 64) {
        return 1;
    }

    for (uint8_t i = 0; i < 4; i++) {
        int32_t dx = xs[i] - player.x;
        int32_t dy = ys[i] - player.y;
        int32_t z = (dx * c + dy * s) >> 8;
        int32_t side;
        int16_t projected_x;
        if (z <= NEAR_Z) {
            continue;
        }
        front_corners++;
        side = (dx * right_x + dy * right_y) >> 8;
        projected_x = (int16_t)(SCREEN_W / 2 + (side * FOCAL) / z);
        if (projected_x < min_x) min_x = projected_x;
        if (projected_x > max_x) max_x = projected_x;
    }

    if (!front_corners) {
        return 0;
    }
    return (uint8_t)(max_x >= -FRUSTUM_MARGIN_PX && min_x < SCREEN_W + FRUSTUM_MARGIN_PX);
}

static void mark_bucket(int16_t x, uint16_t depth) {
    uint8_t bucket = bucket_for_x(x);
    if (!bucket_filled[bucket] || depth < bucket_depth[bucket]) {
        bucket_filled[bucket] = 1;
        bucket_depth[bucket] = depth;
    }
}

static void add_cmd(sprite_cmd_t cmd) {
    if (cmd_count >= MAX_CMDS) {
        pass_overflow = 1;
        return;
    }
    cmds[cmd_count++] = cmd;
}

static uint16_t select_wall_card(uint16_t texture_id, uint16_t u_offset, uint16_t depth) {
    uint16_t base;
    uint8_t count;
    uint8_t shift = 4u;
    if (texture_id >= M2_WALL_TEXTURE_COUNT) {
        return 0;
    }
    if (global_lod >= FAMILY_TEXTURE_LOD || depth > FAMILY_TEXTURE_Z) {
        return m2_texture_family_card[texture_id];
    }
    base = m2_texture_card_base[texture_id];
    count = m2_texture_card_count[texture_id];
    if (count <= 1u) {
        return base;
    }
    if (global_lod >= 2u || depth > TEXTURE_COARSE_Z) {
        shift = 5u;
    }
    return (uint16_t)(base + (((uint16_t)(u_offset >> shift)) % count));
}

static void clip_endpoint_to_near(int32_t *side, int32_t *z, int32_t *u, int32_t other_side, int32_t other_z, int32_t other_u) {
    int32_t denom = other_z - *z;
    int32_t numer;
    if (denom == 0) {
        return;
    }
    numer = NEAR_Z - *z;
    *side += ((other_side - *side) * numer) / denom;
    *u += ((other_u - *u) * numer) / denom;
    *z = NEAR_Z;
}

static void emit_chunk(uint16_t texture_id, wall_role_t role, int16_t x, int16_t top, uint16_t height, uint16_t depth, uint8_t width, uint16_t u_offset) {
    sprite_cmd_t cmd;
    int16_t bot;
    if (height < 2 || width == 0) {
        return;
    }
    if (bucket_occluded(x, depth)) {
        return;
    }
    bot = top + (int16_t)height;
    if (top < VIEW_TOP) top = VIEW_TOP;
    if (bot > VIEW_BOTTOM) bot = VIEW_BOTTOM;
    if (bot <= top + 1) return;
    height = (uint16_t)(bot - top);

    cmd.card_id = select_wall_card(texture_id, u_offset, depth);
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
    cmd.role = (uint8_t)role;
    if (cmd_count < MAX_CMDS) {
        role_counts[(uint8_t)role]++;
        mark_bucket(x, depth);
    }
    add_cmd(cmd);
}

static void emit_wall_role(uint16_t texture_id, int16_t texture_xoff, int16_t seg_offset, uint16_t wall_length, uint16_t v0_index, uint16_t v1_index, wall_role_t role, int16_t floor, int16_t ceil) {
    int16_t c = cos_q8(player.angle);
    int16_t s = sin_q8(player.angle);
    int16_t right_x = -s;
    int16_t right_y = c;
    int32_t dx0 = vertex_x(v0_index) - player.x;
    int32_t dy0 = vertex_y(v0_index) - player.y;
    int32_t dx1 = vertex_x(v1_index) - player.x;
    int32_t dy1 = vertex_y(v1_index) - player.y;
    int32_t z0 = (dx0 * c + dy0 * s) >> 8;
    int32_t z1 = (dx1 * c + dy1 * s) >> 8;
    int32_t side0;
    int32_t side1;
    int32_t u0;
    int32_t u1;
    int16_t x0;
    int16_t x1;
    int16_t unclipped_left;
    int16_t unclipped_right;
    int16_t left;
    int16_t right;
    uint16_t depth;
    int32_t screen_span;
    int32_t u_left;
    int32_t u_right;
    int32_t u_acc;
    int32_t u_step;
    int16_t top;
    int16_t bot;

    if (ceil <= floor || (z0 <= NEAR_Z && z1 <= NEAR_Z)) {
        return;
    }
    if (wall_length == 0) {
        wall_length = 1;
    }

    side0 = ((dx0 * right_x + dy0 * right_y) >> 8);
    side1 = ((dx1 * right_x + dy1 * right_y) >> 8);
    u0 = ((int32_t)texture_xoff + (int32_t)seg_offset) << 8;
    u1 = u0 + ((int32_t)wall_length << 8);

    if (z0 <= NEAR_Z) {
        clip_endpoint_to_near(&side0, &z0, &u0, side1, z1, u1);
    }
    if (z1 <= NEAR_Z) {
        clip_endpoint_to_near(&side1, &z1, &u1, side0, z0, u0);
    }
    if (z0 <= 0 || z1 <= 0) {
        return;
    }

    x0 = (int16_t)(SCREEN_W / 2 + (side0 * FOCAL) / z0);
    x1 = (int16_t)(SCREEN_W / 2 + (side1 * FOCAL) / z1);
    if (x0 == x1) {
        return;
    }
    if (x0 < x1) {
        unclipped_left = x0;
        unclipped_right = x1;
        u_left = u0;
        u_right = u1;
    } else {
        unclipped_left = x1;
        unclipped_right = x0;
        u_left = u1;
        u_right = u0;
    }
    if (unclipped_right < 0 || unclipped_left >= SCREEN_W) {
        return;
    }
    left = clamp_i16(unclipped_left, 0, SCREEN_W - 1);
    right = clamp_i16(unclipped_right, 0, SCREEN_W);
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

    screen_span = (int32_t)unclipped_right - unclipped_left;
    if (screen_span <= 0) {
        return;
    }
    u_step = (u_right - u_left) / screen_span;
    if (u_step == 0 && u_right != u_left) {
        u_step = (u_right > u_left) ? 1 : -1;
    }
    u_acc = u_left + u_step * ((int32_t)left - unclipped_left);
    for (int16_t x = left; x < right; x += WALL_STRIP_WIDTH) {
        uint8_t width = (uint8_t)((right - x) >= (int16_t)WALL_STRIP_WIDTH ? WALL_STRIP_WIDTH : (right - x));
        emit_chunk(texture_id, role, x, top, (uint16_t)(bot - top), depth, width, (uint16_t)(u_acc >> 8));
        u_acc += u_step * width;
    }
}

static void emit_seg(uint16_t seg_index) {
    const m2_seg_t *seg;
    const m2_linedef_t *line;
    int16_t front_side;
    int16_t back_side;
    int16_t front_sector_index;
    int16_t back_sector_index;
    const m2_sector_t *front_sector;
    const m2_sector_t *back_sector;
    if (seg_index >= M2_SEG_COUNT) {
        return;
    }
    segs_visited++;
    seg = &m2_segs[seg_index];
    if (seg->linedef >= M2_LINEDEF_COUNT) {
        return;
    }
    line = &m2_linedefs[seg->linedef];
    if (seg->side == 0) {
        front_side = line->right;
        back_side = line->left;
    } else {
        front_side = line->left;
        back_side = line->right;
    }
    if (front_side < 0 || front_side >= (int16_t)M2_SIDEDEF_COUNT) {
        return;
    }
    front_sector_index = m2_sidedefs[front_side].sector;
    if (front_sector_index < 0 || front_sector_index >= (int16_t)M2_SECTOR_COUNT) {
        return;
    }
    front_sector = &m2_sectors[front_sector_index];
    if (back_side < 0 || back_side >= (int16_t)M2_SIDEDEF_COUNT) {
        uint16_t texture_id = m2_sidedefs[front_side].middle;
        emit_wall_role(texture_id ? (uint16_t)(texture_id - 1u) : 0u, m2_sidedefs[front_side].xoff, seg->offset, seg->length, seg->v1, seg->v2, ROLE_MIDDLE, front_sector->floor, front_sector->ceil);
        return;
    }

    back_sector_index = m2_sidedefs[back_side].sector;
    if (back_sector_index < 0 || back_sector_index >= (int16_t)M2_SECTOR_COUNT) {
        uint16_t texture_id = m2_sidedefs[front_side].middle;
        emit_wall_role(texture_id ? (uint16_t)(texture_id - 1u) : 0u, m2_sidedefs[front_side].xoff, seg->offset, seg->length, seg->v1, seg->v2, ROLE_MIDDLE, front_sector->floor, front_sector->ceil);
        return;
    }
    back_sector = &m2_sectors[back_sector_index];
    if (m2_sidedefs[front_side].middle) {
        emit_wall_role((uint16_t)(m2_sidedefs[front_side].middle - 1u), m2_sidedefs[front_side].xoff, seg->offset, seg->length, seg->v1, seg->v2, ROLE_MIDDLE, front_sector->floor, front_sector->ceil);
    }
    if (back_sector->ceil < front_sector->ceil && m2_sidedefs[front_side].upper) {
        emit_wall_role((uint16_t)(m2_sidedefs[front_side].upper - 1u), m2_sidedefs[front_side].xoff, seg->offset, seg->length, seg->v1, seg->v2, ROLE_UPPER, back_sector->ceil, front_sector->ceil);
    }
    if (back_sector->floor > front_sector->floor && m2_sidedefs[front_side].lower) {
        emit_wall_role((uint16_t)(m2_sidedefs[front_side].lower - 1u), m2_sidedefs[front_side].xoff, seg->offset, seg->length, seg->v1, seg->v2, ROLE_LOWER, front_sector->floor, back_sector->floor);
    }
}

static void emit_subsector(uint16_t subsector_index) {
    const m2_subsector_t *subsector;
    if (subsector_index >= M2_SUBSECTOR_COUNT) {
        return;
    }
    subsectors_visited++;
    subsector = &m2_subsectors[subsector_index];
    for (uint16_t i = 0; i < subsector->seg_count; i++) {
        emit_seg((uint16_t)(subsector->first_seg + i));
    }
}

static int32_t node_side(const m2_node_t *node) {
    int32_t dx = player.x - node->x;
    int32_t dy = player.y - node->y;
    return dx * node->dy - dy * node->dx;
}

static void traverse_child(uint16_t child, uint8_t depth);

static void traverse_node(uint16_t node_index, uint8_t depth) {
    const m2_node_t *node;
    uint8_t near_child;
    uint8_t far_child;
    if (node_index >= M2_NODE_COUNT || depth > BSP_MAX_DEPTH) {
        return;
    }
    nodes_visited++;
    node = &m2_nodes[node_index];
    near_child = (node_side(node) <= 0) ? 0u : 1u;
    far_child = near_child ^ 1u;
    if (bbox_visible(node->bbox[near_child])) {
        traverse_child(node->child[near_child], (uint8_t)(depth + 1u));
    } else {
        nodes_culled++;
    }
    if (bbox_visible(node->bbox[far_child])) {
        traverse_child(node->child[far_child], (uint8_t)(depth + 1u));
    } else {
        nodes_culled++;
    }
}

static void traverse_child(uint16_t child, uint8_t depth) {
    if (child & 0x8000u) {
        emit_subsector((uint16_t)(child & 0x7fffu));
    } else {
        traverse_node(child, depth);
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

static void render_pass(void) {
    cmd_count = 0;
    guard_asserted = 0;
    pass_overflow = 0;
    segs_visited = 0;
    subsectors_visited = 0;
    nodes_visited = 0;
    nodes_culled = 0;
    role_counts[ROLE_MIDDLE] = 0;
    role_counts[ROLE_UPPER] = 0;
    role_counts[ROLE_LOWER] = 0;
    bucket_size = lod_bucket_sizes[global_lod];
    reset_occlusion();
    if (M2_NODE_COUNT) {
        traverse_node((uint16_t)(M2_NODE_COUNT - 1u), 0);
    } else {
        for (uint16_t i = 0; i < M2_SUBSECTOR_COUNT; i++) {
            emit_subsector(i);
        }
    }
    sort_cmds_back_to_front();
    profile.sprites_emitted = cmd_count;
    profile.max_sprites_scanline = compute_peak_scanline();
}

static void render_scene(void) {
    uint8_t selected_lod = RENDER_PASS_COUNT - 1u;
    uint8_t selected_overflow = 0;
    for (global_lod = 0; global_lod < RENDER_PASS_COUNT; global_lod++) {
        render_pass();
        selected_lod = global_lod;
        selected_overflow = pass_overflow;
        if (!pass_overflow && profile.sprites_emitted <= TARGET_SPRITES && profile.max_sprites_scanline <= TARGET_PEAK) {
            break;
        }
    }
    global_lod = selected_lod;
    if (global_lod > 0) {
        profile.degrade_flags |= NG_DEGRADE_MERGED_WALLS;
    }
    if (selected_overflow || profile.max_sprites_scanline > 96u || profile.sprites_emitted >= MAX_CMDS) {
        profile.degrade_flags |= NG_DEGRADE_PANIC_CHUNKS;
    }
}

static void write_tilemap(uint16_t sprite, uint16_t card_id) {
    if (card_id >= M2_WALL_CARD_COUNT) {
        card_id = 0;
    }
    *REG_VRAMMOD = 1;
    *REG_VRAMADDR = ADDR_SCB1 + (sprite * 64u);
    for (uint16_t i = 0; i < CARD_TILE_COUNT; i++) {
        *REG_VRAMRW = CARD_START_TILE + card_id * CARD_TILE_COUNT + (i & 31u);
        *REG_VRAMRW = 1u << 8;
    }
    profile.scb1_words += CARD_TILE_COUNT * 2u;
}

static void preload_wall_tilemaps(void) {
    for (uint8_t i = 0; i < MAX_CMDS; i++) {
        write_tilemap(SPRITE_BASE + i, 0);
        shadow_card_id[i] = 0;
        shadow_valid[i] = 1;
    }
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
    scb1_rewrites = 0;
    scb1_deferred = 0;
    if (active_count > MAX_CMDS) {
        active_count = MAX_CMDS;
    }
    for (uint8_t i = 0; i < active_count; i++) {
        if (i < cmd_count) {
            sprite_cmd_t *cmd = &cmds[i];
            uint16_t sprite = SPRITE_BASE + i;
            uint8_t visible = 1;
            if (!shadow_valid[i] || shadow_card_id[i] != cmd->card_id) {
                if (scb1_rewrites < MAX_SCB1_REWRITES) {
                    write_tilemap(sprite, cmd->card_id);
                    shadow_card_id[i] = cmd->card_id;
                    shadow_valid[i] = 1;
                    scb1_rewrites++;
                } else {
                    scb1_deferred++;
                    visible = 0;
                    profile.degrade_flags |= NG_DEGRADE_PANIC_CHUNKS;
                }
            }
            if (visible) {
                ctrl_scb2[i] = (uint16_t)((cmd->x_shrink << 8) | cmd->y_shrink);
                ctrl_scb3[i] = (uint16_t)((scb3_yfield_from_top(cmd->y) << 7) | (cmd->size_tiles & 0x3fu));
                ctrl_scb4[i] = (uint16_t)(((uint16_t)(cmd->x & 0x01ff)) << 7);
            } else {
                ctrl_scb2[i] = 0;
                ctrl_scb3[i] = 0;
                ctrl_scb4[i] = 0;
            }
        } else {
            ctrl_scb2[i] = 0;
            ctrl_scb3[i] = 0;
            ctrl_scb4[i] = 0;
        }
    }
    upload_controls(active_count);
    last_cmd_count = cmd_count;

    profile.upload_ticks = (uint16_t)((profile.scb1_words + profile.scb_control_words) * STREAM_CYCLES_PER_WORD + ADDR_SET_CYCLES * 4u);
    if (profile.scb1_words + profile.scb_control_words > VBLANK_PRACTICAL_WORDS) {
        profile.degrade_flags |= NG_DEGRADE_PANIC_CHUNKS;
    }
}

static const char *demo_label(void) {
    uint16_t phase = demo_frame % DEMO_CYCLE_FRAMES;
    if (!auto_demo) return "MANUAL";
    if (phase < 160) return "TURN";
    if (phase < 360) return "MOVE";
    if (phase < 560) return "STRAFE";
    if (phase < 760) return "BACK";
    return "SCAN";
}

static void update_max_metrics(uint16_t scb_words, uint16_t fit_frames) {
    uint8_t fps = (uint8_t)(60u / fit_frames);
    if (profile.max_sprites_scanline > max_peak) max_peak = profile.max_sprites_scanline;
    if (profile.sprites_emitted > max_sprites) max_sprites = (uint8_t)profile.sprites_emitted;
    if (scb_words > max_scb_words) max_scb_words = scb_words;
    if (scb1_rewrites > max_scb1_rewrites) max_scb1_rewrites = scb1_rewrites;
    if (scb1_deferred > max_scb1_deferred) max_scb1_deferred = scb1_deferred;
    if (fps < min_fps) min_fps = fps;
    for (uint8_t i = 0; i < 3; i++) {
        if (role_counts[i] > max_roles[i]) {
            max_roles[i] = role_counts[i];
        }
    }
}

static void draw_overlay(uint16_t scb_words, uint16_t fit_frames) {
    char line[38];

    put_overlay_line(1, "DOOM AES M2 E1M1 WALLS");
    snprintf(line, sizeof(line), "DEMO %-6s DPAD TAKES OVER", demo_label());
    put_overlay_line(2, line);
    snprintf(line, sizeof(line), "POS %5d,%5d ANG %02u LOD %u B%02u", player.x, player.y, player.angle, global_lod, bucket_size);
    put_overlay_line(4, line);
    snprintf(line, sizeof(line), "N%03u K%03u SS%03u SEG%03u", nodes_visited, nodes_culled, subsectors_visited, segs_visited);
    put_overlay_line(5, line);
    snprintf(line, sizeof(line), "SPR %02u PEAK %02u SCB %04u FIT %u", profile.sprites_emitted, profile.max_sprites_scanline, scb_words, fit_frames);
    put_overlay_line(6, line);
    snprintf(line, sizeof(line), "MAX P%02u S%02u W%04u MINFPS %02u", max_peak, max_sprites, max_scb_words, min_fps);
    put_overlay_line(7, line);
    snprintf(line, sizeof(line), "ROLE M%02u U%02u L%02u MXU%02u L%02u", role_counts[0], role_counts[1], role_counts[2], max_roles[1], max_roles[2]);
    put_overlay_line(8, line);
    snprintf(line, sizeof(line), "FPS %02u DEG $%04X RAM %5u", (uint16_t)(60u / fit_frames), profile.degrade_flags, profile.ram_high_water_bytes);
    put_overlay_line(9, line);
    snprintf(line, sizeof(line), "TEX R%02u D%02u MAXR%02u D%02u", scb1_rewrites, scb1_deferred, max_scb1_rewrites, max_scb1_deferred);
    put_overlay_line(10, line);
}

int main(void) {
    ng_cls();
    reset_state();
    ng_profile_reset(&profile, frame_id);
    init_palettes();
    bios_lsp_1st();
    preload_wall_tilemaps();
    ram_high_water_bytes = 0;

    for (;;) {
        uint16_t scb_words;
        uint16_t fit_frames;
        ng_wait_vblank();
        ng_profile_reset(&profile, frame_id++);
        update_ram_high_water();

        update_controls();
        update_ram_high_water();
        render_scene();
        update_ram_high_water();
        upload_scene();
        update_ram_high_water();
        scb_words = profile.scb1_words + profile.scb_control_words;
        fit_frames = (uint16_t)((scb_words + VBLANK_PRACTICAL_WORDS - 1u) / VBLANK_PRACTICAL_WORDS);
        if (fit_frames == 0) fit_frames = 1;
        update_max_metrics(scb_words, fit_frames);
        if ((frame_id & OVERLAY_UPDATE_MASK) == 0) {
            draw_overlay(scb_words, fit_frames);
            update_ram_high_water();
        }
        copy_profile_to_mirror();
    }
    return 0;
}
