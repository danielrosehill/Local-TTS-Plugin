# Local TTS

A Claude Code plugin for text-to-speech that runs on your own machine. It works out
what your hardware can handle, installs a suitable open model in its own Python
environment, keeps track of what is installed, and then reads text aloud, writes
audio files or clones a voice from a single recording.

| Engine | For | Cloning |
|---|---|---|
| **Kokoro-82M** (ONNX) | Any machine, including low-resource laptops with no GPU. 54 voices, 8 languages. | no |
| **NeuTTS Air** (GGUF) | CPU-only voice cloning. English. | yes, from a 3–15 s clip and its transcript |
| **Chatterbox** Turbo / standard / multilingual / Nano | AMD ROCm or NVIDIA CUDA GPUs. Nano runs on CPU. | yes, from a clip longer than 5 s |

## Install

```
/plugin install local-tts --marketplace danielrosehill/Claude-Code-Plugins
```

Then ask Claude to "set up local TTS". The `choose-engine` skill takes it from there.

## Skills

| Skill | What it does |
|---|---|
| `choose-engine` | Detects CPU, RAM, GPU and ROCm/CUDA, then recommends what to install |
| `setup-kokoro` | Installs Kokoro if it is missing, downloads the model and runs a smoke test |
| `setup-neutts` | Installs NeuTTS Air on CPU and registers its sample speakers |
| `setup-chatterbox` | Installs Chatterbox with the right PyTorch build for ROCm, CUDA or CPU |
| `tts-status` | Shows installed engines and voices; sets defaults; removes engines |
| `clone-voice` | Clones a voice from one recording and saves its embedding as a voice profile |
| `text-to-audio-file` | Turns text or markdown into WAV, MP3, OGG, FLAC or M4A |
| `read-aloud` | Plays the last reply, the clipboard, the highlighted text or a file through the speakers |

## How it works

Every engine gets its own `uv` virtual environment, so their incompatible PyTorch pins
never meet. The plugin's top-level scripts use only the Python standard library:

- `scripts/detect-hardware.sh` prints the machine's hardware as JSON.
- `scripts/registry.py` is the local memory of what is installed. It lives at
  `~/.local/share/local-tts/registry.json`, or under `$LOCAL_TTS_HOME` if set, and
  records each engine's venv, model files, device, variants, voices and last smoke
  test, plus every cloned voice profile and the defaults.
- `scripts/speak.py` resolves the text, engine and voice, then runs
  `engines/<engine>/run.py` inside that engine's venv. It cleans markdown and terminal
  output into speakable prose, splits long text into chunks, converts to the
  requested format with ffmpeg and can play the result.
- `scripts/clone-voice.py` trims and normalises the reference clip, has the engine
  encode it once, and stores the result under `voices/<name>/`. NeuTTS stores
  NeuCodec codes; Chatterbox stores its `Conditionals`.

```bash
python3 scripts/speak.py --text "Hello" --play
python3 scripts/speak.py --file notes.md --out notes.mp3 --voice bf_emma
python3 scripts/speak.py --clipboard --play --voice dad      # a cloned voice
```

## Requirements

- Linux with `uv`, `ffmpeg` and a player: `pw-play`, `paplay`, `aplay` or `ffplay`.
- `espeak-ng` for NeuTTS.
- `wl-clipboard` or `xclip` to read the clipboard or the highlighted text.
- NeuTTS weights are gated on Hugging Face. Accept the terms for
  `neuphonic/neutts-air-q4-gguf` and `neuphonic/neucodec`, then log in with `hf auth login`.
- Chatterbox on AMD needs ROCm installed. Consumer cards may need `--hsa-override`.

Tested on 2026-11-02 on a Ryzen 7 5700U laptop (CPU only, 13 GB RAM):

- Kokoro fp32: 6.5 s of audio in 10.7 s wall time, including model load.
- NeuTTS Air Q4: 5.7 s of audio in 63 s warm. One-shot cloning works.

The Chatterbox ROCm and CUDA paths follow the upstream sources and the
workaround described in [docs/model-landscape.md](docs/model-landscape.md); they were
not run on a GPU for this release.

Only clone voices that are yours or whose owner has agreed.

## License

MIT for this plugin. Each model has its own licence: Kokoro, NeuTTS Air and
NeuCodec are Apache-2.0, and Chatterbox is MIT.
