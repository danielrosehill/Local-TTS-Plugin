#!/usr/bin/env python3
"""Generate speech with an installed local TTS engine (stdlib dispatcher).

Resolves the text, the engine and the voice from the registry, runs the engine's
runner inside the engine's own venv, converts the WAV if another format was asked
for, and optionally plays it.

Text source (pick one; default reads stdin):
  --text "..."        literal text
  --file PATH         a text / markdown file
  --clipboard         Wayland/X11 clipboard
  --selection         primary selection (highlighted text)

Options:
  --engine NAME       default: registry defaults.engine (or the voice's engine)
  --voice NAME        an engine voice id (e.g. af_heart) or a cloned voice profile name
  --variant NAME      engine model variant (chatterbox: turbo|standard|multilingual|nano)
  --speed FLOAT       1.0 = normal (engines that support it)
  --lang CODE         language hint (engines that support it)
  --out PATH          .wav/.mp3/.ogg/.opus/.flac/.m4a; default: a timestamped WAV
                      under the output dir, or a temp file with --play only
  --play              play the result through the default audio device
  --raw               skip markdown/terminal cleanup
  --dry-run           print the resolved plan as JSON and stop

Prints a JSON result: {"out", "engine", "voice", "seconds", "chars"}.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parent
sys.path.insert(0, str(HERE))
import registry  # noqa: E402
import textprep  # noqa: E402


def die(msg: str, code: int = 1):
    print(json.dumps({"error": msg}), file=sys.stderr)
    sys.exit(code)


def read_text(a) -> str:
    if a.text is not None:
        return a.text
    if a.file:
        return Path(a.file).expanduser().read_text()
    if a.clipboard or a.selection:
        if shutil.which("wl-paste") and os.environ.get("WAYLAND_DISPLAY"):
            cmd = ["wl-paste", "--no-newline"] + (["--primary"] if a.selection else [])
        elif shutil.which("xclip"):
            cmd = ["xclip", "-o", "-selection", "primary" if a.selection else "clipboard"]
        else:
            die("no clipboard tool: install wl-clipboard (Wayland) or xclip (X11)")
        return subprocess.run(cmd, capture_output=True, text=True, check=False).stdout
    if not sys.stdin.isatty():
        return sys.stdin.read()
    die("no text given: use --text, --file, --clipboard, --selection or stdin")


def play(path: Path):
    for p in ("pw-play", "paplay", "aplay"):
        if shutil.which(p):
            subprocess.run([p, str(path)], check=False)
            return
    if shutil.which("ffplay"):
        subprocess.run(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)], check=False)
        return
    die("no audio player found (pw-play, paplay, aplay or ffplay)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--text")
    src.add_argument("--file")
    src.add_argument("--clipboard", action="store_true")
    src.add_argument("--selection", action="store_true")
    ap.add_argument("--engine")
    ap.add_argument("--voice")
    ap.add_argument("--variant")
    ap.add_argument("--speed", type=float)
    ap.add_argument("--lang")
    ap.add_argument("--out")
    ap.add_argument("--play", action="store_true")
    ap.add_argument("--raw", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    reg = registry.load()
    if not reg["engines"]:
        die("no engines installed: run a setup skill (setup-kokoro, setup-chatterbox, ...)")

    text = read_text(a)
    if not a.raw:
        text = textprep.clean(text)
    if not text.strip():
        die("text is empty after cleanup")

    # A cloned voice profile pins its engine.
    profile = reg["voices"].get(a.voice) if a.voice else None
    engine = a.engine or (profile or {}).get("engine") or reg["defaults"].get("engine")
    if engine not in reg["engines"]:
        die(f"engine not installed: {engine}; installed: {sorted(reg['engines'])}")
    if profile and profile.get("engine") != engine:
        die(f"voice '{a.voice}' was cloned for {profile.get('engine')}, not {engine}")
    if profile and a.variant and profile.get("variant") not in (None, a.variant):
        die(f"voice '{a.voice}' was cloned for variant {profile['variant']}, not {a.variant}")
    rec = reg["engines"][engine]
    voice = a.voice or reg["defaults"].get(f"voice.{engine}") or rec.get("default_voice")

    data = registry.home()
    if a.out:
        out = Path(a.out).expanduser().resolve()
    elif a.play:
        out = Path(tempfile.mkdtemp(prefix="local-tts-")) / "speech.wav"
    else:
        outdir = Path(reg["defaults"].get("output_dir", data / "output")).expanduser()
        out = outdir / f"{datetime.now():%Y-%m-%d_%H%M%S}_{engine}.wav"
    out.parent.mkdir(parents=True, exist_ok=True)
    wav = out if out.suffix.lower() == ".wav" else out.with_suffix(".tmp.wav")

    job = {
        "text": text,
        "out": str(wav),
        "voice": voice,
        "profile": profile,
        "variant": (profile or {}).get("variant") or a.variant or rec.get("default_variant"),
        "speed": a.speed,
        "lang": a.lang,
        "engine": rec,
        "plugin_scripts": str(HERE),
    }
    if a.dry_run:
        print(json.dumps({k: v for k, v in job.items() if k != "text"} | {"chars": len(text), "final_out": str(out)}, indent=2))
        return

    runner = PLUGIN / "engines" / engine / "run.py"
    py = rec.get("python")
    if not py or not Path(py).exists():
        die(f"{engine} venv python missing ({py}); rerun its setup skill")
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as jf:
        json.dump(job, jf)
    t0 = time.time()
    env = os.environ | rec.get("env", {})
    r = subprocess.run([py, "-I", str(runner), jf.name], env=env, check=False)
    os.unlink(jf.name)
    if r.returncode != 0 or not wav.exists():
        die(f"{engine} runner failed (exit {r.returncode})")

    if wav != out:
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(wav), str(out)], check=True)
        wav.unlink()

    secs = None
    if shutil.which("ffprobe"):
        p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                           capture_output=True, text=True)
        try:
            secs = round(float(p.stdout.strip()), 2)
        except ValueError:
            pass
    result = {"out": str(out), "engine": engine, "voice": voice, "seconds": secs,
              "chars": len(text), "wall_seconds": round(time.time() - t0, 1)}
    print(json.dumps(result))
    if a.play:
        play(out)


if __name__ == "__main__":
    main()
