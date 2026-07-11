import streamlit as st
import datetime
import os
from database.connection import execute_query
from ai_modules.ocr_engine import DocumentProcessor


# Кэшируем процессор
@st.cache_resource
def get_document_processor():
    return DocumentProcessor()


def render_warehouse_tab():
    st.markdown("### :package: Учет складских запасов")

    # Получение текущих остатков с кэшированием
    cursor_summary = execute_query("SELECT item, SUM(qty) FROM inventory GROUP BY item", fetch="all")
    all_inventory_items = [row[0] for row in cursor_summary] if cursor_summary else []

    if cursor_summary:
        for row in cursor_summary:
            item_name, current_qty = row[0], row[1]
            if current_qty <= 5.0:
                st.error(f"🚨 **{item_name}**: {current_qty:.3f} кг/шт")
            else:
                st.success(f"📦 **{item_name}**: {current_qty:.3f} кг/шт")

    st.write("---")

    inv_col1, inv_col2 = st.columns(2)

    # --- КОЛОНКА 1: ПРИХОД ---
    with inv_col1:
        st.markdown("#### :inbox_tray: Приход сырья")
        import_type = st.radio("Способ добавления:", ["Вручную", "Загрузить файл (OCR)"])

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
            uploaded_file = st.file_uploader("Выберите документ:", type=['jpg', 'jpeg', 'png', 'pdf', 'xlsx'])

            if uploaded_file:
                path = f"temp_doc{os.path.splitext(uploaded_file.name)[1]}"
                with open(path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                if st.button(":rocket: Распознать документ", use_container_width=True):
                    # Используем кэшированный процессор
                    proc = get_document_processor()

                    # Создаем "элитный" индикатор прогресса
                    progress_text = "Анализ документа... Пожалуйста, подождите."
                    my_bar = st.progress(0, text=progress_text)

                    with st.spinner(progress_text):
                        # Шаг 1: Чтение (занимает 30% времени)
                        my_bar.progress(30, text="Читаю текст...")
                        raw = proc.process_file(path)

                        # Шаг 2: Структурирование (занимает 60% времени)
                        my_bar.progress(60, text="Структурирую данные...")
                        st.session_state['ocr_data'] = proc.extract_structured_data(raw)

                        # Шаг 3: Завершение
                        my_bar.progress(100, text="Готово!")

                        # Удаляем временный файл сразу после обработки
                        if os.path.exists(path):
                            os.remove(path)

                    st.rerun()

                if 'ocr_data' in st.session_state and st.session_state['ocr_data']:
                    st.markdown("### 📝 Проверьте данные:")

                    new_data = []

                    for i, entry in enumerate(st.session_state['ocr_data']):
                        row_id = entry.get('id', i)

                        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                        with col1:
                            item = st.text_input("Товар", value=entry.get('item', ''), key=f"item_{row_id}",
                                                 label_visibility="collapsed")
                        with col2:
                            qty = st.number_input("Кол-во", value=float(entry.get('qty', 1.0)), key=f"qty_{row_id}",
                                                  label_visibility="collapsed")
                        with col3:
                            price = st.number_input("Цена", value=float(entry.get('price', 0.0)), key=f"price_{row_id}",
                                                    label_visibility="collapsed")
                        with col4:
                            st.write("###")
                            if st.button("❌", key=f"del_{row_id}"):
                                st.session_state['ocr_data'].pop(i)
                                st.rerun()

                        new_data.append({'item': item, 'qty': qty, 'price': price})

                    if st.button(":white_check_mark: Подтвердить оприходование"):
                        if new_data:
                            for data in new_data:
                                execute_query(
                                    "INSERT INTO inventory (date, item, qty, price, reason) VALUES (%s, %s, %s, %s, %s)",
                                    (str(datetime.date.today()), data['item'], data['qty'], data['price'], "OCR Закуп"))

                            st.success("Данные успешно сохранены!")
                            del st.session_state['ocr_data']
                            st.rerun()
                        else:
                            st.warning("Список товаров пуст!")

    # --- КОЛОНКА 2: СПИСАНИЕ ---
    with inv_col2:
        st.markdown("#### :wastebasket: Списание и потери")
        if not all_inventory_items:
            st.info("Склад пуст.")
        else:
            waste_item = st.selectbox("Что списываем?", all_inventory_items)
            waste_qty = st.number_input("Кол-во для списания:", min_value=0.001, step=0.1, format="%.3f")
            waste_reason = st.selectbox("Причина:", ["Порча", "Брак", "Проработка"])

            if st.button("🗑️ Списать со склада", type="primary", use_container_width=True):
                if waste_qty > 0:
                    execute_query("INSERT INTO inventory (date, item, qty, price, reason) VALUES (%s, %s, %s, %s, %s)",
                                  (str(datetime.date.today()), waste_item, -waste_qty, 0.0, waste_reason))
                    st.success(f"Списано {waste_qty} единиц")
                    st.rerun()