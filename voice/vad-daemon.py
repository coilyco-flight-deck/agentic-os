#!/usr/bin/env python3
"""Voice-activity-detection daemon for Wispr Flow hands-free mode.

The clipboard-based siblings (autohotkey/wispr-auto-enter.ahk, hammerspoon/init.lua)
press Enter after Wispr's paste lands, but they arm on *releasing* a push-to-talk
hold. Hands-free toggle mode (Ctrl+Win+Space on, Ctrl+Win+Space off) has no release
gesture to arm on, so those tools can't close it. This daemon does: it watches the
raw hardware mic, and when ~2s of silence follows speech it generates the end gesture
itself - fires the Wispr commit chord, then Enter. You stop talking and the prompt sends.

VoiceAttack (or any launcher) signals "start" over UDP when a hands-free session opens.
The daemon detects the trailing silence and commits. "cancel" aborts without sending,
"go" commits immediately. Windows-only for the key presses; on other platforms it logs
the keystrokes it would send so the VAD pipeline can be exercised anywhere.
"""

import argparse
import ctypes
import logging
import platform
import queue
import socket
import threading
import time

import numpy as np
import sounddevice as sd
import torch

SAMPLE_RATE = 16000
FRAME_SIZE = 512  # silero-vad requires exactly this many samples per call at 16kHz

# Windows virtual-key codes. Ctrl+Win+Space toggles Wispr hands-free; Enter submits.
VK_CONTROL, VK_LWIN, VK_SPACE, VK_RETURN = 0x11, 0x5B, 0x20, 0x0D
KEYEVENTF_KEYUP = 0x0002

IS_WINDOWS = platform.system() == "Windows"

log = logging.getLogger("vad-daemon")


class Keyboard:
    """Synthesizes the Wispr keystrokes. Falls back to dry-run logging off Windows."""

    def __init__(self):
        self._user32 = ctypes.windll.user32 if IS_WINDOWS else None

    def _tap(self, vk):
        self._user32.keybd_event(vk, 0, 0, 0)
        self._user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)

    def chord(self):
        """Ctrl+Win+Space: toggles the active Wispr hands-free session off."""
        if not IS_WINDOWS:
            log.info("[dry-run] chord Ctrl+Win+Space")
            return
        for vk in (VK_CONTROL, VK_LWIN, VK_SPACE):
            self._user32.keybd_event(vk, 0, 0, 0)
        for vk in (VK_SPACE, VK_LWIN, VK_CONTROL):  # release in reverse
            self._user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)

    def enter(self):
        if not IS_WINDOWS:
            log.info("[dry-run] Enter")
            return
        self._tap(VK_RETURN)

    def clipboard_seq(self):
        """Monotonic counter that bumps on every clipboard change. Lets us detect
        Wispr's paste landing instead of guessing at a fixed delay. 0 off Windows."""
        return self._user32.GetClipboardSequenceNumber() if IS_WINDOWS else 0


