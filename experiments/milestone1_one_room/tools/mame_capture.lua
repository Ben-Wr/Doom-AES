-- Native MAME gate screenshot for M1 after the deterministic auto-demo has
-- exercised turn, move, strafe, door open, and door close phases.

local frame = 0

emu.add_machine_frame_notifier(function()
    frame = frame + 1
    if frame == 960 then
        for _, screen in pairs(manager.machine.screens) do
            screen:snapshot("m1_gate.png")
        end
    end
    if frame > 1020 then
        manager.machine:exit()
    end
end)
