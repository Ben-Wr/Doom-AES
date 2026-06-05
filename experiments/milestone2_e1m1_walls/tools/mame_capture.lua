-- Native MAME gate capture for the M2 walls ROM.
--
-- The screenshot is useful evidence, but the milestone gate is the mirrored
-- profile struct. Sample it after boot settles and fail the make target if the
-- hard runtime limits are exceeded.

local frame = 0
local PROFILE_ADDR = 0x10e080
local SAMPLE_START = 120
local CAPTURE_PROFILE_SAMPLE = 60
local EXIT_PROFILE_SAMPLE = 1080
local MAX_FRAME = 4800
local MIN_FRAME_PROGRESSIONS = 108
local MAX_SPRITES = 92
local MAX_CMDS = 96
local MAX_SCANLINE = 96
local MAX_SCB_WORDS = 1664
local MAX_RAM_BYTES = 56 * 1024
local DEGRADE_PANIC_CHUNKS = 0x0010
local log = io.open("build/m2_profile.tsv", "w")
local error_log = io.open("build/m2_profile_errors.log", "w")
local summary_log = io.open("build/m2_profile_summary.tsv", "w")
local program_space = nil
local frame_subscription = nil
local profile_seen = false
local profile_payload_seen = false
local profile_samples = 0
local last_frame_id = nil
local frame_progressions = 0
local saw_fix_words = false
local saw_palette_words = false
local saw_scb_words = false
local captured_samples = {}
local max_sprites = 0
local max_scanline = 0
local max_scb_words = 0
local max_ram_bytes = 0
local max_degrade_flags = 0
local error_seen = {}
local errors = 0

local captures = {
    { sample = CAPTURE_PROFILE_SAMPLE, name = "m2_e1m1_turn_gate.png" },
    { sample = 300, name = "m2_e1m1_move_gate.png" },
    { sample = 520, name = "m2_e1m1_strafe_gate.png" },
    { sample = 740, name = "m2_e1m1_back_gate.png" },
    { sample = 960, name = "m2_e1m1_scan_gate.png" },
}

local function close_logs()
    if log then
        log:close()
        log = nil
    end
    if error_log then
        error_log:close()
        error_log = nil
    end
    if summary_log then
        summary_log:close()
        summary_log = nil
    end
end

local function record_error(message)
    if error_seen[message] then
        return
    end
    error_seen[message] = true
    errors = errors + 1
    print("M2_PROFILE_ERROR\t" .. message)
    if error_log then
        error_log:write(message .. "\n")
        error_log:flush()
    end
end

local function snapshot(name)
    for _, screen in pairs(manager.machine.screens) do
        local err = screen:snapshot(name)
        if err then
            record_error(string.format("snapshot %s failed: %s", name, tostring(err)))
        end
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
    local scb_words = p.scb1_words + p.scb_control_words
    if p.sprites_emitted > max_sprites then max_sprites = p.sprites_emitted end
    if p.max_sprites_scanline > max_scanline then max_scanline = p.max_sprites_scanline end
    if scb_words > max_scb_words then max_scb_words = scb_words end
    if p.ram_high_water_bytes > max_ram_bytes then max_ram_bytes = p.ram_high_water_bytes end
    max_degrade_flags = max_degrade_flags | p.degrade_flags

    if p.sprites_emitted > MAX_SPRITES then
        record_error(string.format("sprites_emitted %d > budget %d", p.sprites_emitted, MAX_SPRITES))
    end
    if p.sprites_emitted >= MAX_CMDS then
        record_error(string.format("sprites_emitted %d hit MAX_CMDS %d", p.sprites_emitted, MAX_CMDS))
    end
    if p.max_sprites_scanline > MAX_SCANLINE then
        record_error(string.format("max_sprites_scanline %d > %d", p.max_sprites_scanline, MAX_SCANLINE))
    end
    if scb_words > MAX_SCB_WORDS then
        record_error(string.format("scb_words %d > %d", scb_words, MAX_SCB_WORDS))
    end
    if p.ram_high_water_bytes == 0 then
        record_error("ram_high_water_bytes is zero after profile start")
    end
    if p.ram_high_water_bytes > MAX_RAM_BYTES then
        record_error(string.format("ram_high_water_bytes %d > %d", p.ram_high_water_bytes, MAX_RAM_BYTES))
    end
    if (p.degrade_flags & DEGRADE_PANIC_CHUNKS) ~= 0 then
        record_error(string.format("panic degrade flag set: 0x%04X", p.degrade_flags))
    end