class VadDaemon:
    def __init__(self, args):
        self.silence_timeout = args.silence_timeout
        self.vad_threshold = args.vad_threshold
        self.commit_delay = args.commit_delay
        self.paste_timeout = args.paste_timeout
        self.device = args.device
        self.port = args.port
        self.verbose = args.verbose

        self.kbd = Keyboard()
        self._lock = threading.Lock()
        self._q = queue.Queue()
        self._stop = threading.Event()

        # The mic stream is opened only for the duration of a session (start ->
        # commit/cancel), so at rest the mic is released and the OS in-use
        # indicator goes dark. Guarded by its own lock since open/close are
        # driven from both the signal-listener and worker threads.
        self._stream = None
        self._stream_lock = threading.Lock()

        # Guarded by _lock. last_speech == 0 means "no speech seen this session yet",
        # which keeps pre-speech silence from ever tripping the commit.
        self.listening = False
        self.last_speech = 0.0

        log.info("loading silero-vad (first run downloads ~25MB)")
        self.model, _ = torch.hub.load(
            "snakers4/silero-vad", "silero_vad", trust_repo=True
        )

    # --- mic stream lifecycle: open only while a session is live ---

    def _open_stream(self):
        with self._stream_lock:
            if self._stream is not None:
                return
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                blocksize=FRAME_SIZE,
                channels=1,
                dtype="float32",
                device=self.device,
                callback=self._callback,
            )
            self._stream.start()
        log.info("mic stream opened")

    def _close_stream(self):
        # Grab and null the handle under the lock, then stop/close outside it -
        # stop() blocks until PortAudio's callback thread drains, and we don't
        # want to hold the lock across that.
        with self._stream_lock:
            stream, self._stream = self._stream, None
        if stream is None:
            return
        stream.stop()
        stream.close()
        log.info("mic stream closed, mic released")

    # --- session transitions, all triggered by UDP signals ---

    def start_session(self):
        # Drop any audio buffered before the signal, and reset the model's recurrent
        # state so the previous session's trailing frames don't bias this one.
        while True:
            try:
                self._q.get_nowait()
            except queue.Empty:
                break
        if hasattr(self.model, "reset_states"):
            self.model.reset_states()
        with self._lock:
            self.listening = True
            self.last_speech = 0.0
        self._open_stream()
        log.info("session started, listening for speech")

    def cancel_session(self):
        with self._lock:
            self.listening = False
            self.last_speech = 0.0
        self._close_stream()
        self.kbd.chord()  # toggle Wispr off, no Enter: aborts the dictation cleanly
        log.info("session cancelled")

    def force_commit(self):
        with self._lock:
            self.listening = False
            self.last_speech = 0.0
        self._close_stream()
        self._commit()
        log.info("session committed (forced)")

    def _commit(self):
        # Toggle Wispr off, which makes it transcribe and paste. Then wait for the
        # paste to actually land (clipboard change) before pressing Enter - a fixed
        # delay races Wispr's transcription and fires Enter into a still-empty box.
        seq0 = self.kbd.clipboard_seq()
        self.kbd.chord()
        deadline = time.time() + self.paste_timeout
        while IS_WINDOWS and time.time() < deadline:
            if self.kbd.clipboard_seq() != seq0:
                break
            time.sleep(0.02)
        else:
            if IS_WINDOWS:
                log.warning("no paste within %.1fs; pressing Enter anyway", self.paste_timeout)
        time.sleep(self.commit_delay)  # brief settle after the paste, then submit
        self.kbd.enter()

    # --- audio path: callback feeds a queue, worker does the inference ---

    def _callback(self, indata, frames, time_info, status):
        if status:
            log.debug("stream status: %s", status)
        # Copy out of PortAudio's reused buffer and hand off. No torch here: inference
        # in the audio callback can stall the stream and drop frames.
        self._q.put(indata[:, 0].copy())

    def _worker(self):
        buf = np.empty(0, dtype=np.float32)
        while not self._stop.is_set():
            try:
                chunk = self._q.get(timeout=0.1)
            except queue.Empty:
                continue
            buf = np.concatenate((buf, chunk))
            while buf.shape[0] >= FRAME_SIZE:
                self._process_frame(buf[:FRAME_SIZE])
                buf = buf[FRAME_SIZE:]

    def _process_frame(self, frame):
        with self._lock:
            if not self.listening:
                return
        prob = self.model(torch.from_numpy(frame), SAMPLE_RATE).item()
        now = time.time()
        commit = False
        with self._lock:
            if not self.listening:
                return
            if prob >= self.vad_threshold:
                self.last_speech = now
            elif self.last_speech and (now - self.last_speech) > self.silence_timeout:
                self.listening = False
                self.last_speech = 0.0
                commit = True
        if self.verbose:
            log.debug("prob=%.2f", prob)
        if commit:
            log.info("silence after speech, committing")
            self._close_stream()
            self._commit()

    def _signal_listener(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("127.0.0.1", self.port))
        handlers = {
            b"start": self.start_session,
            b"cancel": self.cancel_session,
            b"stop": self.cancel_session,
            b"go": self.force_commit,
        }
        while not self._stop.is_set():
            data, _ = sock.recvfrom(64)
            handler = handlers.get(data.strip())
            if handler:
                handler()
            else:
                log.warning("unknown signal %r (want start/cancel/go)", data)

    def probe(self):
        """Diagnostic: open the mic and log silero's live speech probability,
        never committing or pressing keys. Sit silent to read your noise floor,
        then talk to see the jump - that gap is where --vad-threshold belongs."""
        self._open_stream()
        log.info("probe mode: logging speech probability, no keystrokes. Ctrl+C to stop")
        buf = np.empty(0, dtype=np.float32)
        n = 0
        try:
            while not self._stop.is_set():
                try:
                    chunk = self._q.get(timeout=0.1)
                except queue.Empty:
                    continue
                buf = np.concatenate((buf, chunk))
                while buf.shape[0] >= FRAME_SIZE:
                    prob = self.model(torch.from_numpy(buf[:FRAME_SIZE]), SAMPLE_RATE).item()
                    buf = buf[FRAME_SIZE:]
                    n += 1
                    if n % 8 == 0:  # ~4 lines/sec, not 31
                        log.info("prob=%.2f |%-40s|", prob, "#" * int(prob * 40))
        except KeyboardInterrupt:
            pass
        finally:
            self._close_stream()

    def run(self):
        threading.Thread(target=self._worker, daemon=True).start()
        threading.Thread(target=self._signal_listener, daemon=True).start()
        log.info(
            "VAD daemon up on UDP %d (mic released until 'start'; silence=%.1fs threshold=%.2f device=%s)",
            self.port,
            self.silence_timeout,
            self.vad_threshold,
            self.device,
        )
        try:
            self._stop.wait()
        except KeyboardInterrupt:
            log.info("shutting down")
        finally:
            self._close_stream()


