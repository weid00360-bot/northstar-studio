#!/bin/bash
# 装/卸 每早自动日报(macOS launchd)。路径按本仓库自动生成,不写死任何人。
#   安装: bash scripts/install_daily.sh install [profile_id] [小时]
#   卸载: bash scripts/install_daily.sh uninstall
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.creator.daily-report"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
ACTION="${1:-install}"
PROFILE="${2:-迪迪}"
HOUR="${3:-8}"

if [ "$ACTION" = "uninstall" ]; then
    launchctl unload "$PLIST" 2>/dev/null || true
    rm -f "$PLIST"
    echo "已卸载每日日报任务"
    exit 0
fi

mkdir -p "$REPO/reports" "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array>
    <string>/bin/bash</string><string>$REPO/scripts/daily_run.sh</string><string>$PROFILE</string>
  </array>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>$HOUR</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>$REPO/reports/daily_stdout.log</string>
  <key>StandardErrorPath</key><string>$REPO/reports/daily_stderr.log</string>
</dict></plist>
EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "✅ 已装:每天 ${HOUR}:00 为档案「$PROFILE」生成网页日报并弹出"
echo "   立即试跑一次: bash $REPO/scripts/daily_run.sh $PROFILE"
