import json
from database.connection import execute_query


def _safe_load_json(data):
    if not data:
        return []
    try:
        # Если данные пришли как строка, парсим JSON
        obj = json.loads(data) if isinstance(data, str) else data

        # ГЛАВНОЕ: Если в базе лежит старый формат (словарь),
        # принудительно возвращаем пустой список, чтобы не крашить программу
        if isinstance(obj, list):
            return obj
        return []  # Если это словарь или другое — игнорируем, возвращаем пустой список
    except:
        return []


def db_get_active_orders():
    rows = execute_query(
        "SELECT order_id, order_name, cart_json, discount_percent FROM active_orders ORDER BY order_id ASC",
        fetch="all")
    orders = []
    if rows:
        for row in rows:
            orders.append({
                "id": row[0], "name": row[1],
                "cart": _safe_load_json(row[2]), "discount": row[3]
            })
    return orders


def db_get_order_by_id(order_id):
    row = execute_query(
        "SELECT order_id, order_name, cart_json, discount_percent FROM active_orders WHERE order_id = %s", (order_id,),
        fetch="one")
    if row:
        return {"id": row[0], "name": row[1], "cart": _safe_load_json(row[2]), "discount": row[3]}
    return None


def db_update_order(order_dict):
    cart_json = json.dumps(order_dict["cart"])
    execute_query("UPDATE active_orders SET order_name = %s, cart_json = %s, discount_percent = %s WHERE order_id = %s",
                  (order_dict["name"], cart_json, order_dict["discount"], order_dict["id"]))