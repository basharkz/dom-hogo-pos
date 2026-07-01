import streamlit as st
from database.connection import init_db
# Импортируем все необходимые модули
from gui.kassa import render_kassa_tab
from gui.warehouse import render_warehouse_tab
from gui.history import render_history_tab
from gui.menu_manager import render_menu_manager_tab
from utils.printing import trigger_silent_print, trigger_z_report_print

# Настройка страницы
st.set_page_config(layout="wide", page_title="POS-Терминал VOXYS")

# Инициализация БД
init_db()

# Инициализация сессии
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "user_role" not in st.session_state: st.session_state.user_role = None
if "current_active_order_id" not in st.session_state: st.session_state.current_active_order_id = None

# Окно входа
if not st.session_state.authenticated:
    # Заменяем st.markdown с unsafe_html на обычный st.title
    st.title("🔒 Вход в систему VOXYS")

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
        else:
            st.error("Неверный логин или пароль")
    st.stop()

# Интерфейс
if st.sidebar.button("🚪 Выйти"):
    st.session_state.authenticated = False
    st.rerun()

st.sidebar.title(f"VOXYS | {st.session_state.user_role}")

# Выбор вкладок
tabs_config = {
    "Кассир": ["🛒 Продажи", "📜 История"],
    "Менеджер": ["🛒 Продажи", "📦 Склад", "📜 История"],
    "Администратор": ["🛒 Продажи", "📦 Склад", "📋 Меню", "📜 История"]
}
tabs = st.tabs(tabs_config.get(st.session_state.user_role, []))

# Отрисовка
role = st.session_state.user_role
if role == "Администратор":
    with tabs[0]: render_kassa_tab()
    with tabs[1]: render_warehouse_tab()
    with tabs[2]: render_menu_manager_tab()
    with tabs[3]: render_history_tab()
elif role == "Менеджер":
    with tabs[0]: render_kassa_tab()
    with tabs[1]: render_warehouse_tab()
    with tabs[2]: render_history_tab()
elif role == "Кассир":
    with tabs[0]: render_kassa_tab()
    with tabs[1]: render_history_tab()