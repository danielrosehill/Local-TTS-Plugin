#!/usr/bin/env bash
# Install Chatterbox (Resemble AI) into its own uv venv and register it.
#
#   install.sh --device rocm|cuda|cpu [--variants turbo,standard,multilingual,nano]
#              [--torch-index URL] [--hsa-override 11.0.0]
#
# Defaults: variants = turbo on a GPU, nano on CPU.
#
# Why torch is installed first and chatterbox with --no-deps: chatterbox-tts 0.1.7 pins
# torch==2.6.0, which has no wheel on current ROCm indexes and pulls a ~2.5 GB CUDA
# build on PyPI. Installing the right torch build first, then chatterbox without its
# deps, then its runtime deps unpinned from torch, keeps the build we chose.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS="$HERE/../../scripts"

DEVICE=""; VARIANTS=""; INDEX=""; HSA=""
while [ $# -gt 0 ]; do
  case "$1" in
    --device) DEVICE="$2"; shift 2 ;;
    --variants) VARIANTS="$2"; shift 2 ;;
    --torch-index) INDEX="$2"; shift 2 ;;
    --hsa-override) HSA="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done
[ -n "$DEVICE" ] || DEVICE=$(bash "$SCRIPTS/detect-hardware.sh" | python3 -c 'import json,sys; print(json.load(sys.stdin)["device"])')
if [ -z "$VARIANTS" ]; then [ "$DEVICE" = cpu ] && VARIANTS=nano || VARIANTS=turbo; fi

if [ -z "$INDEX" ]; then
  case "$DEVICE" in
    cpu) INDEX="https://download.pytorch.org/whl/cpu" ;;
    cuda) INDEX="https://download.pytorch.org/whl/cu128" ;;
    rocm)
      # Match the installed ROCm major.minor; fall back to 6.4.
      V=$(cat /opt/rocm/.info/version 2>/dev/null | cut -d. -f1,2 | cut -d- -f1)
      INDEX="https://download.pytorch.org/whl/rocm${V:-6.4}"
      curl -fsI "$INDEX/torch/" >/dev/null 2>&1 || INDEX="https://download.pytorch.org/whl/rocm6.4"
      ;;
    *) echo "device must be rocm, cuda or cpu" >&2; exit 2 ;;
  esac
fi

DATA="$(python3 "$SCRIPTS/registry.py" path)"
DIR="$DATA/engines/chatterbox"
PY="$DIR/venv/bin/python"
mkdir -p "$DIR"
command -v uv >/dev/null || { echo "uv is required: https://docs.astral.sh/uv/" >&2; exit 1; }

[ -x "$PY" ] || uv venv --python 3.11 "$DIR/venv"
pipi() { uv pip install --python "$PY" -q "$@"; }

echo "torch from $INDEX ..." >&2
pipi torch torchaudio --index-url "$INDEX"
pipi --no-deps chatterbox-tts
pipi "numpy>=1.24,<2" "librosa==0.11.0" s3tokenizer "transformers==5.2.0" "diffusers==0.29.0" \
     "resemble-perth @ git+https://github.com/resemble-ai/Perth.git@master" "conformer==0.3.2" \
     "safetensors==0.5.3" spacy-pkuseg "pykakasi==2.3.0" pyloudnorm omegaconf soundfile

ENVJSON="{}"
[ -n "$HSA" ] && ENVJSON="{\"HSA_OVERRIDE_GFX_VERSION\": \"$HSA\"}"
[ -n "$HSA" ] && export HSA_OVERRIDE_GFX_VERSION="$HSA"

# Check the torch build survived the dep install and sees the GPU.
TORCH=$("$PY" -I -c "
import json, torch
print(json.dumps({'torch': torch.__version__, 'hip': torch.version.hip, 'cuda': torch.version.cuda,
                  'gpu': torch.cuda.is_available(),
                  'gpu_name': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}))")
echo "$TORCH" >&2
if [ "$DEVICE" != cpu ] && ! echo "$TORCH" | grep -q '"gpu": true'; then
  echo "WARNING: torch cannot see the GPU; generation will fall back to CPU." >&2
  [ "$DEVICE" = rocm ] && echo "  On consumer AMD cards try --hsa-override (e.g. 11.0.0 for RDNA3, 10.3.0 for RDNA2)." >&2
fi
VERSION=$("$PY" -I -c "import importlib.metadata as m; print(m.version('chatterbox-tts'))")

FIRST=${VARIANTS%%,*}
VLIST=$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1].split(",")))' "$VARIANTS")
python3 "$SCRIPTS/registry.py" set-engine chatterbox "$(cat <<JSON
{
  "family": "chatterbox",
  "model_id": "ResembleAI/chatterbox (turbo: ResembleAI/chatterbox-turbo, nano: ResembleAI/chatterbox-nano)",
  "backend": "chatterbox-tts $VERSION",
  "device": "$DEVICE",
  "torch": $TORCH,
  "torch_index": "$INDEX",
  "python": "$PY",
  "env": $ENVJSON,
  "variants": $VLIST,
  "default_variant": "$FIRST",
  "default_voice": "builtin",
  "default_lang": "en",
  "cloning": true,
  "clone_min_seconds": 5,
  "sample_rate": 24000,
  "license": "MIT",
  "generate": {"standard": {"exaggeration": 0.5, "cfg_weight": 0.5}, "multilingual": {"exaggeration": 0.5, "cfg_weight": 0.5}}
}
JSON
)" >/dev/null

# Downloads each variant's weights (first load) and smoke-tests it.
for v in ${VARIANTS//,/ }; do
  echo "smoke test: $v (first run downloads the weights) ..." >&2
  python3 "$SCRIPTS/speak.py" --engine chatterbox --variant "$v" --voice builtin \
    --text "Chatterbox $v is installed and working." --out "$DIR/smoke-test-$v.wav" || {
      echo "smoke test failed for $v" >&2; exit 1; }
done
python3 "$SCRIPTS/registry.py" set-engine chatterbox "{\"last_smoke_test\": \"$(date -I)\"}" >/dev/null
echo "chatterbox: OK ($DEVICE; variants $VARIANTS)"
