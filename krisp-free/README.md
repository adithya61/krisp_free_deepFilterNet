# Krisp-Free — Free Real-Time Noise Cancellation for macOS

Replaces Krisp using **DeepFilterNet** (better ML model, open source) routed through
**BlackHole 2ch** (free virtual audio driver). Filters dog barks, distant voices,
fans, keyboard clicks — all locally, no cloud, no subscription, forever free.

---

## How it works

```
Your real mic
    │
    ▼
[Python: sounddevice]  ← captures at 48 kHz
    │
    ▼
[DeepFilterNet model]  ← ML noise suppression runs on CPU (Apple Silicon handles this fast)
    │
    ▼
[BlackHole 2ch]        ← virtual audio device (appears as a mic to apps)
    │
    ▼
Zoom / Discord / Meet  ← select "BlackHole 2ch" as your microphone
```

---

## One-time setup (≈ 5 min)

```bash
bash setup.sh
```

This installs:
- **BlackHole 2ch** — virtual audio driver via Homebrew
- **Rust** — needed to compile DeepFilterNet
- **deepfilternet, sounddevice, numpy** — Python packages

> On first run, the DeepFilterNet model (~17 MB) downloads automatically.

---

## Every-day usage

```bash
python3 noise_cancel.py
```

Then in your app (Zoom, Discord, Google Meet, etc.):
- Go to audio/microphone settings
- Select **"BlackHole 2ch"** as your microphone
- That's it

Press `Ctrl+C` to stop.

---

## CLI options

| Flag | Default | Description |
|------|---------|-------------|
| `--list` | — | List all audio devices with their index numbers |
| `--mic N` | system default | Use device index N as your input microphone |
| `--out N` | auto (BlackHole) | Use device index N as the output (override auto-detect) |
| `--atten N` | `20` | Max noise attenuation in dB (higher = more aggressive, try 20–40) |
| `--blocksize N` | `960` | Frames per processing block (960 = 20 ms at 48 kHz) |

**Examples:**
```bash
# See all devices
python3 noise_cancel.py --list

# Use a specific external mic (e.g. index 3)
python3 noise_cancel.py --mic 3

# More aggressive noise suppression
python3 noise_cancel.py --atten 35

# Use external mic + stronger suppression
python3 noise_cancel.py --mic 3 --atten 35
```

---

## Troubleshooting

### BlackHole not detected
```bash
# Reinstall via Homebrew
brew reinstall blackhole-2ch
# Then approve the system extension in System Settings → Privacy & Security
```

### "Audio device error" on launch
```bash
# List devices and find your mic's index
python3 noise_cancel.py --list
# Then specify it explicitly
python3 noise_cancel.py --mic 0
```

### Zoom/Discord still showing built-in mic
- Quit and reopen the meeting app after starting `noise_cancel.py`
- Some apps need to be restarted to detect new audio devices

### High CPU usage
- Lower `--blocksize` increases CPU load; try `--blocksize 1920` (40ms) for less CPU
- DeepFilterNet is optimised for Apple Silicon (M1/M2/M3) — runs at <5% CPU on those chips
- On Intel Macs it may use 10–15% CPU

### Voice sounds slightly robotic
- Reduce attenuation: `--atten 15` or `--atten 10`
- This trades off noise removal vs. voice naturalness

---

## vs. Krisp

| | Krisp | Krisp-Free |
|---|---|---|
| Cost | $96/year | Free forever |
| Model | Proprietary | DeepFilterNet (research-grade, open source) |
| Dog barks / distant voices | ✅ | ✅ |
| Fan / keyboard noise | ✅ | ✅ |
| Runs locally (no cloud) | ✅ | ✅ |
| Works with any app | ✅ | ✅ (via BlackHole) |
| macOS support | ✅ | ✅ |
| Apple Silicon optimised | ✅ | ✅ |

---

## Files

```
krisp-free/
├── setup.sh          — one-time setup script
├── noise_cancel.py   — main script (run this daily)
└── README.md         — this file
```
