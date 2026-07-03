#!/bin/bash
# 每早自动:拉底表 → 生成网页日报 → 浏览器弹出 → 桌面通知
# profile 驱动,不写死任何号。用法: daily_run.sh [profile_id]  (默认读 DAILY_PROFILE 或 "迪迪")
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
PROFILE="${1:-${DAILY_PROFILE:-}}"
if [ -z "$PROFILE" ]; then
    echo "用法: daily_run.sh <你的档案id>  (或设 DAILY_PROFILE 环境变量)" >&2
    echo "不默认任何示例档案——用错档案判定全错。" >&2
    exit 1
fi
PY="$REPO/.venv/bin/python"
[ -x "$PY" ] || PY="python3"

notify() { osascript -e "display notification \"$2\" with title \"$1\" sound name \"Glass\"" 2>/dev/null || true; }

if HTML=$("$PY" "$REPO/engine/fetch/daily_report_html.py" "$PROFILE" --n 10 2>>"$REPO/reports/daily.log"); then
    open "$HTML"
    notify "📊 抖音日报已更新" "$(basename "$HTML")"
else
    notify "❌ 抖音日报失败" "看 reports/daily.log;确认浏览器已登录抖音"
    exit 1
fi
