import streamlit as st
from database.connection import execute_query


def render_menu_manager_tab():
    st.subheader("📋 Управление меню")

    # --- ФОРМА ДОБАВЛЕНИЯ ---
    with st.expander("➕ Добавить новое блюдо", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            new_name = st.text_input("Название блюда")
        with col2:
            new_price = st.number_input("Цена (тг)", min_value=0, value=0)
        with col3:
            new_cat = st.text_input("Категория (например: Закуски)")

        if st.button("Сохранить в меню"):
            if new_name and new_cat:
                execute_query(
                    "INSERT INTO menu (dish_name, price, category) VALUES (%s, %s, %s)",
                    (new_name, new_price, new_cat)
                )
                st.success(f"Блюдо '{new_name}' добавлено!")
                st.rerun()  # Обязательно обновляем страницу
            else:
                st.error("Заполните название и категорию!")

    st.write("---")

    # --- СПИСОК БЛЮД ---
    st.write("### Текущее меню")

    # Получаем список блюд
    rows = execute_query("SELECT id, dish_name, price, category FROM menu ORDER BY category, dish_name", fetch="all")

    if rows:
        # Создаем таблицу
        for row in rows:
            menu_id, name, price, cat = row
            col_a, col_b, col_c = st.columns([0.4, 0.2, 0.2])

            col_a.write(f"**{name}** | {cat}")
            col_b.write(f"{int(price)} тг")

            # Кнопка удаления
            if col_c.button("🗑️ Удалить", key=f"del_{menu_id}"):
                execute_query("DELETE FROM menu WHERE id = %s", (menu_id,))
                st.rerun()  # Обновляем страницу после удаления
    else:
        st.info("Меню пустое. Добавьте первое блюдо.")