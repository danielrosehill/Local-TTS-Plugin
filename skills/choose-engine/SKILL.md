---
name: choose-engine
description: Pick which local text-to-speech engine to install on this machine (Kokoro for low-resource CPUs, NeuTTS Air for CPU voice cloning, Chatterbox for GPUs with CUDA or ROCm) from its detected hardware, and say what is already installed. Use for "set up local TTS", "which TTS model should I use here", "what can this machine run", "install text to speech".
---

# Choose a local TTS engine

1. Run `bash "${CLAUDE_PLUGIN_ROOT}/scripts/detect-hardware.sh"` (JSON: CPU, RAM, GPU vendor, ROCm/CUDA, gfx id, free disk, tools).
2. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/registry.py" show` for what is already installed. Skip anything already there unless the user wants a reinstall.
3. Recommend using the table, in one or two lines, then run the matching setup skill. Install more than one only if the user wants it.

| Situation | Engine | Skill |
|---|---|---|
| Any machine, no GPU, or under 8 GB RAM. The default reader. | Kokoro-82M (ONNX, CPU, 54 preset voices, ~350 MB) | `setup-kokoro` |
| Wants a cloned voice and has no GPU | NeuTTS Air (GGUF on CPU, clones from a 3–15 s clip plus its transcript) | `setup-neutts` |
| NVIDIA GPU (CUDA), or AMD GPU with ROCm working (`rocm: true`) | Chatterbox Turbo (expressive, `[laugh]` tags, clones from a 5–20 s clip). Add `multilingual` for non-English. | `setup-chatterbox` |
| CPU but strong (16+ GB RAM, 8+ cores) and wants Chatterbox anyway | Chatterbox Nano (CPU) | `setup-chatterbox` with `--variants nano` |

Notes:
- An integrated AMD GPU (e.g. Radeon Vega in a Ryzen U-series) shows `gpu_vendor: amd` but `rocm: false`. Treat it as CPU.
- On an AMD GPU without `rocminfo`, ROCm isn't installed. Say so. Installing ROCm is a system change outside this plugin, so ask first.
- `docs/model-landscape.md` lists other current options (Kyutai Pocket TTS, KittenTTS, Piper, VibeVoice) and why they aren't bundled. Read it if the user asks about alternatives.
- If `uv`, `ffmpeg` or `espeak-ng` is missing, give the install command for the distro and let the user run it (`! sudo apt install ffmpeg espeak-ng`).
