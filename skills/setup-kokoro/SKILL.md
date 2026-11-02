---
name: setup-kokoro
description: Install Kokoro-82M, the small fast local text-to-speech model, on CPU via kokoro-onnx (no PyTorch, no GPU) if it is not already installed, download the model, smoke-test it and record it in the local TTS registry. Use for "install Kokoro", "set up lightweight TTS", "local TTS for my laptop", or when choose-engine picks Kokoro.
---

# Set up Kokoro (low-resource default)

Kokoro-82M (hexgrad, Apache-2.0) has 54 preset voices in 8 languages and outputs 24 kHz audio. The ONNX build runs on any x86/ARM CPU in about 1 GB of RAM. Verified on a Ryzen 7 5700U laptop with 13 GB RAM, 2026-11-02: a 1.9 s sentence took 6.6 s wall time, including model load.

1. Check the registry: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/registry.py" get-engine kokoro`. If it exists and `last_smoke_test` is set, say it's already installed and stop, unless the user asked for a reinstall or another precision.
2. Pick the precision from RAM (`scripts/detect-hardware.sh`):
   - `fp32`: 310 MB, best quality. Use it when there is 8 GB or more of RAM.
   - `int8`: 88 MB. Use it on machines under 8 GB or very slow CPUs.
   - `fp16`: 170 MB. A middle option.
3. Run `bash "${CLAUDE_PLUGIN_ROOT}/engines/kokoro/install.sh" --precision <p>`. It takes about 1 minute on a normal connection. It creates `~/.local/share/local-tts/engines/kokoro/{venv,models}` (or under `$LOCAL_TTS_HOME`). It is idempotent.
4. The script ends with a smoke-test WAV and the line `kokoro: OK`. Offer to play the WAV (`pw-play <path>`).
5. If no default engine was set before, Kokoro is now the default.

Voices: `af_heart` (default), `af_bella`, `af_nicole`, `am_michael`, `am_fenrir`, `bf_emma`, `bm_george`, and more. The full list is under `voices` in the registry record. The prefix gives language and gender: `a` = US English, `b` = UK, `e` es, `f` fr, `h` hi, `i` it, `j` ja, `p` pt-br, `z` zh. For non-English, pass `--lang` (e.g. `fr-fr`, `es`, `it`, `pt-br`, `ja`, `cmn`).
Blends work as `--voice "af_heart:60,af_bella:40"`.

Kokoro cannot clone voices. For cloning, use `setup-neutts` (CPU) or `setup-chatterbox` (GPU).

Removal: `rm -rf ~/.local/share/local-tts/engines/kokoro`, then `registry.py remove-engine kokoro`.
