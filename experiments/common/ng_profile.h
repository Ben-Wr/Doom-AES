#ifndef DOOM_AES_NG_PROFILE_H
#define DOOM_AES_NG_PROFILE_H

#include <stdint.h>

typedef struct ng_profile_frame_t {
    uint16_t frame_id;
    uint16_t game_ticks;
    uint16_t render_ticks;
    uint16_t upload_ticks;
    uint16_t sprites_emitted;
    uint16_t max_sprites_scanline;
    uint16_t scb1_words;
    uint16_t scb_control_words;
    uint16_t fix_words;
    uint16_t palette_words;
    uint16_t ram_high_water_bytes;
    uint16_t degrade_flags;
} ng_profile_frame_t;

enum {
    NG_DEGRADE_MERGED_WALLS = 1u << 0,
    NG_DEGRADE_DROPPED_DECOR = 1u << 1,
    NG_DEGRADE_THINNED_THINGS = 1u << 2,
    NG_DEGRADE_DROPPED_SKY = 1u << 3,
    NG_DEGRADE_PANIC_CHUNKS = 1u << 4
};

static inline void ng_profile_reset(ng_profile_frame_t *profile, uint16_t frame_id) {
    profile->frame_id = frame_id;
    profile->game_ticks = 0;
    profile->render_ticks = 0;
    profile->upload_ticks = 0;
    profile->sprites_emitted = 0;
    profile->max_sprites_scanline = 0;
    profile->scb1_words = 0;
    profile->scb_control_words = 0;
    profile->fix_words = 0;
    profile->palette_words = 0;
    profile->ram_high_water_bytes = 0;
    profile->degrade_flags = 0;
}

#endif

