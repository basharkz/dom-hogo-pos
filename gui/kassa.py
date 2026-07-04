import streamlit as st
import datetime
import json
import streamlit.components.v1 as components
from database.connection import execute_query
from database.orders import db_get_active_orders, db_get_order_by_id, db_update_order


def render_kassa_tab():
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

        if st.button("Открыть Новый Чек", type="primary", use_container_width=True):
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

                    # ✅ ОПРЕДЕЛЯЕМ ВСЕ ПЕРЕМЕННЫЕ
                    discount_percent = disc
                    payment_method = pay_method
                    final_total_after_discount = final_total * (1 - discount_percent / 100)
                    receipt_id = order["id"]  # ✅ Используем ID заказа как номер чека

                    # Формируем HTML для чека
                    items_html = ""
                    for item in order["cart"]:
                        items_html += f"""
                            <tr>
                                <td class="item-name">{item['name']}</td>
                                <td class="item-qty">x{item['qty']}</td>
                                <td class="item-price">{int(item['price'] * item['qty'])}</td>
                            </tr>
                        """

                    # Строка со скидкой
                    discount_html = ""
                    if discount_percent > 0:
                        discount_amount = final_total * (discount_percent / 100)
                        discount_html = f"""
                            <tr class="discount-row">
                                <td colspan="2">Скидка ({discount_percent}%):</td>
                                <td class="item-price">-{int(discount_amount)} тг</td>
                            </tr>
                        """

                    receipt_content = f"""
                    <html>
                        <head>
                            <style>
                                body {{ 
                                    width: 280px; 
                                    font-family: 'Courier New', monospace; 
                                    margin: 0; 
                                    padding: 10px;
                                    background: white;
                                }}
                                h2 {{ 
                                    text-align: center; 
                                    margin: 5px 0; 
                                    font-size: 18px;
                                }}
                                .header {{
                                    text-align: center;
                                    font-size: 12px;
                                    margin: 5px 0;
                                }}
                                .divider {{
                                    border: 0;
                                    border-top: 1px dashed #000;
                                    margin: 8px 0;
                                }}
                                .divider-double {{
                                    border: 0;
                                    border-top: 2px solid #000;
                                    margin: 8px 0;
                                }}
                                table {{ 
                                    width: 100%; 
                                    border-collapse: collapse;
                                    font-size: 13px;
                                }}
                                td {{ 
                                    padding: 3px 0;
                                    vertical-align: top;
                                }}
                                .item-name {{
                                    width: 60%;
                                    padding-right: 10px;
                                }}
                                .item-qty {{
                                    width: 15%;
                                    text-align: center;
                                }}
                                .item-price {{
                                    width: 25%;
                                    text-align: right;
                                }}
                                .total-row {{
                                    font-weight: bold;
                                    font-size: 16px;
                                }}
                                .discount-row {{
                                    font-size: 13px;
                                    color: #666;
                                }}
                                .footer {{
                                    text-align: center;
                                    font-size: 12px;
                                    margin-top: 10px;
                                }}
                                .thank-you {{
                                    text-align: center;
                                    font-size: 14px;
                                    font-weight: bold;
                                    margin: 10px 0;
                                }}
                                .order-number {{
                                    text-align: center;
                                    font-size: 11px;
                                    color: #666;
                                    margin: 3px 0;
                                }}
                            </style>
                        </head>
                        <body>
                            <h2>🏮 WoJia HUOGUO</h2>
                            <div class="header">{datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}</div>
                            <div class="order-number">Чек #{receipt_id}</div>
                            <hr class="divider">
                            <table>
                                <thead>
                                    <tr>
                                        <td class="item-name"><b>Наименование</b></td>
                                        <td class="item-qty"><b>Кол</b></td>
                                        <td class="item-price"><b>Сумма</b></td>
                                    </tr>
                                </thead>
                                <tbody>
                                    {items_html}
                                </tbody>
                            </table>
                            <hr class="divider">
                            <table>
                                <tr class="total-row">
                                    <td colspan="2">ИТОГО:</td>
                                    <td class="item-price">{int(final_total)} тг</td>
                                </tr>
                                {discount_html}
                                <tr class="total-row">
                                    <td colspan="2">К ОПЛАТЕ:</td>
                                    <td class="item-price">{int(final_total_after_discount)} тг</td>
                                </tr>
                            </table>
                            <hr class="divider-double">
                            <div class="thank-you">Спасибо за заказ! 🙏</div>
                            <div class="footer">Приятного аппетита!</div>
                            <div class="footer" style="font-size:10px; color:#999; margin-top:5px;">
                                {payment_method} • {datetime.datetime.now().strftime('%H:%M')}
                            </div>
                        </body>
                    </html>
                    """

                    # Скрипт для печати
                    print_script = f"""
                    <script>
                        var content = {json.dumps(receipt_content)};
                        var w = window.open('', '_blank', 'width=400,height=600,menubar=no,toolbar=no,location=no,status=no,scrollbars=yes');
                        w.document.write(content);
                        w.document.close();
                        setTimeout(function() {{
                            w.print();
                            setTimeout(function() {{
                                w.close();
                            }}, 1000);
                        }}, 500);
                    </script>
                    """

                    components.html(print_script, height=0)

                    # Сохраняем продажу в базу
                    for item in order["cart"]:
                        execute_query(
                            "INSERT INTO sales (date, dish, qty, total_price, receipt_id, discount_percent, payment_method) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                            (today, item["name"], item["qty"], item["price"] * item["qty"], order["id"], disc,
                             pay_method)
                        )

                    # Удаляем заказ
                    execute_query("DELETE FROM active_orders WHERE order_id = %s", (order["id"],))
                    st.session_state.current_active_order_id = None
                    st.success("Заказ оплачен!")
                    st.rerun()
            else:
                st.session_state.current_active_order_id = None
                st.rerun()
        else:
            st.info("Выберите или создайте заказ слева")