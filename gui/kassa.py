import streamlit as st
import datetime
import json
import streamlit.components.v1 as components
from database.connection import execute_query
from database.orders import db_get_active_orders, db_get_order_by_id, db_update_order


def render_kassa_tab():
    # Если в сессии есть готовый к печати чек — исполняем скрипт сразу при обновлении страницы
    if "auto_print_script" in st.session_state:
        components.html(st.session_state.auto_print_script, height=0, width=0)
        del st.session_state["auto_print_script"]

    kassa_col1, kassa_col2 = st.columns([0.6, 0.4])

    # Загрузка меню
    rows_menu = execute_query("SELECT dish_name, price, category FROM menu", fetch="all")
    DB_MENU_STRUCT = {}
    if rows_menu:
        for row in rows_menu:
            name, price, cat = row[0], row[1], row[2]
            if cat not in DB_MENU_STRUCT: DB_MENU_STRUCT[cat] = {}
            DB_MENU_STRUCT[cat][name] = price

    with kassa_col1:
        st.subheader("Активные чеки")
        if st.button("➕ Новый Чек", type="primary", use_container_width=True):
            today_str = datetime.date.today().strftime("%y%m%d")
            new_id = int(f"{today_str}{len(db_get_active_orders()) + 1:02d}")
            execute_query(
                "INSERT INTO active_orders (order_id, order_name, cart_json, discount_percent) VALUES (%s, %s, %s, %s)",
                (new_id, f"Чек №{len(db_get_active_orders()) + 1}", json.dumps([]), 0.0))
            st.session_state.current_active_order_id = new_id
            st.rerun()

        # ... (здесь отрисовка списка чеков и меню, как была) ...
        active_orders = db_get_active_orders()
        for order in active_orders:
            if st.button(f"🧾 {order['name']}", key=f"sel_{order['id']}"):
                st.session_state.current_active_order_id = order['id']
                st.rerun()

    with kassa_col2:
        st.subheader("Текущий чек")
        if st.session_state.current_active_order_id:
            order = db_get_order_by_id(st.session_state.current_active_order_id)
            if order:
                total = sum(item["price"] * item["qty"] for item in order["cart"])
                # ... (здесь вывод состава заказа) ...

                final_total = total * (1 - float(order["discount"]) / 100)

                if st.button("✅ Оплатить"):
                    # 1. Сохраняем в продажи
                    today = str(datetime.date.today())
                    for item in order["cart"]:
                        execute_query(
                            "INSERT INTO sales (date, dish, qty, total_price, receipt_id, discount_percent, payment_method) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                            (today, item["name"], item["qty"], item["price"] * item["qty"], order["id"],
                             order["discount"], "Оплата"))

                    # 2. Формируем HTML для печати
                    items_html = "".join(
                        [f"<div>{i['name']} x{i['qty']} - {int(i['price'] * i['qty'])} тг</div>" for i in
                         order["cart"]])
                    st.session_state.auto_print_script = f"""
                    <script>
                        var w = window.open();
                        w.document.write('<html><body><h2>ДОМ ХОГО</h2>{items_html}<hr><h3>ИТОГО: {int(final_total)} тг</h3></body></html>');
                        w.print();
                        w.close();
                    </script>
                    """

                    # 3. Удаляем заказ и обновляем страницу
                    execute_query("DELETE FROM active_orders WHERE order_id = %s", (order["id"],))
                    st.session_state.current_active_order_id = None
                    st.rerun()