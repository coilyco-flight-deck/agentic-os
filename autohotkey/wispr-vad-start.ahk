#Requires AutoHotkey v2.0
#SingleInstance Force
Persistent

; Start-signal sender for the hands-free VAD daemon (../voice/vad-daemon.py).
;
; The daemon sits listening on UDP 127.0.0.1:5555 but does nothing until something
; tells it a dictation session has begun. This hotkey is that something: one press
; toggles Wispr hands-free ON (Ctrl+Win+Space) and fires "start" to the daemon, which
; then watches the mic and presses Enter once you stop talking. It replaces the
; VoiceAttack wiring described in voice/README.md - no VoiceAttack needed.
;
; Flow: press START_HOTKEY -> talk -> stop. The daemon detects the trailing silence
; and commits (toggle off + Enter). You never press anything to end it.
;
; The sibling autohotkey/wispr-auto-enter.ahk covers push-to-talk mode; this covers
; hands-free toggle mode. Run both - they don't conflict (that script ignores the
; Ctrl+Win+Space chord this one sends, by design).

; ===== Config =====
VAD_HOST := "127.0.0.1"
VAD_PORT := 5555
; Hotkeys: ^ = Ctrl, ! = Alt, # = Win, + = Shift. Change these to taste, but avoid
; Ctrl+Alt (^!) combos: on layouts where Ctrl+Alt == AltGr, Windows consumes the
; chord and the hotkey only fires intermittently (~1 in 3). Ctrl+Shift is safe.
START_HOTKEY  := "^+Space"   ; Ctrl+Shift+Space: begin a hands-free dictation session
CANCEL_HOTKEY := "^+["        ; Ctrl+Shift+[: abort without submitting ("scratch that")
GO_HOTKEY     := "^+]"        ; Ctrl+Shift+]: submit now, skip the silence wait
; ==================

Hotkey(START_HOTKEY, StartSession)
Hotkey(CANCEL_HOTKEY, (*) => Flash("cancel", SendUDP("cancel")))
Hotkey(GO_HOTKEY, (*) => Flash("go", SendUDP("go")))
TrayTip("Loaded. " START_HOTKEY " starts a dictation session.", "VAD start sender")

StartSession(*) {
    Send("^#{Space}")        ; toggle Wispr hands-free on
    ok := SendUDP("start")    ; tell the daemon to begin watching the mic
    Flash("start", ok)
}

; Brief on-screen confirmation that a hotkey fired and whether the UDP send worked.
; Purely diagnostic - remove the Flash() calls once the binding is confirmed.
Flash(label, ok) {
    ToolTip("VAD: " label " " (ok ? "sent" : "SEND FAILED"))
    SetTimer(() => ToolTip(), -1200)
}

; --- UDP via winsock, so a keypress never pays PowerShell startup latency ---

SendUDP(msg) {
    global VAD_HOST, VAD_PORT
    static started := WSAStartup()
    sock := DllCall("ws2_32\socket", "int", 2, "int", 2, "int", 17, "ptr")  ; AF_INET, SOCK_DGRAM, IPPROTO_UDP
    if (sock = -1)
        return false
    addr := Buffer(16, 0)
    NumPut("ushort", 2, addr, 0)                                            ; sin_family = AF_INET
    NumPut("ushort", DllCall("ws2_32\htons", "ushort", VAD_PORT, "ushort"), addr, 2)
    NumPut("uint", DllCall("ws2_32\inet_addr", "astr", VAD_HOST, "uint"), addr, 4)
    size := StrPut(msg, "utf-8")            ; includes the null terminator
    buf := Buffer(size)
    StrPut(msg, buf, "utf-8")
    ; Send size-1 bytes: the daemon matches b"start" exactly, and a trailing null
    ; would survive .strip() and break the handler lookup.
    sent := DllCall("ws2_32\sendto", "ptr", sock, "ptr", buf, "int", size - 1, "int", 0, "ptr", addr, "int", 16, "int")
    DllCall("ws2_32\closesocket", "ptr", sock)
    return sent != -1
}

WSAStartup() {
    wsaData := Buffer(408, 0)
    return DllCall("ws2_32\WSAStartup", "ushort", 0x0202, "ptr", wsaData)
}
