#!/bin/bash
# deploy.sh — стартирай в UserLAnd (Ubuntu) или Termux

echo "🚀 Стартиране на инсталация за crypto-spot-bot..."

# Актуализация
apt update && apt upgrade -y

# Инсталиране на Python и Git
apt install python3 python3-pip git -y

# Клониране (ако нямаш репото)
if [ ! -d "crypto-spot-bot" ]; then
    git clone https://github.com/yourname/crypto-spot-bot.git
fi

cd crypto-spot-bot

# Инсталиране на зависимости
pip3 install requests pandas numpy ta

# Проверка за конфигурация
if [ ! -f "config.py" ]; then
    echo "❌ Липсва config.py! Попълнете го с вашите API ключове."
    exit 1
fi

echo "✅ Инсталацията завърши. Стартиране на бота..."
python3 main.py
