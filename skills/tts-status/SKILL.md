---
name: tts-status
description: Show which local text-to-speech engines, model variants and voices (preset and cloned) are installed on this machine, set the default engine, voice and output folder, re-run smoke tests, or remove an engine. Use for "what TTS do I have", "list my voices", "make Chatterbox the default", "set my default voice", "uninstall Kokoro".
---

# Local TTS status and defaults

The registry is the plugin's local memory of this machine. It lives at `$LOCAL_TTS_HOME/registry.json`, by default `~/.local/share/local-tts/registry.json`. Edit it through `registry.py` rather than by hand.

```bash
R="${CLAUDE_PLUGIN_ROOT}/scripts/registry.py"
python3 "$R" show                         # everything
python3 "$R" get-engine chatterbox        # one engine
python3 "$R" set-default engine kokoro
python3 "$R" set-default voice.kokoro bf_emma     # per-engine default voice
python3 "$R" set-default output_dir ~/Audio/tts
python3 "$R" remove-engine neutts         # then: rm -rf ~/.local/share/local-tts/engines/neutts
python3 "$R" remove-voice dad             # then: rm -r ~/.local/share/local-tts/voices/dad
```

Summarise `show` as a short table:

| Field | Source |
|---|---|
| Engine | engine name |
| Backend version | `backend` |
| Device | `device` |
| Variants | `variants` (Chatterbox) |
| Default voice | `default_voice` |
| Cloning | `cloning` |
| Last smoke test | `last_smoke_test` |

After the table, list the voices as name → engine (variant), and the defaults.

- **Health check:** run each engine's smoke test with `speak.py --engine <e> --text "test" --out /tmp/<e>.wav`, plus `--voice jo` for NeuTTS and `--voice builtin` for Chatterbox. A failure means the venv broke, usually from a system Python upgrade. Rerun that engine's setup skill; the installers are idempotent.
- **Stale records:** if the registry lists an engine whose `python` path is gone, the files were deleted by hand. Remove the record.
