# daily_summary.py
import os
import re
from datetime import datetime, timedelta
from telegram_bot import send_telegram_message

def read_last_24h_logs():
    log_path = "logs/bot.log"
    if not os.path.exists(log_path):
        return []
    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    now = datetime.now()
    twenty_four_hours_ago = now - timedelta(hours=24)
    recent = []
    for line in lines:
        try:
            # Извличаме времето от реда: "2025-04-05 14:30:22 | ..."
            timestamp_str = " ".join(line.split(" | ")[:1])
            log_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            if log_time >= twenty_four_hours_ago:
                recent.append(line)
        except:
            continue
    return recent

def generate_summary():
    logs = read_last_24h_logs()
    trades = [l for l in logs if "✅ Успех!" in l]
    errors = [l for l in logs if "❌" in l or "💥" in l]
    
    total_profit = 0.0
    for t in trades:
        try:
            # Извличаме печалбата: "Печалба: 0.1234 USDT"
            match = re.search(r"Печалба: ([\d.]+) USDT", t)
            if match:
                total_profit += float(match.group(1))
        except:
            pass

    msg = (
        "📊 **Ежедневно резюме**\n"
        f"🗓️ {datetime.now().strftime('%Y-%m-%d')}\n"
        f"✅ Успешни сделки: {len(trades)}\n"
        f"⚠️ Грешки: {len(errors)}\n"
        f"💰 Обща печалба: {total_profit:.4f} USDT"
    )
    return msg

if __name__ == "__main__":
    try:
        summary = generate_summary()
        send_telegram_message(summary)
    except Exception as e:
        send_telegram_message(f"🔴 Грешка при резюмето: {e}")
