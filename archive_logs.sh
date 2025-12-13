#!/bin/bash
# archive_logs.sh — архивира bot.log на всеки 7 дни

LOG_DIR="logs"
ARCHIVE_DIR="logs/archive"
mkdir -p "$ARCHIVE_DIR"

# Архивираме текущия лог с дата
DATE=$(date +%Y-%m-%d)
cp "$LOG_DIR/bot.log" "$ARCHIVE_DIR/bot_$DATE.log"

# Изчистваме текущия лог (запазваме последните 100 реда за контекст)
tail -n 100 "$LOG_DIR/bot.log" > "$LOG_DIR/bot.log.tmp" && mv "$LOG_DIR/bot.log.tmp" "$LOG_DIR/bot.log"

echo "✅ Архивиран лог до $DATE"
