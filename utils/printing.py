import streamlit as st
import datetime

def trigger_silent_print(order_name, cart_dict, flat_menu_prices, discount_percent, pay_method, order_id):
    total_raw = 0
    items_html = ""
    for dish, qty in cart_dict.items():
        price = flat_menu_prices.get(dish, 0)
        item_total = price * qty
        total_raw += item_total
        items_html += f'<tr class="item-row"><td>{dish} <br><small>x{qty}</small></td><td style="text-align: right; vertical-align: bottom;">{int(item_total)} ₸</td></tr>'

    discount_html = ""
    if discount_percent > 0:
        disc_amount = total_raw * (discount_percent / 100.0)
        final_sum = total_raw - disc_amount
        discount_html = f'<tr class="total-row"><td><b>Скидка {int(discount_percent)}%:</b></td><td style="text-align: right;">-{int(disc_amount)} ₸</td></tr>'
    else:
        final_sum = total_raw

    receipt_html = f"""
    <html><head><style>@page {{ size: 58mm 210mm; margin: 0mm; }} body {{ font-family: 'Courier New', monospace; width: 200px; margin: 5mm; font-size: 15px; line-height: 1.3; color: #000; }} .center {{ text-align: center; }} .header-title {{ font-size: 18px; font-weight: bold; margin: 5px 0; }} table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }} .item-row td {{ padding: 8px 0; border-bottom: 1px dashed #000; }} .total-row td {{ padding: 6px 0; }} .final-price {{ font-size: 18px; }} hr.main-del {{ border-top: 2px solid #000; border-bottom: 0; margin: 8px 0; }}</style></head>
    <body onload="window.print();"><div class="center"><div class="header-title">WoJia HUOGUO</div><p>Заказ: {order_name}<br>Чек №: {order_id}<br>Дата: {datetime.date.today()}</p></div><hr class="main-del"><table>{items_html}{discount_html}<tr class="total-row final-price"><td><b>ИТОГО:</b></td><td style="text-align: right;"><b>{int(final_sum)} ₸</b></td></tr></table><hr class="main-del"><div class="center" style="margin-top: 10px;"><p>Тип оплаты: {pay_method}<br><br><b>Спасибо за заказ!</b></p></div></body></html>
    """
    st.components.v1.html(receipt_html, height=0, width=0)

def trigger_z_report_print(summary_data):
    today_str = str(datetime.date.today())
    dishes_html = "".join([f'<tr class="item-row"><td>{d}</td><td style="text-align: right;">x{q}</td></tr>' for d, q in summary_data["dishes"].items()])
    z_html = f"""
    <html><head><style>@page {{ size: 58mm 210mm; margin: 0mm; }} body {{ font-family: 'Courier New', monospace; width: 200px; margin: 5mm; font-size: 14px; color: #000; }} .center {{ text-align: center; }} .bold-title {{ font-size: 16px; font-weight: bold; margin: 10px 0; }} table {{ width: 100%; border-collapse: collapse; }} .item-row td {{ padding: 4px 0; border-bottom: 1px dotted #000; }} hr {{ border-top: 2px dashed #000; margin: 10px 0; }}</style></head>
    <body onload="window.print();"><div class="center"><div class="bold-title">💥 Z - ОТЧЕТ 💥</div><p>Ресторан: WoJia HUOGUO<br>Дата: {today_str}</p></div><hr><p><b>ФИНАНСЫ:</b></p><p>💵 Наличные: {int(summary_data["cash"])} ₸</p><p>📱 Kaspi QR: {int(summary_data["kaspi"])} ₸</p><p style="font-size: 16px;"><b>ОБЩАЯ ВЫРУЧКА: {int(summary_data["total"])} ₸</b></p><hr><p><b>ПРОДАНО БЛЮД:</b></p><table>{dishes_html}</table><hr><div class="center"><p>Смена закрыта успешно!<br>VOXYS Intelligence</p></div></body></html>
    """
    st.components.v1.html(z_html, height=0, width=0)