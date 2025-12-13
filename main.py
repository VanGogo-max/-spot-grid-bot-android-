# main.py
import time
import sys
import os
import signal
import logging
import numpy as np

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
error_log = []
active_orders = {}  # {exchange_name: [order_ids]}

# Константи
MIN_ABS_PROFIT_USD = 0.02  # Минимална цел за печалба в USD
MAX_RISK_PERCENT = 0.2     # Макс. 20% от баланса на сделка

def record_error():
    error_log.append(time.time())

def too_many_errors():
    now = time.time()
    global error_log
    error_log = [t for t in error_log if now - t < 600]
    return len(error_log) >= 3

def retry(func, max_retries=3, delay=5):
    for i in range(max_retries):
        try:
            return func()
        except Exception as e:
            if i == max_retries - 1:
                raise e
            logger.warning(f"🔁 Опит {i+1} за повторно изпълнение... Грешка: {e}")
            time.sleep(delay)
    return None

def select_best_symbol_for_exchange(exchange):
    best_symbol = None
    best_score = -1
    for sym in TRADE_SYMBOLS:
        try:
            klines = retry(lambda: exchange.get_klines(sym, "1h", 50))
            if not klines or len(klines) < 20:
                continue
            if not (is_safe_market(klines) and is_market_trending(klines)):
                continue
            volatility = np.std(np.diff(np.log(klines)))
            if volatility > best_score:
                best_score = volatility
                best_symbol = sym
        except Exception as e:
            logger.warning(f"⚠️ Грешка при анализ на {sym}: {e}")
    return best_symbol

def select_best_exchange():
    candidates = []
    for ex in EXCHANGES:
        if not ex.is_active():
            continue
        try:
            balance = retry(lambda: ex.get_balance("USDT"))
            if balance < MIN_TRADE_USDT:
                continue
            candidates.append((ex, balance))
        except Exception as e:
            logger.error(f"⚠️ {ex.name} грешка при баланс: {e}")
            send_telegram_message(f"⚠️ {ex.name}: грешка баланс")
    return max(candidates, key=lambda x: x[1]) if candidates else (None, 0)

def cancel_all_orders(exchange, symbol=None):
    try:
        orders = exchange.get_open_orders(symbol)
        for order in orders:
            exchange.cancel_order(symbol, order["orderId"])
            logger.info(f"❌ Отменена поръчка {order['orderId']}")
    except Exception as e:
        logger.error(f"Грешка при отмяна на поръчки: {e}")

def graceful_shutdown(signum, frame):
    logger.info("🛑 Получен сигнал за спиране. Отмяна на всички активни поръчки...")
    for ex in EXCHANGES:
        try:
            cancel_all_orders(ex)
        except:
            pass
    send_telegram_message("🔴 Ботът спря коректно.")
    sys.exit(0)

