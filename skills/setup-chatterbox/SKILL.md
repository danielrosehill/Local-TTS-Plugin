---
name: setup-chatterbox
description: Install Resemble AI's Chatterbox text-to-speech (Turbo by default; also standard, multilingual and the CPU Nano) on a GPU machine, with the right PyTorch build for AMD ROCm, NVIDIA CUDA or CPU, then smoke-test it and record it in the local TTS registry. Use for "install Chatterbox", "set up Chatterbox Turbo", "TTS on my ROCm/AMD GPU", "expressive local TTS", "voice cloning on my GPU".
---

# Set up Chatterbox (well-resourced machines)

Chatterbox (Resemble AI, MIT) comes in four variants, all at 24 kHz. Every variant can clone a voice from a reference clip (skill `clone-voice`).

| Variant | Size | Languages | Notes |
|---|---|---|---|
| `turbo` | 350M | English | The fastest on a GPU. Supports inline tags `[laugh]`, `[chuckle]`, `[cough]`. Ignores `exaggeration`/`cfg_weight`. |
| `standard` | 500M | English | Supports the `exaggeration` (emotion) and `cfg_weight` (pacing) controls. |
| `multilingual` | 500M | 23 languages | Pass `--lang` with an ISO code (`he`, `fr`, `de`, …). There are no inline language tags, so mixed-language text has to be split per language. |
| `nano` | 110M | English | The CPU option. |

1. Run `bash "${CLAUDE_PLUGIN_ROOT}/scripts/detect-hardware.sh"` and `registry.py get-engine chatterbox`. If it is already installed with the wanted variants, stop.
2. Choose the device:
   - `rocm`: an AMD GPU where `rocminfo` works.
   - `cuda`: NVIDIA.
   - Otherwise `cpu`, which installs only `nano` by default.
3. Choose variants with the user if it isn't obvious. Default is `turbo` on a GPU. Add `multilingual` for non-English, and `standard` for emotion control. Each variant downloads 1–3 GB of weights from Hugging Face on its first load.
4. Run `bash "${CLAUDE_PLUGIN_ROOT}/engines/chatterbox/install.sh" --device <d> --variants <list>`. Expect 5–15 minutes: PyTorch (ROCm about 3 GB) plus weights. Run it in the background and report when it is done.
   - **ROCm:** the script reads `/opt/rocm/.info/version` and installs torch from `https://download.pytorch.org/whl/rocm<major.minor>`, falling back to `rocm6.4`. Pass `--torch-index URL` to override.
   - **ROCm on consumer cards:** if the script warns that torch cannot see the GPU, rerun with `--hsa-override`. Use `11.0.0` for RDNA3 (RX 7000) and `10.3.0` for RDNA2 (RX 6000). The value is stored in the engine's `env` and applied on every run.
   - **Why torch goes in first:** chatterbox-tts 0.1.7 pins `torch==2.6.0`, which isn't on current ROCm indexes and pulls a 2.5 GB CUDA build from PyPI. So the script installs the chosen torch build first, then `chatterbox-tts --no-deps`, then its runtime deps. Running Chatterbox on torch newer than 2.6 is not upstream-tested; the smoke test is the check.
5. Success prints `chatterbox: OK` and leaves `smoke-test-<variant>.wav` files in the engine directory.
6. To make Chatterbox the default engine, use `registry.py set-default engine chatterbox`.

The built-in voice is `builtin`, the model's bundled `conds.pt`. For any other voice, run `clone-voice` first.
