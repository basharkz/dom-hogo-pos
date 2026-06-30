import sqlite3
import streamlit as st
from config import DB_NAME


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (date TEXT, item TEXT, qty REAL, price REAL, reason TEXT)''')
    cursor.execute(
        '''CREATE TABLE IF NOT EXISTS sales (date TEXT, dish TEXT, qty INTEGER, total_price REAL, receipt_id TEXT, discount_percent REAL, payment_method TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS menu (dish_name TEXT UNIQUE, price REAL, category TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS recipes (dish TEXT, ingredient TEXT, qty_needed REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS categories (cat_name TEXT UNIQUE)''')
    cursor.execute(
        '''CREATE TABLE IF NOT EXISTS active_orders (order_id TEXT UNIQUE, order_name TEXT, cart_json TEXT, discount_percent REAL)''')

    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        base_cats = [("ХОГО",), ("ПИЦЦА",), ("СОУСЫ",), ("НАПИТКИ",)]
        cursor.executemany("INSERT OR IGNORE INTO categories (cat_name) VALUES (?)", base_cats)
        conn.commit()

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


def execute_query(query, data=None, fetch="none"):
    conn = sqlite3.connect(DB_NAME)
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