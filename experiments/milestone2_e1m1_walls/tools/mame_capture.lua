-- Native MAME gate screenshot for the M2 E1M1 placeholder-wall ROM.

local frame = 0

emu.add_machine_frame_notifier(function()
    frame = frame + 1
    if frame == 960 then
        for _, screen in pairs(manager.machine.screens) do
            screen:snapshot("m2_e1m1_gate.png")
        end
    end
    if frame > 1020 then
        manager.machine:exit()
    end
end)
