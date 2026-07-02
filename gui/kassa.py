import streamlit as st
import datetime
from database.connection import execute_query
from database.orders import db_get_active_orders, db_get_order_by_id, db_update_order


def render_kassa_tab():
    """Функция отрисовки вкладки Кассира"""

    # 1. Загрузка данных меню
    try:
        categories = execute_query("SELECT cat_name FROM categories ORDER BY cat_name ASC", fetch="all")
        menu_items = execute_query("SELECT dish_name, price, category FROM menu", fetch="all")
    except Exception as e:
        st.error(f"Ошибка загрузки меню: {e}")
        return

    # 2. Разметка колонок: Меню (лево) и Чек (право)
    kassa_col1, kassa_col2 = st.columns([0.6, 0.4])

    with kassa_col1:
        st.subheader("🛒 Выбор блюд")
        # Вывод категорий
        if categories:
            cat_tabs = st.tabs([c[0] for c in categories])
            for i, cat in enumerate(categories):
                with cat_tabs[i]:
                    # Фильтр блюд по категории
                    items = [item for item in menu_items if item[2] == cat[0]]
                    for item in items:
                        if st.button(f"{item[0]} ({item[1]} тг)", key=f"btn_{item[0]}_{i}"):
                            # Логика добавления в активный чек
                            active_order_id = st.session_state.get("current_active_order_id")
                            if active_order_id:
                                # Добавляем в существующий чек (логику db_update_order нужно иметь в orders.py)
                                st.write(f"Добавлено: {item[0]}")
                            else:
                                st.warning("Сначала выберите или создайте чек!")

    with kassa_col2:
        st.subheader("📋 Активный чек")
        current_id = st.session_state.get("current_active_order_id")

        if current_id:
            order = db_get_order_by_id(current_id)
            if order:
                st.write(f"Чек №: {order['id']}")
                # Отображение товаров в чеке
                for dish, qty in order.get("cart", {}).items():
                    st.write(f"{dish} — {qty} шт.")

                # Логика оплаты
                if st.button("✅ Оплатить"):
                    try:
                        today = str(datetime.date.today())
                        # Запись продаж
                        for d, q in order["cart"].items():
                            execute_query(
                                """INSERT INTO sales 
                                (date, dish, qty, total_price, receipt_id, discount_percent, payment_method) 
                                VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                                (today, d, q, 100, str(order["id"]), 0, "Наличные")
                            )

                        # Удаление активного заказа после оплаты
                        execute_query("DELETE FROM active_orders WHERE order_id = %s", (order["id"],))
                        st.session_state.current_active_order_id = None
                        st.success("Оплата принята!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка оплаты: {e}")
        else:
            st.info("Выберите или создайте новый чек")

    # 3. Список активных чеков (можно добавить ниже)
    st.divider()
    st.subheader("📝 Активные заказы")
    active_orders = db_get_active_orders()
    if active_orders:
        for ord_data in active_orders:
            if st.button(f"Чек {ord_data['order_id']} — {ord_data['table_name']}", key=f"ord_{ord_data['order_id']}"):
                st.session_state.current_active_order_id = ord_data['order_id']
                st.rerun()