import streamlit as st
import datetime
import json
import streamlit.components.v1 as components
from database.connection import execute_query
from database.orders import db_get_active_orders, db_get_order_by_id, db_update_order


def render_kassa_tab():
    # --- БЛОК АВТОМАТИЧЕСКОЙ ПЕЧАТИ ЧЕКА ---
    # Этот блок ловит сохраненный чек после перезагрузки страницы и выводит его на принтер
    if "receipt_html" in st.session_state and st.session_state.receipt_html:
        components.html(st.session_state.receipt_html, height=0, width=0)
        del st.session_state["receipt_html"]  # Удаляем, чтобы чек не распечатался дважды

    kassa_col1, kassa_col2 = st.columns([0.6, 0.4])

    # Загрузка меню из базы
    rows_menu = execute_query("SELECT dish_name, price, category FROM menu", fetch="all")
    DB_MENU_STRUCT = {}
    if rows_menu:
        for row in rows_menu:
            name, price, cat = row[0], row[1], row[2]
            if cat not in DB_MENU_STRUCT:
                DB_MENU_STRUCT[cat] = {}
            DB_MENU_STRUCT[cat][name] = price

    # Получаем активные заказы
    active_orders = db_get_active_orders()

    with kassa_col1:
        st.subheader("Активные чеки")

        if st.button("➕ Открыть Новый Чек", type="primary", use_container_width=True):
            today_str = datetime.date.today().strftime("%y%m%d")
            new_order_num = len(active_orders) + 1

            new_id = int(f"{today_str}{new_order_num:02d}")

            execute_query(
                "INSERT INTO active_orders (order_id, order_name, cart_json, discount_percent) VALUES (%s, %s, %s, %s)",
                (new_id, f"Чек №{new_order_num}", json.dumps([]), 0.0)
            )
            st.session_state.current_active_order_id = new_id
            st.rerun()

        st.write("---")

        if active_orders:
            cols = st.columns(3)
            for idx, order in enumerate(active_orders):
                with cols[idx % 3]:
                    if st.button(f"🧾 {order['name']}", key=f"sel_ord_{order['id']}", use_container_width=True):
                        st.session_state.current_active_order_id = order['id']
                        st.rerun()

        st.write("---")

        if DB_MENU_STRUCT:
            tabs = st.tabs(list(DB_MENU_STRUCT.keys()))
            for i, (cat, dishes) in enumerate(DB_MENU_STRUCT.items()):
                with tabs[i]:
                    for dish, price in dishes.items():
                        if st.button(f"{dish} ({int(price)} тг)", key=f"add_{dish}_{i}"):
                            if st.session_state.current_active_order_id:
                                order = db_get_order_by_id(st.session_state.current_active_order_id)
                                if order:
                                    found = False
                                    for item in order["cart"]:
                                        if item["name"] == dish:
                                            item["qty"] += 1
                                            found = True
                                            break
                                    if not found:
                                        order["cart"].append({"name": dish, "price": price, "qty": 1})
                                    db_update_order(order)
                                    st.rerun()

    with kassa_col2:
        st.subheader("Текущий чек")
        if st.session_state.current_active_order_id:
            order = db_get_order_by_id(st.session_state.current_active_order_id)
            if order:
                st.success(f"Выбран: **{order['name']}**")

                total = sum(item["price"] * item["qty"] for item in order["cart"])

                for item in list(order["cart"]):
                    col_a, col_b, col_c = st.columns([0.5, 0.3, 0.2])
                    col_a.write(f"**{item['name']}**")
                    col_b.write(f"{int(item['price'])} тг x {item['qty']}")
                    if col_c.button("❌", key=f"del_{item['name']}_{order['id']}"):
                        item["qty"] -= 1
                        if item["qty"] <= 0:
                            order["cart"].remove(item)
                        db_update_order(order)
                        st.rerun()

                st.write("---")

                disc = st.number_input("Скидка %", min_value=0.0, max_value=100.0, step=5.0,
                                       value=float(order["discount"]))
                if disc != order["discount"]:
                    order["discount"] = disc
                    db_update_order(order)
                    st.rerun()

                final_total = total * (1 - disc / 100)
                st.metric("К оплате", f"{int(final_total)} тг")
                pay_method = st.radio("Метод оплаты:", ["Наличные", "Kaspi QR"])

                if st.button("✅ Оплатить и закрыть", type="primary", use_container_width=True):
                    today = str(datetime.date.today())

                    # --- ГЕНЕРАЦИЯ КРАСИВОГО ЧЕКА ДЛЯ ПЕЧАТИ ---
                    items_html = ""
                    for item in order["cart"]:
                        items_html += f"<div class='line'><span>{item['name']} x{item['qty']}</span><span>{int(item['price'] * item['qty'])} тг</span></div>"

                    now_str = datetime.datetime.now().strftime('%d.%m.%Y %H:%M')

                    receipt_script = f"""
                    <script>
                        var receiptContent = `
                        <html><head><style>
                            body {{ font-family: monospace; width: 300px; color: black; margin: 0 auto; padding: 10px; }}
                            .header {{ text-align: center; margin-bottom: 10px; }}
                            .line {{ display: flex; justify-content: space-between; margin-bottom: 4px; }}
                            .divider {{ border-top: 1px dashed black; margin: 8px 0; }}
                            .total {{ display: flex; justify-content: space-between; font-size: 16px; font-weight: bold; }}
                        </style></head><body>
                            <div class="header">
                                <h2>ДОМ ХОГО</h2>
                                <div>{order['name']}</div>
                                <div>{now_str}</div>
                            </div>
                            <div class="divider"></div>
                            {items_html}
                            <div class="divider"></div>
                            <div class="line"><span>Скидка:</span><span>{disc}%</span></div>
                            <div class="line"><span>Оплата:</span><span>{pay_method}</span></div>
                            <div class="divider"></div>
                            <div class="total"><span>ИТОГО:</span><span>{int(final_total)} тг</span></div>
                            <div class="header" style="margin-top: 20px;">Спасибо за визит!</div>
                        </body></html>
                        `;

                        var iframe = document.createElement('iframe');
                        iframe.style.display = 'none';
                        document.body.appendChild(iframe);
                        iframe.contentDocument.open();
                        iframe.contentDocument.write(receiptContent);
                        iframe.contentDocument.close();

                        // Небольшая задержка, чтобы браузер успел отрисовать HTML перед печатью
                        setTimeout(function() {{
                            iframe.contentWindow.focus();
                            iframe.contentWindow.print();
                        }}, 500);
                    </script>
                    """
                    # Сохраняем скрипт чека в память сессии
                    st.session_state.receipt_html = receipt_script

                    # Сохранение продаж и списание ингредиентов в базу
                    for item in order["cart"]:
                        execute_query(
                            "INSERT INTO sales (date, dish, qty, total_price, receipt_id, discount_percent, payment_method) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                            (today, item["name"], item["qty"], item["price"] * item["qty"], order["id"], disc,
                             pay_method)
                        )

                        recipe_rows = execute_query(
                            "SELECT ingredient, qty_needed FROM recipes WHERE dish = %s",
                            (item["name"],), fetch="all"
                        )

                        if recipe_rows:
                            for ing, needed in recipe_rows:
                                execute_query(
                                    "INSERT INTO inventory (date, item, qty, price, reason) VALUES (%s, %s, %s, %s, %s)",
                                    (today, ing, -needed * item["qty"], 0.0, "Продажа")
                                )

                    # Закрываем чек
                    execute_query("DELETE FROM active_orders WHERE order_id = %s", (order["id"],))
                    st.session_state.current_active_order_id = None
                    st.rerun()
            else:
                st.session_state.current_active_order_id = None
                st.rerun()
        else:
            st.info("Выберите или создайте заказ слева")