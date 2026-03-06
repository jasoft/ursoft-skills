#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"

python3 -m venv "$VENV_DIR"
. "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r "$ROOT_DIR/requirements.txt"

if [[ ! -f "$ROOT_DIR/.env" && -f "$ROOT_DIR/.env.example" ]]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
  echo "已生成 $ROOT_DIR/.env，请填入 AISTUDIO_OCR_API_URL 和 AISTUDIO_OCR_TOKEN。"
fi

echo "安装完成。可先运行："
echo "  $ROOT_DIR/ocr doctor"
echo "  $ROOT_DIR/gui doctor --json"
