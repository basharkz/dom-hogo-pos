import streamlit as st
import datetime
from database.connection import execute_query


def render_warehouse_tab():
    st.subheader("Учет остатков на складе")

    # Отображение критических остатков сырья
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

        # Выбор режима ввода данных (вручную, OCR-сканирование накладной, Excel)
        import_type = st.radio("Способ добавления прихода:",
                               ["Вручную", "Загрузить фото/скан накладной (OCR)", "Импорт из Excel/CSV файла"])

        if import_type == "Вручную":
            in_item = st.text_input("Название сырья:")
            in_qty = st.number_input("Количество (кг/шт):", min_value=0.0, step=0.1, format="%.3f", key="add_inv_qty")
            in_price = st.number_input("Цена закупа (за 1 кг/шт) в тг:", min_value=0.0, step=50.0, key="add_inv_pr")

            if st.button("📥 Оприходовать сырье", use_container_width=True):
                if in_item and in_qty > 0:
                    execute_query("INSERT INTO inventory (date, item, qty, price, reason) VALUES (?, ?, ?, ?, ?)",
                                  (str(datetime.date.today()), in_item, in_qty, in_price, "Закуп"))
                    st.success(f"Успешно закуплено: {in_item}")
                    st.rerun()


        elif import_type == "Загрузить фото/скан накладной (OCR)":

            uploaded_doc = st.file_uploader("Выберите изображение накладной", type=["jpg", "jpeg", "png"])

            if uploaded_doc:

                st.image(uploaded_doc, caption="Загруженная накладная", width=300)

                if st.button("🔍 Распознать текст накладной", use_container_width=True):

                    with st.spinner("ИИ сканирует документ..."):

                        # Импортируем наш ИИ-модуль

                        from ai_modules.vision import process_invoice_image

                        # Запускаем распознавание

                        recognized_lines = process_invoice_image(uploaded_doc)

                        st.success("Сканирование завершено!")

                        st.markdown("#### Распознанный текст:")

                        # Выводим строки списком

                        for line in recognized_lines:
                            st.write(f"📄 {line}")

        elif import_type == "Импорт из Excel/CSV файла":
            uploaded_file = st.file_uploader("Выберите файл таблицы поставщика", type=["xlsx", "csv"])
            if uploaded_file:
                st.info("Файл прочитан. Настройте сопоставление колонок...")

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
                    execute_query("INSERT INTO inventory (date, item, qty, price, reason) VALUES (?, ?, ?, ?, ?)",
                                  (str(datetime.date.today()), waste_item, -waste_qty, 0.0, waste_reason))
                    st.success(f"Успешно списано {waste_qty:.3f} кг/шт")
                    st.rerun()