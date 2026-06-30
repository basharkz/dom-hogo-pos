import json
from database.connection import execute_query

def db_get_active_orders():
    rows = execute_query("SELECT order_id, order_name, cart_json, discount_percent FROM active_orders ORDER BY rowid ASC", fetch="all")
    orders = []
    if rows:
        for row in rows:
            cart_dict = json.loads(row[2]) if row[2] else {}
            orders.append({"id": row[0], "name": row[1], "cart": cart_dict, "discount": row[3]})
    return orders

def db_get_order_by_id(order_id):
    row = execute_query("SELECT order_id, order_name, cart_json, discount_percent FROM active_orders WHERE order_id = ?", (order_id,), fetch="one")
    if row: return {"id": row[0], "name": row[1], "cart": json.loads(row[2]) if row[2] else {}, "discount": row[3]}
    return None

def db_update_order(order_dict):
    cart_json = json.dumps(order_dict["cart"])
    execute_query("UPDATE active_orders SET order_name = ?, cart_json = ?, discount_percent = ? WHERE order_id = ?",
                  (order_dict["name"], cart_json, order_dict["discount"], order_dict["id"]))