import streamlit as st
import datetime
import json
import streamlit.components.v1 as components
from database.connection import execute_query
from utils.printing import trigger_silent_print


def render_history_tab():
    st.subheader("📊 Аналитика и Финансовые показатели")
    today_date_str = str(datetime.date.today())
    user_role = st.session_state.get("user_role", "Кассир")

    if st.button("🖨️ Закрыть смену и Распечатать Z-Отчет", type="secondary", use_container_width=True):
        today_sales_rows = execute_query("SELECT dish, qty, total_price, payment_method FROM sales WHERE date = %s",
                                         (today_date_str,), fetch="all")
        z_summary = {"cash": 0.0, "kaspi": 0.0, "total": 0.0, "dishes": {}}
        if today_sales_rows:
            for r in today_sales_rows:
                d_name, d_qty, d_total, d_meth = r[0], r[1], r[2], r[3]
                z_summary["total"] += d_total
                if d_meth == "Kaspi QR":
                    z_summary["kaspi"] += d_total
                else:
                    z_summary["cash"] += d_total
                z_summary["dishes"][d_name] = z_summary["dishes"].get(d_name, 0) + d_qty
        st.session_state.z_print_trigger = z_summary
        st.rerun()

    st.write("---")

    rows_sales = execute_query(
        "SELECT date, dish, qty, total_price, receipt_id, discount_percent, payment_method FROM sales ORDER BY id DESC",
        fetch="all")

    if not rows_sales:
        st.info("Продаж пока не было.")
    else:
        total_today = total_today_kaspi = total_today_cash = 0.0
        grouped_receipts, sales_by_date, dishes_popularity = {}, {}, {}

        for row in rows_sales:
            date, dish, qty, total_price, r_id, d_percent, pay_meth = row
            sales_by_date[date] = sales_by_date.get(date, 0.0) + total_price
            dishes_popularity[dish] = dishes_popularity.get(dish, 0) + qty

            if date == today_date_str:
                total_today += total_price
                if pay_meth == "Kaspi QR":
                    total_today_kaspi += total_price
                else:
                    total_today_cash += total_price

            if r_id not in grouped_receipts:
                grouped_receipts[r_id] = {
                    "date": date,
                    "items": [],  # Изменяем на список для хранения всех деталей
                    "final_sum": 0.0,
                    "discount": d_percent,
                    "pay_method": pay_meth
                }
            # Добавляем товар с ценой и количеством
            grouped_receipts[r_id]["items"].append({
                "dish": dish,
                "qty": qty,
                "total": total_price
            })
            grouped_receipts[r_id]["final_sum"] += total_price

        # Вывод статистики
        t_col1, t_col2, t_col3 = st.columns(3)
        t_col1.metric("Выручка за сегодня:", f"{int(total_today)} тг.")
        t_col2.metric("Kaspi QR:", f"{int(total_today_kaspi)} тг.")
        t_col3.metric("Наличные:", f"{int(total_today_cash)} тг.")

        st.write("---")
        st.markdown("#### 📜 Журнал закрытых чеков")

        # Цикл по чекам
        for r_id, info in grouped_receipts.items():
            with st.expander(f"🧾 Чек №{r_id} | Дата: {info['date']} | Сумма: {int(info['final_sum'])} тг."):
                # Показываем товары в чеке
                for item in info["items"]:
                    st.write(f"• {item['dish']} (x{item['qty']}) - {int(item['total'])} тг")

                if info['discount'] > 0:
                    st.write(f"💫 Скидка: {info['discount']}%")

                st.write(f"💳 Оплата: {info['pay_method']}")
                st.write("---")

                if user_role == "Администратор":
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if st.button(f"🖨 Печать чека №{r_id}", key=f"print_{r_id}"):
                            # Получаем данные для печати
                            sales_data = execute_query(
                                "SELECT dish, qty, total_price FROM sales WHERE receipt_id = %s",
                                (r_id,), fetch="all"
                            )

                            if not sales_data:
                                st.error("Ошибка: Чек пустой!")
                            else:
                                # Получаем скидку и метод оплаты
                                receipt_info = execute_query(
                                    "SELECT discount_percent, payment_method FROM sales WHERE receipt_id = %s LIMIT 1",
                                    (r_id,), fetch="one"
                                )

                                discount_percent = receipt_info[0] if receipt_info else 0
                                payment_method = receipt_info[1] if receipt_info else "Наличные"

                                # Формируем HTML для чека
                                items_html = ""
                                total = 0
                                for row in sales_data:
                                    dish, qty, price = row[0], row[1], row[2]
                                    items_html += f"""
                                        <tr>
                                            <td class="item-name">{dish}</td>
                                            <td class="item-qty">x{qty}</td>
                                            <td class="item-price">{int(price)}</td>
                                        </tr>
                                    """
                                    total += price

                                # Строка со скидкой
                                discount_html = ""
                                if discount_percent > 0:
                                    discount_amount = total * (discount_percent / 100)
                                    discount_html = f"""
                                        <tr class="discount-row">
                                            <td colspan="2">Скидка ({discount_percent}%):</td>
                                            <td class="item-price">-{int(discount_amount)} тг</td>
                                        </tr>
                                    """

                                final_total = total * (1 - discount_percent / 100)

                                # Полный HTML чека
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
                                        <div class="order-number">Чек #{r_id}</div>
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
                                                <td class="item-price">{int(total)} тг</td>
                                            </tr>
                                            {discount_html}
                                            <tr class="total-row">
                                                <td colspan="2">К ОПЛАТЕ:</td>
                                                <td class="item-price">{int(final_total)} тг</td>
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

                    with btn_col2:
                        if st.button(f"❌ Удалить №{r_id}", key=f"btn_del_{r_id}", type="secondary"):
                            execute_query("DELETE FROM sales WHERE receipt_id = %s", (r_id,))
                            st.success(f"Чек {r_id} удален!")
                            st.rerun()
                else:
                    # Для кассира - печать чека через отдельную функцию
                    if st.button(f"🖨️ Распечатать №{r_id}", key=f"btn_p_{r_id}"):
                        # Собираем данные для чека
                        sales_data = execute_query(
                            "SELECT dish, qty, total_price FROM sales WHERE receipt_id = %s",
                            (r_id,), fetch="all"
                        )

                        if sales_data:
                            # Формируем items для печати
                            items_for_print = {}
                            total = 0
                            for row in sales_data:
                                dish, qty, price = row[0], row[1], row[2]
                                items_for_print[dish] = qty
                                total += price

                            # Вызываем функцию печати
                            trigger_silent_print(
                                f"Чек {r_id}",
                                items_for_print,
                                {},
                                info.get('discount', 0),
                                info.get('pay_method', 'Наличные'),
                                r_id
                            )