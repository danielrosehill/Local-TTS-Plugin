"""NeuTTS one-shot clone: reference clip -> NeuCodec codes (codes.pt), the stored embedding.

Called by scripts/clone-voice.py inside the neutts venv with a job JSON file:
  {"engine": rec, "reference": "ref.wav", "out_dir": ".../voices/<name>", "ref_text": "..."}
Loads only the codec (not the backbone), so cloning is quick.
"""
import json
import sys
from pathlib import Path

import librosa
import torch
from neucodec import NeuCodec

job = json.load(open(sys.argv[1]))
if not job.get("ref_text"):
    raise SystemExit("neutts cloning needs the exact transcript of the reference clip (ref_text)")

codec = NeuCodec.from_pretrained(job["engine"]["codec"]).eval().to("cpu")
wav, _ = librosa.load(job["reference"], sr=16000, mono=True)
with torch.no_grad():
    codes = codec.encode_code(audio_or_path=torch.from_numpy(wav).float()[None, None]).squeeze(0).squeeze(0)
out = Path(job["out_dir"]) / "neutts.codes.pt"
torch.save(codes, out)
print(json.dumps({"codes": str(out), "ref_text": job["ref_text"]}))
