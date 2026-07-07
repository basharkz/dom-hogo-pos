import streamlit as st
import datetime
import json
import streamlit.components.v1 as components
from database.connection import execute_query
import base64
import time

# 🔥 ВАЖНО: Устанавливаем кодировку для всего файла
import sys
import io
if sys.stdout.encoding != 'UTF-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ============ УНИВЕРСАЛЬНАЯ ФУНКЦИЯ ПЕЧАТИ ============
def print_receipt_universal(html_content):
    """
    Универсальная функция печати для всех браузеров
    """
    import base64

    # 🔥 ВАЖНО: Кодируем с правильной кодировкой UTF-8
    html_bytes = html_content.encode('utf-8')
    b64_html = base64.b64encode(html_bytes).decode('utf-8')

    print_script = f"""
    <script>
    (function() {{
        console.log('🖨️ Запуск печати...');

        // 🔥 Декодируем из base64
        var htmlContent = atob('{b64_html}');

        // 🔥 СОЗДАЕМ НОВОЕ ОКНО
        var w = window.open('', '_blank', 'width=400,height=600,menubar=no,toolbar=no,location=no,status=no,scrollbars=yes');
        if (!w) {{
            alert('Пожалуйста, разрешите всплывающие окна для печати!');
            return;
        }}

        // 🔥 ЗАПИСЫВАЕМ HTML С ПРАВИЛЬНОЙ КОДИРОВКОЙ
        w.document.write(htmlContent);
        w.document.close();

        // 🔥 ЖДЕМ ЗАГРУЗКИ И ПЕЧАТАЕМ
        setTimeout(function() {{
            w.focus();
            w.print();
            setTimeout(function() {{
                try {{ w.close(); }} catch(e) {{}}
            }}, 3000);
        }}, 1000);
    }})();
    </script>
    """
    components.html(print_script, height=0)


# ============ ГЕНЕРАЦИЯ ЧЕКА (С ПРАВИЛЬНОЙ КОДИРОВКОЙ) ============
def generate_receipt_html(receipt_data):
    r_id = receipt_data.get('receipt_id', '')
    items = receipt_data.get('items', [])
    total = receipt_data.get('total', 0)
    discount_percent = receipt_data.get('discount', 0)
    payment_method = receipt_data.get('payment_method', 'Наличные')
    date_time = receipt_data.get('datetime', datetime.datetime.now().strftime('%d.%m.%Y %H:%M'))

    items_html = ""
    for item in items:
        dish = str(item.get('dish', ''))
        # 🔥 Экранируем для HTML
        dish = dish.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'",
                                                                                                                   '&#39;')
        qty = item.get('qty', 1)
        price = item.get('price', 0)

        items_html += f"""
            <tr>
                <td class="item-name">{dish}</td>
                <td class="item-qty">x{qty}</td>
                <td class="item-price">{int(price)} тг</td>
            </tr>
        """

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

    return f"""<!DOCTYPE html>
<html>
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
        <meta http-equiv="Content-Language" content="ru">
        <title>Чек #{r_id}</title>
        <style>
            @page {{ size: 48mm auto; margin: 2mm 3mm; }}
            body {{ 
                width: 48mm; 
                font-family: 'Courier New', 'Lucida Console', 'Monaco', monospace; 
                margin: 0; 
                padding: 0; 
                font-size: 11px;
            }}
            .header {{ text-align: center; font-size: 14px; font-weight: bold; }}
            .sub-header {{ text-align: center; font-size: 11px; }}
            .order-number {{ text-align: center; font-size: 10px; color: #666; }}
            .divider {{ border: 0; border-top: 1px dashed #000; margin: 3px 0; }}
            .divider-double {{ border: 0; border-top: 2px solid #000; margin: 3px 0; }}
            table {{ width: 100%; border-collapse: collapse; font-size: 10px; }}
            td {{ padding: 1px 0; }}
            .item-name {{ width: 55%; }}
            .item-qty {{ width: 15%; text-align: center; }}
            .item-price {{ width: 30%; text-align: right; }}
            .total-row {{ font-weight: bold; font-size: 12px; }}
            .discount-row {{ font-size: 10px; color: #666; }}
            .footer {{ text-align: center; font-size: 10px; margin: 3px 0; }}
            .thank-you {{ text-align: center; font-size: 12px; font-weight: bold; margin: 5px 0; }}
        </style>
    </head>
    <body>
        <div class="header">🏮 WoJia HUOGUO</div>
        <div class="sub-header">{date_time}</div>
        <div class="order-number">Чек #{r_id}</div>
        <hr class="divider">
        <table>
            <tr style="border-bottom: 1px solid #000;">
                <td class="item-name"><b>Наименование</b></td>
                <td class="item-qty"><b>Кол</b></td>
                <td class="item-price"><b>Сумма</b></td>
            </tr>
            {items_html}
        </table>
        <hr class="divider">
        <table>
            <tr class="total-row"><td colspan="2">ИТОГО:</td><td class="item-price">{int(total)} тг</td></tr>
            {discount_html}
            <tr class="total-row" style="border-top:1px solid #000; font-size:14px;">
                <td colspan="2">К ОПЛАТЕ:</td>
                <td class="item-price">{int(final_total)} тг</td>
            </tr>
        </table>
        <hr class="divider-double">
        <div class="thank-you">Спасибо! 🙏</div>
        <div class="footer">Приятного аппетита!</div>
        <div class="footer" style="font-size:9px; color:#999; margin-top:2px;">
            {payment_method} • {datetime.datetime.now().strftime('%H:%M')}
        </div>
    </body>
</html>"""


