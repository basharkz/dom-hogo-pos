import streamlit as st
from database.connection import init_db
from gui.kassa import render_kassa_tab
from gui.warehouse import render_warehouse_tab
from gui.history import render_history_tab
from gui.menu_manager import render_menu_manager_tab
from utils.printing import trigger_silent_print, trigger_z_report_print

# 1. Настройка страницы
st.set_page_config(
    layout="wide",
    page_title="POS-Терминал VOXYS",
    page_icon="logo.png"
)

# Оптимизация: используем кеширование для инициализации базы данных
@st.cache_resource
def setup_application():
    init_db()
    return True

setup_application()

# 2. Инициализация переменных сессии
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "current_active_order_id" not in st.session_state:
    st.session_state.current_active_order_id = None

# --- ОКНО ВХОДА ---
if not st.session_state.authenticated:
    st.components.v1.html("<h1 style='text-align: center;'>🔒 Вход в систему VOXYS</h1>")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("voxys_foto_logo2.png", use_container_width=True)
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

# --- ОСНОВНОЙ ИНТЕРФЕЙС ---
if st.sidebar.button("🚪 Выйти из системы"):
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.rerun()

st.sidebar.image("voxys_foto_logo3.png", use_container_width=True)
st.sidebar.title(f"VOXYS | {st.session_state.user_role}")

# Обработка событий печати
if "just_paid_order_data" in st.session_state and st.session_state.just_paid_order_data:
    p = st.session_state.just_paid_order_data
    trigger_silent_print(p["name"], p["cart"], p["prices"], p["discount"], p["method"], p["id"])
    st.session_state.just_paid_order_data = None

if "z_print_trigger" in st.session_state and st.session_state.z_print_trigger:
    trigger_z_report_print(st.session_state.z_print_trigger)
    st.session_state.z_print_trigger = None

# Отрисовка вкладок
role = st.session_state.user_role
tabs_config = {
    "Кассир": ["🛒 Продажи", "📜 История"],
    "Менеджер": ["🛒 Продажи", "📦 Склад", "📜 История"],
    "Администратор": ["🛒 Продажи", "📦 Склад", "📋 Меню", "📜 История"]
}

tabs = st.tabs(tabs_config.get(role, []))

# Функция-обертка для отрисовки в зависимости от роли и индекса вкладки
if role == "Кассир":
    with tabs[0]: render_kassa_tab()
    with tabs[1]: render_history_tab()
elif role == "Менеджер":
    with tabs[0]: render_kassa_tab()
    with tabs[1]: render_warehouse_tab()
    with tabs[2]: render_history_tab()
elif role == "Администратор":
    with tabs[0]: render_kassa_tab()
    with tabs[1]: render_warehouse_tab()
    with tabs[2]: render_menu_manager_tab()
    with tabs[3]: render_history_tab()