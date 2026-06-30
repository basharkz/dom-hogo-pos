import streamlit as st  # Подключаем Streamlit для создания интерфейса
import sqlite3  # Подключаем встроенную базу данных SQLite
import datetime  # Подключаем модуль времени для фиксации дат и генерации уникальных ключей
import json  # Подключаем модуль JSON для сериализации корзины


# =========================================================
# 📦 ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ
# =========================================================
def init_db():  # Функция для создания таблиц при первом запуске
    conn = sqlite3.connect("school_voxys.db")
    cursor = conn.cursor()

    # Таблица Склада: поле reason фиксирует закуп или конкретную причину списания (брак, порча)
    cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (date TEXT, item TEXT, qty REAL, price REAL, reason TEXT)''')

    # Таблица Истории Продаж
    cursor.execute(
        '''CREATE TABLE IF NOT EXISTS sales (date TEXT, dish TEXT, qty INTEGER, total_price REAL, receipt_id TEXT, discount_percent REAL, payment_method TEXT)''')

    # Таблица Меню
    cursor.execute('''CREATE TABLE IF NOT EXISTS menu (dish_name TEXT UNIQUE, price REAL, category TEXT)''')

    # Таблица Рецептов
    cursor.execute('''CREATE TABLE IF NOT EXISTS recipes (dish TEXT, ingredient TEXT, qty_needed REAL)''')

    # Таблица Категорий меню
    cursor.execute('''CREATE TABLE IF NOT EXISTS categories (cat_name TEXT UNIQUE)''')

    # Таблица Активных заказов для многочекового режима
    cursor.execute(
        '''CREATE TABLE IF NOT EXISTS active_orders (order_id TEXT UNIQUE, order_name TEXT, cart_json TEXT, discount_percent REAL)''')

    # Наполнение базовыми категориями при первом запуске
    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        base_cats = [("ХОГО",), ("ПИЦЦА",), ("СОУСЫ",), ("НАПИТКИ",)]
        cursor.executemany("INSERT OR IGNORE INTO categories (cat_name) VALUES (?)", base_cats)
        conn.commit()

    # Наполнение базовым меню при первом запуске
    cursor.execute("SELECT COUNT(*) FROM menu")
    if cursor.fetchone()[0] == 0:
        base_menu = [
            ("Красна Тарелка ХОГО", 1950, "ХОГО"),
            ("Оранжевая Тарелка ХОГО", 1500, "ХОГО"),
            ("Белая Тарелка ХОГО", 800, "ХОГО"),
            ("Пицца Маргарита", 2700, "ПИЦЦА"),
            ("Кола 0.5л", 300, "НАПИТКИ")
        ]
        cursor.executemany("INSERT OR IGNORE INTO menu (dish_name, price, category) VALUES (?, ?, ?)", base_menu)
        conn.commit()
    conn.close()


init_db()


# =========================================================
# 🔄 УТИЛИТЫ ДЛЯ БЫСТРОЙ РАБОТЫ С БАЗОЙ ДАННЫХ
# =========================================================
def execute_query(query, data=None, fetch="none"):
    conn = sqlite3.connect("school_voxys.db")
    cursor = conn.cursor()
    try:
        if data:
            cursor.execute(query, data)
        else:
            cursor.execute(query)

        result = None
        if fetch == "all":
            result = cursor.fetchall()
        elif fetch == "one":
            result = cursor.fetchone()
        else:
            conn.commit()
        return result
    except Exception as e:
        st.error(f"Ошибка базы данных: {e}")
        return None
    finally:
        conn.close()


def db_get_active_orders():
    rows = execute_query(
        "SELECT order_id, order_name, cart_json, discount_percent FROM active_orders ORDER BY rowid ASC", fetch="all")
    orders = []
    if rows:
        for row in rows:
            cart_dict = json.loads(row[2]) if row[2] else {}
            orders.append({"id": row[0], "name": row[1], "cart": cart_dict, "discount": row[3]})
    return orders


def db_get_order_by_id(order_id):
    row = execute_query(
        "SELECT order_id, order_name, cart_json, discount_percent FROM active_orders WHERE order_id = ?", (order_id,),
        fetch="one")
    if row: return {"id": row[0], "name": row[1], "cart": json.loads(row[2]) if row[2] else {}, "discount": row[3]}
    return None


def db_update_order(order_dict):
    cart_json = json.dumps(order_dict["cart"])
    execute_query("UPDATE active_orders SET order_name = ?, cart_json = ?, discount_percent = ? WHERE order_id = ?",
                  (order_dict["name"], cart_json, order_dict["discount"], order_dict["id"]))


def calculate_dish_food_cost(dish_name):
    """Высчитывает себестоимость порции блюда на основе цен последних закупок сырья"""
    recipe = execute_query("SELECT ingredient, qty_needed FROM recipes WHERE dish = ?", (dish_name,), fetch="all")
    if not recipe:
        return 0.0

    total_cost = 0.0
    for ing, qty in recipe:
        last_price_row = execute_query(
            "SELECT price FROM inventory WHERE item = ? AND price > 0 ORDER BY rowid DESC LIMIT 1",
            (ing,), fetch="one"
        )
        price_per_unit = last_price_row[0] if last_price_row else 0.0
        total_cost += qty * price_per_unit
    return total_cost


# =========================================================
# 🖨️ СКРЫТЫЙ HTML-МОДУЛЬ ДЛЯ МГНОВЕННОЙ АВТОПЕЧАТИ
# =========================================================
def trigger_silent_print(order_name, cart_dict, flat_menu_prices, discount_percent, pay_method, order_id):
    """Формирует чистый HTML-чек и мгновенно отправляет его на термопринтер"""
    total_raw = 0
    items_html = ""

    for dish, qty in cart_dict.items():
        price = flat_menu_prices.get(dish, 0)
        item_total = price * qty
        total_raw += item_total
        items_html += f"""
        <tr class="item-row">
            <td>{dish} <br><small>x{qty}</small></td>
            <td style="text-align: right; vertical-align: bottom;">{int(item_total)} ₸</td>
        </tr>
        """

    if discount_percent > 0:
        disc_amount = total_raw * (discount_percent / 100.0)
        final_sum = total_raw - disc_amount
        discount_html = f"""
        <tr class="total-row">
            <td><b>Скидка {int(discount_percent)}%:</b></td>
            <td style="text-align: right;">-{int(disc_amount)} ₸</td>
        </tr>
        """
    else:
        final_sum = total_raw
        discount_html = ""

    receipt_html = f"""
        <html>
        <head>
            <style>
                @page {{ size: 58mm 210mm; margin: 0mm; }}
                body {{ 
                    font-family: 'Courier New', Courier, monospace; 
                    width: 200px; margin: 5mm; padding: 0; font-size: 15px; line-height: 1.3; color: #000;
                }}
                .center {{ text-align: center; }}
                .header-title {{ font-size: 18px; font-weight: bold; margin: 5px 0; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                .item-row td {{ padding: 8px 0; border-bottom: 1px dashed #000; }}
                .total-row td {{ padding: 6px 0; }}
                .final-price {{ font-size: 18px; }}
                hr.main-del {{ border-top: 2px solid #000; border-bottom: 0; margin: 8px 0; }}
            </style>
        </head>
        <body onload="window.print();">
            <div class="center">
                <div class="header-title">WoJia HUOGUO</div>
                <p style="margin: 3px 0;">
                    Заказ: {order_name}<br>
                    Чек №: {order_id}<br>
                    Дата: {datetime.date.today()}
                </p>
            </div>
            <hr class="main-del">
            <table>
                {items_html}
                {discount_html}
                <tr class="total-row final-price">
                    <td><b>ИТОГО:</b></td>
                    <td style="text-align: right;"><b>{int(final_sum)} ₸</b></td>
                </tr>
            </table>
            <hr class="main-del">
            <div class="center" style="margin-top: 10px;">
                <p>Тип оплаты: {pay_method}<br><br><b>Спасибо за заказ!</b></p>
            </div>
        </body>
        </html>
        """
    print_key = f"print_frame_{int(datetime.datetime.now().timestamp())}_{order_id}"
    st.components.v1.html(receipt_html, height=0, width=0, key=print_key)


def trigger_z_report_print(summary_data):
    """Генерирует финансовый Z-отчет за день для вывода на чековый принтер"""
    today_str = str(datetime.date.today())

    dishes_html = ""
    for dish, qty in summary_data["dishes"].items():
        dishes_html += f"""
        <tr class="item-row">
            <td>{dish}</td>
            <td style="text-align: right;">x{qty}</td>
        </tr>
        """

    z_html = f"""
    <html>
    <head>
        <style>
            @page {{ size: 58mm 210mm; margin: 0mm; }}
            body {{ font-family: 'Courier New', monospace; width: 200px; margin: 5mm; font-size: 14px; color: #000; }}
            .center {{ text-align: center; }}
            .bold-title {{ font-size: 16px; font-weight: bold; margin: 10px 0; }}
            table {{ width: 100%; border-collapse: collapse; }}
            .item-row td {{ padding: 4px 0; border-bottom: 1px dotted #000; }}
            hr {{ border-top: 2px dashed #000; margin: 10px 0; }}
        </style>
    </head>
    <body onload="window.print();">
        <div class="center">
            <div class="bold-title">💥 Z - ОТЧЕТ 💥</div>
            <p>Ресторан: WoJia HUOGUO<br>Дата: {today_str}</p>
        </div>
        <hr>
        <p><b>ФИНАНСЫ:</b></p>
        <p>💵 Наличные: {int(summary_data["cash"])} ₸</p>
        <p>📱 Kaspi QR: {int(summary_data["kaspi"])} ₸</p>
        <p style="font-size: 16px;"><b>ОБЩАЯ ВЫРУЧКА: {int(summary_data["total"])} ₸</b></p>
        <hr>
        <p><b>ПРОДАНО БЛЮД:</b></p>
        <table>
            {dishes_html}
        </table>
        <hr>
        <div class="center"><p>Смена закрыта успешно!<br>VOXYS Intelligence</p></div>
    </body>
    </html>
    """
    print_key = f"z_print_frame_{int(datetime.datetime.now().timestamp())}"
    st.components.v1.html(z_html, height=0, width=0, key=print_key)


# =========================================================
# 🔐 СЕССИЯ, АВТОРИЗАЦИЯ И ВКЛАДКИ
# =========================================================
if "current_active_order_id" not in st.session_state:
    st.session_state.current_active_order_id = None

if "just_paid_order_data" not in st.session_state:
    st.session_state.just_paid_order_data = None

if "z_print_trigger" not in st.session_state:
    st.session_state.z_print_trigger = None

st.sidebar.title("Система управления VOXYS")
user_role = st.sidebar.selectbox("Выберите вашу роль:", ["Кассир", "Менеджер", "Администратор"])
access_granted = False

if user_role == "Кассир":
    access_granted = True
elif user_role == "Менеджер":
    password = st.sidebar.text_input("Введите пароль Менеджера:", type="password")
    if password == "manager123": access_granted = True
elif user_role == "Администратор":
    password = st.sidebar.text_input("Введите пароль Администратора:", type="password")
    if password == "admin777": access_granted = True

tabs_to_show = ["Касса (Продажи)"]
if access_granted:
    if user_role == "Менеджер":
        tabs_to_show.extend(["История продаж", "Управление меню"])
    elif user_role == "Администратор":
        tabs_to_show.extend(["История продаж", "Склад и Аналитика", "Управление меню"])
else:
    st.sidebar.warning("Для доступа к управлению введите пароль.")

active_tabs = st.tabs(tabs_to_show)
st.title("POS-Терминал VOXYS")

if st.session_state.just_paid_order_data:
    od = st.session_state.just_paid_order_data
    trigger_silent_print(od["name"], od["cart"], od["prices"], od["discount"], od["method"], od["id"])
    st.session_state.just_paid_order_data = None

if st.session_state.z_print_trigger:
    trigger_z_report_print(st.session_state.z_print_trigger)
    st.session_state.z_print_trigger = None

# =========================================================
# 🛒 ВКЛАДКА №1: КАССА (РАБОТА С НЕСКОЛЬКИМИ ЧЕКАМИ)
# =========================================================
with active_tabs[0]:
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
                        execute_query(
                            "INSERT INTO active_orders (order_id, order_name, cart_json, discount_percent) VALUES (?, ?, ?, ?)",
                            (new_order_id, new_order_name_inp, json.dumps({}), 0.0))
                        st.session_state.current_active_order_id = new_order_id
                        st.rerun()
                    else:
                        st.error("Введите название!")

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
                        with m_col1:
                            st.write(f"**{dish}** — {int(price)} тг.")
                        with m_col2:
                            btn_disabled = True if not current_active_order else False
                            if st.button("➕ Добавить", key=f"add_{dish}_{cat_name}", disabled=btn_disabled):
                                if dish in current_active_order["cart"]:
                                    current_active_order["cart"][dish] += 1
                                else:
                                    current_active_order["cart"][dish] = 1
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
                if not current_active_order["cart"]:
                    st.write("Чек пуст.")
                else:
                    # 👍 Защита от DuplicateKey: перечисляем через enumerate и добавляем уникальный idx в key кнопки
                    for idx, (dish, qty) in enumerate(list(current_active_order["cart"].items())):
                        price = flat_menu_prices.get(dish, 0)
                        item_total_raw = price * qty
                        total_bill_raw += item_total_raw

                        ch_col1, ch_col2 = st.columns([0.8, 0.2])
                        with ch_col1:
                            st.write(f"• {dish} x{qty} = **{int(item_total_raw)} тг.**")
                        with ch_col2:
                            if st.button("❌", key=f"rem_{dish}_{current_active_order['id']}_{idx}"):
                                current_active_order["cart"][dish] -= 1
                                if current_active_order["cart"][dish] <= 0: del current_active_order["cart"][dish]
                                db_update_order(current_active_order)
                                st.rerun()

            st.write("---")
            active_discount = current_active_order["discount"]
            final_discount_percent = st.number_input("Скидка (%):", min_value=0.0, max_value=100.0, step=1.0,
                                                     value=active_discount)

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
                    "id": current_active_order["id"],
                    "name": current_active_order["name"],
                    "cart": current_active_order["cart"],
                    "prices": flat_menu_prices,
                    "discount": final_discount_percent,
                    "method": pay_method
                }

                for dish, qty in current_active_order["cart"].items():
                    price = flat_menu_prices.get(dish, 0)
                    item_discounted_total = (price * qty) * (1 - final_discount_percent / 100.0)
                    execute_query(
                        "INSERT INTO sales (date, dish, qty, total_price, receipt_id, discount_percent, payment_method) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                        today_str, dish, qty, item_discounted_total, current_active_order["id"], final_discount_percent,
                        pay_method))

                    recipe_rows = execute_query("SELECT ingredient, qty_needed FROM recipes WHERE dish = ?", (dish,),
                                                fetch="all")
                    if recipe_rows:
                        for ing_row in recipe_rows:
                            ing_name, qty_per_item = ing_row[0], ing_row[1]
                            total_deduct = qty_per_item * qty
                            execute_query(
                                "INSERT INTO inventory (date, item, qty, price, reason) VALUES (?, ?, ?, ?, ?)",
                                (today_str, ing_name, -total_deduct, 0.0, "Продажа"))

                execute_query("DELETE FROM active_orders WHERE order_id = ?", (current_active_order["id"],))
                st.session_state.current_active_order_id = None
                st.rerun()

# =========================================================
# 📊 ВКЛАДКА №2: ИСТОРИЯ ПРОДАЖ (ОТЧЕТЫ И ГРАФИКИ)
# =========================================================
if "История продаж" in tabs_to_show:
    idx = tabs_to_show.index("История продаж")
    with active_tabs[idx]:
        st.subheader("📊 Аналитика и Финансовые показатели")

        today_date_str = str(datetime.date.today())
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
            total_all_time = 0.0
            total_all_time_kaspi = 0.0
            total_all_time_cash = 0.0
            total_today = 0.0
            total_today_kaspi = 0.0
            total_today_cash = 0.0
            grouped_receipts = {}

            sales_by_date = {}
            dishes_popularity = {}

            for row in rows_sales:
                date, dish, qty, total_price, r_id, d_percent, pay_meth = row[0], row[1], row[2], row[3], row[4], row[
                    5], row[6]
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
            with t_col1:
                st.metric("Выручка за сегодня:", f"{int(total_today)} тг.")
            with t_col2:
                st.metric("Сегодня через Kaspi QR:", f"{int(total_today_kaspi)} тг.")
            with t_col3:
                st.metric("Сегодня наличными:", f"{int(total_today_cash)} тг.")

            st.write("---")
            st.markdown("#### 📈 Графики эффективности")
            g_col1, g_col2 = st.columns(2)
            with g_col1:
                st.caption("Выручка по дням (тг):")
                st.line_chart(sales_by_date)
            with g_col2:
                st.caption("Топ продаваемых блюд (шт):")
                st.bar_chart(dishes_popularity)

            st.write("---")
            st.markdown("#### 📈 Выручка за всё время")
            a_col1, a_col2, a_col3 = st.columns(3)
            with a_col1:
                st.metric("Общая выручка:", f"{int(total_all_time)} тг.")
            with a_col2:
                st.metric("Всего через Kaspi QR:", f"{int(total_all_time_kaspi)} тг.")
            with a_col3:
                st.metric("Всего наличными:", f"{int(total_all_time_cash)} тг.")

            st.write("---")
            st.markdown("#### 📜 Журнал закрытых чеков")
            for r_id, info in grouped_receipts.items():
                discount_text = f" | Скидка: {int(info['discount'])}%" if info['discount'] > 0 else ""
                with st.expander(
                        f"🧾 Чек №{r_id} | Дата: {info['date']} | Оплата: {info['pay_method']}{discount_text} | Сумма: {int(info['final_sum'])} тг."):
                    for dish, qty in info["items"].items(): st.write(f"- {dish} (x{qty})")

# =========================================================
# ⚙️ ВКЛАДКА №3: СКЛАД (ПРИХОД, КОНТРОЛЬ И СПИСАНИЕ БРАКА)
# =========================================================
if "Склад и Аналитика" in tabs_to_show:
    idx = tabs_to_show.index("Склад и Аналитика")
    with active_tabs[idx]:
        st.subheader("Учет остатков на складе")

        cursor_summary = execute_query("SELECT item, SUM(qty) FROM inventory GROUP BY item", fetch="all")
        all_inventory_items = [row[0] for row in cursor_summary] if cursor_summary else []

        if cursor_summary:
            for row in cursor_summary:
                item_name, current_qty = row[0], row[1]
                if current_qty <= 5.0:
                    st.error(f"🚨 **{item_name}**: {current_qty:.3f} кг/шт (ЗАПАС КРИТИЧЕСКИ МАЛ!)")
                elif current_qty <= 15.0:
                    st.warning(f"⚠️ **{item_name}**: {current_qty:.3f} кг/шт (Заканчивается)")
                else:
                    st.success(f"📦 **{item_name}**: {current_qty:.3f} кг/шт")

        st.write("---")

        inv_col1, inv_col2 = st.columns(2)

        with inv_col1:
            st.markdown("#### 📥 Приход товара на склад")
            in_item = st.text_input("Название сырья:")
            in_qty = st.number_input("Количество (кг/шт):", min_value=0.0, step=0.1, format="%.3f", key="add_inv_qty")
            in_price = st.number_input("Цена закупа (за 1 кг/шт) в тг:", min_value=0.0, step=50.0, key="add_inv_pr")

            if st.button("📥 Оприходовать сырье", use_container_width=True):
                if in_item and in_qty > 0:
                    execute_query("INSERT INTO inventory (date, item, qty, price, reason) VALUES (?, ?, ?, ?, ?)",
                                  (str(datetime.date.today()), in_item, in_qty, in_price, "Закуп"))
                    st.success(f"Успешно закуплено: {in_item}")
                    st.rerun()

        with inv_col2:
            st.markdown("#### 🗑️ Списание и Брак сырья")
            if not all_inventory_items:
                st.info("На складе еще нет товаров для списания.")
            else:
                waste_item = st.selectbox("Что нужно списать?", all_inventory_items, key="waste_sel")
                waste_qty = st.number_input("Вес/Кол-во для удаления (кг/шт):", min_value=0.001, step=0.1,
                                            format="%.3f")
                waste_reason = st.selectbox("Причина списания:",
                                            ["Порча / Просрочка", "Брак сырья (Сырое)", "Персонал / Проработка"])

                if st.button("🗑️ Списать со склада", type="secondary", use_container_width=True):
                    if waste_qty > 0:
                        execute_query("INSERT INTO inventory (date, item, qty, price, reason) VALUES (?, ?, ?, ?, ?)",
                                      (str(datetime.date.today()), waste_item, -waste_qty, 0.0, waste_reason))
                        st.success(
                            f"Успешно списано {waste_qty:.3f} кг/шт продукта '{waste_item}' по причине: {waste_reason}")
                        st.rerun()

# =========================================================
# 🛠️ ВКЛАДКА №4: УПРАВЛЕНИЕ МЕНЮ, КАТЕГОРИЯМИ И РЕЦЕПТАМИ
# =========================================================
if "Управление меню" in tabs_to_show:
    idx = tabs_to_show.index("Управление меню")
    with active_tabs[idx]:
        st.subheader("Редактор категорий и разделов")
        rows_cats_all = execute_query("SELECT cat_name FROM categories ORDER BY cat_name ASC", fetch="all")
        db_categories_list_all = [r[0] for r in rows_cats_all] if rows_cats_all else []

        cat_edit_col1, cat_edit_col2 = st.columns(2)
        with cat_edit_col1:
            new_cat_name = st.text_input("Название новой категории:")
            if st.button("➕ Создать категорию"):
                if new_cat_name:
                    execute_query("INSERT OR IGNORE INTO categories (cat_name) VALUES (?)", (new_cat_name.upper(),))
                    st.success("Категория добавлена!")
                    st.rerun()
        with cat_edit_col2:
            if db_categories_list_all:
                cat_to_del = st.selectbox("Удалить категорию из базы:", db_categories_list_all)
                if st.button("❌ Удалить категорию"):
                    execute_query("DELETE FROM categories WHERE cat_name = ?", (cat_to_del,))
                    st.rerun()

        st.write("---")

        menu_col1, menu_col2 = st.columns(2)

        with menu_col1:
            st.subheader("Добавление новых блюд в меню")
            with st.form("add_dish_form", clear_on_submit=True):
                new_dish_name = st.text_input("Название нового блюда:")
                new_dish_price = st.number_input("Цена продажи (тг):", min_value=0, step=100)
                if not db_categories_list_all:
                    st.error("Сначала создайте хотя бы одну категорию!")
                    st.form_submit_button("Сохранить блюдо", disabled=True)
                else:
                    new_dish_cat = st.selectbox("Привязать к категории:", db_categories_list_all)
                    if st.form_submit_button("Сохранить блюдо") and new_dish_name:
                        # 👍 Исправлено: чистый кортеж без "price=" и "category=" внутри значений
                        execute_query("INSERT OR IGNORE INTO menu (dish_name, price, category) VALUES (?, ?, ?)",
                                      (new_dish_name, new_dish_price, new_dish_cat))
                        st.success(f"Блюдо '{new_dish_name}' добавлено!")
                        st.rerun()

        with menu_col2:
            st.subheader("Конструктор Рецептов")
            all_dishes_rows = execute_query("SELECT dish_name, price FROM menu", fetch="all")
            list_dishes_for_recipes = [r[0] for r in all_dishes_rows] if all_dishes_rows else []

            if not list_dishes_for_recipes:
                st.info("Создайте блюда слева, чтобы привязать к ним рецепт.")
            else:
                selected_dish_rec = st.selectbox("Выберите блюдо:", list_dishes_for_recipes)
                rec_ing = st.text_input("Ингредиент со склада (напр. 'Говяжий фарш'):", key="ing_field")
                rec_qty = st.number_input("Вес/кол-во на 1 порцию (кг/шт):", min_value=0.001, step=0.01, format="%.3f")

                if st.button("🔗 Добавить ингредиент в рецепт"):
                    if rec_ing and rec_qty > 0:
                        execute_query("INSERT INTO recipes (dish, ingredient, qty_needed) VALUES (?, ?, ?)",
                                      (selected_dish_rec, rec_ing, rec_qty))
                        st.success(f"В рецепт '{selected_dish_rec}' добавлен ингредиент {rec_ing}!")
                        st.rerun()

                st.write(f"**Анализ стоимости для '{selected_dish_rec}':**")

                dish_sale_price = 0
                for r in all_dishes_rows:
                    if r[0] == selected_dish_rec: dish_sale_price = r[1]

                food_cost = calculate_dish_food_cost(selected_dish_rec)
                margin = dish_sale_price - food_cost
                margin_percent = (margin / dish_sale_price * 100) if dish_sale_price > 0 else 0

                fc_col1, fc_col2 = st.columns(2)
                fc_col1.metric("Себестоимость порции:", f"{int(food_cost)} тг.")
                fc_col2.metric("Маржинальность:", f"{int(margin_percent)}%")

                st.write("**Текущий состав блюда:**")
                curr_recipe = execute_query("SELECT ingredient, qty_needed FROM recipes WHERE dish = ?",
                                            (selected_dish_rec,), fetch="all")
                if not curr_recipe:
                    st.caption("Рецепт не задан. Товар списывается поштучно.")
                else:
                    for ing in curr_recipe:
                        st.write(f" - {ing[0]}: {ing[1]:.3f} кг/шт")