def parse_args():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--list-devices", action="store_true", help="print input devices and exit")
    p.add_argument("--probe", action="store_true", help="open the mic and log live speech probability, no keystrokes; for tuning --vad-threshold against your noise floor")
    p.add_argument("--device", default=None, help="mic index/name; use the raw hardware mic, not Krisp's virtual device")
    p.add_argument("--silence-timeout", type=float, default=1.8, help="seconds of silence after speech before committing")
    p.add_argument("--vad-threshold", type=float, default=0.5, help="silero speech probability 0-1; raise to 0.6-0.7 if it commits on thinking pauses")
    p.add_argument("--commit-delay", type=float, default=0.15, help="settle pause after the paste lands, before pressing Enter")
    p.add_argument("--paste-timeout", type=float, default=3.0, help="max wait for Wispr's paste (clipboard change) after toggle-off before pressing Enter regardless")
    p.add_argument("--port", type=int, default=5555, help="UDP signal port")
    p.add_argument("--log-file", default=None, help="append logs here (per-line flush) in addition to stderr; for unattended/Task Scheduler runs")
    p.add_argument("--verbose", action="store_true", help="log per-frame speech probabilities (tuning aid)")
    args = p.parse_args()
    # A bare integer means a device index. Without this, sounddevice treats "1" as
    # a device *name* substring and fails to find the mic on the first session.
    if args.device is not None and args.device.isdigit():
        args.device = int(args.device)
    return args


def main():
    args = parse_args()
    handlers = [logging.StreamHandler()]
    if args.log_file:
        handlers.append(logging.FileHandler(args.log_file, encoding="utf-8"))
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
    )
    if args.list_devices:
        print(sd.query_devices())
        return
    # Log any startup failure (bad device, import/DLL error) where an unattended
    # launcher can see it, instead of dying silently with a lost stderr.
    try:
        daemon = VadDaemon(args)
        daemon.probe() if args.probe else daemon.run()
    except Exception:
        log.exception("daemon exited on unhandled error")
        raise


if __name__ == "__main__":
    main()
