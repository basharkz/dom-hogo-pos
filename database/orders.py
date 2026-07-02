import json
from database.connection import execute_query


def _safe_parse(data):
    """Вспомогательная функция: безопасно возвращает словарь"""
    if isinstance(data, dict):
        return data
    if isinstance(data, str):
        return json.loads(data)
    return {}


def db_get_active_orders():
    rows = execute_query(
        "SELECT order_id, order_name, cart_json, discount_percent FROM active_orders ORDER BY order_id ASC",
        fetch="all")
    return [{"id": r[0], "name": r[1], "cart": _safe_parse(r[2]), "discount": r[3]} for r in rows] if rows else []


def db_get_order_by_id(order_id):
    row = execute_query(
        "SELECT order_id, order_name, cart_json, discount_percent FROM active_orders WHERE order_id = %s", (order_id,),
        fetch="one")
    if not row:
        return None
    return {"id": row[0], "name": row[1], "cart": _safe_parse(row[2]), "discount": row[3]}


def db_update_order(order_id, updates):
    """
    Обновляет заказ.
    updates — это словарь с полями, которые нужно изменить, например {"cart": {...}}
    """
    # 1. Получаем текущий заказ, чтобы взять актуальные данные
    order = db_get_order_by_id(order_id)
    if not order:
        return

    # 2. Обновляем данные (используем то, что пришло, или старое значение)
    new_cart = updates.get("cart", order["cart"])
    new_name = updates.get("name", order["name"])
    new_discount = updates.get("discount", order["discount"])

    # 3. Сохраняем обратно
    execute_query(
        "UPDATE active_orders SET order_name = %s, cart_json = %s, discount_percent = %s WHERE order_id = %s",
        (new_name, json.dumps(new_cart), new_discount, order_id)
    )