import psycopg2
import os
import streamlit as st

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (date TEXT, item TEXT, qty REAL, price REAL, reason TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS sales (
        id SERIAL PRIMARY KEY, 
        date TEXT, dish TEXT, qty INTEGER, total_price REAL, 
        receipt_id TEXT, discount_percent REAL, payment_method TEXT
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS menu (dish_name TEXT UNIQUE, price REAL, category TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS recipes (dish TEXT, ingredient TEXT, qty_needed REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS categories (cat_name TEXT UNIQUE)''')
    cursor.execute(
        '''CREATE TABLE IF NOT EXISTS active_orders (order_id TEXT UNIQUE, order_name TEXT, cart_json TEXT, discount_percent REAL)''')

    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        base_cats = [("ХОГО",), ("ПИЦЦА",), ("СОУСЫ",), ("НАПИТКИ",)]
        for cat in base_cats:
            cursor.execute("INSERT INTO categories (cat_name) VALUES (%s) ON CONFLICT DO NOTHING", cat)

    cursor.execute("SELECT COUNT(*) FROM menu")
    if cursor.fetchone()[0] == 0:
        base_menu = [("Красная Тарелка ХОГО", 1950, "ХОГО"), ("Пицца Маргарита", 3000, "ПИЦЦА")]
        for item in base_menu:
            cursor.execute("INSERT INTO menu (dish_name, price, category) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                           item)

    conn.commit()
    conn.close()


def execute_query(query, data=None, fetch="none"):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = query.replace("?", "%s")
        if data:
            cursor.execute(query, data)
        else:
            cursor.execute(query)
        result = None
        if fetch == "all":
            result = cursor.fetchall()
        elif fetch == "one":
            result = cursor.fetchone()
        conn.commit()
        return result
    except Exception as e:
        st.error(f"Ошибка БД: {e}")
        return None
    finally:
        conn.close()