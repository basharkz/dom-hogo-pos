import easyocr
import cv2
import os
import streamlit as st
import fitz
import pandas as pd


class DocumentProcessor:
    def __init__(self):
        # Модель загружается один раз и кэшируется
        self.reader = self._get_reader()

    @st.cache_resource
    def _get_reader(_self):
        # Используем только необходимые языки для скорости
        return easyocr.Reader(['ru', 'en'], gpu=False)

    def process_file(self, file_path):
        """Безопасный метод обработки без использования сигналов."""
        ext = os.path.splitext(file_path)[1].lower()

        # Простая проверка размера (больше 10мб не берем)
        if os.path.getsize(file_path) > 10 * 1024 * 1024:
            return ["Ошибка: Файл слишком большой"]

        try:
            if ext in ['.jpg', '.jpeg', '.png']:
                return self._process_image(file_path)
            elif ext == '.pdf':
                return self._process_pdf(file_path)
            elif ext in ['.xlsx', '.xls']:
                return self._process_excel(file_path)
            return ["Неподдерживаемый формат"]
        except Exception as e:
            return [f"Ошибка обработки: {str(e)}"]

    def _process_image(self, path):
        img = cv2.imread(path)
        if img is None: return ["Ошибка чтения картинки"]

        # Ускорение: сжимаем, если картинка огромная
        h, w = img.shape[:2]
        if w > 1000:
            scale = 1000 / w
            img = cv2.resize(img, (1000, int(h * scale)))

        # detail=0 - это самый быстрый режим работы EasyOCR
        return self.reader.readtext(img, detail=0, paragraph=False)

    def _process_pdf(self, path):
        doc = fitz.open(path)
        # Обрабатываем только первую страницу, чтобы не виснуть на многостраничных документах
        page = doc.load_page(0)
        pix = page.get_pixmap()
        img_path = "temp_pdf_page.jpg"
        pix.save(img_path)
        return self._process_image(img_path)

    def extract_structured_data(self, raw_data):
        forbidden = ['товар', 'количество', 'цена', 'сумма', 'итого', 'реализация', 'подпись']
        structured = []
        for i, line in enumerate(raw_data):
            text = str(line).lower()
            if any(word in text for word in forbidden) or len(text) < 4:
                continue
            structured.append({'item': str(line), 'qty': 1.0, 'price': 0.0, 'id': i})
        return structured