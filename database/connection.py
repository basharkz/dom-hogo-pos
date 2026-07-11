import psycopg2
import psycopg2.pool
import os
import urllib.parse
import streamlit as st
from functools import lru_cache
import time
import logging
from contextlib import contextmanager

# Настройка логирования
logging.basicConfig(level=logging.ERROR)

# Конфигурация подключения к БД
DATABASE_URL = os.environ.get("DATABASE_URL",
                              "postgresql://postgres:BtIIGshesJcpBBaFEYScmzKsBKXONcZW@postgres.railway.internal:5432/railway")

# Пул соединений (глобальный)
_pool = None


def get_pool():
    """Создание или получение пула соединений"""
    global _pool
    if _pool is None:
        try:
            # Парсим URL для получения параметров
            parsed = urllib.parse.urlparse(DATABASE_URL)

            # Создаем пул соединений
            _pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,  # Максимум 10 соединений в пуле
                dsn=DATABASE_URL,
                client_encoding='UTF8',
                keepalives=1,
                keepalives_idle=5,
                keepalives_interval=2,
                keepalives_count=2
            )
            print(f"✅ Пул соединений создан (макс: 10)")
        except Exception as e:
            print(f"❌ Ошибка создания пула: {e}")
            return None
    return _pool


def get_connection():
    """Получение соединения из пула"""
    pool = get_pool()
    if pool is None:
        return None

    try:
        conn = pool.getconn()
        # Проверяем соединение
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        return conn
    except Exception as e:
        print(f"❌ Ошибка получения соединения: {e}")
        return None


def return_connection(conn):
    """Возврат соединения в пул"""
    if conn:
        pool = get_pool()
        if pool:
            try:
                pool.putconn(conn)
            except Exception as e:
                print(f"❌ Ошибка возврата соединения: {e}")
                try:
                    conn.close()
                except:
                    pass


