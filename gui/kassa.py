import streamlit as st
import datetime
import json
import streamlit.components.v1 as components
from database.connection import execute_query
from database.orders import db_get_active_orders, db_get_order_by_id, db_update_order
import base64
import time


# ============ УНИВЕРСАЛЬНАЯ ФУНКЦИЯ ПЕЧАТИ ============
def print_receipt_universal(html_content):
    """
    Универсальная функция печати для всех браузеров (Edge, Firefox, Chrome)
    """
    html_bytes = html_content.encode('utf-8')
    b64_html = base64.b64encode(html_bytes).decode('utf-8')

    print_script = f"""
    <script>
    (function() {{
        console.log('🖨️ Starting print process...');

        var userAgent = navigator.userAgent;
        var isEdge = userAgent.indexOf("Edg") > -1;
        var isFirefox = userAgent.indexOf("Firefox") > -1;

        var htmlContent = atob('{b64_html}');

        function printWithWindow() {{
            try {{
                console.log('🖨️ Trying window method...');
                var w = window.open('', '_blank', 'width=400,height=600,menubar=no,toolbar=no,location=no,status=no,scrollbars=yes');
                if (!w) {{
                    console.error('❌ Window blocked!');
                    alert('Пожалуйста, разрешите всплывающие окна для печати!');
                    return false;
                }}
                w.document.write(htmlContent);
                w.document.close();
                setTimeout(function() {{
                    w.focus();
                    w.print();
                    setTimeout(function() {{
                        w.close();
                    }}, 2000);
                }}, 500);
                return true;
            }} catch(e) {{
                console.error('❌ Window print error:', e);
                return false;
            }}
        }}

        function printWithIframe() {{
            try {{
                console.log('🖨️ Trying iframe method...');
                var iframe = document.createElement('iframe');
                iframe.style.position = 'fixed';
                iframe.style.right = '0';
                iframe.style.bottom = '0';
                iframe.style.width = '0';
                iframe.style.height = '0';
                iframe.style.border = 'none';
                iframe.style.visibility = 'hidden';
                document.body.appendChild(iframe);

                var iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                iframeDoc.open();
                iframeDoc.write(htmlContent);
                iframeDoc.close();

                setTimeout(function() {{
                    iframe.contentWindow.focus();
                    iframe.contentWindow.print();
                    setTimeout(function() {{
                        document.body.removeChild(iframe);
                    }}, 2000);
                }}, 500);
                return true;
            }} catch(e) {{
                console.error('❌ Iframe print error:', e);
                return false;
            }}
        }}

        var printed = false;

        if (isEdge) {{
            console.log('🖨️ Edge detected');
            printed = printWithIframe();
            if (!printed) printed = printWithWindow();
        }} else if (isFirefox) {{
            console.log('🖨️ Firefox detected');
            printed = printWithWindow();
            if (!printed) printed = printWithIframe();
        }} else {{
            console.log('🖨️ Other browser detected');
            printed = printWithWindow();
            if (!printed) printed = printWithIframe();
        }}

        if (!printed) {{
            console.error('❌ All print methods failed!');
            alert('Не удалось открыть окно печати. Проверьте настройки браузера.');
        }}
    }})();
    </script>
    """
    components.html(print_script, height=0)


