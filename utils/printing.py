import streamlit as st
import datetime

def trigger_silent_print(order_name, cart_dict, flat_menu_prices, discount_percent, pay_method, order_id):
    # ... (весь код формирования items_html и discount_html остается прежним)

    # Увеличиваем высоту и добавляем задержку в JS
    receipt_html = f"""
    <html>
    <head>
        <style>@page {{ size: 58mm 210mm; margin: 0mm; }} body {{ font-family: 'Courier New', monospace; width: 200px; margin: 5mm; font-size: 15px; }}</style>
    </head>
    <body>
        <script>
            setTimeout(function() {{ window.print(); }}, 500);
        </script>
    </body>
    </html>
    """
    # Устанавливаем высоту хотя бы 100px, чтобы компонент "существовал"
    st.components.v1.html(receipt_html, height=100, width=200)

def trigger_z_report_print(summary_data):
    # ... (аналогично для Z-отчета)
    z_html = f"""
    <html>
    <head>
        <style>@page {{ size: 58mm 210mm; margin: 0mm; }} body {{ font-family: 'Courier New', monospace; width: 200px; margin: 5mm; font-size: 14px; }}</style>
    </head>
    <body>
        <script>
            setTimeout(function() {{ window.print(); }}, 500);
        </script>
    </body>
    </html>
    """
    st.components.v1.html(z_html, height=100, width=200)