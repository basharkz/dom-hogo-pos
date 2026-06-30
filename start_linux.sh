#!/bin/bash
cd "$(dirname "$0")"
# Активируем виртуальное окружение
source .venv/bin/activate
# Запускаем систему
streamlit run app.py