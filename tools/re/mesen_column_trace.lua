-- Which code fills the VRAM upload staging buffer $7E:2C00 while Block 1-1 scrolls?
-- Mesen 2 test runner. CONFIG = { out = "C:/dir" } is prepended by the runner.
local OUT = (CONFIG or {}).out or "."
local WRAM = emu.memType.snesWorkRam
local log = io.open(OUT .. "/columns.txt", "w")
local frame, phase, phaseFrames = 0, "boot", 0
local held = nil
local writers = {}

local function rd16(a) return emu.read(a, WRAM) + emu.read(a + 1, WRAM) * 256 end
local function w(fmt, ...) log:write(string.format("%6d %-6s " .. fmt .. "\n", frame, phase, ...)) log:flush() end

emu.addEventCallback(function() if held then emu.setInput(held, 0) end end, emu.eventType.inputPolled)

emu.addMemoryCallback(function(address, value)
  if phase ~= "right" and phase ~= "left" then return end
  local s = emu.getState()
  local pc = string.format("%02X:%04X", s["cpu.k"], s["cpu.pc"])
  local key = phase .. " " .. pc
  writers[key] = (writers[key] or 0) + 1
  if writers[key] <= 3 then
    w("write $%06X=%02X by %s A=%04X X=%04X Y=%04X DB=%02X cam=%d", address, value, pc,
      s["cpu.a"], s["cpu.x"], s["cpu.y"], s["cpu.dbr"], rd16(0x1C))
  end
end, emu.callbackType.write, 0x7E2C00, 0x7E2C7F, emu.cpuType.snes, emu.memType.snesMemory)

local START = { start = true }
local script = {  -- {frame offset within phase, buttons, hold}
  { 240, START, 2 }, { 120, START, 2 }, { 240, START, 2 }, { 240, START, 2 },
}
local step = 1

emu.addEventCallback(function()
  frame = frame + 1
  phaseFrames = phaseFrames + 1
  if phase == "boot" then
    -- Press START for 2 frames every 150 frames until the level is playable.
    if emu.read(0x32, WRAM) == 4 and emu.read(0x70, WRAM) == 5 then
      held = nil
      if phaseFrames > 60 then
        phase = "right"; phaseFrames = 0; held = { right = true }
        w("gameplay reached, cam=%d", rd16(0x1C))
      end
    else
      if phaseFrames % 150 == 0 then held = START elseif phaseFrames % 150 == 2 then held = nil end
      if emu.read(0x32, WRAM) ~= 4 or emu.read(0x70, WRAM) ~= 5 then phaseFrames = phaseFrames % 150 end
    end
  elseif phase == "right" and phaseFrames == 380 then
    phase = "left"; phaseFrames = 0; held = { left = true }
    w("turning left, cam=%d", rd16(0x1C))
  elseif phase == "left" and phaseFrames == 380 then
    w("done, cam=%d", rd16(0x1C))
    local keys = {}
    for k in pairs(writers) do keys[#keys + 1] = k end
    table.sort(keys)
    for _, k in ipairs(keys) do w("writer %s count=%d", k, writers[k]) end
    log:close()
    emu.stop(0)
  end
  if frame % 300 == 0 then w("mode=%d step=%d p70=%d", emu.read(0x32, WRAM), emu.read(0x34, WRAM), emu.read(0x70, WRAM)) end
  if frame > 6000 then w("timeout") log:close() emu.stop(1) end
end, emu.eventType.endFrame)
