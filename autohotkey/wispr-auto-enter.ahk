#Requires AutoHotkey v2.0
#SingleInstance Force
Persistent

; Wispr Flow auto-Enter for Windows. The sibling of hammerspoon/init.lua, which
; does the same on macOS: after you finish a Wispr dictation hold, press Enter
; once Wispr's clipboard-paste lands, so dictating into a chat/prompt box
; auto-submits.
;
; How it works: Wispr pastes via Ctrl+V (clipboard). We "arm" on releasing a
; dictation hold, then the next clipboard change within ARM_WINDOW_MS fires
; Enter. Arming means an ordinary Ctrl+C copy never triggers a stray Enter.
;
; The trigger keys below are Wispr's defaults from %APPDATA%\Wispr Flow\config.json:
;   ptt              = Left Ctrl + Left Win  (VK 162+91)  -> TRIGGER_COMBO
;   modifierShortcut = Left Alt              (VK 164)     -> TRIGGER_ALT
; If your Wispr hotkeys differ, adjust the GetKeyState checks in PollTriggers.

; ===== Config (edit these) =====
ARM_WINDOW_MS    := 6000   ; max wait from dictation-end to paste before we give up
PASTE_SETTLE_MS  := 150    ; pause after clipboard change so the paste lands before Enter
MIN_HOLD_MS      := 200    ; ignore quick taps of trigger keys (Alt+Tab, Win shortcuts)
TRIGGER_COMBO    := true   ; arm on Left Ctrl + Left Win hold (Wispr "ptt")
TRIGGER_ALT      := true   ; arm on Left Alt hold (Wispr "modifierShortcut")
; ===============================

global armed := false, armedAt := 0
global comboWasDown := false, comboDownAt := 0
global altWasDown := false, altDownAt := 0

SetTimer(PollTriggers, 40)
OnClipboardChange(ClipChanged)

PollTriggers(*) {
    global
    if (TRIGGER_COMBO) {
        comboDown := GetKeyState("LControl", "P") && GetKeyState("LWin", "P")
        if (comboDown && !comboWasDown)
            comboDownAt := A_TickCount
        else if (!comboDown && comboWasDown && A_TickCount - comboDownAt >= MIN_HOLD_MS)
            Arm()
        comboWasDown := comboDown
    }
    if (TRIGGER_ALT) {
        altDown := GetKeyState("LAlt", "P")
        if (altDown && !altWasDown)
            altDownAt := A_TickCount
        else if (!altDown && altWasDown && A_TickCount - altDownAt >= MIN_HOLD_MS)
            Arm()
        altWasDown := altDown
    }
}

Arm() {
    global armed, armedAt
    armed := true
    armedAt := A_TickCount
}

ClipChanged(dataType) {
    global armed, armedAt, ARM_WINDOW_MS, PASTE_SETTLE_MS
    if (!armed)
        return
    armed := false
    if (A_TickCount - armedAt > ARM_WINDOW_MS)
        return
    Sleep(PASTE_SETTLE_MS)
    Send("{Enter}")
}
