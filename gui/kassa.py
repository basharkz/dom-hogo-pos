import streamlit as st
import datetime
import json
from database.connection import execute_query
from database.orders import db_get_active_orders, db_get_order_by_id, db_update_order

def render_kassa_tab():
    kassa_col1, kassa_col2 = st.columns([0.6, 0.4])
    rows_cats = execute_query("SELECT cat_name FROM categories ORDER BY cat_name ASC", fetch="all")
    db_categories_list = [r[0] for r in rows_cats] if rows_cats else []

    rows_menu = execute_query("SELECT dish_name, price, category FROM menu", fetch="all")
    menu_data = rows_menu if rows_menu else []

    DB_MENU_STRUCT = {}
    for row in menu_data:
        name, price, cat = row[0], row[1], row[2]
        if cat not in DB_MENU_STRUCT: DB_MENU_STRUCT[cat] = {}
        DB_MENU_STRUCT[cat][name] = price

    active_orders = db_get_active_orders()

    with kassa_col1:
        st.subheader("Активные чеки / Столы")
        check_mgr_col1, check_mgr_col2 = st.columns([0.6, 0.4])

        with check_mgr_col1:
            if not active_orders:
                st.info("Нет открытых чеков. Создайте новый чек справа ➔")
            else:
                cols_orders = st.columns(len(active_orders))
                for i, order in enumerate(active_orders):
                    if cols_orders[i].button(order["name"], key=f"sel_ord_{order['id']}"):
                        st.session_state.current_active_order_id = order["id"]
                        st.rerun()

        with check_mgr_col2:
            with st.popover("➕ Открыть Новый Чек", use_container_width=True):
                new_order_name_inp = st.text_input("Название (например, 'Стол 4'):")
                if st.button("Создать чек", use_container_width=True):
                    if new_order_name_inp:
                        new_order_id = str(int(datetime.datetime.now().timestamp()))
                        execute_query("INSERT INTO active_orders (order_id, order_name, cart_json, discount_percent) VALUES (?, ?, ?, ?)",
                                      (new_order_id, new_order_name_inp, json.dumps({}), 0.0))
                        st.session_state.current_active_order_id = new_order_id
                        st.rerun()

        st.write("---")
        current_active_order = None
        if st.session_state.current_active_order_id:
            current_active_order = db_get_order_by_id(st.session_state.current_active_order_id)

        st.subheader("Меню ресторана")
        if not DB_MENU_STRUCT:
            st.warning("В меню пусто.")
        else:
            categories_tabs = st.tabs(list(DB_MENU_STRUCT.keys()))
            for i, (cat_name, dishes_dict) in enumerate(DB_MENU_STRUCT.items()):
                with categories_tabs[i]:
                    for dish, price in dishes_dict.items():
                        m_col1, m_col2 = st.columns([0.7, 0.3])
                        with m_col1: st.write(f"**{dish}** — {int(price)} тг.")
                        with m_col2:
                            btn_disabled = True if not current_active_order else False
                            if st.button("➕ Добавить", key=f"add_{dish}_{cat_name}", disabled=btn_disabled):
                                if dish in current_active_order["cart"]: current_active_order["cart"][dish] += 1
                                else: current_active_order["cart"][dish] = 1
                                db_update_order(current_active_order)
                                st.rerun()

    with kassa_col2:
        st.subheader("Текущий чек")
        if not current_active_order:
            st.info("Выберите или создайте чек слева.")
        else:
            st.success(f"Выбран заказ: **{current_active_order['name']}**")
            total_bill_raw = 0
            flat_menu_prices = {}
            for c in DB_MENU_STRUCT.values(): flat_menu_prices.update(c)

            with st.container(border=True):
                if not current_active_order["cart"]: st.write("Чек пуст.")
                else:
                    for idx, (dish, qty) in enumerate(list(current_active_order["cart"].items())):
                        price = flat_menu_prices.get(dish, 0)
                        item_total_raw = price * qty
                        total_bill_raw += item_total_raw

                        ch_col1, ch_col2 = st.columns([0.8, 0.2])
                        with ch_col1: st.write(f"• {dish} x{qty} = **{int(item_total_raw)} тг.**")
                        with ch_col2:
                            # Добавляем idx и id заказа в ключ, чтобы они никогда не повторялись
                            if st.button("❌", key=f"rem_{dish.replace(' ', '_')}_{current_active_order['id']}_{idx}"):
                                current_active_order["cart"][dish] -= 1
                                if current_active_order["cart"][dish] <= 0: del current_active_order["cart"][dish]
                                db_update_order(current_active_order)
                                st.rerun()

            st.write("---")
            active_discount = current_active_order["discount"]
            final_discount_percent = st.number_input("Скидка (%):", min_value=0.0, max_value=100.0, step=1.0, value=active_discount)

            if final_discount_percent != active_discount:
                current_active_order["discount"] = final_discount_percent
                db_update_order(current_active_order)
                st.rerun()

            discount_amount = total_bill_raw * (final_discount_percent / 100.0)
            final_bill_with_discount = total_bill_raw - discount_amount

            st.markdown(f"### ИТОГО: **{int(final_bill_with_discount)} тг.**")
            pay_method = st.radio("Метод оплаты:", ["Наличные", "Kaspi QR"])

            if st.button("💾 Оплатить и закрыть", type="primary", use_container_width=True):
                today_str = str(datetime.date.today())
                st.session_state.just_paid_order_data = {
                    "id": current_active_order["id"], "name": current_active_order["name"],
                    "cart": current_active_order["cart"], "prices": flat_menu_prices,
                    "discount": final_discount_percent, "method": pay_method
                }

                for dish, qty in current_active_order["cart"].items():
                    price = flat_menu_prices.get(dish, 0)
                    item_discounted_total = (price * qty) * (1 - final_discount_percent / 100.0)
                    execute_query("INSERT INTO sales (date, dish, qty, total_price, receipt_id, discount_percent, payment_method) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                  (today_str, dish, qty, item_discounted_total, current_active_order["id"], final_discount_percent, pay_method))

                    recipe_rows = execute_query("SELECT ingredient, qty_needed FROM recipes WHERE dish = ?", (dish,), fetch="all")
                    if recipe_rows:
                        for ing_row in recipe_rows:
                            execute_query("INSERT INTO inventory (date, item, qty, price, reason) VALUES (?, ?, ?, ?, ?)",
                                          (today_str, ing_row[0], -ing_row[1] * qty, 0.0, "Продажа"))

                execute_query("DELETE FROM active_orders WHERE order_id = ?", (current_active_order["id"],))
                st.session_state.current_active_order_id = None
                st.rerun()