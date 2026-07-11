import easyocr
import cv2
import os
import streamlit as st
import fitz
import pandas as pd
import re


class DocumentProcessor:
    def __init__(self):
        # Используем кэшированный ридер
        self.reader = self._get_reader()

    @staticmethod
    @st.cache_resource
    def _get_reader():
        """Кэшируем модель EasyOCR в памяти"""
        print("--- Загрузка модели EasyOCR (первый и последний раз) ---")
        model_storage = os.path.expanduser('~/.EasyOCR')
        return easyocr.Reader(['ru', 'en'], gpu=False, model_storage_directory=model_storage)

    def process_file(self, file_path):
        """Обработка файла с оптимизацией"""
        ext = os.path.splitext(file_path)[1].lower()

        if ext in ['.jpg', '.jpeg', '.png']:
            return self._process_image_optimized(file_path)
        elif ext == '.pdf':
            return self._process_pdf_optimized(file_path)
        elif ext in ['.xlsx', '.xls']:
            return self._process_excel(file_path)
        return ["Ошибка формата"]

    def _process_image_optimized(self, path):
        """Оптимизированная обработка изображения"""
        # Читаем изображение
        img = cv2.imread(path)
        if img is None:
            return []

        # Уменьшаем размер для ускорения (если изображение большое)
        height, width = img.shape[:2]
        if height > 1000 or width > 1000:
            scale = min(1000 / height, 1000 / width)
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)

        # Конвертируем в градации серого
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Применяем пороговую фильтрацию для улучшения контраста
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Ускоренный OCR (detail=0 - только текст, без координат)
        result = self.reader.readtext(thresh, detail=0, paragraph=False)
        return result

    def _process_pdf_optimized(self, path):
        """Оптимизированная обработка PDF"""
        doc = fitz.open(path)

        # Обрабатываем только первую страницу (если документ многстраничный)
        page = doc.load_page(0)

        # Уменьшаем разрешение для ускорения
        zoom = 1.0  # Можно уменьшить до 0.8 для скорости
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        temp_path = "temp_pdf_page.jpg"
        pix.save(temp_path)

        doc.close()

        result = self._process_image_optimized(temp_path)

        # Удаляем временный файл
        try:
            os.remove(temp_path)
        except:
            pass

        return result

    def _process_excel(self, path):
        """Быстрая обработка Excel"""
        try:
            df = pd.read_excel(path, nrows=100)  # Ограничиваем количество строк
            # Объединяем все ячейки в один список
            all_text = df.astype(str).values.flatten().tolist()
            return [text for text in all_text if text and text != 'nan']
        except Exception as e:
            return [f"Ошибка Excel: {str(e)}"]

    def extract_structured_data(self, raw_data):
        """Более быстрая структуризация данных"""
        ignore_list = ['товар', 'количество', 'цена', 'сумма', 'поставщик', 'покупатель',
                       'реализация', 'итого', 'всего', 'наименование', 'ед', 'изм']

        structured = []

        for i, line in enumerate(raw_data):
            text = str(line).strip()

            # Быстрые проверки
            if not text or len(text) < 3:
                continue

            text_lower = text.lower()

            # Пропускаем заголовки
            if any(word in text_lower for word in ignore_list):
                continue

            # Пытаемся извлечь количество и цену из строки
            # Ищем числа в строке
            numbers = re.findall(r'(\d+[\.,]?\d*)', text)

            qty = 1.0
            price = 0.0

            if numbers:
                # Пробуем интерпретировать числа
                try:
                    if len(numbers) >= 2:
                        # Предполагаем, что последнее число - цена, предпоследнее - количество
                        price = float(numbers[-1].replace(',', '.'))
                        qty = float(numbers[-2].replace(',', '.'))
                    elif len(numbers) == 1:
                        qty = float(numbers[0].replace(',', '.'))
                except:
                    pass

            # Очищаем текст от цифр для названия товара
            item_name = re.sub(r'\d+[\.,]?\d*', '', text).strip()
            if not item_name:
                item_name = text

            structured.append({
                'item': item_name,
                'qty': qty,
                'price': price,
                'id': i
            })

        # Ограничиваем количество элементов (если их слишком много)
        return structured[:50]  # Максимум 50 позиций