import streamlit as st
import datetime
from database.connection import execute_query

def render_warehouse_tab():
    st.subheader("Учет остатков на складе")

    # Отображение критических остатков сырья (Заменили ? на %s)
    # В Postgres GROUP BY работает корректно
    cursor_summary = execute_query("SELECT item, SUM(qty) FROM inventory GROUP BY item", fetch="all")
    all_inventory_items = [row[0] for row in cursor_summary] if cursor_summary else []

    if cursor_summary:
        for row in cursor_summary:
            item_name, current_qty = row[0], row[1]
            if current_qty <= 5.0:
                st.error(f"🚨 **{item_name}**: {current_qty:.3f} кг/шт (ЗАПАС КРИТИЧЕСКИ МАЛ!)")
            elif current_qty <= 15.0:
                st.warning(f"⚠️ **{item_name}**: {current_qty:.3f} кг/шт (Заканчивается)")
            else:
                st.success(f"📦 **{item_name}**: {current_qty:.3f} кг/шт")

    st.write("---")
    inv_col1, inv_col2 = st.columns(2)

    with inv_col1:
        st.markdown("#### 📥 Приход товара на склад")

        import_type = st.radio("Способ добавления прихода:",
                               ["Вручную", "Загрузить фото/скан накладной (OCR)", "Импорт из Excel/CSV файла"])

        if import_type == "Вручную":
            in_item = st.text_input("Название сырья:")
            in_qty = st.number_input("Количество (кг/шт):", min_value=0.0, step=0.1, format="%.3f", key="add_inv_qty")
            in_price = st.number_input("Цена закупа (за 1 кг/шт) в тг:", min_value=0.0, step=50.0, key="add_inv_pr")

            if st.button("📥 Оприходовать сырье", use_container_width=True):
                if in_item and in_qty > 0:
                    # ИСПРАВЛЕНО: Заменили ? на %s
                    execute_query("INSERT INTO inventory (date, item, qty, price, reason) VALUES (%s, %s, %s, %s, %s)",
                                  (str(datetime.date.today()), in_item, in_qty, in_price, "Закуп"))
                    st.success(f"Успешно закуплено: {in_item}")
                    st.rerun()

        # ... [код OCR и Excel остается прежним] ...

    with inv_col2:
        st.markdown("#### 🗑️ Списание и Брак сырья")
        if not all_inventory_items:
            st.info("На складе еще нет товаров.")
        else:
            waste_item = st.selectbox("Что нужно списать?", all_inventory_items, key="waste_sel")
            waste_qty = st.number_input("Вес/Кол-во для удаления:", min_value=0.001, step=0.1, format="%.3f")
            waste_reason = st.selectbox("Причина списания:",
                                        ["Порча / Просрочка", "Брак сырья (Сырое)", "Персонал / Проработка"])

            if st.button("🗑️ Списать со склада", type="secondary", use_container_width=True):
                if waste_qty > 0:
                    # ИСПРАВЛЕНО: Заменили ? на %s
                    execute_query("INSERT INTO inventory (date, item, qty, price, reason) VALUES (%s, %s, %s, %s, %s)",
                                  (str(datetime.date.today()), waste_item, -waste_qty, 0.0, waste_reason))
                    st.success(f"Успешно списано {waste_qty:.3f} кг/шт")
                    st.rerun()