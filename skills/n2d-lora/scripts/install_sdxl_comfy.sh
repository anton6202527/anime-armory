#!/usr/bin/env bash
set -euo pipefail

# Install a local SDXL/ComfyUI sidechain for n2d LoRA validation and hero-shot
# enhancement. This does not download checkpoint weights by default; place SDXL
# checkpoints under ComfyUI/models/checkpoints and LoRAs under models/loras.

COMFY_HOME="${N2D_COMFYUI_HOME:-$HOME/ComfyUI}"
CONDA_ENV="${N2D_SDXL_CONDA_ENV:-sdxl-comfy}"
PYTHON_VERSION="${N2D_SDXL_PYTHON:-3.12}"
REPO_URL="${N2D_COMFYUI_REPO:-https://github.com/comfyanonymous/ComfyUI.git}"

usage() {
  cat <<EOF
Usage: $0 [--comfy-home PATH] [--env NAME] [--python VERSION]

Defaults:
  --comfy-home  $COMFY_HOME
  --env         $CONDA_ENV
  --python      $PYTHON_VERSION

This installs ComfyUI + a conda env for SDXL inference on macOS/Apple Silicon.
It does not download model weights.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --comfy-home)
      COMFY_HOME="$2"; shift 2 ;;
    --env)
      CONDA_ENV="$2"; shift 2 ;;
    --python)
      PYTHON_VERSION="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if ! command -v git >/dev/null 2>&1; then
  echo "[error] git not found" >&2
  exit 1
fi
if ! command -v conda >/dev/null 2>&1; then
  echo "[error] conda not found" >&2
  exit 1
fi

if [[ ! -d "$COMFY_HOME/.git" ]]; then
  mkdir -p "$(dirname "$COMFY_HOME")"
  git clone "$REPO_URL" "$COMFY_HOME"
else
  echo "[ok] ComfyUI already exists: $COMFY_HOME"
fi

if ! conda env list | awk '{print $1}' | grep -Fxq "$CONDA_ENV"; then
  conda create -y -n "$CONDA_ENV" "python=$PYTHON_VERSION"
else
  echo "[ok] conda env already exists: $CONDA_ENV"
fi

conda run -n "$CONDA_ENV" python -m pip install --upgrade pip wheel setuptools
conda run -n "$CONDA_ENV" python -m pip install --upgrade torch torchvision torchaudio
conda run -n "$CONDA_ENV" python -m pip install -r "$COMFY_HOME/requirements.txt"

mkdir -p "$COMFY_HOME/models/checkpoints" "$COMFY_HOME/models/loras" "$COMFY_HOME/models/controlnet" "$COMFY_HOME/models/ipadapter"

cat > "$COMFY_HOME/launch_n2d_sdxl.sh" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$COMFY_HOME"
conda run -n "$CONDA_ENV" python main.py --listen 127.0.0.1 --port "\${N2D_COMFYUI_PORT:-8188}"
EOF
chmod +x "$COMFY_HOME/launch_n2d_sdxl.sh"

echo "[ok] local SDXL/ComfyUI sidechain installed"
echo "[path] $COMFY_HOME"
echo "[env]  $CONDA_ENV"
echo "[next] put SDXL checkpoints in: $COMFY_HOME/models/checkpoints"
echo "[next] put LoRA safetensors in: $COMFY_HOME/models/loras"
echo "[run]  $COMFY_HOME/launch_n2d_sdxl.sh"
