---
name: read-aloud
description: Speak text out loud right now through the speakers with a local TTS engine. It can read the last reply, a passage on screen, the clipboard, the highlighted selection, or a file, with no file kept. Use for "read that out", "read this to me", "say it out loud", "read my clipboard", "read the selected text", "speak the answer", "stop reading".
---

# Read aloud

The engine, voice and defaults come from the registry. If `registry.py show` lists no engines, run `choose-engine` first.

Pick the source from what the user said:

| User says | Command |
|---|---|
| "read that out", "read your answer" | Write the reply text (just the prose the user means, not tool output) to a temp file, then use `--file <tmp>` |
| "read this: …" or quotes a passage | `--text "<passage>"`, or a temp file for anything long or full of quotes |
| "read my clipboard" | `--clipboard` |
| "read what I highlighted" | `--selection` (the primary selection: Wayland `wl-paste -p`, X11 `xclip`) |
| "read this file" | `--file <path>` |

Run it in the background so the conversation isn't blocked:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/speak.py" --play <source> [--engine E] [--voice V] [--speed 1.1]
```

- Markdown, code blocks, URLs and ANSI codes are cleaned to speakable prose by default. Pass `--raw` to read text verbatim.
- Audio is generated in full, then played. On a laptop CPU, Kokoro takes about as long as the audio itself (6.5 s of audio in 10.7 s, including model load), so a long reply takes a while before playback starts. For anything over about 2,000 characters, say so. NeuTTS on CPU is about 11× slower than real time, so warn before using a NeuTTS voice for read-aloud.
- **Stop:** `pkill -f 'pw-play|paplay|aplay|ffplay' ; pkill -f local-tts/engines`.
- **Voice:** a cloned profile name (`--voice dad`) selects its engine automatically. `tts-status` lists voices.
- **No sound:** check `pactl info`/`wpctl status`, and that a player (`pw-play`, `paplay`, `aplay` or `ffplay`) exists.
