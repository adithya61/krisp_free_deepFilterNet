#!/usr/bin/env python3
"""
noise_cancel.py — Free real-time noise cancellation for macOS
Uses DeepFilterNet (ML model) to filter your mic, outputs to BlackHole (virtual mic).
Select "BlackHole 2ch" as your microphone in Zoom, Discord, Meet, etc.

Usage:
    python3 noise_cancel.py              # auto-detects mic and BlackHole
    python3 noise_cancel.py --list       # list all audio devices
    python3 noise_cancel.py --mic 1      # use device index 1 as input mic
    python3 noise_cancel.py --atten 20   # set attenuation dB (default 20, range 0-100)
"""

import sys
import time
import argparse
import threading
import queue
import signal
import numpy as np

# ── Argument parsing ──────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description="Real-time noise cancellation via DeepFilterNet → BlackHole")
parser.add_argument("--list", action="store_true", help="List all audio devices and exit")
parser.add_argument("--mic", type=int, default=None, help="Input device index (default: system default mic)")
parser.add_argument("--out", type=int, default=None, help="Output device index (default: auto-detect BlackHole 2ch)")
parser.add_argument("--atten", type=float, default=20.0, help="Max attenuation in dB (default: 20)")
parser.add_argument("--blocksize", type=int, default=960, help="Audio block size in frames (default: 960 = 20ms @ 48kHz)")
args = parser.parse_args()

# ── Imports (with helpful errors) ─────────────────────────────────────────────

try:
    import sounddevice as sd
except ImportError:
    print("❌  sounddevice not found. Run: pip install sounddevice")
    sys.exit(1)

if args.list:
    print("\n── Audio Devices ────────────────────────────────────────────────")
    for i, dev in enumerate(sd.query_devices()):
        tag = []
        if dev["max_input_channels"] > 0:
            tag.append("IN")
        if dev["max_output_channels"] > 0:
            tag.append("OUT")
        flag = "★ " if "BlackHole" in dev["name"] else "  "
        print(f"  [{i:2d}] {flag}{'/'.join(tag):3s}  {dev['name']}")
    print("\n★ = BlackHole device (use as --out)")
    print("────────────────────────────────────────────────────────────────\n")
    sys.exit(0)

try:
    from df.enhance import enhance, init_df, load_audio, save_audio
    from df import config
except ImportError:
    print("❌  deepfilternet not found.")
    print("    Run: pip install deepfilternet")
    print("    (If that fails, first run: brew install rust)")
    sys.exit(1)

# ── Find BlackHole output device ──────────────────────────────────────────────

def find_blackhole():
    for i, dev in enumerate(sd.query_devices()):
        if "BlackHole" in dev["name"] and dev["max_output_channels"] > 0:
            return i
    return None

output_device = args.out
if output_device is None:
    output_device = find_blackhole()
    if output_device is None:
        print("❌  BlackHole 2ch not found.")
        print("    Install it: brew install blackhole-2ch")
        print("    Then re-run this script.")
        sys.exit(1)

input_device = args.mic  # None = system default mic

# ── Describe what we found ────────────────────────────────────────────────────

in_name  = sd.query_devices(input_device)["name"] if input_device is not None else sd.query_devices(sd.default.device[0])["name"]
out_name = sd.query_devices(output_device)["name"]

print()
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("  🎙  Krisp-Free — DeepFilterNet noise cancellation")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print(f"  Input  (your real mic)  : {in_name}")
print(f"  Output (virtual mic)    : {out_name}")
print(f"  Attenuation ceiling     : {args.atten} dB")
print(f"  Block size              : {args.blocksize} frames")
print()
print("  Loading DeepFilterNet model… (first run downloads ~17MB)")

# ── Load DeepFilterNet ────────────────────────────────────────────────────────

try:
    model, df_state, _ = init_df()
except Exception as e:
    print(f"❌  Failed to load DeepFilterNet model: {e}")
    sys.exit(1)

SAMPLE_RATE = df_state.sr()   # DeepFilterNet requires 48 kHz
BLOCK       = args.blocksize  # frames per callback (20 ms @ 48 kHz)

