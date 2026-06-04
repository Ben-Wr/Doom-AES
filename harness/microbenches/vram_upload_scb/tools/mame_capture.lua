-- Capture the M0B auto-sweep in MAME.
--
-- M0B is judged by the visible profile overlay. MAME's Neo Geo autoboot timing
-- leaves a narrow script window, so this tool logs the deterministic sweep math
-- immediately and captures the first cached-case overlay as native PNG proof.

local SWEEP_HOLD_FRAMES = 96
local FIRST_CAPTURE_FRAME = 72
local STREAM_CYCLES_PER_WORD = 12
local ADDR_SET_CYCLES = 16
local VBLANK_PRACTICAL_WORDS = 1664
local VBLANK_THEORETICAL_WORDS = 2560

local cases = {
    { mode = "MIXED",  target = 10,  scb1 = 1216, ctrl = 192, addr = 37, label = "mixed_40w25_24t" },
    { mode = "FULL",   target = 24,  scb1 = 1536, ctrl = 72,  addr = 27, label = "full_24" },
    { mode = "FULL",   target = 25,  scb1 = 1600, ctrl = 75,  addr = 28, label = "full_25" },
    { mode = "FULL",   target = 38,  scb1 = 2432, ctrl = 114, addr = 41, label = "full_38" },
    { mode = "FULL",   target = 39,  scb1 = 2496, ctrl = 117, addr = 42, label = "full_39" },
    { mode = "CTRL",   target = 320, scb1 = 0,    ctrl = 960, addr = 3,  label = "ctrl_320" },
    { mode = "ACTIVE", target = 24,  scb1 = 1536, ctrl = 72,  addr = 27, label = "active_24" },
    { mode = "ACTIVE", target = 25,  scb1 = 1600, ctrl = 75,  addr = 28, label = "active_25" },
    { mode = "ACTIVE", target = 38,  scb1 = 2432, ctrl = 114, addr = 41, label = "active_38" },
    { mode = "ACTIVE", target = 39,  scb1 = 2496, ctrl = 117, addr = 42, label = "active_39" },
}

local frame = 0
local captured = false
local log = io.open("build/m0b_capture.tsv", "w")
local error_log = io.open("build/m0b_capture_errors.log", "w")

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

local function capture_error(message)
    print("M0B_CAPTURE_ERROR\t" .. message)
    if error_log then
        error_log:write(message .. "\n")
        error_log:flush()
    end
end

local function snapshot(name)
    for _, screen in pairs(manager.machine.screens) do
        local err = screen:snapshot(name)
        if err then
            capture_error(string.format("snapshot failed: %s", tostring(err)))
        end
    end
end

local function row_for_case(index, c)
    local words = c.scb1 + c.ctrl
    local cycles = (words * STREAM_CYCLES_PER_WORD) + (c.addr * ADDR_SET_CYCLES)
    local cpw_x10 = math.floor((cycles * 10) / words)
    local fit_frames = math.floor((words + VBLANK_PRACTICAL_WORDS - 1) / VBLANK_PRACTICAL_WORDS)
    local safe_fps = math.floor(60 / fit_frames)
    local over_practical = words > VBLANK_PRACTICAL_WORDS and 1 or 0
    local over_theoretical = words > VBLANK_THEORETICAL_WORDS and 1 or 0
    local file = string.format("m0b_%02d_%s_%04dw.png", index, c.label, words)

    return file, string.format(
        "%02d\t%s\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\n",
        index,
        c.mode,
        c.target,
        words,
        c.scb1,
        c.ctrl,
        c.addr,
        cycles,
        cpw_x10,
        fit_frames,
        safe_fps,
        over_practical,
        over_theoretical)
end

if log then
    log:write("capture\tmode\ttarget\twords\tscb1\tctrl\taddr_sets\tcycles\tcpw_x10\tfit_frames\tsafe_fps\tover_practical\tover_theoretical\n")
end

for i, c in ipairs(cases) do
    local _, row = row_for_case(i, c)
    io.write("M0B_CASE\t" .. row)
    if log then
        log:write(row)
    end
end
if log then
    log:flush()
end

emu.add_machine_frame_notifier(function()
    local ok, err = pcall(function()
        frame = frame + 1

        if not captured and frame >= FIRST_CAPTURE_FRAME then
            local file, row = row_for_case(1, cases[1])
            snapshot(file)
            io.write("M0B_CAPTURE\t" .. row)
            captured = true
        end

        if captured or frame > FIRST_CAPTURE_FRAME + 120 then
            close_logs()
            manager.machine:exit()
        end
    end)

    if not ok then
        capture_error(tostring(err))
        close_logs()
        manager.machine:exit()
    end
end)
