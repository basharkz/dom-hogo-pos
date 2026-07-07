import json
from database.connection import execute_query


def _safe_load_json(data):
    if not data:
        return []
    try:
        if isinstance(data, str):
            parsed = json.loads(data)
        else:
            parsed = data

        # Если это словарь, пытаемся достать из него 'cart' или превратить в список
        if isinstance(parsed, dict):
            # Если словарь содержит ключ 'cart', возвращаем его
            return parsed.get("cart", [])

        # Если это список — всё ок
        if isinstance(parsed, list):
            return parsed

        return []
    except Exception:
        return []


def db_get_active_orders():
    rows = execute_query(
        "SELECT order_id, order_name, cart_json, discount_percent FROM active_orders ORDER BY order_id ASC",
        fetch="all")
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
        "SELECT order_id, order_name, cart_json, discount_percent FROM active_orders WHERE order_id = %s", (order_id,),
        fetch="one")
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
    # ✅ ВАЖНО: execute_query уже делает commit, если ваша функция его содержит!
    # Если в вашей функции execute_query нет commit, добавьте его здесь:


def db_create_order(order_name, cart_items, discount_percent=0):
    """Создание нового заказа"""
    import uuid
    order_id = str(uuid.uuid4())[:8]  # Генерируем ID заказа
    cart_json = json.dumps(cart_items)

    execute_query(
        "INSERT INTO active_orders (order_id, order_name, cart_json, discount_percent) VALUES (%s, %s, %s, %s)",
        (order_id, order_name, cart_json, discount_percent)
    )
    # ✅ commit уже внутри execute_query
    return order_id


def db_delete_order(order_id):
    """Удаление заказа"""
    execute_query(
        "DELETE FROM active_orders WHERE order_id = %s",
        (order_id,)
    )
    # ✅ commit уже внутри execute_query


def db_clear_all_orders():
    """Очистка всех заказов"""
    execute_query("DELETE FROM active_orders")
    # ✅ commit уже внутри execute_query