@contextmanager
def get_db_cursor():
    """Контекстный менеджер для работы с БД (автоматическое управление)"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        if not conn:
            raise Exception("Нет соединения с БД")

        cursor = conn.cursor()
        yield cursor

        # Если нет ошибок - коммитим
        conn.commit()

    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        raise e
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if conn:
            return_connection(conn)


# Кэш для SELECT запросов
@lru_cache(maxsize=256)
def cached_query(query, params_hash=None):
    """Кэширование результатов SELECT запросов"""
    # params_hash - хэш параметров для кэширования
    return None  # Заполняется в execute_query


def execute_query(query, params=None, fetch="none", use_cache=True, cache_ttl=300):
    """
    Универсальная функция для выполнения запросов с оптимизациями

    Args:
        query: SQL запрос
        params: Параметры для запроса
        fetch: "one", "all", "none"
        use_cache: Использовать кэш для SELECT (True/False)
        cache_ttl: Время жизни кэша в секундах

    Returns:
        Результат запроса
    """
    query_upper = query.strip().upper()
    is_select = query_upper.startswith('SELECT')

    # Для SELECT запросов проверяем кэш
    if is_select and use_cache:
        cache_key = f"{query}_{str(params)}"
        # Используем st.cache_data для кэширования в Streamlit
        return _execute_with_cache(query, params, fetch, cache_ttl)

    # Для остальных запросов выполняем напрямую
    return _execute_raw(query, params, fetch)


@st.cache_data(ttl=300, show_spinner=False)
def _execute_with_cache(query, params, fetch, cache_ttl):
    """Выполнение SELECT запроса с кэшированием"""
    return _execute_raw(query, params, fetch)


def _execute_raw(query, params=None, fetch="none"):
    """Выполнение сырого запроса без кэша"""
    conn = None
    cursor = None
    result = None
    start_time = time.time()

    try:
        conn = get_connection()
        if not conn:
            print("❌ Нет соединения с БД")
            return None

        cursor = conn.cursor()

        # Выполняем запрос
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        # Получаем результат
        if fetch == "all":
            result = cursor.fetchall()
        elif fetch == "one":
            result = cursor.fetchone()
        else:
            # Для INSERT/UPDATE/DELETE - коммитим
            conn.commit()
            result = cursor.rowcount

        # Логируем медленные запросы
        elapsed = time.time() - start_time
        if elapsed > 1.0:
            logging.warning(f"Медленный запрос ({elapsed:.2f}с): {query[:100]}...")

        return result

    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        print(f"❌ Ошибка базы данных: {e}")
        print(f"📝 Запрос: {query[:200]}...")
        if params:
            print(f"📝 Параметры: {params}")
        return None

    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if conn:
            return_connection(conn)


def execute_batch(query, params_list, batch_size=100):
    """
    Пакетное выполнение запросов (быстрее для массовых операций)

    Args:
        query: SQL запрос
        params_list: Список кортежей с параметрами
        batch_size: Размер пакета

    Returns:
        Количество успешных операций
    """
    if not params_list:
        return 0

    conn = None
    cursor = None
    total_rows = 0

    try:
        conn = get_connection()
        if not conn:
            return 0

        cursor = conn.cursor()

        # Разбиваем на пакеты
        for i in range(0, len(params_list), batch_size):
            batch = params_list[i:i + batch_size]
            cursor.executemany(query, batch)
            total_rows += cursor.rowcount

        conn.commit()
        return total_rows

    except Exception as e:
        print(f"❌ Ошибка пакетного выполнения: {e}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
        return 0

    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if conn:
            return_connection(conn)


def init_db():
    """Инициализация базы данных с оптимизациями"""
    try:
        with get_db_cursor() as cursor:
            # Создаем таблицы с индексами для ускорения

            # Таблица inventory с индексами
            cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (
                id SERIAL PRIMARY KEY,
                date TEXT, 
                item TEXT, 
                qty REAL, 
                price REAL, 
                reason TEXT
            )''')

            # Индексы для ускорения запросов
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_inventory_item ON inventory(item)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_inventory_date ON inventory(date)')

            # Таблица sales
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
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sales_dish ON sales(dish)')

            # Таблица menu
            cursor.execute('''CREATE TABLE IF NOT EXISTS menu (
                id SERIAL PRIMARY KEY,
                dish_name TEXT UNIQUE, 
                price REAL, 
                category TEXT
            )''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_menu_category ON menu(category)')

            # Таблица recipes
            cursor.execute('''CREATE TABLE IF NOT EXISTS recipes (
                id SERIAL PRIMARY KEY,
                dish TEXT, 
                ingredient TEXT, 
                qty_needed REAL
            )''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_recipes_dish ON recipes(dish)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_recipes_ingredient ON recipes(ingredient)')

            # Таблица categories
            cursor.execute('''CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                cat_name TEXT UNIQUE
            )''')

            # Таблица active_orders
            cursor.execute('''CREATE TABLE IF NOT EXISTS active_orders (
                id SERIAL PRIMARY KEY,
                order_id TEXT UNIQUE, 
                order_name TEXT, 
                cart_json TEXT, 
                discount_percent REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_active_orders_order_id ON active_orders(order_id)')

            # Добавляем категории если пусто
            cursor.execute("SELECT COUNT(*) FROM categories")
            count = cursor.fetchone()
            if count and count[0] == 0:
                base_cats = [("ХОГО",), ("ПИЦЦА",), ("СОУСЫ",), ("НАПИТКИ",)]
                for cat in base_cats:
                    cursor.execute(
                        "INSERT INTO categories (cat_name) VALUES (%s) ON CONFLICT (cat_name) DO NOTHING",
                        cat
                    )

        print("✅ База данных инициализирована с оптимизациями")

    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")


def clear_query_cache():
    """Очистка кэша запросов"""
    _execute_with_cache.clear()
    return True


def test_connection():
    """Тестирование подключения к БД"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            return result is not None
    except:
        return False


def get_db_stats():
    """Получение статистики БД"""
    try:
        with get_db_cursor() as cursor:
            stats = {}

            # Количество записей в таблицах
            cursor.execute("SELECT COUNT(*) FROM inventory")
            stats['inventory'] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM sales")
            stats['sales'] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM menu")
            stats['menu'] = cursor.fetchone()[0]

            # Размер таблиц
            cursor.execute("""
                SELECT 
                    pg_size_pretty(pg_total_relation_size('inventory')) as inv_size,
                    pg_size_pretty(pg_total_relation_size('sales')) as sales_size,
                    pg_size_pretty(pg_total_relation_size('menu')) as menu_size
            """)
            sizes = cursor.fetchone()
            stats['inv_size'] = sizes[0]
            stats['sales_size'] = sizes[1]
            stats['menu_size'] = sizes[2]

            return stats
    except:
        return None


# Инициализация при загрузке
try:
    init_db()
    print("✅ Подключение к Railway PostgreSQL установлено с оптимизациями")
    print(f"✅ Пул соединений: {get_pool() is not None}")
except Exception as e:
    print(f"⚠️ Ошибка при инициализации: {e}")

# Экспортируем основные функции
__all__ = [
    'get_connection',
    'get_db_cursor',
    'execute_query',
    'execute_batch',
    'init_db',
    'clear_query_cache',
    'test_connection',
    'get_db_stats',
    'return_connection'
]