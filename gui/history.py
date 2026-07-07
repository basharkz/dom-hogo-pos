import streamlit as st
import datetime
import json
import streamlit.components.v1 as components
from database.connection import execute_query
from utils.printing import trigger_silent_print
import base64


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


# ============ ГЕНЕРАЦИЯ HTML ДЛЯ Z-ОТЧЕТА ============
def generate_z_report_html(z_data):
    """Генерирует HTML для печати Z-отчета"""

    items_html = ""
    if z_data.get("dishes"):
        for dish, qty in z_data["dishes"].items():
            if len(dish) > 20:
                dish = dish[:18] + ".."
            dish_price = z_data.get("dishes_price", {}).get(dish, 0)
            items_html += f"""
                <tr>
                    <td class="item-name">{dish}</td>
                    <td class="item-qty">x{qty}</td>
                    <td class="item-price">{int(dish_price)} тг</td>
                </tr>
            """
    else:
        items_html = """
            <tr>
                <td colspan="3" style="text-align:center; color:#999; padding:3px 0;">Нет продаж</td>
            </tr>
        """

    date_short = z_data.get('date', '').replace('.', '/')

    html = f"""
    <!DOCTYPE html>
    <html>
        <head>
            <meta charset="UTF-8">
            <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
            <title>Z-Отчет</title>
            <style>
                @page {{
                    size: 48mm auto;
                    margin: 2mm 3mm;
                }}

                body {{ 
                    width: 48mm;
                    font-family: 'Courier New', monospace;
                    margin: 0;
                    padding: 0;
                    background: white;
                    font-size: 10px;
                    line-height: 1.2;
                }}

                .header {{
                    text-align: center;
                    font-size: 13px;
                    font-weight: bold;
                    margin: 1px 0;
                }}

                .sub-header {{
                    text-align: center;
                    font-size: 12px;
                    font-weight: bold;
                    margin: 1px 0;
                }}

                .order-number {{
                    text-align: center;
                    font-size: 9px;
                    color: #666;
                    margin: 1px 0;
                }}

                .divider {{
                    border: 0;
                    border-top: 1px dashed #000;
                    margin: 2px 0;
                }}

                .divider-double {{
                    border: 0;
                    border-top: 2px solid #000;
                    margin: 2px 0;
                }}

                table {{ 
                    width: 100%; 
                    border-collapse: collapse;
                    font-size: 9px;
                }}

                td {{ 
                    padding: 1px 0;
                    vertical-align: top;
                }}

                .item-name {{
                    width: 55%;
                    padding-right: 3px;
                    font-size: 9px;
                }}

                .item-qty {{
                    width: 15%;
                    text-align: center;
                    font-size: 9px;
                }}

                .item-price {{
                    width: 30%;
                    text-align: right;
                    font-size: 9px;
                }}

                .total-row {{
                    font-weight: bold;
                    font-size: 11px;
                }}

                .footer {{
                    text-align: center;
                    font-size: 9px;
                    margin: 2px 0;
                }}

                .thank-you {{
                    text-align: center;
                    font-size: 11px;
                    font-weight: bold;
                    margin: 3px 0;
                    color: #2e7d32;
                }}

                .filter-info {{
                    text-align: center;
                    font-size: 8px;
                    color: #888;
                    margin: 1px 0;
                    font-style: italic;
                }}

                .item-name {{
                    word-wrap: break-word;
                    max-width: 28mm;
                }}
            </style>
        </head>
        <body>
            <div class="header">🏮 WoJia</div>
            <div class="header" style="font-size:11px;">HUOGUO</div>
            <div class="sub-header">📋 Z-ОТЧЕТ</div>
            <div class="order-number">{date_short} {datetime.datetime.now().strftime('%H:%M')}</div>
            {f"<div class='filter-info'>📌 {z_data.get('dish_filter', '')}</div>" if z_data.get('dish_filter') and z_data['dish_filter'] != "Все блюда" else ""}

            <hr class="divider">

            <table>
                <thead>
                    <tr style="border-bottom: 1px solid #000;">
                        <td class="item-name"><b>Блюдо</b></td>
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
                <tr>
                    <td colspan="2">💵 Наличные:</td>
                    <td class="item-price">{int(z_data.get('cash', 0))} тг</td>
                </tr>
                <tr>
                    <td colspan="2">💳 Kaspi:</td>
                    <td class="item-price">{int(z_data.get('kaspi', 0))} тг</td>
                </tr>
                <tr class="total-row" style="border-top: 1px solid #000;">
                    <td colspan="2">💰 ИТОГО:</td>
                    <td class="item-price">{int(z_data.get('total', 0))} тг</td>
                </tr>
            </table>

            <hr class="divider-double">

            <div class="thank-you">✅ Смена закрыта!</div>
            <div class="footer">Спасибо! 🙏</div>
        </body>
    </html>
    """
    return html


