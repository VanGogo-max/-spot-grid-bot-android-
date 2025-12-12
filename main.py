# main.py
import time
import sys
import os

# Добавяме директорията към пътя, ако е нужно
sys.path.append(os.path.dirname(__file__))

from config import *
from adapters import MEXCSpot, GateIOSpot, KuCoinSpot, CoinExSpot
from utils import is_safe_market

# Импортираме Telegram функцията (ако е налична)
try:
    from telegram_bot import send_telegram_message
except ImportError:
    def send_telegram_message(text):
        pass  # Ако няма telegram_bot.py, не прави нищо

# Списък с всички активни адаптери
EXCHANGES = [
    MEXCSpot(),
    GateIOSpot(),
    KuCoinSpot(),
    CoinExSpot()
]

def select_best_exchange():
    candidates = []
    for ex in EXCHANGES:
        if not ex.is_active():
            continue
        try:
            balance = ex.get_balance("USDT")
            if balance < MIN_TRADE_USDT:
                continue
            candidates.append((ex, balance))
        except Exception as e:
            print(f"⚠️ {ex.name} грешка при баланс: {e}")
            send_telegram_message(f"⚠️ {ex.name} грешка: {str(e)[:100]}")
    if not candidates:
        return None, 0
    # Избира борсата с най-голям наличен баланс
    return max(candidates, key=lambda x: x[1])

def main():
    print("🌍 Универсален spot бот стартира...")
    print("🔒 Без KYC | Поддържа MEXC, Gate.io, KuCoin, CoinEx\n")
    send_telegram_message("🟢 Ботът стартира! Готов за търговия.")

    while True:
        try:
            exchange, balance = select_best_exchange()
            if not exchange:
                msg = "❌ Няма активна борса с достатъчен баланс"
                print(msg)
                send_telegram_message(msg)
                time.sleep(600)
                continue

            symbol = TRADE_SYMBOLS[0]  # Можеш да разшириш логиката за избор
            current_price = exchange.get_price(symbol)
            trade_usdt = max(MIN_TRADE_USDT, balance * RISK_PERCENT)
            qty = trade_usdt / current_price

            # Проверка за безопасност на пазара (ако има klines)
            safe = True
            if hasattr(exchange, "get_klines"):
                klines = exchange.get_klines(symbol, "1h", 100)
                if klines:
                    safe = is_safe_market(klines)
            if not safe:
                msg = f"⏸️ {exchange.name}: пазарът не е безопасен за {symbol}"
                print(msg)
                send_telegram_message(msg)
                time.sleep(300)
                continue

            # Цени — 0.2% под и 0.1% над текущата
            buy_price = round(current_price * 0.998, 8)
            sell_price = round(current_price * 1.001, 8)

            print(f"📈 {exchange.name} | {symbol} | Баланс: {balance:.2f} USDT")
            print(f"🛒 Купувам {qty:.6f} на {buy_price}")

            buy_resp = exchange.place_order(symbol, "BUY", buy_price, qty)
            if "error" in str(buy_resp).lower() or (isinstance(buy_resp, dict) and "code" in buy_resp and buy_resp["code"] != 0):
                err_msg = f"❌ Грешка при покупка на {exchange.name}: {buy_resp}"
                print(err_msg)
                send_telegram_message(err_msg)
                time.sleep(300)
                continue

            time.sleep(12)  # Чакаме изпълнение

            print(f"💰 Продавам на {sell_price}")
            sell_resp = exchange.place_order(symbol, "SELL", sell_price, qty)
            if "error" in str(sell_resp).lower() or (isinstance(sell_resp, dict) and "code" in sell_resp and sell_resp["code"] != 0):
                err_msg = f"❌ Грешка при продажба на {exchange.name}: {sell_resp}"
                print(err_msg)
                send_telegram_message(err_msg)
                time.sleep(300)
                continue

            estimated_profit = (sell_price - buy_price) * qty
            success_msg = f"✅ Успешна сделка!\n{exchange.name} | {symbol}\nПечалба: {estimated_profit:.4f} USDT"
            print(success_msg + "\n")
            send_telegram_message(success_msg)

            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("\n🛑 Ботът спрян от потребителя.")
            send_telegram_message("🔴 Ботът беше спрян ръчно.")
            break
        except Exception as e:
            err_msg = f"💥 Грешка в main цикъла: {str(e)[:150]}"
            print(err_msg)
            send_telegram_message(err_msg)
            time.sleep(300)

if __name__ == "__main__":
    main()
