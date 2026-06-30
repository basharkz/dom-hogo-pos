import cv2
import pytesseract
import numpy as np
from PIL import Image


def process_invoice_image(image_file):
    """
    Безопасное распознавание текста с накладной через Tesseract OCR.
    Гарантированно возвращает список строк, даже если произошла ошибка.
    """
    try:
        # 1. Читаем изображение безопасным способом
        image = Image.open(image_file)
        img_np = np.array(image)
        img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

        # 2. Предобработка: переводим в ЧБ для улучшения читаемости
        gray = cv2.columns = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

        # 3. Распознавание
        config = '--oem 3 --psm 6'
        text = pytesseract.image_to_string(gray, lang='rus+eng', config=config)

        # Разбиваем на строки и очищаем
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        if not lines:
            return ["⚠️ Текст на изображении не найден или не распознан."]

        return lines

    except Exception as e:
        # Если Tesseract не установлен в Linux, вернем понятную инструкцию вместо падения
        return [
            f"❌ Ошибка OCR модуля: {str(e)}",
            "Возможная причина: В вашей Kali Linux не установлен пакет tesseract-ocr.",
            "Решение: Выполните в терминале Linux команду:",
            "sudo apt update && sudo apt install tesseract-ocr tesseract-ocr-rus -y"
        ]


def count_plates_on_conveyor(frame):
    """Будущий функционал компьютерного зрения"""
    pass