---
name: setup-neutts
description: Install NeuTTS Air (Neuphonic, Apache-2.0), an on-device voice-cloning TTS model that runs on CPU from a quantised GGUF backbone, register its bundled sample speakers and smoke-test it. Use for "voice cloning without a GPU", "clone a voice on my laptop", "install NeuTTS", or when choose-engine picks it.
---

# Set up NeuTTS Air (CPU voice cloning)

NeuTTS Air is a 0.7B model on a Qwen 0.5B backbone. Here it runs as a Q4 GGUF through llama.cpp on CPU and outputs 24 kHz English. It clones a voice in one shot from a 3–15 s clip plus the clip's exact transcript. The clip is encoded once into NeuCodec codes and stored on disk, so later generations never re-read the audio. Outputs carry a Perth audio watermark.

1. Run `registry.py get-engine neutts`. If it is installed with a `last_smoke_test`, stop.
2. Prerequisites:
   - `espeak-ng` (the phonemiser) and `uv`. If either is missing, give the install command and stop.
   - **Gated weights.** The user must accept Neuphonic's terms on both `https://huggingface.co/neuphonic/neutts-air-q4-gguf` (or `-q8-gguf`) and `https://huggingface.co/neuphonic/neucodec`. Approval is automatic, but it has to be done in the browser, logged in as the token's account. A token must also be available: `hf auth login`, or `HF_TOKEN` in the environment. You cannot accept the terms for the user; give them the links. The installer checks access with `huggingface_hub.auth_check`. If access is missing, it exits with code 3 and prints the links.
   - Torch is CPU-only and pinned (`torch==2.9.1+cpu`, `torchao==0.14.1`). Newer torchao breaks `torchtune`, which `neucodec` imports.
3. Run `bash "${CLAUDE_PLUGIN_ROOT}/engines/neutts/install.sh"` in the background. Use `--quant q8` for slightly better quality at about twice the size. The script:
   - installs CPU-only torch and a prebuilt CPU `llama-cpp-python` wheel, falling back to a source build that needs `cmake` and `g++`;
   - installs `neutts[llama]`;
   - registers six bundled sample speakers as voice profiles: `jo` (default), `dave`, `emily`, `paul`, `sophie`, `steven`;
   - runs the smoke test, whose first run downloads about 0.6 GB of weights.
4. Success prints `neutts: OK`.

Limits:
- English only (the Air backbone).
- The context is 2048 tokens for the reference and output together, so `speak.py` sends about 220 characters per call and joins the pieces.
- It's slow on laptop CPUs. Measured 2026-11-02 on a Ryzen 7 5700U (8 cores, Q4): 5.7 s of audio took 63 s warm, about 11× slower than real time, and the first run also downloads about 0.6 GB. Use it for short clips or files generated in the background, not live read-aloud. For instant reading use Kokoro. Cloning (codec only) takes about 30 s.

Clone a new voice with `clone-voice --engine neutts`, which needs a transcript.