print(f"  Model loaded ✓  (sample rate: {SAMPLE_RATE} Hz)")
print()
print("  In your meeting app, select  \"BlackHole 2ch\"  as microphone.")
print("  Press  Ctrl+C  to stop.")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print()

# ── Audio processing pipeline ─────────────────────────────────────────────────
# We use a queue to decouple the capture callback (runs in a real-time thread)
# from the DeepFilterNet inference (can take variable time).

audio_queue  = queue.Queue(maxsize=50)  # raw mic chunks
output_queue = queue.Queue(maxsize=50)  # filtered chunks

stop_event = threading.Event()

# Stats
stats = {"processed": 0, "dropped": 0, "last_print": time.time()}

def capture_callback(indata, frames, time_info, status):
    """Called by sounddevice on the audio thread. Must be fast — just enqueue."""
    if status:
        pass  # ignore xruns in callback; we handle drops via queue size
    try:
        # indata shape: (frames, 1) — mono
        audio_queue.put_nowait(indata[:, 0].copy())
    except queue.Full:
        stats["dropped"] += 1


def inference_thread():
    """Pulls raw audio, runs DeepFilterNet, pushes filtered audio."""
    # DeepFilterNet processes chunks — we accumulate enough for one pass.
    # The model prefers 480–4800 sample chunks. BLOCK (960) works well.
    while not stop_event.is_set():
        try:
            chunk = audio_queue.get(timeout=0.1)
        except queue.Empty:
            continue

        # DeepFilterNet expects float32 tensor shaped (1, samples)
        audio_np = chunk.astype(np.float32)
        audio_2d = audio_np[np.newaxis, :]  # (1, N)

        try:
            enhanced = enhance(model, df_state, audio_2d, atten_lim_db=args.atten)
            # enhanced shape: (1, N)
            output_queue.put_nowait(enhanced[0])
        except Exception:
            # On error, pass through unfiltered rather than going silent
            output_queue.put_nowait(audio_np)

        stats["processed"] += 1


def playback_thread():
    """Pulls filtered audio and writes it to BlackHole (the virtual mic)."""
    with sd.OutputStream(
        device=output_device,
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=BLOCK,
    ) as out_stream:
        while not stop_event.is_set():
            try:
                chunk = output_queue.get(timeout=0.1)
            except queue.Empty:
                # Write silence so the stream doesn't underflow
                out_stream.write(np.zeros(BLOCK, dtype=np.float32))
                continue
            out_stream.write(chunk.astype(np.float32))


def print_stats():
    """Prints a running status line every 5 seconds."""
    while not stop_event.is_set():
        time.sleep(5)
        q_in  = audio_queue.qsize()
        q_out = output_queue.qsize()
        print(
            f"  ✓  processed={stats['processed']}  "
            f"dropped={stats['dropped']}  "
            f"queue_in={q_in}  queue_out={q_out}"
        )

# ── Start threads ─────────────────────────────────────────────────────────────

threads = [
    threading.Thread(target=inference_thread, daemon=True, name="inference"),
    threading.Thread(target=playback_thread,  daemon=True, name="playback"),
    threading.Thread(target=print_stats,      daemon=True, name="stats"),
]

for t in threads:
    t.start()

# ── Capture stream (blocking) ─────────────────────────────────────────────────

def handle_sigint(sig, frame):
    print("\n\n  Stopping…")
    stop_event.set()

signal.signal(signal.SIGINT, handle_sigint)

try:
    with sd.InputStream(
        device=input_device,
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=BLOCK,
        callback=capture_callback,
    ):
        while not stop_event.is_set():
            time.sleep(0.2)
except sd.PortAudioError as e:
    print(f"\n❌  Audio device error: {e}")
    print("    Try: python3 noise_cancel.py --list  to see available devices")
    print("    Then: python3 noise_cancel.py --mic <index>")
    stop_event.set()
except Exception as e:
    print(f"\n❌  Unexpected error: {e}")
    stop_event.set()

# Wait for threads to clean up
for t in threads:
    t.join(timeout=2.0)

print("  Stopped. Goodbye.\n")
