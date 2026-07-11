import streamlit as st
import datetime
import os
from tabs.warehouse_tab import render_warehouse_tab

# Настройка страницы (ДОЛЖНА БЫТЬ ПЕРВОЙ КОМАНДОЙ Streamlit)
st.set_page_config(
    page_title="📊 Система управления складом",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# Кэширование функции для получения данных склада
@st.cache_data(ttl=300)  # Кэш на 5 минут
def get_inventory_data():
    """Кэшированное получение данных склада"""
    from database.connection import execute_query
    result = execute_query("SELECT item, SUM(qty) FROM inventory GROUP BY item", fetch="all")
    return result


# Кэширование функции для получения истории
@st.cache_data(ttl=600)  # Кэш на 10 минут
def get_inventory_history(days=7):
    """Кэшированное получение истории за последние N дней"""
    from database.connection import execute_query
    result = execute_query(
        "SELECT date, item, qty, price, reason FROM inventory WHERE date >= DATE_SUB(CURDATE(), INTERVAL %s DAY) ORDER BY date DESC",
        (days,),
        fetch="all"
    )
    return result


def render_inventory_summary():
    """Отображение сводки по складу с кэшированными данными"""
    cursor_summary = get_inventory_data()

    if cursor_summary:
        # Сортировка по остаткам (сначала критичные)
        sorted_items = sorted(cursor_summary, key=lambda x: x[1])

        for row in sorted_items:
            item_name, current_qty = row[0], row[1]
            if current_qty <= 5.0:
                st.error(f"🚨 **{item_name}**: {current_qty:.3f} кг/шт")
            elif current_qty <= 20.0:
                st.warning(f"⚠️ **{item_name}**: {current_qty:.3f} кг/шт")
            else:
                st.success(f"📦 **{item_name}**: {current_qty:.3f} кг/шт")
    else:
        st.info("Склад пуст")


def main():
    # Заголовок приложения
    st.title("📊 Система управления складом")

    # Текущая дата
    st.caption(f"📅 Сегодня: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}")

    # Создаем вкладки
    tab1, tab2, tab3 = st.tabs(["📦 Склад", "📈 История операций", "⚙️ Настройки"])

    with tab1:
        # Отображение сводки
        st.markdown("### 📋 Текущие остатки")
        render_inventory_summary()

        st.write("---")

        # Вкладка склада (приход/расход)
        render_warehouse_tab()

    with tab2:
        st.markdown("### 📜 История операций")

        # Фильтры для истории
        col1, col2 = st.columns(2)
        with col1:
            days = st.selectbox("Период:", [7, 14, 30, 90, 365], index=0)
        with col2:
            # Получаем список всех товаров для фильтра
            inventory_data = get_inventory_data()
            if inventory_data:
                items = ["Все"] + [row[0] for row in inventory_data]
                filter_item = st.selectbox("Фильтр по товару:", items)
            else:
                filter_item = "Все"

        # Получаем историю
        history = get_inventory_history(days)

        if history:
            # Применяем фильтр
            if filter_item != "Все":
                history = [row for row in history if row[1] == filter_item]

            # Отображаем в таблице
            import pandas as pd
            df = pd.DataFrame(history, columns=["Дата", "Товар", "Кол-во", "Цена", "Причина"])
            df["Кол-во"] = df["Кол-во"].astype(float).round(3)
            df["Цена"] = df["Цена"].astype(float).round(2)

            # Цветовое выделение
            def color_qty(val):
                color = 'red' if val < 0 else 'green'
                return f'color: {color}'

            st.dataframe(
                df.style.applymap(color_qty, subset=['Кол-во']),
                use_container_width=True,
                hide_index=True
            )

            # Статистика
            st.markdown("### 📊 Статистика за период")
            col1, col2, col3 = st.columns(3)
            with col1:
                total_in = df[df['Кол-во'] > 0]['Кол-во'].sum()
                st.metric("📥 Всего приход", f"{total_in:.3f} ед.")
            with col2:
                total_out = abs(df[df['Кол-во'] < 0]['Кол-во'].sum())
                st.metric("📤 Всего расход", f"{total_out:.3f} ед.")
            with col3:
                operations = len(df)
                st.metric("🔄 Операций", f"{operations}")
        else:
            st.info("Нет данных за выбранный период")

    with tab3:
        st.markdown("### ⚙️ Настройки системы")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 🗄️ База данных")
            if st.button("🔄 Обновить кэш данных"):
                st.cache_data.clear()
                st.success("Кэш очищен!")
                st.rerun()

            if st.button("📊 Показать статистику БД"):
                from database.connection import execute_query
                count = execute_query("SELECT COUNT(*) FROM inventory", fetch="one")
                if count:
                    st.info(f"Всего записей в БД: {count[0]}")

        with col2:
            st.markdown("#### 🤖 Настройки OCR")
            st.info("Модель EasyOCR загружена в память")
            if st.button("🔄 Перезагрузить OCR модель"):
                st.cache_resource.clear()
                st.success("OCR модель будет перезагружена при следующем вызове")
                st.rerun()

        st.markdown("---")
        st.markdown("#### 🧹 Очистка временных файлов")
        if st.button("🗑️ Удалить все временные файлы"):
            temp_files = [f for f in os.listdir('.') if f.startswith('temp_')]
            deleted = 0
            for f in temp_files:
                try:
                    os.remove(f)
                    deleted += 1
                except:
                    pass
            st.success(f"Удалено {deleted} временных файлов")


if __name__ == "__main__":
    main()