# ============ ФУНКЦИЯ ГЕНЕРАЦИИ ЧЕКА ============
def generate_receipt_html(receipt_data):
    r_id = receipt_data.get('receipt_id', '')
    items = receipt_data.get('items', [])
    total = receipt_data.get('total', 0)
    discount_percent = receipt_data.get('discount', 0)
    payment_method = receipt_data.get('payment_method', 'Наличные')
    date_time = receipt_data.get('datetime', datetime.datetime.now().strftime('%d.%m.%Y %H:%M'))

    items_html = ""
    for item in items:
        dish = item.get('dish', '')
        qty = item.get('qty', 1)
        price = item.get('price', 0)

        if len(dish) > 25:
            dish = dish[:23] + ".."

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

    html = f"""
    <!DOCTYPE html>
    <html>
        <head>
            <meta charset="UTF-8">
            <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
            <title>Чек #{r_id}</title>
            <style>
                @page {{
                    size: 48mm auto;
                    margin: 2mm 3mm;
                }}

                body {{ 
                    width: 48mm;
                    font-family: 'Courier New', 'Lucida Console', monospace;
                    margin: 0;
                    padding: 0;
                    background: white;
                    font-size: 11px;
                    line-height: 1.3;
                }}

                .header {{
                    text-align: center;
                    font-size: 14px;
                    font-weight: bold;
                    margin: 2px 0;
                    padding: 0;
                }}

                .sub-header {{
                    text-align: center;
                    font-size: 11px;
                    margin: 1px 0;
                    padding: 0;
                }}

                .order-number {{
                    text-align: center;
                    font-size: 10px;
                    color: #666;
                    margin: 1px 0;
                }}

                .divider {{
                    border: 0;
                    border-top: 1px dashed #000;
                    margin: 3px 0;
                }}

                .divider-double {{
                    border: 0;
                    border-top: 2px solid #000;
                    margin: 3px 0;
                }}

                table {{ 
                    width: 100%; 
                    border-collapse: collapse;
                    font-size: 10px;
                }}

                td {{ 
                    padding: 1px 0;
                    vertical-align: top;
                }}

                .item-name {{
                    width: 55%;
                    padding-right: 3px;
                    font-size: 10px;
                }}

                .item-qty {{
                    width: 15%;
                    text-align: center;
                    font-size: 10px;
                }}

                .item-price {{
                    width: 30%;
                    text-align: right;
                    font-size: 10px;
                }}

                .total-row {{
                    font-weight: bold;
                    font-size: 12px;
                }}

                .discount-row {{
                    font-size: 10px;
                    color: #666;
                }}

                .footer {{
                    text-align: center;
                    font-size: 10px;
                    margin: 3px 0;
                    padding: 0;
                }}

                .thank-you {{
                    text-align: center;
                    font-size: 12px;
                    font-weight: bold;
                    margin: 5px 0;
                    padding: 0;
                }}

                .item-name {{
                    word-wrap: break-word;
                    max-width: 30mm;
                }}
            </style>
        </head>
        <body>
            <div class="header">🏮 WoJia</div>
            <div class="header" style="font-size:12px;">HUOGUO</div>
            <div class="sub-header">{date_time}</div>
            <div class="order-number">Чек #{r_id}</div>

            <hr class="divider">

            <table>
                <thead>
                    <tr style="border-bottom: 1px solid #000;">
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
                <tr class="total-row" style="font-size:14px; border-top: 1px solid #000;">
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
    </html>
    """
    return html


# ============ УПРОЩЕННАЯ ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ НОМЕРА ЧЕКА ============
def get_unique_receipt_number():
    """Генерирует уникальный номер чека используя timestamp"""
    today = datetime.date.today()
    today_str = today.strftime("%y%m%d")

    # Используем время в миллисекундах
    timestamp = int(time.time() * 1000) % 10000
    new_id = int(f"{today_str}{timestamp:04d}")

    # Проверяем в активных заказах
    try:
        check = execute_query(
            "SELECT order_id FROM active_orders WHERE order_id = %s",
            (new_id,),
            fetch="one"
        )

        # Если занято, добавляем случайное число
        import random
        while check and check[0] is not None:
            new_id = int(f"{today_str}{random.randint(1, 9999):04d}")
            check = execute_query(
                "SELECT order_id FROM active_orders WHERE order_id = %s",
                (new_id,),
                fetch="one"
            )
    except Exception as e:
        print(f"Error in get_unique_receipt_number: {e}")
        # Если ошибка, просто генерируем на основе времени
        new_id = int(f"{today_str}{int(time.time()) % 10000:04d}")

    return new_id


