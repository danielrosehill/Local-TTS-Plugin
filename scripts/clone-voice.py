#!/usr/bin/env python3
"""Clone a voice from one reference clip and store it as a reusable voice profile.

  clone-voice.py --engine neutts|chatterbox --name NAME --ref CLIP
                 [--ref-text "exact transcript" | --ref-text-file F]
                 [--start SEC] [--duration SEC] [--variant turbo] [--exaggeration 0.5]
                 [--no-preview]

The clip can be any audio/video format ffmpeg reads. It is converted to mono 24 kHz
WAV, trimmed, and kept as voices/<NAME>/reference.wav. The engine then encodes it
once into its stored embedding (neutts: NeuCodec codes; chatterbox: Conditionals),
and the profile is registered so `speak.py --voice NAME` uses it.

Clip guidance: one speaker, no music, little room echo.
  neutts      3-15 s, and the exact transcript is required
  chatterbox  more than 5 s (10-20 s is better); no transcript needed
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parent
sys.path.insert(0, str(HERE))
import registry  # noqa: E402

LIMITS = {"neutts": (3.0, 15.0), "chatterbox": (5.0, 20.0)}


def die(msg):
    print(json.dumps({"error": msg}), file=sys.stderr)
    sys.exit(1)


def duration(p: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--ref-text")
    ap.add_argument("--ref-text-file")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--duration", type=float)
    ap.add_argument("--variant")
    ap.add_argument("--exaggeration", type=float, default=0.5)
    ap.add_argument("--no-preview", action="store_true")
    a = ap.parse_args()

    reg = registry.load()
    rec = reg["engines"].get(a.engine)
    if not rec:
        die(f"engine not installed: {a.engine}")
    if not rec.get("cloning"):
        die(f"{a.engine} does not support cloning; use neutts (CPU) or chatterbox (GPU)")
    if not shutil.which("ffmpeg"):
        die("ffmpeg is required")
    name = a.name.strip().lower().replace(" ", "-")
    lo, hi = LIMITS.get(a.engine, (3.0, 20.0))
    dur = a.duration or hi

    vdir = registry.home() / "voices" / name
    vdir.mkdir(parents=True, exist_ok=True)
    ref = vdir / "reference.wav"
    src = Path(a.ref).expanduser().resolve()
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(a.start), "-t", str(dur), "-i", str(src),
                    "-ac", "1", "-ar", "24000", "-af", "silenceremove=start_periods=1:start_threshold=-45dB",
                    str(ref)], check=True)
    got = duration(ref)
    if got < lo:
        die(f"reference is {got:.1f}s; {a.engine} needs at least {lo:.0f}s")

    ref_text = a.ref_text or (Path(a.ref_text_file).read_text().strip() if a.ref_text_file else None)
    if ref_text:
        (vdir / "reference.txt").write_text(ref_text + "\n")

    job = {"engine": rec, "reference": str(ref), "out_dir": str(vdir), "ref_text": ref_text,
           "variant": a.variant or rec.get("default_variant"), "exaggeration": a.exaggeration}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as jf:
        json.dump(job, jf)
    r = subprocess.run([rec["python"], "-I", str(PLUGIN / "engines" / a.engine / "clone.py"), jf.name],
                       capture_output=True, text=True, env=os.environ | rec.get("env", {}))
    Path(jf.name).unlink()
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-3000:])
        die(f"{a.engine} clone failed (exit {r.returncode})")
    frag = json.loads(r.stdout.strip().splitlines()[-1])

    profile = {"engine": a.engine, "dir": str(vdir), "reference": str(ref), "reference_seconds": round(got, 2),
               "source": str(src), "source_offset": a.start} | frag
    reg = registry.load()
    reg["voices"].setdefault(name, {}).update(profile)
    registry.save(reg)

    if not a.no_preview:
        subprocess.run([sys.executable, str(HERE / "speak.py"), "--voice", name,
                        "--text", f"Hello. This is the cloned voice called {name}.",
                        "--out", str(vdir / "preview.wav")], check=False)
        profile["preview"] = str(vdir / "preview.wav")
    print(json.dumps({"voice": name} | profile, indent=2))


if __name__ == "__main__":
    main()
