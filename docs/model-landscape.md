# Local TTS model landscape (snapshot 2026-11-02)

Why these three engines are bundled, and what else was considered. This changes fast,
so re-check Hugging Face before adding an engine. Facts below were read from the model
cards, PyPI and the upstream sources on 2026-11-02 unless marked *unverified*.

## Bundled

| Engine | HF id | Size | License | Runs on | Cloning | Why |
|---|---|---|---|---|---|---|
| Kokoro-82M via `kokoro-onnx` 0.6.x | `hexgrad/Kokoro-82M` | 82M (ONNX fp32 310 MB / int8 88 MB) | Apache-2.0 | CPU | no | The best quality-per-watt preset-voice model; no torch needed in the ONNX build. 54 voices, 8 languages. |
| NeuTTS Air via `neutts` 1.4.x | `neuphonic/neutts-air-q4-gguf` (+ `neuphonic/neucodec`) | 0.7B (Q4 GGUF ~0.5 GB) | Apache-2.0, **gated (auto-approve)** | CPU (llama.cpp) | yes, 3–15 s + transcript | CPU voice cloning with a storable embedding (NeuCodec codes). English. Watermarked output. |
| Chatterbox via `chatterbox-tts` 0.1.7 | `ResembleAI/chatterbox`, `ResembleAI/chatterbox-turbo`, `ResembleAI/chatterbox-nano` | 110M–500M | MIT | GPU (CUDA/ROCm); Nano on CPU | yes, >5 s clip | Most expressive open model with paralinguistic tags (Turbo) and 23-language multilingual variant. Conditionals are savable (`conds.pt`). |

## Considered, not bundled

| Model | HF id | Notes |
|---|---|---|
| Kyutai Pocket TTS | `kyutai/pocket-tts` | ~100M, CPU, WAV-prompt cloning, 6 languages; CC-BY-4.0 and files gated. Strong candidate for a fourth engine. |
| KittenTTS mini 0.8 | `KittenML/kitten-tts-mini-0.8` | ~80M, CPU, 8 preset voices, Apache-2.0; overlaps Kokoro. |
| Piper | `rhasspy/piper-voices` | Tiny ONNX voices, very fast, many languages; code is GPL-3.0 (piper1-gpl). |
| NeuTTS Nano | `neuphonic/neutts-nano-*` | Smaller/faster than Air but under the NeuTTS Open License, not Apache. Swappable by editing `backbone` in the registry. |
| VibeVoice-Realtime-0.5B | `microsoft/VibeVoice-Realtime-0.5B` | MIT; *unverified* CPU viability. |
| Orpheus 3B, Dia, F5-TTS, Fish/OpenAudio, IndexTTS2, Voxtral TTS | various | GPU-class or not evaluated. |

## Version traps found while building (2026-11-02)

- **chatterbox-tts 0.1.7 pins `torch==2.6.0`.** Current ROCm indexes have no torch 2.6 wheel
  (rocm6.4 → torch 2.9.1, rocm7.2 → 2.14.1), and PyPI's 2.6 is a ~2.5 GB CUDA build. The
  installer installs torch first from the matching index, then `chatterbox-tts --no-deps`.
- **NeuTTS on CPU:** unpinned, uv picks torch 2.15+cpu, torchaudio 2.11 and torchao 0.18;
  `torchtune` 0.6.1 (a `neucodec` dependency) then fails with
  `No module named 'torchao.dtypes.nf4tensor'`. Pinned to torch/torchaudio 2.9.1+cpu and
  torchao 0.14.1, which import cleanly.
- **NeuTTS repos are gated** (`gated: auto`): every user must click-accept on Hugging Face
  for both the backbone and `neuphonic/neucodec`, and have a token available.
- **Chatterbox Turbo** asserts the reference clip is longer than 5 s and ignores
  `exaggeration` / `cfg_weight` (`tts_turbo.py`, master, 2026-11-02).
