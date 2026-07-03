import streamlit as st
import datetime
import json
import streamlit.components.v1 as components
from database.connection import execute_query
from database.orders import db_get_active_orders, db_get_order_by_id, db_update_order


def render_kassa_tab():
    # --- Кнопка печати последнего чека ---
    if "last_receipt_html" in st.session_state:
        if st.button("🖨 Печать последнего чека", type="secondary"):
            components.html(st.session_state.last_receipt_html, height=0, width=0)

    kassa_col1, kassa_col2 = st.columns([0.6, 0.4])

    # Загрузка меню
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
        if st.button("➕ Открыть Новый Чек", type="primary", use_container_width=True):
            today_str = datetime.date.today().strftime("%y%m%d")
            new_order_num = len(active_orders) + 1
            new_id = int(f"{today_str}{new_order_num:02d}")
            execute_query(
                "INSERT INTO active_orders (order_id, order_name, cart_json, discount_percent) VALUES (%s, %s, %s, %s)",
                (new_id, f"Чек №{new_order_num}", json.dumps([]), 0.0))
            st.session_state.current_active_order_id = new_id
            st.rerun()

        st.write("---")
        if active_orders:
            for order in active_orders:
                if st.button(f"🧾 {order['name']}", key=f"sel_{order['id']}", use_container_width=True):
                    st.session_state.current_active_order_id = order['id']
                    st.rerun()

        st.write("---")
        if DB_MENU_STRUCT:
            tabs = st.tabs(list(DB_MENU_STRUCT.keys()))
            for i, (cat, dishes) in enumerate(DB_MENU_STRUCT.items()):
                with tabs[i]:
                    for dish, price in dishes.items():
                        if st.button(f"{dish} ({int(price)} тг)", key=f"add_{dish}_{i}"):
                            order = db_get_order_by_id(st.session_state.current_active_order_id)
                            if order:
                                found = False
                                for item in order["cart"]:
                                    if item["name"] == dish:
                                        item["qty"] += 1
                                        found = True
                                        break
                                if not found: order["cart"].append({"name": dish, "price": price, "qty": 1})
                                db_update_order(order)
                                st.rerun()

    with kassa_col2:
        st.subheader("Текущий чек")
        if st.session_state.current_active_order_id:
            order = db_get_order_by_id(st.session_state.current_active_order_id)
            if order:
                total = sum(item["price"] * item["qty"] for item in order["cart"])
                for item in list(order["cart"]):
                    col_a, col_b, col_c = st.columns([0.5, 0.3, 0.2])
                    col_a.write(f"**{item['name']}**")
                    col_b.write(f"{int(item['price'])} тг x {item['qty']}")
                    if col_c.button("❌", key=f"del_{item['name']}"):
                        item["qty"] -= 1
                        if item["qty"] <= 0: order["cart"].remove(item)
                        db_update_order(order)
                        st.rerun()

                disc = st.number_input("Скидка %", min_value=0.0, max_value=100.0, value=float(order["discount"]))
                final_total = total * (1 - disc / 100)
                st.metric("К оплате", f"{int(final_total)} тг")
                pay_method = st.radio("Метод:", ["Наличные", "Kaspi QR"])

                if st.button("✅ Оплатить"):
                    # Логика сохранения в базу (sales + inventory)
                    today = str(datetime.date.today())
                    for item in order["cart"]:
                        execute_query(
                            "INSERT INTO sales (date, dish, qty, total_price, receipt_id, discount_percent, payment_method) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                            (today, item["name"], item["qty"], item["price"] * item["qty"], order["id"], disc,
                             pay_method))

                    # ГЕНЕРАЦИЯ ЧЕКА
                    items_html = "".join(
                        [f"<li>{item['name']} x{item['qty']} - {int(item['price'] * item['qty'])} тг</li>" for item in
                         order["cart"]])
                    st.session_state.last_receipt_html = f"""
                    <script>
                        var w = window.open();
                        w.document.write('<html><body><h3>ДОМ ХОГО</h3><ul>{items_html}</ul><hr><b>ИТОГО: {int(final_total)} тг</b></body></html>');
                        w.print();
                    </script>
                    """
                    execute_query("DELETE FROM active_orders WHERE order_id = %s", (order["id"],))
                    st.session_state.current_active_order_id = None
                    st.rerun()