# ============ ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ УНИКАЛЬНОГО НОМЕРА ЧЕКА ============
def get_unique_receipt_number():
    """Генерирует уникальный номер чека на основе истории продаж"""
    today = datetime.date.today()
    today_str = today.strftime("%y%m%d")

    try:
        max_row = execute_query(
            "SELECT MAX(receipt_id) FROM sales WHERE receipt_id LIKE %s",
            (f"{today_str}%",),
            fetch="one"
        )

        if max_row and max_row[0]:
            try:
                last_num = int(str(max_row[0])[-4:]) + 1
            except:
                last_num = 1
        else:
            last_num = 1

    except Exception as e:
        print(f"Ошибка получения MAX ID: {e}")
        last_num = 1

    new_id = f"{today_str}{last_num:04d}"

    try:
        check = execute_query(
            "SELECT order_id FROM active_orders WHERE order_id = %s",
            (new_id,),
            fetch="one"
        )
        while check and check[0]:
            last_num += 1
            new_id = f"{today_str}{last_num:04d}"
            check = execute_query(
                "SELECT order_id FROM active_orders WHERE order_id = %s",
                (new_id,),
                fetch="one"
            )
    except:
        pass

    return new_id


# ============ ГЛАВНАЯ ФУНКЦИЯ КАССЫ ============
def render_kassa_tab():
    st.subheader("🏪 Касса")

    if "current_active_order_id" not in st.session_state:
        st.session_state.current_active_order_id = None

    try:
        execute_query("""
            CREATE TABLE IF NOT EXISTS active_orders (
                order_id TEXT PRIMARY KEY,
                order_name TEXT NOT NULL,
                cart_json TEXT NOT NULL,
                discount_percent REAL DEFAULT 0.0
            )
        """)
    except Exception as e:
        st.error(f"❌ Ошибка создания таблицы: {e}")

    col_left, col_right = st.columns([0.6, 0.4])

    try:
        menu_rows = execute_query("SELECT dish_name, price, category FROM menu", fetch="all")
        menu = {}
        if menu_rows:
            for row in menu_rows:
                name, price, cat = row[0], row[1], row[2]
                if cat not in menu:
                    menu[cat] = {}
                menu[cat][name] = price
    except Exception as e:
        st.error(f"❌ Ошибка загрузки меню: {e}")
        menu = {}

    try:
        orders_rows = execute_query(
            "SELECT order_id, order_name, cart_json, discount_percent FROM active_orders ORDER BY order_id",
            fetch="all"
        )
        active_orders = []
        if orders_rows:
            for row in orders_rows:
                try:
                    cart = json.loads(row[2]) if row[2] else []
                    active_orders.append({
                        "id": row[0],
                        "name": row[1],
                        "cart": cart,
                        "discount": float(row[3]) if row[3] else 0.0
                    })
                except Exception as e:
                    print(f"Ошибка парсинга: {e}")
    except Exception as e:
        st.error(f"❌ Ошибка загрузки заказов: {e}")
        active_orders = []

    with col_left:
        st.subheader("📋 Активные чеки")

        st.write(f"📌 Текущий ID в сессии: {st.session_state.current_active_order_id}")
        st.write(f"📌 Активных заказов в БД: {len(active_orders)}")

        if st.button("🆕 Открыть Новый Чек", type="primary", use_container_width=True):
            try:
                new_id = get_unique_receipt_number()

                st.info(f"🔄 Создается чек №{new_id}...")

                execute_query(
                    "INSERT INTO active_orders (order_id, order_name, cart_json, discount_percent) VALUES (%s, %s, %s, %s)",
                    (new_id, f"Чек №{new_id}", json.dumps([]), 0.0)
                )

                check = execute_query(
                    "SELECT order_id FROM active_orders WHERE order_id = %s",
                    (new_id,),
                    fetch="one"
                )

                if check and check[0]:
                    st.session_state.current_active_order_id = new_id
                    st.success(f"✅ Чек №{new_id} открыт!")
                    st.rerun()
                else:
                    st.error("❌ Чек не сохранился в БД!")

            except Exception as e:
                st.error(f"❌ Ошибка: {e}")
                import traceback
                st.code(traceback.format_exc())

        st.write("---")

        if active_orders:
            cols = st.columns(3)
            for idx, order in enumerate(active_orders):
                with cols[idx % 3]:
                    if st.button(f"🧾 {order['name']}", key=f"sel_{order['id']}", use_container_width=True):
                        st.session_state.current_active_order_id = order['id']
                        st.rerun()
        else:
            st.info("📭 Нет активных чеков")

        st.write("---")

        if menu:
            tabs = st.tabs(list(menu.keys()))
            for i, (cat, dishes) in enumerate(menu.items()):
                with tabs[i]:
                    for dish, price in dishes.items():
                        if st.button(f"{dish} ({int(price)} тг)", key=f"add_{dish}_{i}"):
                            if st.session_state.current_active_order_id:
                                order_row = execute_query(
                                    "SELECT cart_json, discount_percent FROM active_orders WHERE order_id = %s",
                                    (st.session_state.current_active_order_id,),
                                    fetch="one"
                                )
                                if order_row:
                                    try:
                                        cart = json.loads(order_row[0]) if order_row[0] else []
                                        discount = float(order_row[1]) if order_row[1] else 0.0

                                        found = False
                                        for item in cart:
                                            if item["name"] == dish:
                                                item["qty"] += 1
                                                found = True
                                                break
                                        if not found:
                                            cart.append({"name": dish, "price": price, "qty": 1})

                                        execute_query(
                                            "UPDATE active_orders SET cart_json = %s, discount_percent = %s WHERE order_id = %s",
                                            (json.dumps(cart), discount, st.session_state.current_active_order_id)
                                        )
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Ошибка: {e}")
                            else:
                                st.warning("⚠️ Сначала откройте чек!")

    with col_right:
        st.subheader("🧾 Текущий чек")

        if st.session_state.current_active_order_id:
            order_row = execute_query(
                "SELECT order_name, cart_json, discount_percent FROM active_orders WHERE order_id = %s",
                (st.session_state.current_active_order_id,),
                fetch="one"
            )

            if order_row:
                try:
                    order_name = order_row[0]
                    cart = json.loads(order_row[1]) if order_row[1] else []
                    discount = float(order_row[2]) if order_row[2] else 0.0

                    st.success(f"✅ Чек: {order_name}")

                    total = sum(item["price"] * item["qty"] for item in cart)

                    if not cart:
                        st.info("📭 Чек пуст")
                    else:
                        for item in list(cart):
                            c1, c2, c3 = st.columns([0.5, 0.3, 0.2])
                            c1.write(f"**{item['name']}**")
                            c2.write(f"{int(item['price'])} x {item['qty']}")
                            if c3.button("❌", key=f"del_{item['name']}_{st.session_state.current_active_order_id}"):
                                item["qty"] -= 1
                                if item["qty"] <= 0:
                                    cart.remove(item)
                                execute_query(
                                    "UPDATE active_orders SET cart_json = %s WHERE order_id = %s",
                                    (json.dumps(cart), st.session_state.current_active_order_id)
                                )
                                st.rerun()

                    st.write("---")

                    disc = st.number_input("Скидка %", min_value=0.0, max_value=100.0,
                                           value=discount, step=5.0)
                    if disc != discount:
                        execute_query(
                            "UPDATE active_orders SET discount_percent = %s WHERE order_id = %s",
                            (disc, st.session_state.current_active_order_id)
                        )
                        st.rerun()

                    final_total = total * (1 - disc / 100)
                    st.metric("💳 К оплате", f"{int(final_total)} тг")
                    pay_method = st.radio("Оплата:", ["Наличные", "Kaspi QR"])

                    if st.button("✅ Оплатить и закрыть", type="primary", use_container_width=True):
                        if not cart:
                            st.error("❌ Чек пуст!")
                        else:
                            try:
                                today = str(datetime.date.today())
                                for item in cart:
                                    execute_query(
                                        "INSERT INTO sales (date, dish, qty, total_price, receipt_id, discount_percent, payment_method) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                                        (today, item["name"], item["qty"], item["price"] * item["qty"],
                                         st.session_state.current_active_order_id, disc, pay_method)
                                    )

                                items_list = [
                                    {"dish": item["name"], "qty": item["qty"], "price": item["price"] * item["qty"]} for
                                    item in cart]
                                receipt_data = {
                                    "receipt_id": st.session_state.current_active_order_id,
                                    "items": items_list,
                                    "total": total,
                                    "discount": disc,
                                    "payment_method": pay_method,
                                    "datetime": datetime.datetime.now().strftime('%d.%m.%Y %H:%M')
                                }
                                receipt_html = generate_receipt_html(receipt_data)
                                print_receipt_universal(receipt_html)

                                execute_query("DELETE FROM active_orders WHERE order_id = %s",
                                              (st.session_state.current_active_order_id,))
                                st.session_state.current_active_order_id = None
                                st.success("✅ Заказ оплачен!")
                                st.rerun()

                            except Exception as e:
                                st.error(f"❌ Ошибка: {e}")
                                import traceback
                                st.code(traceback.format_exc())
                except Exception as e:
                    st.error(f"❌ Ошибка загрузки: {e}")
                    st.session_state.current_active_order_id = None
                    st.rerun()
            else:
                st.warning("Чек не найден в БД")
                st.session_state.current_active_order_id = None
                st.rerun()
        else:
            st.info("👈 Выберите или создайте чек")