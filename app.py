import streamlit as st
from database.connection import init_db
from gui.kassa import render_kassa_tab
from gui.warehouse import render_warehouse_tab
from gui.history import render_history_tab
from gui.menu_manager import render_menu_manager_tab
from utils.printing import trigger_silent_print, trigger_z_report_print

# 1. Настройка страницы (Твой логотип как иконка)
st.set_page_config(
    layout="wide",
    page_title="POS-Терминал VOXYS",
    page_icon="logo.png"
)

# Инициализируем базу данных
init_db()

# 2. Инициализация переменных сессии для авторизации
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_role" not in st.session_state:
    st.session_state.user_role = None

# --- ОКНО ВХОДА (ОТОБРАЖАЕТСЯ, ЕСЛИ ПОЛЬЗОВАТЕЛЬ НЕ АВТОРИЗОВАН) ---
if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align: center;'>🔒 Вход в систему VOXYS</h1>", unsafe_allow_html=True)

    # Центрируем форму авторизации с помощью колонок
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.image("voxys_foto_logo2.png", use_container_width=True)

        # Поля для ввода данных
        username = st.text_input("Логин (Имя пользователя):")
        password = st.text_input("Пароль:", type="password")

        if st.button("Войти", use_container_width=True):
            # Проверяем учетные данные сотрудников
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

    st.stop()  # Полностью останавливаем выполнение кода ниже, пока человек не зайдет

# --- КОД НИЖЕ ВЫПОЛНЯЕТСЯ ТОЛЬКО ПОСЛЕ УСПЕШНОГО ВХОДА ---

# Кнопка "Выйти" в самом верху боковой панели
if st.sidebar.button("🚪 Выйти из системы"):
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.rerun()

st.sidebar.image("voxys_foto_logo3.png", use_container_width=True)
st.sidebar.title(f"VOXYS | {st.session_state.user_role}")
st.sidebar.write(f"Вы вошли как: **{st.session_state.user_role}**")

# Скрытая логика печати (оставляем без изменений)
if "current_active_order_id" not in st.session_state: st.session_state.current_active_order_id = None
if "just_paid_order_data" not in st.session_state: st.session_state.just_paid_order_data = None
if "z_print_trigger" not in st.session_state: st.session_state.z_print_trigger = None

if st.session_state.just_paid_order_data:
    p = st.session_state.just_paid_order_data
    trigger_silent_print(p["name"], p["cart"], p["prices"], p["discount"], p["method"], p["id"])
    st.session_state.just_paid_order_data = None

if st.session_state.z_print_trigger:
    trigger_z_report_print(st.session_state.z_print_trigger)
    st.session_state.z_print_trigger = None

# --- ОТРЕНДЕРИТЬ ВКЛАДКИ В ЗАВИСИМОСТИ ОТ РОЛИ ---
if st.session_state.user_role == "Кассир":
    tab_kassa, tab_history = st.tabs(["🛒 Продажи (Касса)", "📜 История и Аналитика"])
    with tab_kassa:
        render_kassa_tab()
    with tab_history:
        render_history_tab()

elif st.session_state.user_role == "Менеджер":
    tab_kassa, tab_warehouse, tab_history = st.tabs([
        "🛒 Продажи (Касса)", "📦 Склад (Учет)", "📊 История и Аналитика"
    ])
    with tab_kassa:
        render_kassa_tab()
    with tab_warehouse:
        render_warehouse_tab()
    with tab_history:
        render_history_tab()

elif st.session_state.user_role == "Администратор":
    tab_kassa, tab_warehouse, tab_menu, tab_history = st.tabs([
        "🛒 Продажи (Касса)", "📦 Склад (Учет)", "📋 Управление меню", "📊 История и Аналитика"
    ])
    with tab_kassa:
        render_kassa_tab()
    with tab_warehouse:
        render_warehouse_tab()
    with tab_menu:
        render_menu_manager_tab()
    with tab_history:
        render_history_tab()