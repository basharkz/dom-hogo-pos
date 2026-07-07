import streamlit as st
import datetime
from database.connection import init_db, execute_query
from gui.kassa import render_kassa_tab
from gui.warehouse import render_warehouse_tab
from gui.history import render_history_tab
from gui.menu_manager import render_menu_manager_tab
from utils.printing import trigger_silent_print, trigger_z_report_print

# ❌ УБИРАЕМ ЭТОТ КОД (вызывает ошибку):
# import sys
# import io
# import os
#
# try:
#     if hasattr(sys.stdout, 'buffer'):
#         sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
#     if hasattr(sys.stderr, 'buffer'):
#         sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
# except Exception as e:
#     print(f"⚠️ Не удалось установить UTF-8 для stdout: {e}")


# 1. НАСТРОЙКА СТРАНИЦЫ (ДОЛЖНА БЫТЬ ПЕРВОЙ)
st.set_page_config(
    layout="wide",
    page_title="POS-Терминал VOXYS",
    initial_sidebar_state="expanded",
)


# 2. ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ
@st.cache_resource
def setup_application():
    init_db()
    return True


setup_application()

# 3. УПРАВЛЕНИЕ СЕССИЕЙ
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "user_role" not in st.session_state: st.session_state.user_role = None
if "current_active_order_id" not in st.session_state: st.session_state.current_active_order_id = None

# --- ОКНО ВХОДА ---
if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align: center;'>🔒 Вход в систему VOXYS</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        username = st.text_input("Логин:")
        password = st.text_input("Пароль:", type="password")
        if st.button("Войти", use_container_width=True):
            if username == "admin" and password == "1111":
                st.session_state.authenticated = True
                st.session_state.user_role = "Администратор"
                st.rerun()
            elif username == "manager" and password == "2222":
                st.session_state.authenticated = True
                st.session_state.user_role = "Менеджер"
                st.rerun()
            elif username == "kassa" and password == "3333":
                st.session_state.authenticated = True
                st.session_state.user_role = "Кассир"
                st.rerun()
            else:
                st.error("❌ Неверный логин или пароль!")
    st.stop()

# --- ОСНОВНОЙ ИНТЕРФЕЙС (Если авторизован) ---

# Боковая панель
with st.sidebar:
    st.title(f"VOXYS | {st.session_state.user_role}")
    st.image("voxys_foto_logo2.png", use_container_width=True)



    st.write("---")
    if st.button("🚪 Выйти из системы"):
        st.session_state.authenticated = False
        st.session_state.user_role = None
        st.rerun()

# Обработка отложенных событий печати
if "just_paid_order_data" in st.session_state and st.session_state.just_paid_order_data:
    p = st.session_state.just_paid_order_data
    trigger_silent_print(p["name"], p["cart"], p["prices"], p["discount"], p["method"], p["id"])
    st.session_state.just_paid_order_data = None

# Определение вкладок
role = st.session_state.user_role
tabs_config = {
    "Кассир": ["🛒 Продажи", "📜 История"],
    "Менеджер": ["🛒 Продажи", "📦 Склад", "📜 История"],
    "Администратор": ["🛒 Продажи", "📦 Склад", "📋 Меню", "📜 История"]
}

# Рендеринг
try:
    if role in tabs_config:
        tabs = st.tabs(tabs_config[role])

        # Индексация вкладок в зависимости от роли
        if role == "Администратор":
            with tabs[0]:
                render_kassa_tab()
            with tabs[1]:
                render_warehouse_tab()
            with tabs[2]:
                render_menu_manager_tab()
            with tabs[3]:
                render_history_tab()
        elif role == "Менеджер":
            with tabs[0]:
                render_kassa_tab()
            with tabs[1]:
                render_warehouse_tab()
            with tabs[2]:
                render_history_tab()
        elif role == "Кассир":
            with tabs[0]:
                render_kassa_tab()
            with tabs[1]:
                render_history_tab()
    else:
        st.error(f"Неизвестная роль: {role}")
except Exception as e:
    st.error(f"Ошибка при отрисовке интерфейса: {e}")
    st.exception(e)