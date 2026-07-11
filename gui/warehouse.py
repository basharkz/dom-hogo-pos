import streamlit as st
import datetime
import os
from database.connection import execute_query
from ai_modules.ocr_engine import DocumentProcessor


def render_warehouse_tab():
    st.subheader("📦 Учет остатков на складе")

    # Получение текущих остатков из БД
    cursor_summary = execute_query("SELECT item, SUM(qty) FROM inventory GROUP BY item", fetch="all")
    all_inventory_items = [row[0] for row in cursor_summary] if cursor_summary else []

    # Отображение остатков
    if cursor_summary:
        for row in cursor_summary:
            item_name, current_qty = row[0], row[1]
            if current_qty <= 5.0:
                st.error(f"🚨 **{item_name}**: {current_qty:.3f} кг/шт")
            else:
                st.success(f"📦 **{item_name}**: {current_qty:.3f} кг/шт")

    st.write("---")

    # Создаем две колонки для интерфейса
    inv_col1, inv_col2 = st.columns(2)

    # --- КОЛОНКА 1: ПРИХОД ---
    with inv_col1:
        st.markdown("#### 📥 Приход товара")
        import_type = st.radio("Способ добавления:", ["Вручную", "Загрузить фото (OCR)"])

        if import_type == "Вручную":
            in_item = st.text_input("Название сырья:")
            in_qty = st.number_input("Количество (кг/шт):", min_value=0.0, step=0.1, format="%.3f")
            in_price = st.number_input("Цена закупа:", min_value=0.0, step=50.0)

            if st.button("📥 Оприходовать"):
                if in_item and in_qty > 0:
                    execute_query("INSERT INTO inventory (date, item, qty, price, reason) VALUES (%s, %s, %s, %s, %s)",
                                  (str(datetime.date.today()), in_item, in_qty, in_price, "Закуп"))
                    st.success("Успешно добавлено!")
                    st.rerun()


        else:  # РЕЖИМ OCR

            # Найди строку с file_uploader и замени тип на:
            uploaded_file = st.file_uploader("Выберите документ:", type=['jpg', 'jpeg', 'png', 'pdf', 'xlsx'])

            if uploaded_file:
                path = f"temp_doc{os.path.splitext(uploaded_file.name)[1]}"
                with open(path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                if st.button("🚀 Распознать документ"):
                    with st.spinner("Анализирую документ..."):
                        proc = DocumentProcessor()
                        raw = proc.process_file(path)  # Используем новый универсальный метод
                        st.session_state['ocr_data'] = proc.extract_structured_data(raw)
                        # ... (остальной код отображения колонок остается таким же)

                # Если данные распознаны, выводим их в редактируемые поля

                        # ... (код выше такой же)

                        if 'ocr_data' not in st.session_state:
                            st.session_state['ocr_data'] = []

                        final_data = []
                        # Используем список индексов для удаления
                        to_remove = None

                        for i, entry in enumerate(st.session_state['ocr_data']):
                            # Делим на 4 колонки: Название, Кол-во, Цена, Удаление
                            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

                            with col1:
                                # Уникальный ключ для названия
                                item = st.text_input(f"Товар", value=entry.get('item', ''), key=f"item_{i}")
                            with col2:
                                # Уникальный ключ для кол-ва
                                qty = st.number_input(f"Кол-во", value=float(entry.get('qty', 1.0)), key=f"qty_{i}")
                            with col3:
                                # Уникальный ключ для цены (изменили на price_{i})
                                price = st.number_input(f"Цена", value=float(entry.get('price', 0.0)), key=f"price_{i}")
                            with col4:
                                st.write("###")
                                if st.button("🗑️", key=f"del_{i}"):
                                    st.session_state['ocr_data'].pop(i)
                                    st.rerun()

                            # Сохраняем все данные в список
                            final_data.append({'item': item, 'qty': qty, 'price': price})

                        # Логика удаления
                        if to_remove is not None:
                            st.session_state['ocr_data'].pop(to_remove)
                            st.rerun()  # Перезагружаем страницу, чтобы список обновился

                        # ... (далее идет кнопка сохранения)

                    if st.button("✅ Сохранить в базу"):

                        for data in final_data:
                            execute_query(

                                "INSERT INTO inventory (date, item, qty, price, reason) VALUES (%s, %s, %s, %s, %s)",

                                (str(datetime.date.today()), data['item'], data['qty'], 0.0, "OCR Закуп"))

                        st.success("Данные успешно сохранены!")

                        del st.session_state['ocr_data']

                        os.remove(path)

                        st.rerun()

    # --- КОЛОНКА 2: СПИСАНИЕ ---
    with inv_col2:
        st.markdown("#### 🗑️ Списание и Брак")
        if not all_inventory_items:
            st.info("Склад пуст.")
        else:
            waste_item = st.selectbox("Что списываем?", all_inventory_items)
            waste_qty = st.number_input("Кол-во для списания:", min_value=0.001, step=0.1, format="%.3f")
            waste_reason = st.selectbox("Причина:", ["Порча", "Брак", "Проработка"])

            if st.button("🗑️ Списать со склада", type="primary", use_container_width=True):
                if waste_qty > 0:
                    # ВАЖНО: используем -waste_qty для вычитания из остатков
                    execute_query("INSERT INTO inventory (date, item, qty, price, reason) VALUES (%s, %s, %s, %s, %s)",
                                  (str(datetime.date.today()), waste_item, -waste_qty, 0.0, waste_reason))
                    st.success(f"Списано {waste_qty} единиц")
                    st.rerun()