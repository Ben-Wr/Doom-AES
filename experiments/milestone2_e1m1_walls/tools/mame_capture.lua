-- Native MAME gate capture for the M2 walls ROM.
--
-- The screenshot is useful evidence, but the milestone gate is the mirrored
-- profile struct. Sample it after boot settles and fail the make target if the
-- hard runtime limits are exceeded.

local frame = 0
local PROFILE_ADDR = 0x10e080
local SAMPLE_START = 120
local CAPTURE_PROFILE_SAMPLE = 60
local EXIT_PROFILE_SAMPLE = 120
local MAX_FRAME = 3600
local MAX_SPRITES = 96
local MAX_SCANLINE = 96
local MAX_RAM_BYTES = 56 * 1024
local log = io.open("build/m2_profile.tsv", "w")
local error_log = io.open("build/m2_profile_errors.log", "w")
local program_space = nil
local frame_subscription = nil
local profile_seen = false
local profile_samples = 0
local captured = false
local errors = 0

local function close_logs()
    if log then
        log:close()
        log = nil
    end
    if error_log then
        error_log:close()
        error_log = nil
    end
end

local function record_error(message)
    errors = errors + 1
    print("M2_PROFILE_ERROR\t" .. message)
    if error_log then
        error_log:write(message .. "\n")
        error_log:flush()
    end
end

local function maincpu_space()
    if program_space then
        return program_space
    end
    local cpu = manager.machine.devices[":maincpu"]
    if not cpu then
        error("maincpu device not found")
    end
    program_space = cpu.spaces["program"]
    if not program_space then
        error("maincpu program space not found")
    end
    return program_space
end

local function read_u16(addr)
    local space = maincpu_space()
    if space.read_u16 then
        return space:read_u16(addr)
    end
    if space.read_word then
        return space:read_word(addr)
    end
    error("program space cannot read u16")
end

local function read_profile()
    return {
        frame_id = read_u16(PROFILE_ADDR + 0),
        game_ticks = read_u16(PROFILE_ADDR + 2),
        render_ticks = read_u16(PROFILE_ADDR + 4),
        upload_ticks = read_u16(PROFILE_ADDR + 6),
        sprites_emitted = read_u16(PROFILE_ADDR + 8),
        max_sprites_scanline = read_u16(PROFILE_ADDR + 10),
        scb1_words = read_u16(PROFILE_ADDR + 12),
        scb_control_words = read_u16(PROFILE_ADDR + 14),
        fix_words = read_u16(PROFILE_ADDR + 16),
        palette_words = read_u16(PROFILE_ADDR + 18),
        ram_high_water_bytes = read_u16(PROFILE_ADDR + 20),
        degrade_flags = read_u16(PROFILE_ADDR + 22),
    }
end

local function write_profile_row(p)
    if not log then
        return
    end
    log:write(string.format(
        "%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\n",
        frame,
        p.frame_id,
        p.game_ticks,
        p.render_ticks,
        p.upload_ticks,
        p.sprites_emitted,
        p.max_sprites_scanline,
        p.scb1_words,
        p.scb_control_words,
        p.fix_words,
        p.palette_words,
        p.ram_high_water_bytes,
        p.degrade_flags))
end

local function assert_profile(p)
    if p.sprites_emitted > MAX_SPRITES then
        record_error(string.format("sprites_emitted %d > %d", p.sprites_emitted, MAX_SPRITES))
    end
    if p.max_sprites_scanline > MAX_SCANLINE then
        record_error(string.format("max_sprites_scanline %d > %d", p.max_sprites_scanline, MAX_SCANLINE))
    end
    if p.ram_high_water_bytes == 0 then
        record_error("ram_high_water_bytes is zero after profile start")
    end
    if p.ram_high_water_bytes > MAX_RAM_BYTES then
        record_error(string.format("ram_high_water_bytes %d > %d", p.ram_high_water_bytes, MAX_RAM_BYTES))
    end
end

local function profile_ready(p)
    return p.frame_id ~= 0 or p.sprites_emitted ~= 0 or p.ram_high_water_bytes ~= 0
end

if log then
    log:write("mame_frame\tframe_id\tgame_ticks\trender_ticks\tupload_ticks\tsprites_emitted\tmax_sprites_scanline\tscb1_words\tscb_control_words\tfix_words\tpalette_words\tram_high_water_bytes\tdegrade_flags\n")
end

frame_subscription = emu.add_machine_frame_notifier(function()
    local ok, err = pcall(function()
        frame = frame + 1
        if frame >= SAMPLE_START then
            local p = read_profile()
            write_profile_row(p)
            if profile_ready(p) then
                profile_seen = true
            end
            if profile_seen then
                profile_samples = profile_samples + 1
                assert_profile(p)
                if not captured and profile_samples >= CAPTURE_PROFILE_SAMPLE then
                    for _, screen in pairs(manager.machine.screens) do
                        screen:snapshot("m2_e1m1_gate.png")
                    end
                    captured = true
                end
            end
        end

        if profile_seen and profile_samples >= EXIT_PROFILE_SAMPLE then
            if frame_subscription then
                frame_subscription:unsubscribe()
                frame_subscription = nil
            end
            close_logs()
            manager.machine:exit()
        end
        if frame > MAX_FRAME then
            if not profile_seen then
                record_error("profile mirror never became nonzero")
            end
            if not captured then
                record_error("profile became live but capture sample was not reached")
            end
            if frame_subscription then
                frame_subscription:unsubscribe()
                frame_subscription = nil
            end
            close_logs()
            manager.machine:exit()
        end
    end)

    if not ok then
        record_error(tostring(err))
        if frame_subscription then
            frame_subscription:unsubscribe()
            frame_subscription = nil
        end
        close_logs()
        manager.machine:exit()
    end
end)
