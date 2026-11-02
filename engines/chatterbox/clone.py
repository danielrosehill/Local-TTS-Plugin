"""Chatterbox one-shot clone: reference clip -> saved Conditionals (conds.pt).

Called by scripts/clone-voice.py inside the chatterbox venv with a job JSON file:
  {"engine": rec, "variant": "turbo", "reference": "ref.wav", "out_dir": ".../voices/<name>",
   "exaggeration": 0.5}
Prints a JSON fragment for the voice profile. The conds file is the stored embedding:
speaker embedding + prompt speech tokens + S3Gen reference features, reloaded on each
generate so the reference never has to be re-encoded.
"""
import json
import sys
from pathlib import Path

job = json.load(open(sys.argv[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load  # noqa: E402

variant = job.get("variant") or job["engine"].get("default_variant") or "turbo"
model, _, dev = load(variant, job["engine"])
ex = job.get("exaggeration", 0.5)
model.prepare_conditionals(job["reference"], exaggeration=ex)
out = Path(job["out_dir"]) / f"chatterbox-{variant}.conds.pt"
model.conds.save(out)
print(json.dumps({"variant": variant, "conds": str(out), "exaggeration": ex}))
