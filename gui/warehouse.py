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
            uploaded_file = st.file_uploader("Выберите фото накладной:", type=['jpg', 'jpeg', 'png'])
            if uploaded_file:
                path = "temp_scan.jpg"
                with open(path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                st.image(path, caption="Ваша накладная")

                if st.button("🚀 Распознать накладную"):
                    with st.spinner("ИИ анализирует накладную..."):
                        # ... (твой код до этого места)
                        proc = DocumentProcessor()
                        raw = proc.process_image(path)
                        data_list = proc.extract_structured_data(raw)  # Теперь это список словарей

                        # Отображаем всё, что нашел ИИ
                        for data in data_list:
                            st.write(
                                f"**Найдено:** {data.get('item', 'Без имени')} | **Кол-во:** {data.get('qty', '0')}")

                        # Кнопка подтверждения должна быть вне цикла
                        if st.button("✅ Подтвердить и сохранить все"):
                            for data in data_list:
                                execute_query(
                                    "INSERT INTO inventory (date, item, qty, price, reason) VALUES (%s, %s, %s, %s, %s)",
                                    (str(datetime.date.today()),
                                     data.get('item', 'Без имени'),
                                     data.get('qty', 0),
                                     data.get('price', 0),
                                     "OCR Закуп"))
                            st.success("Все данные из накладной добавлены в базу!")
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