---
name: clone-voice
description: Clone a voice in one shot from a single reference recording and save it locally as a reusable voice profile (a stored embedding), on CPU with NeuTTS Air or on a GPU with Chatterbox. Use for "clone my voice", "make a voice from this recording", "use this person's voice", "add a voice", "delete that voice".
---

# Clone a voice

The reference is encoded once and stored under `~/.local/share/local-tts/voices/<name>/`, which holds:
- `reference.wav`: the trimmed, mono 24 kHz copy of the clip;
- `reference.txt`: the transcript, for NeuTTS;
- the engine's embedding: `neutts.codes.pt` for NeuTTS (NeuCodec codes), or `chatterbox-<variant>.conds.pt` for Chatterbox (speaker embedding, prompt tokens and decoder reference features);
- `preview.wav`: a test line in the new voice.

The profile is registered, so `--voice <name>` works in `read-aloud` and `text-to-audio-file` from then on.

**Consent:** only clone the user's own voice, or a voice whose owner has agreed. If it's unclear whose voice the clip is, ask once.

1. **Engine.** It must be installed with `cloning: true`:
   - `neutts` on CPU-only machines (English only).
   - `chatterbox` on a GPU. Use the `multilingual` variant for non-English.
   - A profile belongs to one engine and variant. To use the same voice on another engine, clone it again under a new name such as `dad-cb`.
2. **Clip.** Any format ffmpeg reads, video included.
   - One speaker, no music, little echo.
   - NeuTTS needs 3–15 s; Chatterbox needs more than 5 s, and 10–20 s is best.
   - For a long recording, pick a clean stretch with `--start`/`--duration`. Listen to it first, or ask the user.
3. **Transcript (NeuTTS only).** NeuTTS needs the exact words of the trimmed clip. Ask the user, or transcribe the clip with whatever speech-to-text is available. The transcript must match the trimmed segment, not the whole file.
4. **Run:**

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/clone-voice.py" --engine neutts --name dad \
  --ref ~/recordings/dad.m4a --start 12 --duration 10 --ref-text "exact words spoken in that segment"
# GPU:
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/clone-voice.py" --engine chatterbox --variant turbo --name dad --ref dad.wav [--exaggeration 0.5]
```

5. Play `preview.wav` to the user. If it sounds off, the cause is almost always the clip: noise, a second voice, a transcript mismatch on NeuTTS, or too short a clip. Re-clone from a cleaner segment.

Manage profiles:
- List them with `registry.py show`, under `voices`.
- Delete with `registry.py remove-voice <name>`, then `rm -r ~/.local/share/local-tts/voices/<name>`.
- NeuTTS's bundled sample speakers (`jo`, `dave`, `emily`, `paul`, `sophie`, `steven`) are registered at install.
