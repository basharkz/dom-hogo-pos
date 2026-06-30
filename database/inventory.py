from database.connection import execute_query

def calculate_dish_food_cost(dish_name):
    recipe = execute_query("SELECT ingredient, qty_needed FROM recipes WHERE dish = ?", (dish_name,), fetch="all")
    if not recipe: return 0.0
    total_cost = 0.0
    for ing, qty in recipe:
        last_price_row = execute_query("SELECT price FROM inventory WHERE item = ? AND price > 0 ORDER BY rowid DESC LIMIT 1", (ing,), fetch="one")
        price_per_unit = last_price_row[0] if last_price_row else 0.0
        total_cost += qty * price_per_unit
    return total_cost