def render_history_tab():
    st.subheader("📊 Аналитика и Финансовые показатели")
    today_date_str = str(datetime.date.today())
    user_role = st.session_state.get("user_role", "Кассир")

    # ============ БЛОК Z-ОТЧЕТА С ФИЛЬТРАМИ ============
    st.markdown("### 🧾 Z-Отчет")

    col_filter1, col_filter2, col_filter3 = st.columns([2, 2, 1])

    with col_filter1:
        report_date = st.date_input(
            "📅 Выберите дату",
            value=datetime.date.today(),
            key="z_report_date"
        )

    with col_filter2:
        all_dishes = execute_query(
            "SELECT DISTINCT dish FROM sales ORDER BY dish",
            fetch="all"
        )
        dish_options = ["Все блюда"] + [d[0] for d in all_dishes] if all_dishes else ["Все блюда"]

        selected_dish = st.selectbox(
            "🍽️ Фильтр по блюду",
            options=dish_options,
            key="z_report_dish"
        )

    with col_filter3:
        if st.button("🖨️ Сформировать Z-Отчет", type="secondary", use_container_width=True):
            try:
                query = "SELECT dish, qty, total_price, payment_method FROM sales WHERE date = %s"
                params = [report_date.strftime("%Y-%m-%d")]

                if selected_dish != "Все блюда":
                    query += " AND dish = %s"
                    params.append(selected_dish)

                today_sales_rows = execute_query(query, tuple(params), fetch="all")

                z_summary = {
                    "cash": 0.0,
                    "kaspi": 0.0,
                    "total": 0.0,
                    "dishes": {},
                    "dishes_price": {},
                    "date": report_date.strftime("%d.%m.%Y"),
                    "dish_filter": selected_dish
                }

                if today_sales_rows:
                    for r in today_sales_rows:
                        d_name, d_qty, d_total, d_meth = r[0], r[1], r[2], r[3]
                        z_summary["total"] += float(d_total)

                        if d_meth == "Kaspi QR":
                            z_summary["kaspi"] += float(d_total)
                        else:
                            z_summary["cash"] += float(d_total)

                        z_summary["dishes"][d_name] = z_summary["dishes"].get(d_name, 0) + d_qty
                        z_summary["dishes_price"][d_name] = z_summary["dishes_price"].get(d_name, 0) + float(d_total)
                else:
                    st.warning("За выбранный период продаж нет!")
                    st.stop()

                # ✅ ИСПРАВЛЕНИЕ: Сохраняем в сессию и НЕ делаем rerun
                st.session_state.z_report_data = z_summary

            except Exception as e:
                st.error(f"❌ Ошибка при формировании отчета: {e}")

    # ✅ ИСПРАВЛЕНИЕ: Показываем отчет, если данные есть в сессии
    if "z_report_data" in st.session_state and st.session_state.z_report_data:
        z_data = st.session_state.z_report_data

        with st.container():
            st.markdown("---")
            st.markdown(f"### 📋 Z-Отчет за {z_data['date']}")
            if z_data.get('dish_filter') and z_data['dish_filter'] != "Все блюда":
                st.markdown(f"**Фильтр по блюду:** {z_data['dish_filter']}")

            col1, col2, col3 = st.columns(3)
            col1.metric("💰 Общая выручка", f"{int(z_data['total'])} тг.")
            col2.metric("💳 Kaspi QR", f"{int(z_data['kaspi'])} тг.")
            col3.metric("💵 Наличные", f"{int(z_data['cash'])} тг.")

            if z_data.get('dishes'):
                st.markdown("#### 📊 Продажи по блюдам")
                dish_data = []
                for dish, qty in z_data['dishes'].items():
                    dish_total = z_data.get('dishes_price', {}).get(dish, 0)
                    dish_data.append({
                        "Блюдо": dish,
                        "Количество": qty,
                        "Сумма": int(dish_total)
                    })
                st.table(dish_data)

            col_print1, col_print2, col_print3 = st.columns([1, 1, 2])
            with col_print1:
                if st.button("🖨️ Печать Z-Отчета", type="primary"):
                    try:
                        z_html = generate_z_report_html(z_data)
                        print_receipt_universal(z_html)
                        st.success("✅ Z-отчет отправлен на печать!")
                    except Exception as e:
                        st.error(f"❌ Ошибка печати: {e}")

            with col_print2:
                if st.button("❌ Закрыть отчет", type="secondary"):
                    # ✅ ИСПРАВЛЕНИЕ: Просто удаляем данные из сессии
                    del st.session_state.z_report_data
                    st.rerun()

    st.write("---")

    # ============ СТАТИСТИКА ЗА СЕГОДНЯ ============
    rows_sales = execute_query(
        "SELECT date, dish, qty, total_price, receipt_id, discount_percent, payment_method FROM sales ORDER BY id DESC",
        fetch="all"
    )

    if not rows_sales:
        st.info("Продаж пока не было.")
        return

    total_today = total_today_kaspi = total_today_cash = 0.0
    grouped_receipts = {}

    for row in rows_sales:
        date, dish, qty, total_price, r_id, d_percent, pay_meth = row

        if date == today_date_str:
            total_today += float(total_price)
            if pay_meth == "Kaspi QR":
                total_today_kaspi += float(total_price)
            else:
                total_today_cash += float(total_price)

        if r_id not in grouped_receipts:
            grouped_receipts[r_id] = {
                "date": date,
                "items": [],
                "final_sum": 0.0,
                "discount": d_percent,
                "payment_method": pay_meth
            }

        grouped_receipts[r_id]["items"].append({
            "dish": dish,
            "qty": qty,
            "price": float(total_price)
        })
        grouped_receipts[r_id]["final_sum"] += float(total_price)

    t_col1, t_col2, t_col3 = st.columns(3)
    t_col1.metric("Выручка за сегодня:", f"{int(total_today)} тг.")
    t_col2.metric("Kaspi QR:", f"{int(total_today_kaspi)} тг.")
    t_col3.metric("Наличные:", f"{int(total_today_cash)} тг.")

    st.write("---")
    st.markdown("#### 📜 Журнал закрытых чеков")

    # ============ ОТОБРАЖЕНИЕ ЧЕКОВ ============
    for r_id, info in grouped_receipts.items():
        with st.expander(f"🧾 Чек №{r_id} | Дата: {info['date']} | Сумма: {int(info['final_sum'])} тг."):
            for item in info["items"]:
                st.write(f"• {item['dish']} (x{item['qty']}) - {int(item['price'])} тг")

            if info['discount'] > 0:
                st.write(f"💫 Скидка: {info['discount']}%")

            st.write(f"💳 Оплата: {info['payment_method']}")
            st.write("---")

            if user_role == "Администратор":
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button(f"🖨 Печать чека №{r_id}", key=f"print_{r_id}"):
                        sales_data = execute_query(
                            "SELECT dish, qty, total_price FROM sales WHERE receipt_id = %s",
                            (r_id,), fetch="all"
                        )

                        if not sales_data:
                            st.error("Ошибка: Чек пустой!")
                        else:
                            receipt_info = execute_query(
                                "SELECT discount_percent, payment_method FROM sales WHERE receipt_id = %s LIMIT 1",
                                (r_id,), fetch="one"
                            )

                            discount_percent = receipt_info[0] if receipt_info else 0
                            payment_method = receipt_info[1] if receipt_info else "Наличные"

                            items_list = []
                            total = 0
                            for row in sales_data:
                                dish, qty, price = row[0], row[1], float(row[2])
                                items_list.append({
                                    'dish': dish,
                                    'qty': qty,
                                    'price': price
                                })
                                total += price

                            receipt_data = {
                                'receipt_id': r_id,
                                'items': items_list,
                                'total': total,
                                'discount': discount_percent,
                                'payment_method': payment_method,
                                'datetime': datetime.datetime.now().strftime('%d.%m.%Y %H:%M')
                            }

                            receipt_html = generate_receipt_html(receipt_data)
                            print_receipt_universal(receipt_html)

                with btn_col2:
                    if st.button(f"❌ Удалить №{r_id}", key=f"btn_del_{r_id}", type="secondary"):
                        execute_query("DELETE FROM sales WHERE receipt_id = %s", (r_id,))
                        st.success(f"Чек {r_id} удален!")
                        st.rerun()
            else:
                if st.button(f"🖨️ Распечатать №{r_id}", key=f"btn_p_{r_id}"):
                    sales_data = execute_query(
                        "SELECT dish, qty, total_price FROM sales WHERE receipt_id = %s",
                        (r_id,), fetch="all"
                    )

                    if sales_data:
                        items_list = []
                        total = 0
                        for row in sales_data:
                            dish, qty, price = row[0], row[1], float(row[2])
                            items_list.append({
                                'dish': dish,
                                'qty': qty,
                                'price': price
                            })
                            total += price

                        receipt_data = {
                            'receipt_id': r_id,
                            'items': items_list,
                            'total': total,
                            'discount': info.get('discount', 0),
                            'payment_method': info.get('payment_method', 'Наличные'),
                            'datetime': datetime.datetime.now().strftime('%d.%m.%Y %H:%M')
                        }

                        receipt_html = generate_receipt_html(receipt_data)
                        print_receipt_universal(receipt_html)


# ============ ФУНКЦИЯ ГЕНЕРАЦИИ ЧЕКА (для history) ============
def generate_receipt_html(receipt_data):
    """Генерирует HTML для чека 58мм x 210мм (копия функции из kassa_tab)"""
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