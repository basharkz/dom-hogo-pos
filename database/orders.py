import json
from database.connection import execute_query

def db_get_active_orders():
    rows = execute_query("SELECT order_id, order_name, cart_json, discount_percent FROM active_orders ORDER BY order_id ASC", fetch="all")
    return [{"id": r[0], "name": r[1], "cart": json.loads(r[2]), "discount": r[3]} for r in rows] if rows else []

def db_get_order_by_id(order_id):
    row = execute_query("SELECT order_id, order_name, cart_json, discount_percent FROM active_orders WHERE order_id = %s", (order_id,), fetch="one")
    return {"id": row[0], "name": row[1], "cart": json.loads(row[2]), "discount": row[3]} if row else None

def db_update_order(order_dict):
    execute_query("UPDATE active_orders SET order_name = %s, cart_json = %s, discount_percent = %s WHERE order_id = %s",
                  (order_dict["name"], json.dumps(order_dict["cart"]), order_dict["discount"], order_dict["id"]))