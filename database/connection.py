import psycopg2
import os

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL)


def execute_query(query, params=None, fetch="none"):
    print(f"DEBUG: Подключаюсь к БД: {DATABASE_URL}")
    """Универсальная функция для выполнения запросов"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        if not conn:
            return None

        cursor = conn.cursor()

        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        # ⚠️ ВАЖНО: Для запросов изменения данных - делаем commit
        query_upper = query.strip().upper()
        if query_upper.startswith(('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER', 'TRUNCATE')):
            conn.commit()  # ✅ ЭТО ОБЯЗАТЕЛЬНО!

        if fetch == "all":
            result = cursor.fetchall()
        elif fetch == "one":
            result = cursor.fetchone()
        else:
            result = None

        cursor.close()
        conn.close()
        return result

    except Exception as e:
        if conn:
            conn.rollback()  # Откатываем при ошибке
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print(f"Ошибка базы данных: {e}")
        return None

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