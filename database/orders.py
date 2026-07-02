import json
from database.connection import execute_query

# Вспомогательная функция для безопасной загрузки JSON
def _safe_load_json(data):
    if isinstance(data, dict):
        return data  # Если это уже словарь, возвращаем как есть
    if isinstance(data, str):
        return json.loads(data) # Если строка, то парсим
    return {} # Если пусто, возвращаем пустой словарь

def db_get_active_orders():
    rows = execute_query(
        "SELECT order_id, order_name, cart_json, discount_percent FROM active_orders ORDER BY order_id ASC",
        fetch="all"
    )
    orders = []
    if rows:
        for row in rows:
            orders.append({
                "id": row[0],
                "name": row[1],
                "cart": _safe_load_json(row[2]),
                "discount": row[3]
            })
    return orders

def db_get_order_by_id(order_id):
    row = execute_query(
        "SELECT order_id, order_name, cart_json, discount_percent FROM active_orders WHERE order_id = %s",
        (order_id,),
        fetch="one"
    )
    if row:
        return {
            "id": row[0],
            "name": row[1],
            "cart": _safe_load_json(row[2]),
            "discount": row[3]
        }
    return None

def db_update_order(order_dict):
    cart_json = json.dumps(order_dict["cart"])
    execute_query(
        "UPDATE active_orders SET order_name = %s, cart_json = %s, discount_percent = %s WHERE order_id = %s",
        (order_dict["name"], cart_json, order_dict["discount"], order_dict["id"])
    )