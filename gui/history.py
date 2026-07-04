import streamlit as st
import datetime
import json
import streamlit.components.v1 as components # <-- ОБЯЗАТЕЛЬНО добавить этот импорт
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
                grouped_receipts[r_id] = {"date": date, "items": {}, "final_sum": 0.0, "discount": d_percent,
                                          "pay_method": pay_meth}
            grouped_receipts[r_id]["items"][dish] = qty
            grouped_receipts[r_id]["final_sum"] += total_price

        # Вывод статистики
        t_col1, t_col2, t_col3 = st.columns(3)
        t_col1.metric("Выручка за сегодня:", f"{int(total_today)} тг.")
        t_col2.metric("Kaspi QR:", f"{int(total_today_kaspi)} тг.")
        t_col3.metric("Наличные:", f"{int(total_today_cash)} тг.")

        st.write("---")
        st.markdown("#### 📜 Журнал закрытых чеков")

        # ТЕПЕРЬ ЦИКЛ НАХОДИТСЯ ВНУТРИ ELSE И ИМЕЕТ ДОСТУП К GROUPED_RECEIPTS
        for r_id, info in grouped_receipts.items():
            with st.expander(f"🧾 Чек №{r_id} | Дата: {info['date']} | Сумма: {int(info['final_sum'])} тг."):
                for dish, qty in info["items"].items():
                    st.write(f"• {dish} (x{qty})")

                st.write("---")

                if user_role == "Администратор":
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        # ИСПРАВЛЕНИЕ: здесь было order['id'], меняем на r_id
                        if st.button(f"🖨 Печать чека №{r_id}", key=f"print_{r_id}"):
                            # 1. Запрос данных
                            sales_data = execute_query(
                                "SELECT dish, qty, total_price FROM sales WHERE receipt_id = %s",
                                (r_id,), fetch="all"
                            )

                            if not sales_data:
                                st.error("Ошибка: Чек пустой!")
                            else:
                                # 2. Формируем HTML
                                items_html = ""
                                total = 0
                                for row in sales_data:
                                    dish, qty, price = row[0], row[1], row[2]
                                    items_html += f"<tr><td>{dish}</td><td>x{qty}</td><td>{int(price)} тг</td></tr>"
                                    total += price

                                # 3. HTML шаблон (стили взяты из предыдущего успешного чека)
                                receipt_content = f"""
                                            <html>
                                                <head><style>body {{ width: 280px; font-family: monospace; }} table {{ width: 100%; }}</style></head>
                                                <body>
                                                    <h2>WoJia HUOGUO</h2>
                                                    <table>{items_html}</table>
                                                    <hr>
                                                    <h3>ИТОГО: {int(total)} тг</h3>
                                                </body>
                                            </html>
                                            """

                                # 4. Скрипт печати
                                print_script = f"""
                                            <script>
                                                var content = {json.dumps(receipt_content)};
                                                var w = window.open('', '_blank', 'width=400,height=600');
                                                w.document.write(content);
                                                w.document.close();
                                                setTimeout(function() {{ w.print(); w.close(); }}, 500);
                                            </script>
                                            """
                                components.html(print_script, height=0)
                    with btn_col2:
                        if st.button(f"❌ Удалить №{r_id}", key=f"btn_del_{r_id}", type="secondary"):
                            execute_query("DELETE FROM sales WHERE receipt_id = %s", (r_id,))
                            st.success(f"Чек {r_id} удален!")
                            st.rerun()
                else:
                    # Если не администратор, используем твою функцию trigger_silent_print
                    if st.button(f"🖨️ Распечатать №{r_id}", key=f"btn_p_{r_id}"):
                        trigger_silent_print(f"Чек {r_id}", info["items"], {}, info["discount"], info["pay_method"],
                                             r_id)