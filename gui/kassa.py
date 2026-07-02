import streamlit as st
import datetime
import json
from database.connection import execute_query
from database.orders import db_get_active_orders, db_get_order_by_id, db_update_order


def render_kassa_tab():
    """Функция отрисовки вкладки Кассира"""

    st.title("🛒 Касса")

    # 1. Загрузка данных меню и категорий
    try:
        categories = execute_query("SELECT cat_name FROM categories ORDER BY cat_name ASC", fetch="all")
        menu_items = execute_query("SELECT dish_name, price, category FROM menu", fetch="all")
    except Exception as e:
        st.error(f"Ошибка загрузки меню: {e}")
        return

    # 2. Разметка колонок: Меню (лево) и Чек (право)
    kassa_col1, kassa_col2 = st.columns([0.6, 0.4])

    with kassa_col1:
        st.subheader("Меню")
        if categories:
            cat_tabs = st.tabs([c[0] for c in categories])
            for i, cat in enumerate(categories):
                with cat_tabs[i]:
                    items = [item for item in menu_items if item[2] == cat[0]]
                    for item in items:
                        # Кнопка добавления блюда
                        if st.button(f"{item[0]} — {item[1]} тг", key=f"btn_{item[0]}_{i}"):
                            current_id = st.session_state.get("current_active_order_id")
                            if current_id:
                                # Получаем текущий заказ, обновляем корзину
                                order = db_get_order_by_id(current_id)
                                cart = order.get("cart", {})
                                if isinstance(cart, str): cart = json.loads(cart)  # Если вдруг в базе json строкой

                                # Добавляем блюдо или увеличиваем кол-во
                                cart[item[0]] = cart.get(item[0], 0) + 1

                                # Сохраняем обратно через db_update_order
                                db_update_order(current_id, {"cart": cart})
                                st.rerun()
                            else:
                                st.warning("⚠️ Сначала создайте или выберите чек!")

    with kassa_col2:
        st.subheader("📋 Активный чек")

        # Кнопка "Новый заказ" (создает запись в active_orders)
        if st.button("➕ Создать новый заказ"):
            # Создаем пустой заказ в БД
            execute_query("INSERT INTO active_orders (table_name, cart) VALUES (%s, %s)", ("Стол 1", json.dumps({})))
            # Получаем ID последнего созданного заказа
            new_id = execute_query("SELECT MAX(order_id) FROM active_orders", fetch="one")[0]
            st.session_state.current_active_order_id = new_id
            st.rerun()

        current_id = st.session_state.get("current_active_order_id")

        if current_id:
            order = db_get_order_by_id(current_id)
            if order:
                st.write(f"**Чек №: {order['id']}**")

                # Отображение товаров в чеке
                cart = order.get("cart", {})
                if isinstance(cart, str): cart = json.loads(cart)

                total_sum = 0
                for dish, qty in cart.items():
                    # Нужно подтянуть цену из меню для расчета суммы
                    price_row = execute_query("SELECT price FROM menu WHERE dish_name = %s", (dish,), fetch="one")
                    price = price_row[0] if price_row else 0
                    st.write(f"{dish} x {qty} = {price * qty} тг")
                    total_sum += (price * qty)

                st.divider()
                st.write(f"### Итого: {total_sum} тг")

                # Логика оплаты
                if st.button("✅ Оплатить"):
                    try:
                        today = str(datetime.date.today())
                        # Запись каждой позиции в sales
                        for d, q in cart.items():
                            execute_query(
                                """INSERT INTO sales 
                                (date, dish, qty, total_price, receipt_id, discount_percent, payment_method) 
                                VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                                (today, d, q, total_sum, str(order["id"]), 0, "Наличные")
                            )

                        # Удаление заказа
                        execute_query("DELETE FROM active_orders WHERE order_id = %s", (order["id"],))
                        st.session_state.current_active_order_id = None
                        st.success("Оплата принята!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка оплаты: {e}")
            else:
                st.session_state.current_active_order_id = None
                st.rerun()
        else:
            st.info("Выберите чек из списка ниже или создайте новый")

    # 3. Список активных чеков
    st.divider()
    st.subheader("📝 Активные заказы")
    active_orders = db_get_active_orders()
    if active_orders:
        for ord_data in active_orders:
            if st.button(f"Заказ {ord_data['order_id']} | {ord_data['table_name']}", key=f"ord_{ord_data['order_id']}"):
                st.session_state.current_active_order_id = ord_data['order_id']
                st.rerun()
    else:
        st.write("Нет открытых заказов.")