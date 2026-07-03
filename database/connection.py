import psycopg2
import os

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def execute_query(query, params=(), fetch=None):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(query, params)
        if fetch == "all":
            result = cur.fetchall()
        elif fetch == "one":
            result = cur.fetchone()
        else:
            conn.commit()  # Обязательно для сохранения данных
            result = None
        return result
    except Exception as e:
        print(f"Ошибка БД: {e}")
        return None
    finally:
        cur.close()
        conn.close()

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (date TEXT, item TEXT, qty REAL, price REAL, reason TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS sales (
            id SERIAL PRIMARY KEY, 
            date TEXT, dish TEXT, qty INTEGER, total_price REAL, 
            receipt_id TEXT, discount_percent REAL, payment_method TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS menu (dish_name TEXT UNIQUE, price REAL, category TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS recipes (dish TEXT, ingredient TEXT, qty_needed REAL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS categories (cat_name TEXT UNIQUE)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS active_orders (order_id TEXT UNIQUE, order_name TEXT, cart_json TEXT, discount_percent REAL)''')

        cursor.execute("SELECT COUNT(*) FROM categories")
        if cursor.fetchone()[0] == 0:
            base_cats = [("ХОГО",), ("ПИЦЦА",), ("СОУСЫ",), ("НАПИТКИ",)]
            for cat in base_cats:
                cursor.execute("INSERT INTO categories (cat_name) VALUES (%s) ON CONFLICT DO NOTHING", cat)
        conn.commit()  # Сохраняем создание таблиц
    finally:
        cursor.close()
        conn.close()