# main.py
import time
import sys
import os
import logging

# Настройка на logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("logs/bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

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

last_trade_timestamp = 0
error_log = []  # за защита при грешки

def record_error():
    error_log.append(time.time())

def too_many_errors():
    now = time.time()
    global error_log
    error_log = [t for t in error_log if now - t < 600]  # последните 10 мин
    return len(error_log) >= 3

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
            logger.warning(f"⚠️ Грешка при анализ на {sym}: {e}")
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
            logger.error(f"⚠️ {ex.name} грешка при баланс: {e}")
            send_telegram_message(f"⚠️ {ex.name}: грешка баланс")
    return max(candidates, key=lambda x: x[1]) if candidates else (None, 0)

def main():
    global last_trade_timestamp
    logger.info("🚀 Оптимизиран бот стартира...")
    logger.info("🔒 Без KYC | 4 борси | Логване | Защита от грешки")
    send_telegram_message("🟢 Ботът стартира! Готов за търговия.")

    while True:
        try:
            if too_many_errors():
                halt_msg = "🛑 Твърде много грешки! Ботът спира за 1 час."
                logger.critical(halt_msg)
                send_telegram_message(halt_msg)
                time.sleep(3600)
                continue

            exchange, balance = select_best_exchange()
            if not exchange:
                logger.warning("❌ Няма активна борса с достатъчен баланс.")
                time.sleep(600)
                continue

            # Ограничение: 1 сделка на час
            if time.time() - last_trade_timestamp < 3600:
                logger.info("⏳ Чакам до следваща възможност (1 час между сделки)...")
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
                logger.warning("⚠️ Невалиден размер на позиция.")
                time.sleep(600)
                continue

            # Цел за печалба: минимум 0.25% + такси за BUY и SELL
            maker_fee = getattr(exchange, 'maker_fee', 0.001)
            profit_margin = max(PROFIT_TARGET, 0.0025 + maker_fee * 2)
            buy_price = round(current_price * 0.998, 8)
            sell_price = round(buy_price * (1 + profit_margin), 8)

            msg = f"📈 {exchange.name} | {symbol} | Баланс: {balance:.2f} USDT"
            logger.info(msg)

            logger.info(f"🛒 Купувам {qty:.6f} на {buy_price}")
            buy_resp = exchange.place_order(symbol, "BUY", buy_price, qty)
            if isinstance(buy_resp, dict) and buy_resp.get("code", 0) != 0:
                err = f"❌ Грешка при покупка: {buy_resp}"
                logger.error(err)
                send_telegram_message(f"❌ BUY грешка ({exchange.name})")
                record_error()
                time.sleep(600)
                continue

            time.sleep(15)

            logger.info(f"💰 Продавам на {sell_price}")
            sell_resp = exchange.place_order(symbol, "SELL", sell_price, qty)
            if isinstance(sell_resp, dict) and sell_resp.get("code", 0) != 0:
                err = f"❌ Грешка при продажба: {sell_resp}"
                logger.error(err)
                send_telegram_message(f"❌ SELL грешка ({exchange.name})")
                record_error()
                time.sleep(600)
                continue

            estimated_profit = (sell_price - buy_price) * qty
            success_msg = f"✅ Успех!\n{exchange.name} | {symbol}\nПечалба: {estimated_profit:.4f} USDT"
            logger.info(success_msg)
            send_telegram_message(success_msg)

            last_trade_timestamp = time.time()
            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            logger.info("🛑 Спряно от потребителя.")
            send_telegram_message("🔴 Ботът е спрян ръчно.")
            break
        except Exception as e:
            record_error()
            err_msg = f"💥 Неочаквана грешка: {str(e)[:150]}"
            logger.exception(err_msg)
            send_telegram_message(err_msg)

            if too_many_errors():
                halt_msg = "🛑 Твърде много грешки! Спиране за 1 час."
                logger.critical(halt_msg)
                send_telegram_message(halt_msg)
                time.sleep(3600)
            else:
                time.sleep(600)

if __name__ == "__main__":
    main()
