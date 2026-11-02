#!/usr/bin/env bash
# Install NeuTTS Air (Neuphonic, Apache-2.0) for CPU voice cloning and register it.
#   install.sh [--quant q4|q8]     (default q4: ~0.5 GB backbone, real-time-ish on laptop CPUs)
# Uses CPU torch (not the 2.5 GB CUDA build) and a prebuilt CPU llama-cpp-python wheel.
# Registers Neuphonic's bundled sample speakers (jo, dave, emily, ...) as voice profiles.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS="$HERE/../../scripts"
QUANT="q4"
[ "${1:-}" = "--quant" ] && QUANT="${2:-q4}"
BACKBONE="neuphonic/neutts-air-${QUANT}-gguf"
CODEC="neuphonic/neucodec"

command -v uv >/dev/null || { echo "uv is required: https://docs.astral.sh/uv/" >&2; exit 1; }
command -v espeak-ng >/dev/null || { echo "espeak-ng is required (apt install espeak-ng / dnf install espeak-ng)" >&2; exit 1; }

DATA="$(python3 "$SCRIPTS/registry.py" path)"
DIR="$DATA/engines/neutts"
PY="$DIR/venv/bin/python"
mkdir -p "$DIR"
[ -x "$PY" ] || uv venv --python 3.12 "$DIR/venv"
pipi() { uv pip install --python "$PY" -q "$@"; }

# Pinned set, verified 2026-11-02. Unpinned, uv resolves torch 2.15+cpu with torchaudio
# 2.11 and torchao 0.18, and torchtune 0.6.1 (pulled in by neucodec) then fails with
# "No module named torchao.dtypes.nf4tensor". The constraints file keeps neutts from
# upgrading torch back to a CUDA build from PyPI.
CPU_INDEX="https://download.pytorch.org/whl/cpu"
PINS="$DIR/constraints.txt"
printf 'torch==2.9.1\ntorchaudio==2.9.1\ntorchao==0.14.1\n' > "$PINS"
pipi "torch==2.9.1" "torchaudio==2.9.1" --index-url "$CPU_INDEX"
pipi llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu --only-binary llama-cpp-python \
  || { echo "no prebuilt llama-cpp-python wheel; building from source (needs cmake + a C++ compiler) ..." >&2; pipi llama-cpp-python; }
pipi "neutts[llama]" "torchao==0.14.1" -c "$PINS" --extra-index-url "$CPU_INDEX" --index-strategy unsafe-best-match
"$PY" -I -c "import torch; assert torch.version.cuda is None, torch.__version__" \
  || { echo "a CUDA torch build slipped in; expected CPU-only" >&2; exit 1; }
VERSION=$("$PY" -I -c "import importlib.metadata as m; print(m.version('neutts'))")

# Both Neuphonic repos are gated (auto-approved): the user must accept the terms on
# Hugging Face and have a token (`hf auth login`, or HF_TOKEN).
"$PY" -I - "$BACKBONE" "$CODEC" <<'PYEOF' || exit 3
import sys
from huggingface_hub import auth_check
bad = []
for repo in sys.argv[1:]:
    try:
        auth_check(repo)
    except Exception as e:
        bad.append(f"  https://huggingface.co/{repo}   ({type(e).__name__})")
if bad:
    print("Accept the terms for these gated Hugging Face repos (logged in as your token's account), then rerun:", file=sys.stderr)
    print("\n".join(bad), file=sys.stderr)
    sys.exit(3)
PYEOF

python3 "$SCRIPTS/registry.py" set-engine neutts "$(cat <<JSON
{
  "family": "neutts",
  "model_id": "neuphonic/neutts-air",
  "backend": "neutts $VERSION (llama.cpp GGUF)",
  "backbone": "$BACKBONE",
  "codec": "$CODEC",
  "device": "cpu",
  "python": "$PY",
  "default_voice": "jo",
  "cloning": true,
  "clone_needs_transcript": true,
  "clone_seconds": "3-15",
  "languages": ["en"],
  "sample_rate": 24000,
  "license": "Apache-2.0 (outputs watermarked with Perth)"
}
JSON
)" >/dev/null

# Bundled sample speakers, already encoded by Neuphonic.
RAW="https://raw.githubusercontent.com/neuphonic/neutts/main/samples"
for s in jo dave emily paul sophie steven; do
  d="$DATA/voices/neutts-$s"; mkdir -p "$d"
  [ -s "$d/neutts.codes.pt" ] || curl -fsSL "$RAW/$s.pt" -o "$d/neutts.codes.pt"
  [ -s "$d/reference.txt" ] || curl -fsSL "$RAW/$s.txt" -o "$d/reference.txt"
  python3 "$SCRIPTS/registry.py" add-voice "$s" "$(python3 -c '
import json,sys; d=sys.argv[1]
print(json.dumps({"engine":"neutts","codes":d+"/neutts.codes.pt","ref_text":open(d+"/reference.txt").read().strip(),
                  "source":"neuphonic sample","dir":d}))' "$d")" >/dev/null
done

TEST="$DIR/smoke-test.wav"
echo "smoke test (first run downloads the backbone and codec) ..." >&2
python3 "$SCRIPTS/speak.py" --engine neutts --voice jo --text "NeuTTS Air is installed and working." --out "$TEST"
python3 "$SCRIPTS/registry.py" set-engine neutts "{\"last_smoke_test\": \"$(date -I)\", \"smoke_test_wav\": \"$TEST\"}" >/dev/null
echo "neutts: OK ($BACKBONE)"
