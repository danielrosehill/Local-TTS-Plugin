"""Chatterbox runner. Called by scripts/speak.py inside the chatterbox venv with one
argument: a job JSON file. Writes a WAV at model.sr (24 kHz)."""
import json
import sys
from pathlib import Path

job = json.load(open(sys.argv[1]))
sys.path.insert(0, job["plugin_scripts"])
sys.path.insert(0, str(Path(__file__).resolve().parent))
import textprep  # noqa: E402
from common import load  # noqa: E402

import torch  # noqa: E402
import torchaudio as ta  # noqa: E402

rec = job["engine"]
variant = job.get("variant") or "turbo"
model, Conditionals, dev = load(variant, rec)

profile = job.get("profile")
if profile:
    model.conds = Conditionals.load(profile["conds"], map_location=dev).to(dev)
elif model.conds is None:
    raise SystemExit(f"chatterbox {variant} has no built-in voice; clone one with clone-voice first")

opts = rec.get("generate", {}).get(variant, {}).copy()
if variant == "multilingual":
    opts["language_id"] = job.get("lang") or rec.get("default_lang") or "en"
for k in ("exaggeration", "cfg_weight", "temperature"):
    if k in (profile or {}) and variant in ("standard", "multilingual"):
        opts[k] = profile[k]

pieces = []
gap = torch.zeros(1, int(model.sr * 0.2))
for chunk in textprep.chunk(job["text"], 280):
    wav = model.generate(chunk, **opts)
    pieces += [wav.cpu(), gap]
ta.save(job["out"], torch.cat(pieces[:-1], dim=1), model.sr)
