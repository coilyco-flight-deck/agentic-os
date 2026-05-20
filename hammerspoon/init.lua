-- Wispr Flow auto-submit in Warp.
-- Watches for Fn release, then waits for Wispr's clipboard paste,
-- then sends Return. Robust to Wispr's variable cloud latency.

-- Both Warp channels recognized as Warp-frontmost so Wispr auto-submit works
-- whether the daily-driver Preview or the fallback Stable is focused.
-- See agentic-os/warp/README.md for the channel-split rationale.
local WARP_BUNDLES = {
  ["dev.warp.Warp-Preview"] = true,
  ["dev.warp.Warp-Stable"]  = true,
}
local ARM_TIMEOUT = 5.0
local POLL_INTERVAL = 0.05

local state = {
  armed = false,
  armedAt = 0,
  baselineChangeCount = 0,
}

local function isWarpFrontmost()
  local app = hs.application.frontmostApplication()
  return app and WARP_BUNDLES[app:bundleID()] == true
end

local function disarm()
  state.armed = false
end

local prevFnDown = false
flagsTap = hs.eventtap.new({hs.eventtap.event.types.flagsChanged}, function(e)
  local flags = e:getFlags()
  local fnDown = flags.fn or false
  if prevFnDown and not fnDown then
    if isWarpFrontmost() and not flags.alt then
      state.armed = true
      state.armedAt = hs.timer.secondsSinceEpoch()
      state.baselineChangeCount = hs.pasteboard.changeCount()
    end
  end
  prevFnDown = fnDown
  return false
end)
flagsTap:start()

pasteTimer = hs.timer.doEvery(POLL_INTERVAL, function()
  if not state.armed then return end
  if hs.timer.secondsSinceEpoch() - state.armedAt > ARM_TIMEOUT then
    disarm()
    return
  end
  if hs.pasteboard.changeCount() > state.baselineChangeCount then
    if isWarpFrontmost() then
      hs.timer.doAfter(0.05, function()
        hs.eventtap.keyStroke({}, "return", 0)
      end)
    end
    disarm()
  end
end)

hs.alert.show("Wispr auto-submit loaded")
