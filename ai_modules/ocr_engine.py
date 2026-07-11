# ai_modules/ocr_engine.py

import cv2
import easyocr
import numpy as np


class DocumentProcessor:
    def __init__(self):
        # Добавляем model_storage_directory для кэширования
        # и ограничиваем размер модели, если нужно
        self.reader = easyocr.Reader(['ru', 'en'], gpu=False, model_storage_directory='~/.EasyOCR/')
        print("--- VOXYS AI OCR Module Initialized ---")

    def process_image(self, image_path):
        """
        Метод получает путь к картинке и возвращает список найденного текста.
        """
        # 1. Читаем изображение через OpenCV
        img = cv2.imread(image_path)

        # Если изображение не загрузилось, возвращаем пустой список
        if img is None:
            print("Ошибка: Не удалось прочитать изображение!")
            return []

        # 2. Переводим в серый цвет для улучшения качества распознавания
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 3. Распознаем текст. detail=0 возвращает только текст в виде списка
        results = self.reader.readtext(gray, detail=0)

        return results

    def extract_structured_data(self, results):
        """
        Умный парсинг данных для VOXYS AI
        """
        data = {"item": "Неизвестно", "qty": 0.0, "price": 0.0}

        # Перебираем список результатов
        for i, val in enumerate(results):
            # Если находим текст, который не является числом - считаем его товаром
            if not any(char.isdigit() for char in val) and len(val) > 2:
                data["item"] = val

            # Если следующее слово похоже на число - берем его
            if i + 1 < len(results):
                try:
                    num = float(results[i + 1].replace(',', '.'))
                    # Если число похоже на цену (большое)
                    if num > 100:
                        data["price"] = num
                    # Если число похоже на количество (маленькое)
                    elif num > 0:
                        data["qty"] = num
                except:
                    continue

        return data