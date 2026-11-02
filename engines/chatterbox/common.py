"""Shared loader for the Chatterbox runner and cloner (runs inside the chatterbox venv).

Variants (Resemble AI, MIT):
  turbo         ChatterboxTurboTTS            350M, English, inline [laugh]/[cough] tags, fastest on GPU
  nano          ChatterboxTurboTTS(nano=True) 110M, English, the CPU option
  standard      ChatterboxTTS                 500M, English, exaggeration + cfg_weight controls
  multilingual  ChatterboxMultilingualTTS     500M, 23 languages, language_id per call
"""
import os


def device_for(rec: dict) -> str:
    import torch

    want = rec.get("device", "cpu")
    if want in ("cuda", "rocm") and torch.cuda.is_available():
        return "cuda"  # ROCm builds of torch expose the GPU as "cuda"
    return "cpu"


def load(variant: str, rec: dict):
    dev = device_for(rec)
    if variant in ("turbo", "nano"):
        from chatterbox.tts_turbo import ChatterboxTurboTTS as M, Conditionals as C

        model = M.from_pretrained(device=dev, nano=(variant == "nano"))
    elif variant == "standard":
        from chatterbox.tts import ChatterboxTTS as M, Conditionals as C

        model = M.from_pretrained(device=dev)
    elif variant == "multilingual":
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS as M, Conditionals as C

        model = M.from_pretrained(device=dev)
    else:
        raise SystemExit(f"unknown chatterbox variant: {variant}")
    return model, C, dev


os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
