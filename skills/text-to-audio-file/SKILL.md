---
name: text-to-audio-file
description: Turn text, a markdown document or a script into an audio file (WAV, MP3, OGG/Opus, FLAC, M4A) with a locally installed TTS engine and voice, including cloned voices. Use for "make an MP3 of this", "generate a voiceover", "convert this document to audio", "TTS this file", "save it as audio".
---

# Text to audio file

1. Read the registry: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/registry.py" show`. If no engines are installed, run `choose-engine`.
2. Pick the engine and voice:
   - Use the user's choice if they gave one.
   - A cloned voice profile (`voices` in the registry) pins its own engine.
   - Otherwise use `defaults.engine` and that engine's `default_voice`.
3. Pick the output path. Use the user's path if given. Otherwise put it next to the source file, named `<source-stem>.<ext>`. With no source file, `speak.py` writes a timestamped WAV to `defaults.output_dir`, or `~/.local/share/local-tts/output/` if that is unset. Use MP3 when the user hasn't named a format and the file is meant for sharing.
4. Run it. Use the background for long documents: Chatterbox and NeuTTS on CPU can take as long as the audio itself.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/speak.py" --file doc.md --out doc.mp3 [--engine kokoro] [--voice af_heart] \
  [--speed 1.0] [--lang en-us] [--variant turbo] [--raw]
```

Text can also come from `--text "..."` or stdin. Add `--dry-run` to see the resolved engine, voice and paths without generating anything.

5. Report the `out` path and the audio duration from the JSON line `speak.py` prints. Offer to play it.

Text handling:
- Markdown is cleaned: headings and list items become sentences, code blocks become "code block omitted", and links are read as their text.
- Text is chunked by sentence per engine (Kokoro 400, Chatterbox 280, NeuTTS 220 characters) and joined with short pauses.
- For a script with several speakers, generate one file per line with each speaker's `--voice`, then join them: `ffmpeg -f concat -safe 0 -i list.txt -c copy out.wav`.
- Expressive tags such as `[laugh]` and `[chuckle]` only work on Chatterbox `turbo`. Pass `--raw` so the cleanup leaves the brackets alone. Other engines read the tags as words, so strip them first.
- Per-engine languages: Kokoro covers 8 languages via `--lang`, Chatterbox `multilingual` covers 23 via `--lang <iso>`, and NeuTTS Air is English only.
