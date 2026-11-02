"""NeuTTS Air runner (Neuphonic, Apache-2.0; GGUF backbone on CPU via llama.cpp).
Called by scripts/speak.py inside the neutts venv with one argument: a job JSON file.

Every NeuTTS voice is a clone: a voice profile holds the reference's pre-encoded
NeuCodec codes (codes.pt) and its transcript (ref_text). The reference audio is
not re-read at generation time."""
import json
import os
import sys

import numpy as np
import soundfile as sf
import torch

job = json.load(open(sys.argv[1]))
sys.path.insert(0, job["plugin_scripts"])
import textprep  # noqa: E402
from neutts import NeuTTS  # noqa: E402

rec = job["engine"]
profile = job.get("profile")
if not profile:
    raise SystemExit("neutts needs a cloned voice: pass --voice <profile> (setup registers the bundled samples)")

tts = NeuTTS(backbone_repo=rec["backbone"], backbone_device="cpu",
             codec_repo=rec["codec"], codec_device="cpu")
codes = torch.load(profile["codes"], map_location="cpu")
ref_text = profile["ref_text"]

# 2048-token context covers reference + output (~30 s of audio), so keep chunks short.
out, gap = [], np.zeros(int(24000 * 0.2), dtype=np.float32)
for piece in textprep.chunk(job["text"], 220):
    out += [tts.infer(piece, codes, ref_text).astype(np.float32), gap]
sf.write(job["out"], np.concatenate(out[:-1]), 24000)

# llama-cpp-python's finaliser raises "'NoneType' object is not callable" at interpreter
# shutdown (free_model after module teardown). The WAV is written; skip the teardown.
sys.stdout.flush()
os._exit(0)
