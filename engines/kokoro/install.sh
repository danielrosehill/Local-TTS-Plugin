#!/usr/bin/env bash
# Install Kokoro-82M (ONNX build, CPU) into its own uv venv and register it.
#   install.sh [--precision fp32|fp16|int8]   (default fp32; int8 for <8 GB RAM)
# Idempotent: re-running skips what is already there.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS="$HERE/../../scripts"
PREC="fp32"
[ "${1:-}" = "--precision" ] && PREC="${2:-fp32}"

DATA="$(python3 "$SCRIPTS/registry.py" path)"
DIR="$DATA/engines/kokoro"
MODELS="$DIR/models"
REL="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
case "$PREC" in
  fp32) MODEL_FILE="kokoro-v1.0.onnx" ;;
  fp16) MODEL_FILE="kokoro-v1.0.fp16.onnx" ;;
  int8) MODEL_FILE="kokoro-v1.0.int8.onnx" ;;
  *) echo "unknown precision: $PREC" >&2; exit 2 ;;
esac

command -v uv >/dev/null || { echo "uv is required: https://docs.astral.sh/uv/" >&2; exit 1; }
mkdir -p "$MODELS"

if [ ! -x "$DIR/venv/bin/python" ]; then
  uv venv --python 3.12 "$DIR/venv"
fi
VIRTUAL_ENV="$DIR/venv" uv pip install --python "$DIR/venv/bin/python" -q "kokoro-onnx>=0.4" soundfile

fetch() { # url dest
  [ -s "$2" ] && return 0
  echo "downloading $(basename "$2") ..." >&2
  curl -fsSL --retry 3 -o "$2.part" "$1" && mv "$2.part" "$2"
}
fetch "$REL/$MODEL_FILE" "$MODELS/$MODEL_FILE"
fetch "$REL/voices-v1.0.bin" "$MODELS/voices-v1.0.bin"

# Smoke test straight through the runner, then record what is installed.
VOICES=$("$DIR/venv/bin/python" -I -c "
import sys, json
from kokoro_onnx import Kokoro
k = Kokoro(sys.argv[1], sys.argv[2])
print(json.dumps(sorted(k.get_voices())))
" "$MODELS/$MODEL_FILE" "$MODELS/voices-v1.0.bin")
VERSION=$("$DIR/venv/bin/python" -I -c "import importlib.metadata as m; print(m.version('kokoro-onnx'))")

python3 "$SCRIPTS/registry.py" set-engine kokoro "$(cat <<JSON
{
  "family": "kokoro",
  "model_id": "hexgrad/Kokoro-82M",
  "backend": "kokoro-onnx $VERSION",
  "precision": "$PREC",
  "device": "cpu",
  "python": "$DIR/venv/bin/python",
  "model": "$MODELS/$MODEL_FILE",
  "voices_file": "$MODELS/voices-v1.0.bin",
  "default_voice": "af_heart",
  "default_lang": "en-us",
  "voices": $VOICES,
  "cloning": false,
  "sample_rate": 24000,
  "license": "Apache-2.0"
}
JSON
)" >/dev/null

TEST="$DIR/smoke-test.wav"
python3 "$SCRIPTS/speak.py" --engine kokoro --text "Kokoro is installed and working." --out "$TEST"
python3 "$SCRIPTS/registry.py" set-engine kokoro "{\"last_smoke_test\": \"$(date -I)\", \"smoke_test_wav\": \"$TEST\"}" >/dev/null
echo "kokoro: OK ($PREC, $(echo "$VOICES" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))') voices)"
