#!/usr/bin/env bash
# Print a JSON summary of this machine's TTS-relevant hardware and tools.
# Used by the setup skills to pick an engine, a device and a torch build.
# stdlib only: bash, coreutils, optional lspci / rocminfo / nvidia-smi.
set -uo pipefail

cpu=$(grep -m1 'model name' /proc/cpuinfo 2>/dev/null | cut -d: -f2- | sed 's/^ *//')
cores=$(nproc 2>/dev/null || echo 0)
ram_gb=$(awk '/MemTotal/ {printf "%.1f", $2/1048576}' /proc/meminfo 2>/dev/null)
avail_gb=$(awk '/MemAvailable/ {printf "%.1f", $2/1048576}' /proc/meminfo 2>/dev/null)
disk_free_gb=$(df -Pk "${HOME}" | awk 'NR==2 {printf "%.0f", $4/1048576}')

gpu_vendor="none"; gpu_name=""; gfx=""; vram_gb=""
rocm="false"; cuda="false"

if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
  gpu_vendor="nvidia"; cuda="true"
  gpu_name=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)
  vram_gb=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1 | awk '{printf "%.1f", $1/1024}')
elif command -v rocminfo >/dev/null 2>&1 && rocminfo >/dev/null 2>&1; then
  gpu_vendor="amd"; rocm="true"
  # First GPU agent (skip the CPU agent).
  gfx=$(rocminfo | grep -oE 'gfx[0-9a-f]+' | grep -v '^gfx000$' | head -1)
  gpu_name=$(rocminfo | awk '/Marketing Name/ {sub(/.*Marketing Name: */,""); print}' | grep -viE 'ryzen|epyc|threadripper|cpu' | head -1)
elif command -v lspci >/dev/null 2>&1; then
  line=$(lspci | grep -iE 'vga|3d|display' | head -1)
  case "$line" in
    *NVIDIA*) gpu_vendor="nvidia"; gpu_name=${line#*: } ;;
    *AMD*|*ATI*) gpu_vendor="amd"; gpu_name=${line#*: } ;;
    *Intel*) gpu_vendor="intel"; gpu_name=${line#*: } ;;
  esac
fi

# An integrated AMD/Intel GPU without ROCm/CUDA is CPU-only for TTS purposes.
if [ "$cuda" = "true" ]; then device="cuda"; elif [ "$rocm" = "true" ]; then device="rocm"; else device="cpu"; fi

# Tier: low = run Kokoro (CPU); high = Chatterbox on GPU is realistic.
tier="low"
if [ "$device" != "cpu" ]; then tier="high"; fi

have() { command -v "$1" >/dev/null 2>&1 && echo true || echo false; }

player=""
for p in pw-play paplay aplay ffplay; do command -v $p >/dev/null 2>&1 && { player=$p; break; }; done

cat <<JSON
{
  "cpu": "${cpu}",
  "cores": ${cores},
  "ram_gb": ${ram_gb:-0},
  "ram_available_gb": ${avail_gb:-0},
  "disk_free_gb": ${disk_free_gb:-0},
  "gpu_vendor": "${gpu_vendor}",
  "gpu_name": "${gpu_name}",
  "gfx": "${gfx}",
  "vram_gb": "${vram_gb}",
  "rocm": ${rocm},
  "cuda": ${cuda},
  "device": "${device}",
  "tier": "${tier}",
  "tools": {
    "uv": $(have uv),
    "espeak_ng": $(have espeak-ng),
    "ffmpeg": $(have ffmpeg),
    "wl_paste": $(have wl-paste),
    "xclip": $(have xclip),
    "player": "${player}"
  }
}
JSON
