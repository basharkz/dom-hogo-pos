import json
from database.connection import execute_query


def db_get_active_orders():
    # Убрали rowid, используем order_id для сортировки
    rows = execute_query(
        "SELECT order_id, order_name, cart_json, discount_percent FROM active_orders ORDER BY order_id ASC",
        fetch="all"
    )
    orders = []
    if rows:
        for row in rows:
            # Безопасно парсим JSON
            try:
                cart_dict = json.loads(row[2]) if row[2] else {}
            except json.JSONDecodeError:
                cart_dict = {}

            orders.append({
                "id": row[0],
                "name": row[1],
                "cart": cart_dict,
                "discount": row[3]
            })
    return orders


def db_get_order_by_id(order_id):
    # Заменили ? на %s
    row = execute_query(
        "SELECT order_id, order_name, cart_json, discount_percent FROM active_orders WHERE order_id = %s",
        (order_id,),
        fetch="one"
    )
    if row:
        try:
            cart = json.loads(row[2]) if row[2] else {}
        except json.JSONDecodeError:
            cart = {}
        return {"id": row[0], "name": row[1], "cart": cart, "discount": row[3]}
    return None


def db_update_order(order_dict):
    cart_json = json.dumps(order_dict["cart"])
    # Заменили ? на %s
    execute_query(
        "UPDATE active_orders SET order_name = %s, cart_json = %s, discount_percent = %s WHERE order_id = %s",
        (order_dict["name"], cart_json, order_dict["discount"], order_dict["id"])
    )