def main():
    global last_trade_timestamp
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    logger.info("🚀 Оптимизиран low-risk spot бот стартира...")
    logger.info("🔒 Без KYC | 4 борси | Проверка на изпълнение | Динамична печалба")
    send_telegram_message("🟢 Ботът стартира! Готов за търговия.")

    while True:
        try:
            if too_many_errors():
                halt_msg = "🛑 Твърде много грешки! Спиране за 1 час."
                logger.critical(halt_msg)
                send_telegram_message(halt_msg)
                time.sleep(3600)
                continue

            exchange, balance = select_best_exchange()
            if not exchange:
                logger.warning("❌ Няма активна борса с достатъчен баланс.")
                time.sleep(600)
                continue

            if time.time() - last_trade_timestamp < 3600:
                logger.info("⏳ Чакам до следваща възможност (1 час между сделки)...")
                time.sleep(600)
                continue

            symbol = select_best_symbol_for_exchange(exchange)
            if not symbol:
                logger.warning("❌ Няма подходящ символ за търговия в момента.")
                time.sleep(1800)
                continue

            # Получаване на информация за символа
            symbol_info = exchange.get_symbol_info(symbol)
            current_price = exchange.get_price(symbol)

            # Изчисление на размер на сделката
            risk_pct = min(RISK_PERCENT, MAX_RISK_PERCENT)
            trade_usdt = max(MIN_TRADE_USDT, balance * risk_pct)

            qty_raw = trade_usdt / current_price
            qty = round(qty_raw, symbol_info["quantity_precision"])
            if qty < symbol_info["min_qty"]:
                logger.warning(f"❌ Количеството {qty} е под минимума {symbol_info['min_qty']}")
                time.sleep(600)
                continue

            # Получаване на такси и изчисление на цел за печалба
            maker_fee = getattr(exchange, 'maker_fee', 0.001)
            min_profit_pct = (MIN_ABS_PROFIT_USD / trade_usdt) + 2 * maker_fee
            profit_margin = max(PROFIT_TARGET, min_profit_pct, 0.003)  # мин. 0.3%

            # Динамичен лимит: -0.1% вместо -0.2%, или спрямо 50% от spread
            ticker = exchange.get_ticker(symbol)
            bid = float(ticker["bidPrice"])
            ask = float(ticker["askPrice"])
            spread_pct = (ask - bid) / ask if ask > 0 else 0.001

            # Купуваме малко под текущия bid, но не твърде далеч
            buy_price_raw = bid * (1 - min(0.001, spread_pct * 2))
            buy_price = round(buy_price_raw, symbol_info["price_precision"])
            sell_price_raw = buy_price * (1 + profit_margin)
            sell_price = round(sell_price_raw, symbol_info["price_precision"])

            if buy_price <= 0 or sell_price <= buy_price:
                logger.warning("⚠️ Невалидни цени за поръчка.")
                time.sleep(600)
                continue

            msg = f"📈 {exchange.name} | {symbol} | Баланс: {balance:.2f} USDT | Цел: ≥${MIN_ABS_PROFIT_USD}"
            logger.info(msg)
            send_telegram_message(msg)

            # ПОКУПКА
            logger.info(f"🛒 Изпращам лимит ордер за покупка: {qty} @ {buy_price}")
            buy_resp = retry(lambda: exchange.place_order(symbol, "BUY", buy_price, qty))
            if not buy_resp or (isinstance(buy_resp, dict) and buy_resp.get("code", 0) != 0):
                err = f"❌ Грешка при покупка: {buy_resp}"
                logger.error(err)
                send_telegram_message(f"❌ BUY грешка ({exchange.name})")
                record_error()
                time.sleep(600)
                continue

            order_id = buy_resp.get("orderId")
            filled_qty = 0
            filled_price = 0
            logger.info(f"⏳ Очакване за изпълнение на поръчка {order_id}...")

            for attempt in range(40):  # до 20 минути
                time.sleep(30)
                try:
                    status = exchange.get_order_status(symbol, order_id)
                    if status == "filled":
                        trades = exchange.get_my_trades(symbol, order_id)
                        if trades:
                            total_qty = sum(float(t["qty"]) for t in trades)
                            total_cost = sum(float(t["quoteQty"]) for t in trades)
                            filled_qty = total_qty
                            filled_price = total_cost / total_qty if total_qty > 0 else buy_price
                        break
                    elif status in ("canceled", "rejected"):
                        logger.warning(f"🛒 Поръчката е {status}. Пропускам сделка.")
                        break
                except Exception as e:
                    logger.warning(f"⚠️ Проблем при проверка на статус: {e}")

            if filled_qty <= 0:
                logger.warning("⚠️ Поръчката не е изпълнена. Отмяна.")
                try:
                    exchange.cancel_order(symbol, order_id)
                except:
                    pass
                time.sleep(600)
                continue

            # ПРОДАЖБА
            sell_qty = round(filled_qty, symbol_info["quantity_precision"])
            logger.info(f"💰 Изпращам лимит ордер за продажба: {sell_qty} @ {sell_price}")
            sell_resp = retry(lambda: exchange.place_order(symbol, "SELL", sell_price, sell_qty))
            if not sell_resp or (isinstance(sell_resp, dict) and sell_resp.get("code", 0) != 0):
                logger.error(f"❌ Грешка при продажба: {sell_resp}")
                send_telegram_message(f"❌ SELL грешка ({exchange.name})")
                record_error()
                time.sleep(600)
                continue

            sell_order_id = sell_resp.get("orderId")
            for attempt in range(40):
                time.sleep(30)
                try:
                    status = exchange.get_order_status(symbol, sell_order_id)
                    if status == "filled":
                        break
                    elif status in ("canceled", "rejected"):
                        logger.warning(f"💰 Продажбата е {status}. Неуспешна.")
                        break
                except Exception as e:
                    logger.warning(f"⚠️ Грешка при проверка на продажба: {e}")

            # Изчисление на реална печалба
            try:
                buy_trades = exchange.get_my_trades(symbol, order_id)
                sell_trades = exchange.get_my_trades(symbol, sell_order_id)

                total_buy_cost = sum(float(t["quoteQty"]) for t in buy_trades)
                total_sell_revenue = sum(float(t["quoteQty"]) for t in sell_trades)

                real_profit = total_sell_revenue - total_buy_cost
            except Exception as e:
                real_profit = (sell_price - filled_price) * filled_qty
                logger.warning(f"⚠️ Използвам оценена печалба: {e}")

            success_msg = f"✅ Успех!\n{exchange.name} | {symbol}\nРеална печалба: {real_profit:.4f} USDT"
            logger.info(success_msg)
            send_telegram_message(success_msg)

            last_trade_timestamp = time.time()
            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            graceful_shutdown(None, None)
        except Exception as e:
            record_error()
            err_msg = f"💥 Грешка: {str(e)[:150]}"
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
