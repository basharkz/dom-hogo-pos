import streamlit as st
import datetime
import json
from database.connection import execute_query
from database.orders import db_get_active_orders, db_get_order_by_id, db_update_order


def render_kassa_tab():
    st.title("🛒 Касса")

    # 1. Загрузка данных
    try:
        categories = execute_query("SELECT cat_name FROM categories ORDER BY cat_name ASC", fetch="all")
        menu_items = execute_query("SELECT dish_name, price, category FROM menu", fetch="all")
    except Exception as e:
        st.error(f"Ошибка БД: {e}")
        return

    col1, col2 = st.columns([0.6, 0.4])

    with col1:
        st.subheader("Меню")
        if categories:
            tabs = st.tabs([c[0] for c in categories])
            for i, cat in enumerate(categories):
                with tabs[i]:
                    items = [item for item in menu_items if item[2] == cat[0]]
                    for item in items:
                        if st.button(f"{item[0]} ({item[1]} тг)", key=f"add_{item[0]}_{i}"):
                            cur_id = st.session_state.get("current_active_order_id")
                            if cur_id:
                                order = db_get_order_by_id(cur_id)
                                # Используем cart_json вместо cart
                                cart = order.get("cart_json", {})
                                if isinstance(cart, str): cart = json.loads(cart)
                                cart[item[0]] = cart.get(item[0], 0) + 1
                                db_update_order(cur_id, {"cart_json": cart})
                                st.rerun()
                            else:
                                st.warning("Выберите чек!")

    with col2:
        st.subheader("📋 Активный чек")

        # Кнопка создания заказа
        if st.button("➕ Создать новый заказ"):
            try:
                # Вставка с использованием order_name и cart_json
                sql = "INSERT INTO active_orders (order_name, cart_json) VALUES (%s, %s) RETURNING order_id"
                result = execute_query(sql, ("Стол 1", json.dumps({})), fetch="one")
                if result:
                    st.session_state.current_active_order_id = result[0]
                    st.rerun()
            except Exception as e:
                st.error(f"Ошибка создания: {e}")

        # Отображение чека
        cur_id = st.session_state.get("current_active_order_id")
        if cur_id:
            order = db_get_order_by_id(cur_id)
            if order:
                st.write(f"**Чек №: {order['id']}**")
                # Используем cart_json
                cart = order.get("cart_json", {})
                if isinstance(cart, str): cart = json.loads(cart)

                total = 0
                for dish, qty in cart.items():
                    price_row = execute_query("SELECT price FROM menu WHERE dish_name = %s", (dish,), fetch="one")
                    price = price_row[0] if price_row else 0
                    st.write(f"{dish} x {qty} = {price * qty} тг")
                    total += (price * qty)

                st.write(f"### Итого: {total} тг")

                if st.button("✅ Оплатить"):
                    st.success("Оплачено!")
                    execute_query("DELETE FROM active_orders WHERE order_id = %s", (cur_id,))
                    st.session_state.current_active_order_id = None
                    st.rerun()
            else:
                st.session_state.current_active_order_id = None
                st.rerun()

    # Активные заказы
    st.divider()
    st.subheader("📝 Активные заказы")
    active_orders = db_get_active_orders()
    if active_orders:
        for ord_data in active_orders:
            o_id = ord_data['order_id']
            # Используем order_name
            if st.button(f"Заказ {o_id} | {ord_data.get('order_name', 'Стол')}", key=f"load_{o_id}"):
                st.session_state.current_active_order_id = o_id
                st.rerun()
    else:
        st.write("Нет открытых заказов.")