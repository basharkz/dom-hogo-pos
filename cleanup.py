from database.connection import execute_query
try:
    execute_query("DELETE FROM active_orders")
    print("УСПЕШНО: Таблица active_orders очищена.")
except Exception as e:
    print(f"ОШИБКА: {e}")