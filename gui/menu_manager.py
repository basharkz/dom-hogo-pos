import streamlit as st
from database.connection import execute_query
from database.inventory import calculate_dish_food_cost

def render_menu_manager_tab():
    st.subheader("Редактор категорий и разделов")
    rows_cats_all = execute_query("SELECT cat_name FROM categories ORDER BY cat_name ASC", fetch="all")
    db_categories_list_all = [r[0] for r in rows_cats_all] if rows_cats_all else []

    user_role = st.session_state.get("role") or st.session_state.get("user_role") or "Кассир"

    cat_edit_col1, cat_edit_col2 = st.columns(2)
    with cat_edit_col1:
        new_cat_name = st.text_input("Название новой категории:")
        if st.button("➕ Создать категорию"):
            if new_cat_name:
                execute_query("INSERT INTO categories (cat_name) VALUES (%s) ON CONFLICT DO NOTHING", (new_cat_name.upper(),))
                st.success("Категория добавлена!")
                st.rerun()
    with cat_edit_col2:
        if db_categories_list_all:
            cat_to_del = st.selectbox("Удалить категорию из базы:", db_categories_list_all)
            if st.button("❌ Удалить категорию"):
                execute_query("DELETE FROM categories WHERE cat_name = %s", (cat_to_del,))
                st.rerun()

    st.write("---")
    menu_col1, menu_col2 = st.columns(2)

    with menu_col1:
        st.subheader("Добавление новых блюд в меню")
        with st.form("add_dish_form", clear_on_submit=True):
            new_dish_name = st.text_input("Название нового блюда:")
            new_dish_price = st.number_input("Цена продажи (тг):", min_value=0, step=100)
            if not db_categories_list_all:
                st.error("Сначала создайте категорию!")
                st.form_submit_button("Сохранить блюдо", disabled=True)
            else:
                new_dish_cat = st.selectbox("Привязать к категории:", db_categories_list_all)
                if st.form_submit_button("Сохранить блюдо") and new_dish_name:
                    execute_query("INSERT INTO menu (dish_name, price, category) VALUES (%s, %s, %s) ON CONFLICT (dish_name) DO UPDATE SET price = EXCLUDED.price, category = EXCLUDED.category",
                                  (new_dish_name, new_dish_price, new_dish_cat))
                    st.success(f"Блюдо '{new_dish_name}' добавлено!")
                    st.rerun()

    with menu_col2:
        st.subheader("Конструктор Рецептов")
        all_dishes_rows = execute_query("SELECT dish_name, price FROM menu", fetch="all")
        list_dishes_for_recipes = [r[0] for r in all_dishes_rows] if all_dishes_rows else []

        # Получаем список ингредиентов из таблицы inventory
        inv_items = execute_query("SELECT DISTINCT item FROM inventory", fetch="all")
        inv_items_list = [r[0] for r in inv_items] if inv_items else []

        if not list_dishes_for_recipes:
            st.info("Создайте блюда.")
        elif not inv_items_list:
            st.info("Сначала добавьте сырье на склад (инвентарь).")
        else:
            with st.form("recipe_form", clear_on_submit=True):
                selected_dish_rec = st.selectbox("Выберите блюдо:", list_dishes_for_recipes)
                rec_ing = st.selectbox("Ингредиент со склада:", inv_items_list)
                rec_qty = st.number_input("Вес/кол-во на 1 порцию:", min_value=0.001, step=0.01, format="%.3f")

                if st.form_submit_button("🔗 Добавить в рецепт"):
                    if rec_ing and rec_qty > 0:
                        execute_query("INSERT INTO recipes (dish, ingredient, qty_needed) VALUES (%s, %s, %s)",
                                      (selected_dish_rec, rec_ing, rec_qty))
                        st.success(f"Ингредиент {rec_ing} добавлен!")
                        st.rerun()

            # --- ОТЛАДОЧНЫЙ БЛОК ВЫНОСИМ СЮДА ---
            # Теперь он работает независимо от нажатия кнопки и показывает текущую ситуацию
            st.write("---")
            st.markdown(f"🛠 **Отладка: Что сейчас реально лежит в базе для '{selected_dish_rec}'?**")

            check_recipes = execute_query("SELECT * FROM recipes WHERE dish = %s", (selected_dish_rec,), fetch="all")
            if check_recipes:
                st.dataframe(check_recipes)  # Выведет таблицу на экран
            else:
                st.warning("В базе пока нет ингредиентов для этого блюда.")

            check_inventory = execute_query("SELECT item, price FROM inventory", fetch="all")
            st.write("Товары на складе (для расчета себестоимости):")
            st.dataframe(check_inventory)
            # --- КОНЕЦ ОТЛАДОЧНОГО БЛОКА ---

            # Отображение аналитики
            dish_sale_price = next((r[1] for r in all_dishes_rows if r[0] == selected_dish_rec), 0)
            food_cost = calculate_dish_food_cost(selected_dish_rec)
            margin = dish_sale_price - food_cost
            margin_percent = (margin / dish_sale_price * 100) if dish_sale_price > 0 else 0

            st.write(f"Себестоимость: **{int(food_cost)} тг.** | Маржа: **{int(margin)} тг.** ({int(margin_percent)}%)")

            if user_role == "Администратор":
                st.write("---")
                if st.button(f"🗑️ Удалить рецепт блюда '{selected_dish_rec}'"):
                    execute_query("DELETE FROM recipes WHERE dish = %s", (selected_dish_rec,))
                    st.success(f"Рецепт блюда '{selected_dish_rec}' удален!")
                    st.rerun()