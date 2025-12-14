# stats.py
import json
import time
import os
from datetime import datetime, date

STATS_FILE = "logs/trade_stats.json"

def load_stats():
    try:
        with open(STATS_FILE, "r") as f:
            return json.load(f)
    except:
        return {
            "total_trades": 0,
            "successful_trades": 0,
            "total_profit": 0.0,
            "daily": {}  # { "2025-12-14": { "trades": 1, "profit": 0.023 } }
        }

def save_stats(stats):
    os.makedirs("logs", exist_ok=True)
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f)

def record_trade(profit_usd, success=True):
    stats = load_stats()
    today = str(date.today())

    # Общи статистики
    stats["total_trades"] += 1
    if success:
        stats["successful_trades"] += 1
        stats["total_profit"] += profit_usd

    # Дневни статистики
    if today not in stats["daily"]:
        stats["daily"][today] = {"trades": 0, "profit": 0.0}
    stats["daily"][today]["trades"] += 1
    stats["daily"][today]["profit"] += profit_usd if success else 0

    save_stats(stats)
    return stats

def get_trend_7d():
    """Връща текстов тренд за последните 7 дни"""
    stats = load_stats()
    dates = sorted(stats["daily"].keys())[-7:]
    if not dates:
        return "Няма данни за последните 7 дни."

    lines = ["📈 **Тренд (последните 7 дни):**"]
    for d in dates:
        day_data = stats["daily"][d]
        profit = day_data["profit"]
        trades = day_data["trades"]
        arrow = "🔺" if profit > 0 else "🔻" if profit < 0 else "➖"
        lines.append(f"{d}: {arrow} ${profit:.3f} ({trades} сделки)")
    return "\n".join(lines)
