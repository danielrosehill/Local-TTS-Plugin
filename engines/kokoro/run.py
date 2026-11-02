"""Kokoro-82M runner (kokoro-onnx, CPU). Called by scripts/speak.py inside the
kokoro venv with one argument: a job JSON file. Writes a 24 kHz mono WAV."""
import json
import sys

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

job = json.load(open(sys.argv[1]))
sys.path.insert(0, job["plugin_scripts"])
import textprep  # noqa: E402

eng = job["engine"]
k = Kokoro(eng["model"], eng["voices_file"])
voice = job.get("voice") or "af_heart"
lang = job.get("lang") or eng.get("default_lang") or "en-us"
speed = job.get("speed") or 1.0

# Voice blends: "af_heart:60,af_bella:40" -> weighted style vector.
if "," in voice or ":" in voice:
    parts = [p.split(":") for p in voice.split(",")]
    weights = np.array([float(p[1]) if len(p) > 1 else 1.0 for p in parts])
    weights = weights / weights.sum()
    style = sum(w * k.get_voice_style(p[0]) for w, p in zip(weights, parts))
else:
    style = voice

audio, sr = [], 24000
gap = None
for piece in textprep.chunk(job["text"], 400):
    samples, sr = k.create(piece, voice=style, speed=speed, lang=lang)
    if gap is None:
        gap = np.zeros(int(sr * 0.25), dtype=samples.dtype)
    audio += [samples, gap]
sf.write(job["out"], np.concatenate(audio[:-1]) if audio else np.zeros(1), sr)
