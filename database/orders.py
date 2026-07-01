import json
from database.connection import execute_query

def db_get_active_orders():
    # Убрали rowid, теперь сортируем по порядку добавления через order_id
    rows = execute_query("SELECT order_id, order_name, cart_json, discount_percent FROM active_orders ORDER BY order_id ASC", fetch="all")
    orders = []
    if rows:
        for row in rows:
            cart_dict = json.loads(row[2]) if row[2] else {}
            orders.append({"id": row[0], "name": row[1], "cart": cart_dict, "discount": row[3]})
    return orders

def db_get_order_by_id(order_id):
    # Поменяли ? на %s
    row = execute_query("SELECT order_id, order_name, cart_json, discount_percent FROM active_orders WHERE order_id = %s", (order_id,), fetch="one")
    if row: return {"id": row[0], "name": row[1], "cart": json.loads(row[2]) if row[2] else {}, "discount": row[3]}
    return None

def db_update_order(order_dict):
    cart_json = json.dumps(order_dict["cart"])
    # Поменяли ? на %s
    execute_query("UPDATE active_orders SET order_name = %s, cart_json = %s, discount_percent = %s WHERE order_id = %s",
                  (order_dict["name"], cart_json, order_dict["discount"], order_dict["id"]))