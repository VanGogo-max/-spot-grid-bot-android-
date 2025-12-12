# main.py
import time
import sys
import os

sys.path.append(os.path.dirname(__file__))

from config import *
from adapters import MEXCSpot, GateIOSpot, KuCoinSpot, CoinExSpot
from utils import is_safe_market, is_market_trending

# Telegram (по избор)
try:
    from telegram_bot import send_telegram_message
except ImportError:
    def send_telegram_message(text):
        pass

EXCHANGES = [
    MEXCSpot(),
    GateIOSpot(),
    KuCoinSpot(),
    CoinExSpot()
]

# Глобален таймер за последна сделка
last_trade_timestamp = 0

def select_best_symbol_for_exchange(exchange):
    best_symbol = None
    best_score = -1
    for sym in TRADE_SYMBOLS:
        try:
            klines = exchange.get_klines(sym, "1h", 50)
            if not klines:
                continue
            if not (is_safe_market(klines) and is_market_trending(klines)):
                continue
            volatility = np.std(np.diff(np.log(klines))) if len(klines) > 1 else 0
            if volatility > best_score:
                best_score = volatility
                best_symbol = sym
        except Exception as e:
            print(f"⚠️ Грешка при анализ на {sym}: {e}")
    return best_symbol or TRADE_SYMBOLS[0]

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
            send_telegram_message(f"⚠️ {ex.name}: грешка баланс")
    return max(candidates, key=lambda x: x[1]) if candidates else (None, 0)

def main():
    global last_trade_timestamp
    print("🚀 Оптимизиран бот стартира...")
    print("🔒 Без KYC | 4 борси | Волатилностен филтър | Адаптивен профит\n")
    send_telegram_message("🟢 Оптимизиран бот стартира!")

    while True:
        try:
            exchange, balance = select_best_exchange()
            if not exchange:
                print("❌ Няма активна борса с достатъчен баланс.")
                time.sleep(600)
                continue

            # Ограничение: 1 сделка на 1 час
            if time.time() - last_trade_timestamp < 3600:
                print("⏳ Чакам до следваща възможност (1 час между сделки)...")
                time.sleep(600)
                continue

            symbol = select_best_symbol_for_exchange(exchange)
            current_price = exchange.get_price(symbol)

            # Адаптивен размер на сделка
            if balance < 10:
                trade_usdt = MIN_TRADE_USDT
            else:
                trade_usdt = max(MIN_TRADE_USDT, balance * RISK_PERCENT)

            qty = trade_usdt / current_price
            if qty <= 0:
                continue

            # Динамична цел за печалба (минимум 0.25% + такси)
            maker_fee = getattr(exchange, 'maker_fee', 0.001)
            profit_margin = max(PROFIT_TARGET, 0.0025 + maker_fee)
            buy_price = round(current_price * 0.998, 8)
            sell_price = round(buy_price * (1 + profit_margin), 8)

            print(f"📈 {exchange.name} | {symbol} | Баланс: {balance:.2f} USDT")
            print(f"🛒 Купувам {qty:.6f} на {buy_price}")

            buy_resp = exchange.place_order(symbol, "BUY", buy_price, qty)
            if isinstance(buy_resp, dict) and buy_resp.get("code", 0) != 0:
                print(f"❌ Грешка при покупка: {buy_resp}")
                send_telegram_message(f"❌ BUY грешка ({exchange.name}): {buy_resp.get('msg', 'Неизвестна')}")
                time.sleep(600)
                continue

            time.sleep(15)

            print(f"💰 Продавам на {sell_price}")
            sell_resp = exchange.place_order(symbol, "SELL", sell_price, qty)
            if isinstance(sell_resp, dict) and sell_resp.get("code", 0) != 0:
                print(f"❌ Грешка при продажба: {sell_resp}")
                send_telegram_message(f"❌ SELL грешка ({exchange.name})")
                time.sleep(600)
                continue

            estimated_profit = (sell_price - buy_price) * qty
            success_msg = f"✅ Успех!\n{exchange.name} | {symbol}\nПечалба: {estimated_profit:.4f} USDT"
            print(success_msg + "\n")
            send_telegram_message(success_msg)

            last_trade_timestamp = time.time()  # Запомняме времето на последна сделка

            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("\n🛑 Спряно от потребителя.")
            send_telegram_message("🔴 Ботът е спрян.")
            break
        except Exception as e:
            print(f"💥 Грешка: {e}")
            send_telegram_message(f"💥 Грешка: {str(e)[:120]}")
            time.sleep(600)

if __name__ == "__main__":
    main()
