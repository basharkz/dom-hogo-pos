import streamlit as st
import datetime
import json
from database.connection import execute_query
from database.orders import db_get_active_orders, db_get_order_by_id, db_update_order


def render_kassa_tab():
    kassa_col1, kassa_col2 = st.columns([0.6, 0.4])

    # Получение категорий и меню
    rows_cats = execute_query("SELECT cat_name FROM categories ORDER BY cat_name ASC", fetch="all")
    rows_menu = execute_query("SELECT dish_name, price, category FROM menu", fetch="all")

    DB_MENU_STRUCT = {}
    if rows_menu:
        for row in rows_menu:
            name, price, cat = row[0], row[1], row[2]
            if cat not in DB_MENU_STRUCT: DB_MENU_STRUCT[cat] = {}
            DB_MENU_STRUCT[cat][name] = price

    active_orders = db_get_active_orders()

    with kassa_col1:
        st.subheader("Активные чеки")

        # Создание нового чека
        with st.popover("➕ Открыть Новый Чек"):
            new_order_name = st.text_input("Название (например, Стол 4):")
            if st.button("Создать", key="btn_create_order"):
                if new_order_name:
                    new_id = str(int(datetime.datetime.now().timestamp()))
                    execute_query(
                        "INSERT INTO active_orders (order_id, order_name, cart_json, discount_percent) VALUES (%s, %s, %s, %s)",
                        (new_id, new_order_name, json.dumps({}), 0.0))
                    st.session_state.current_active_order_id = new_id
                    st.rerun()

        # Выбор чека
        if active_orders:
            for order in active_orders:
                if st.button(f"🧾 {order['name']}", key=f"sel_ord_{order['id']}"):
                    st.session_state.current_active_order_id = order['id']
                    st.rerun()

        st.write("---")
        # Меню
        if DB_MENU_STRUCT:
            tabs = st.tabs(list(DB_MENU_STRUCT.keys()))
            for i, (cat, dishes) in enumerate(DB_MENU_STRUCT.items()):
                with tabs[i]:
                    for dish, price in dishes.items():
                        if st.button(f"{dish} ({int(price)} тг)", key=f"add_{dish}_{i}"):
                            if st.session_state.current_active_order_id:
                                order = db_get_order_by_id(st.session_state.current_active_order_id)
                                if order:
                                    order["cart"][dish] = order["cart"].get(dish, 0) + 1
                                    db_update_order(order)
                                    st.rerun()

    with kassa_col2:
        st.subheader("Текущий чек")
        if st.session_state.current_active_order_id:
            order = db_get_order_by_id(st.session_state.current_active_order_id)
            if order:
                st.success(f"Заказ: **{order['name']}**")

                # Подсчет суммы
                flat_prices = {dish: p for cat in DB_MENU_STRUCT.values() for dish, p in cat.items()}
                total = sum(flat_prices.get(d, 0) * q for d, q in order["cart"].items())

                # Список товаров
                for dish, qty in list(order["cart"].items()):
                    col_a, col_b = st.columns([0.8, 0.2])
                    col_a.write(f"{dish} x {qty}")
                    if col_b.button("❌", key=f"del_{dish}_{order['id']}"):
                        order["cart"][dish] -= 1
                        if order["cart"][dish] <= 0: del order["cart"][dish]
                        db_update_order(order)
                        st.rerun()

                st.write("---")
                # Оплата
                disc = st.number_input("Скидка %", min_value=0.0, max_value=100.0, value=float(order["discount"]))
                if disc != order["discount"]:
                    order["discount"] = disc
                    db_update_order(order)
                    st.rerun()

                final_total = total * (1 - disc / 100)
                st.metric("К оплате", f"{int(final_total)} тг")

                pay_method = st.radio("Метод оплаты:", ["Наличные", "Kaspi QR"])

                if st.button("✅ Оплатить и закрыть", type="primary"):
                    today = str(datetime.date.today())
                    for d, q in order["cart"].items():
                        # Продажа
                        execute_query(
                            "INSERT INTO sales (date, dish, qty, total_price, receipt_id, discount_percent, payment_method) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                            (today, d, q, flat_prices.get(d, 0) * q, order["id"], disc, pay_method))
                        # Списание ингредиентов
                        recipe_rows = execute_query("SELECT ingredient, qty_needed FROM recipes WHERE dish = %s", (d,),
                                                    fetch="all")
                        if recipe_rows:
                            for ing, needed in recipe_rows:
                                execute_query(
                                    "INSERT INTO inventory (date, item, qty, price, reason) VALUES (%s, %s, %s, %s, %s)",
                                    (today, ing, -needed * q, 0.0, "Продажа"))

                    execute_query("DELETE FROM active_orders WHERE order_id = %s", (order["id"],))
                    st.session_state.current_active_order_id = None
                    st.rerun()
            else:
                st.session_state.current_active_order_id = None
                st.rerun()
        else:
            st.info("Выберите или создайте заказ слева")