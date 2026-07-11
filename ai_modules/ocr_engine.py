import easyocr
import cv2
import os
import streamlit as st
import fitz
import pandas as pd

class DocumentProcessor:
    def __init__(self):
        # Сама модель загружается через кэширующий метод
        self.reader = self._get_reader()

    @st.cache_resource
    def _get_reader(_self):
        print("--- Загрузка модели в память (этот текст появится только 1 раз) ---")
        model_storage = os.path.expanduser('~/.EasyOCR')
        return easyocr.Reader(['ru', 'en'], gpu=False, model_storage_directory=model_storage)

    # ... (далее методы process_file и extract_structured_data оставляем без изменений)

    def process_file(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png']: return self._process_image(file_path)
        elif ext == '.pdf': return self._process_pdf(file_path)
        elif ext in ['.xlsx', '.xls']: return self._process_excel(file_path)
        return ["Ошибка формата"]

    def _process_image(self, path):
        img = cv2.imread(path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return self.reader.readtext(gray, detail=0)

    def _process_pdf(self, path):
        doc = fitz.open(path)
        page = doc.load_page(0)
        pix = page.get_pixmap()
        pix.save("temp_pdf_page.jpg")
        return self._process_image("temp_pdf_page.jpg")

    def _process_excel(self, path):
        df = pd.read_excel(path)
        return df.iloc[:, 0].astype(str).tolist()

    def extract_structured_data(self, raw_data):
        # Список слов, которые точно не являются товарами
        ignore_list = ['товар', 'количество', 'цена', 'сумма', 'поставщик', 'покупатель', 'реализация']

        structured = []
        for i, line in enumerate(raw_data):
            text = str(line).lower()
            # Пропускаем явные заголовки и слишком короткие строки
            if any(word in text for word in ignore_list) or len(text) < 5:
                continue

            # Если строка содержит цифры, пытаемся вытащить их
            # Это логика для строк типа "Моцарелла 10,31 4143,00"
            parts = text.split()
            # Простейший эвристический подход: считаем последнее число ценой, предпоследнее — кол-вом
            structured.append({'item': line, 'qty': 1.0, 'price': 0.0, 'id': i})
        return structured