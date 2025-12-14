#!/bin/bash
# notify_android.sh
# Използва Termux:API за нотификации и вибрация

TITLE="${1:-Съобщение}"
CONTENT="${2:-}"
VIBRATE="${3:-300}"  # милисекунди

# Изпращане на нотификация към Android
am broadcast \
  --user 0 \
  -a android.intent.action.NOTIFICATION \
  --es title "$TITLE" \
  --es content "$CONTENT" \
  --ei vibrate $VIBRATE \
  > /dev/null 2>&1

# Ако горното не работи (в някои ROMs), използвай termux-notification
if command -v termux-notification &> /dev/null; then
  termux-notification -t "$TITLE" -c "$CONTENT" --vibrate $VIBRATE
fi