end

local function profile_ready(p)
    return p.frame_id ~= 0 and p.sprites_emitted ~= 0 and p.ram_high_water_bytes ~= 0 and (p.scb1_words + p.scb_control_words) ~= 0
end

local function profile_has_payload(p)
    return p.sprites_emitted ~= 0 or p.ram_high_water_bytes ~= 0 or (p.scb1_words + p.scb_control_words) ~= 0
end

local function update_profile_contract(p)
    if last_frame_id ~= nil and p.frame_id ~= last_frame_id then
        frame_progressions = frame_progressions + 1
    end
    last_frame_id = p.frame_id
    if p.fix_words ~= 0 then saw_fix_words = true end
    if p.palette_words ~= 0 then saw_palette_words = true end
    if (p.scb1_words + p.scb_control_words) ~= 0 then saw_scb_words = true end
end

local function maybe_capture()
    for _, capture in ipairs(captures) do
        if profile_samples >= capture.sample and not captured_samples[capture.sample] then
            snapshot(capture.name)
            captured_samples[capture.sample] = true
        end
    end
end

local function write_summary()
    local captured = 0
    for _, capture in ipairs(captures) do
        if captured_samples[capture.sample] then
            captured = captured + 1
        end
    end
    if summary_log then
        summary_log:write("profile_samples\tframe_progressions\tmax_sprites\tmax_scanline\tmax_scb_words\tmax_ram_bytes\tmax_degrade_flags\tcaptures\n")
        summary_log:write(string.format("%d\t%d\t%d\t%d\t%d\t%d\t0x%04X\t%d\n",
            profile_samples,
            frame_progressions,
            max_sprites,
            max_scanline,
            max_scb_words,
            max_ram_bytes,
            max_degrade_flags,
            captured))
        summary_log:flush()
    end
    print(string.format(
        "M2_PROFILE_SUMMARY\tsamples=%d\tframe_progressions=%d\tmax_sprites=%d\tmax_scanline=%d\tmax_scb_words=%d\tmax_ram=%d\tdegrade=0x%04X\tcaptures=%d",
        profile_samples,
        frame_progressions,
        max_sprites,
        max_scanline,
        max_scb_words,
        max_ram_bytes,
        max_degrade_flags,
        captured))
end

local function assert_contract()
    if not profile_payload_seen then
        record_error("profile mirror never exposed runtime payload fields")
    end
    if not profile_seen then
        record_error("profile mirror never satisfied required live fields")
    end
    if frame_progressions < MIN_FRAME_PROGRESSIONS then
        record_error(string.format("profile frame_id progressed %d times; need >= %d for 6 fps worst-case gate", frame_progressions, MIN_FRAME_PROGRESSIONS))
    end
    if not saw_scb_words then
        record_error("profile scb word fields stayed zero")
    end
    if not saw_fix_words then
        record_error("profile fix_words stayed zero")
    end
    if not saw_palette_words then
        record_error("profile palette_words stayed zero")
    end
    for _, capture in ipairs(captures) do
        if not captured_samples[capture.sample] then
            record_error(string.format("missing worst-case capture sample %d (%s)", capture.sample, capture.name))
        end
    end
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
            update_profile_contract(p)
            if profile_has_payload(p) then
                profile_payload_seen = true
                assert_profile(p)
            end
            if profile_ready(p) then
                profile_seen = true
            end
            if profile_seen then
                profile_samples = profile_samples + 1
                maybe_capture()
            end
        end

        if profile_seen and profile_samples >= EXIT_PROFILE_SAMPLE then
            assert_contract()
            write_summary()
            if frame_subscription then
                frame_subscription:unsubscribe()
                frame_subscription = nil
            end
            close_logs()
            manager.machine:exit()
        end
        if frame > MAX_FRAME then
            assert_contract()
            write_summary()
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
