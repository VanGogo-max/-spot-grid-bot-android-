# config.py

# Основни настройки
MIN_TRADE_USDT = 5.0          # Минимален USDT за сделка
RISK_PERCENT = 0.10           # 10% от баланса на сделка (макс. 20% в кода)
PROFIT_TARGET = 0.003         # 0.3% цел за печалба (минимум)
CHECK_INTERVAL = 300          # 5 минути между проверки (след успешна сделка)

# Търговски двойки — трябва да са налични на ВСИЧКИ 4 борси
TRADE_SYMBOLS = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "XRP/USDT",    # проверено: налично навсякъде
    "DOGE/USDT"
]

# API ключове — попълнете с ваши
EXCHANGE_KEYS = {
    "mexc": {
        "api_key": "YOUR_MEXC_API_KEY",
        "api_secret": "YOUR_MEXC_SECRET"
    },
    "gateio": {
        "api_key": "YOUR_GATEIO_API_KEY",
        "api_secret": "YOUR_GATEIO_SECRET"
    },
    "kucoin": {
        "api_key": "YOUR_KUCOIN_API_KEY",
        "api_secret": "YOUR_KUCOIN_SECRET",
        "api_passphrase": "YOUR_KUCOIN_PASSPHRASE"
    },
    "coinex": {
        "access_id": "YOUR_COINEX_ACCESS_ID",
        "secret_key": "YOUR_COINEX_SECRET_KEY"
    }
}

# Telegram (незадължително)
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"

# Забележка: Никога не споделяйте този файл публично!
