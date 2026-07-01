import streamlit as st
import datetime
from database.connection import execute_query
from utils.printing import trigger_silent_print  # Импортируем функцию печати чека


def render_history_tab():
    st.subheader("📊 Аналитика и Финансовые показатели")
    today_date_str = str(datetime.date.today())

    # Проверяем роль текущего пользователя из всех возможных переменных сессии
    # Если зашёл Кассир, то user_role НЕ будет равен "Администратор"
    user_role = st.session_state.get("role") or st.session_state.get("user_role") or "Кассир"

    if st.button("🖨️ Закрыть смену и Распечатать Z-Отчет", type="secondary", use_container_width=True):
        today_sales_rows = execute_query("SELECT dish, qty, total_price, payment_method FROM sales WHERE date = ?",
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
        "SELECT date, dish, qty, total_price, receipt_id, discount_percent, payment_method FROM sales ORDER BY rowid DESC",
        fetch="all")

    if not rows_sales:
        st.info("Продаж пока не было.")
    else:
        total_all_time = total_all_time_kaspi = total_all_time_cash = 0.0
        total_today = total_today_kaspi = total_today_cash = 0.0
        grouped_receipts, sales_by_date, dishes_popularity = {}, {}, {}

        for row in rows_sales:
            date, dish, qty, total_price, r_id, d_percent, pay_meth = row
            total_all_time += total_price
            sales_by_date[date] = sales_by_date.get(date, 0.0) + total_price
            dishes_popularity[dish] = dishes_popularity.get(dish, 0) + qty

            if pay_meth == "Kaspi QR":
                total_all_time_kaspi += total_price
            else:
                total_all_time_cash += total_price

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

        st.markdown("#### 📆 Касса за сегодня")
        t_col1, t_col2, t_col3 = st.columns(3)
        t_col1.metric("Выручка за сегодня:", f"{int(total_today)} тг.")
        t_col2.metric("Сегодня через Kaspi QR:", f"{int(total_today_kaspi)} тг.")
        t_col3.metric("Сегодня наличными:", f"{int(total_today_cash)} тг.")

        st.write("---")
        st.markdown("#### 📈 Графики эффективности")
        g_col1, g_col2 = st.columns(2)
        with g_col1:
            st.line_chart(sales_by_date)
        with g_col2:
            st.bar_chart(dishes_popularity)

        st.write("---")
        st.markdown("#### 📜 Журнал закрытых чеков")
        for r_id, info in grouped_receipts.items():
            with st.expander(f"🧾 Чек №{r_id} | Дата: {info['date']} | Сумма: {int(info['final_sum'])} тг."):
                for dish, qty in info["items"].items():
                    st.write(f"• {dish} (x{qty})")

                st.write("---")

                # Если вошел Администратор — создаем две колонки (для Печати и Удаления)
                if user_role == "Администратор":
                    btn_col1, btn_col2 = st.columns(2)

                    with btn_col1:
                        if st.button(f"🖨️ Распечатать чек №{r_id}", key=f"btn_p_{r_id}", use_container_width=True):
                            trigger_silent_print(
                                order_name=f"Чек {r_id}",
                                cart_dict=info["items"],
                                flat_menu_prices={},
                                discount_percent=info["discount"],
                                pay_method=info["pay_method"],
                                order_id=r_id
                            )
                            st.success("Сигнал на печать отправлен!")

                    with btn_col2:
                        if st.button(f"❌ Удалить чек №{r_id}", key=f"btn_del_{r_id}", type="secondary",
                                     use_container_width=True):
                            execute_query("DELETE FROM sales WHERE receipt_id = ?", (r_id,))
                            st.success(f"Чек №{r_id} успешно удален!")
                            st.rerun()

                # Если вошел Кассир — показываем ТОЛЬКО кнопку печати на всю ширину, кнопки удаления вообще не будет в коде
                else:
                    if st.button(f"🖨️ Распечатать чек №{r_id}", key=f"btn_p_{r_id}", use_container_width=True):
                        trigger_silent_print(
                            order_name=f"Чек {r_id}",
                            cart_dict=info["items"],
                            flat_menu_prices={},
                            discount_percent=info["discount"],
                            pay_method=info["pay_method"],
                            order_id=r_id
                        )
                        st.success("Сигнал на печать отправлен!")