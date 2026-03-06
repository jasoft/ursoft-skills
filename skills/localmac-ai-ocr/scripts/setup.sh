#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

if ! command -v uv >/dev/null 2>&1; then
  echo "找不到 uv，请先安装 uv。" >&2
  exit 1
fi

uv sync --project "$ROOT_DIR"

if [[ ! -f "$ROOT_DIR/.env" && -f "$ROOT_DIR/.env.example" ]]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
  echo "已生成 $ROOT_DIR/.env，请填入 AISTUDIO_OCR_API_URL 和 AISTUDIO_OCR_TOKEN。"
fi

echo "安装完成。可先运行："
echo "  $ROOT_DIR/ocr doctor"
echo "  $ROOT_DIR/gui doctor --json"
