#!/usr/bin/env bash
# setup.sh — One-shot setup for Krisp-Free on macOS
# Run once: bash setup.sh
# Then every time you need noise cancellation: python3 noise_cancel.py

set -e

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Krisp-Free — macOS Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── 1. Homebrew ───────────────────────────────────────────────────────────────
if ! command -v brew &>/dev/null; then
    echo "→ Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Add brew to PATH for Apple Silicon Macs
    if [[ $(uname -m) == "arm64" ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
else
    echo "✓ Homebrew already installed"
fi

# ── 2. BlackHole 2ch (virtual audio driver) ───────────────────────────────────
if system_profiler SPAudioDataType 2>/dev/null | grep -q "BlackHole"; then
    echo "✓ BlackHole 2ch already installed"
else
    echo "→ Installing BlackHole 2ch (virtual audio driver)..."
    brew install blackhole-2ch
    echo ""
    echo "  ⚠️  macOS will ask you to approve a System Extension."
    echo "     Go to: System Settings → Privacy & Security → scroll down → Allow"
    echo "     Then come back here and press Enter to continue."
    read -p "  Press Enter once you've approved the extension… "
fi

# ── 3. Rust (needed to compile DeepFilterNet) ─────────────────────────────────
if command -v cargo &>/dev/null; then
    echo "✓ Rust already installed"
else
    echo "→ Installing Rust (needed to build DeepFilterNet)..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --quiet
    source "$HOME/.cargo/env"
    echo "✓ Rust installed"
fi

# Make sure cargo is on PATH for this session
source "$HOME/.cargo/env" 2>/dev/null || true

# ── 4. Python packages ────────────────────────────────────────────────────────
echo "→ Installing Python packages (deepfilternet, sounddevice, numpy)..."
echo "  (deepfilternet compiles from source — takes ~2 min on first install)"
pip3 install --upgrade deepfilternet sounddevice numpy

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅  Setup complete!"
echo ""
echo "  Next steps:"
echo "   1. Run:  python3 noise_cancel.py"
echo "   2. In Zoom/Discord/Meet → select  \"BlackHole 2ch\"  as microphone"
echo "   3. Done. Free noise cancellation, forever."
echo ""
echo "  Optional:"
echo "   python3 noise_cancel.py --list        # see all audio devices"
echo "   python3 noise_cancel.py --mic 2       # use a specific mic"
echo "   python3 noise_cancel.py --atten 30    # stronger suppression"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