# ============ ОСНОВНАЯ ФУНКЦИЯ КАССЫ ============
def render_kassa_tab():
    st.subheader("🏪 Касса")

    # ИНИЦИАЛИЗАЦИЯ СЕССИИ
    if "current_active_order_id" not in st.session_state:
        st.session_state.current_active_order_id = None

    kassa_col1, kassa_col2 = st.columns([0.6, 0.4])

    # Загрузка меню из базы
    try:
        rows_menu = execute_query("SELECT dish_name, price, category FROM menu", fetch="all")
        DB_MENU_STRUCT = {}
        if rows_menu:
            for row in rows_menu:
                name, price, cat = row[0], row[1], row[2]
                if cat not in DB_MENU_STRUCT:
                    DB_MENU_STRUCT[cat] = {}
                DB_MENU_STRUCT[cat][name] = price
    except Exception as e:
        st.error(f"❌ Ошибка загрузки меню: {e}")
        DB_MENU_STRUCT = {}

    # Получаем активные заказы
    try:
        active_orders = db_get_active_orders()
        if active_orders is None:
            active_orders = []
    except Exception as e:
        st.error(f"❌ Ошибка загрузки заказов: {e}")
        active_orders = []

    with kassa_col1:
        st.subheader("📋 Активные чеки")

        if "debug_msg" not in st.session_state:
            st.session_state.debug_msg = ""

        if st.button("🆕 Открыть Новый Чек", type="primary", use_container_width=True):
            st.session_state.debug_msg = "Кнопка нажата, идем в БД..."
            try:
                new_id = int(datetime.datetime.now().strftime("%y%m%d%H%M%S"))

                # Вставка
                execute_query(
                    "INSERT INTO active_orders (order_id, order_name, cart_json, discount_percent) VALUES (%s, %s, %s, %s)",
                    (new_id, f"Чек №{new_id}", json.dumps([]), 0.0)
                )

                st.session_state.debug_msg = "Запись в БД успешна!"
                st.session_state.current_active_order_id = new_id
                st.rerun()  # Теперь после перезагрузки мы увидим результат

            except Exception as e:
                st.session_state.debug_msg = f"ОШИБКА: {e}"

            # Отображаем сообщение, если оно есть
        if st.session_state.debug_msg:
            st.info(st.session_state.debug_msg)
            # Чтобы сообщение исчезло после прочтения:
            if st.button("Очистить лог"):
                st.session_state.debug_msg = ""
                st.rerun()

        st.write("---")

        # Отображаем активные чеки
        if active_orders:
            st.write(f"📋 Найдено {len(active_orders)} активных чеков")
            cols = st.columns(3)
            for idx, order in enumerate(active_orders):
                with cols[idx % 3]:
                    if st.button(f"🧾 {order['name']}", key=f"sel_ord_{order['id']}", use_container_width=True):
                        st.session_state.current_active_order_id = order['id']
                        st.rerun()
        else:
            st.info("📭 Нет активных чеков")

        st.write("---")

        # Меню
        if DB_MENU_STRUCT:
            tabs = st.tabs(list(DB_MENU_STRUCT.keys()))
            for i, (cat, dishes) in enumerate(DB_MENU_STRUCT.items()):
                with tabs[i]:
                    for dish, price in dishes.items():
                        if st.button(f"{dish} ({int(price)} тг)", key=f"add_{dish}_{i}"):
                            if st.session_state.current_active_order_id:
                                try:
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
                                except Exception as e:
                                    st.error(f"❌ Ошибка добавления: {e}")
                            else:
                                st.warning("⚠️ Сначала откройте новый чек!")

    with kassa_col2:
        st.subheader("🧾 Текущий чек")

        if st.session_state.current_active_order_id:
            st.write(f"📌 ID текущего чека: {st.session_state.current_active_order_id}")

            try:
                order = db_get_order_by_id(st.session_state.current_active_order_id)
            except Exception as e:
                st.error(f"❌ Ошибка загрузки заказа: {e}")
                order = None

            if order:
                st.success(f"✅ Выбран: **{order['name']}**")

                total = sum(item["price"] * item["qty"] for item in order["cart"])

                if not order["cart"]:
                    st.info("📭 Чек пуст. Добавьте блюда из меню слева.")
                else:
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
                st.metric("💳 К оплате", f"{int(final_total)} тг")
                pay_method = st.radio("Метод оплаты:", ["Наличные", "Kaspi QR"])

                if st.button("✅ Оплатить и закрыть", type="primary", use_container_width=True):
                    if not order["cart"]:
                        st.error("❌ Чек пуст! Добавьте блюда.")
                    else:
                        try:
                            today = str(datetime.date.today())
                            receipt_id = order["id"]
                            discount_percent = disc
                            payment_method = pay_method

                            # Подготавливаем данные для чека
                            items_list = []
                            for item in order["cart"]:
                                items_list.append({
                                    'dish': item['name'],
                                    'qty': item['qty'],
                                    'price': item['price'] * item['qty']
                                })

                            receipt_data = {
                                'receipt_id': receipt_id,
                                'items': items_list,
                                'total': total,
                                'discount': discount_percent,
                                'payment_method': payment_method,
                                'datetime': datetime.datetime.now().strftime('%d.%m.%Y %H:%M')
                            }

                            # Генерируем и печатаем чек
                            receipt_html = generate_receipt_html(receipt_data)
                            print_receipt_universal(receipt_html)

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
                            st.success("✅ Заказ оплачен!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Ошибка при оплате: {e}")
                            import traceback
                            st.error(traceback.format_exc())
            else:
                st.session_state.current_active_order_id = None
                st.rerun()
        else:
            st.info("👈 Выберите или создайте заказ слева")