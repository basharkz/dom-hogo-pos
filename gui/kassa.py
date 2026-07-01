import streamlit as st
import datetime
import json
from database.connection import execute_query
from database.orders import db_get_active_orders, db_get_order_by_id, db_update_order


def render_kassa_tab():
    current_id = st.session_state.get("current_active_order_id")
    kassa_col1, kassa_col2 = st.columns([0.6, 0.4])

    # ... (логика загрузки меню из базы)

    with kassa_col1:
        st.subheader("Активные чеки")
        # ... (логика создания и выбора чеков)

    with kassa_col2:
        st.subheader("Текущий чек")
        if current_id:
            order = db_get_order_by_id(current_id)
            if order:
                # ... (логика отображения товаров и оплаты)
                if st.button("✅ Оплатить"):
                    # Запись в sales без указания ID (он автоинкрементный)
                    today = str(datetime.date.today())
                    for d, q in order["cart"].items():
                        execute_query(
                            "INSERT INTO sales (date, dish, qty, total_price, receipt_id, discount_percent, payment_method) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                            (today, d, q, 100, order["id"], 0, "Наличные"))
                    execute_query("DELETE FROM active_orders WHERE order_id = %s", (order["id"],))
                    st.session_state.current_active_order_id = None
                    st.rerun()