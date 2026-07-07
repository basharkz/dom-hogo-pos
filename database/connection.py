import psycopg2
import os
import urllib.parse

DATABASE_URL = os.environ.get("DATABASE_URL",
                              "postgresql://postgres:BtIIGshesJcpBBaFEYScmzKsBKXONcZW@postgres.railway.internal:5432/railway")


def get_connection():
    """Подключение к базе с правильной кодировкой UTF-8"""
    try:
        # 🔥 ВАЖНО: Добавляем параметры для правильной кодировки
        conn = psycopg2.connect(
            DATABASE_URL,
            client_encoding='UTF8',
            options='-c client_encoding=UTF8'
        )
        return conn
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return None


def execute_query(query, params=None, fetch="none"):
    """Универсальная функция для выполнения запросов"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        if not conn:
            print("❌ Нет соединения с БД")
            return None

        cursor = conn.cursor()

        # 🔥 Устанавливаем кодировку для этого соединения
        cursor.execute("SET client_encoding TO 'UTF8'")

        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        query_upper = query.strip().upper()
        if query_upper.startswith(('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER', 'TRUNCATE')):
            conn.commit()

        if fetch == "all":
            result = cursor.fetchall()
        elif fetch == "one":
            result = cursor.fetchone()
        else:
            result = None

        return result

    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        print(f"❌ Ошибка базы данных: {e}")
        print(f"📝 Запрос: {query}")
        print(f"📝 Параметры: {params}")
        return None

    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass


def init_db():
    """Инициализация базы данных"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        if not conn:
            print("❌ Не удалось подключиться к БД для инициализации")
            return

        cursor = conn.cursor()

        # 🔥 Устанавливаем кодировку
        cursor.execute("SET client_encoding TO 'UTF8'")

        # Создаем таблицы с UTF8
        cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (
            date TEXT, 
            item TEXT, 
            qty REAL, 
            price REAL, 
            reason TEXT
        )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS sales (
            id SERIAL PRIMARY KEY, 
            date TEXT, 
            dish TEXT, 
            qty INTEGER, 
            total_price REAL, 
            receipt_id TEXT, 
            discount_percent REAL, 
            payment_method TEXT
        )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS menu (
            dish_name TEXT UNIQUE, 
            price REAL, 
            category TEXT
        )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS recipes (
            dish TEXT, 
            ingredient TEXT, 
            qty_needed REAL
        )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS categories (
            cat_name TEXT UNIQUE
        )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS active_orders (
            order_id TEXT UNIQUE, 
            order_name TEXT, 
            cart_json TEXT, 
            discount_percent REAL
        )''')

        # Добавляем категории если пусто
        cursor.execute("SELECT COUNT(*) FROM categories")
        count = cursor.fetchone()
        if count and count[0] == 0:
            base_cats = [("ХОГО",), ("ПИЦЦА",), ("СОУСЫ",), ("НАПИТКИ",)]
            for cat in base_cats:
                cursor.execute("INSERT INTO categories (cat_name) VALUES (%s) ON CONFLICT (cat_name) DO NOTHING", cat)

        conn.commit()
        print("✅ База данных инициализирована с кодировкой UTF-8")

    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass


# Инициализация при загрузке
try:
    init_db()
    print("✅ Подключение к Railway PostgreSQL установлено")
except Exception as e:
    print(f"⚠️ Ошибка при инициализации: {e}")