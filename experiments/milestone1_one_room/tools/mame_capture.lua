-- Native MAME smoke screenshot for M1.

local frame = 0

emu.add_machine_frame_notifier(function()
    frame = frame + 1
    if frame == 180 then
        for _, screen in pairs(manager.machine.screens) do
            screen:snapshot("m1_smoke.png")
        end
    end
    if frame > 210 then
        manager.machine:exit()
    end
end)
