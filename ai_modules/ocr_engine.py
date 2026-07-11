import easyocr
import cv2
import os


class DocumentProcessor:
    def __init__(self):
        """
        Инициализируем класс и сразу загружаем модель в память,
        так как ресурсов сервера (8 ГБ RAM) теперь достаточно.
        """
        print("--- Инициализация VOXYS AI OCR Module ---")
        self.model_storage = os.path.expanduser('~/.EasyOCR')
        # Сразу загружаем и русский, и английский языки
        self.reader = easyocr.Reader(['ru', 'en'], gpu=False, model_storage_directory=self.model_storage)
        print("--- Модели успешно загружены ---")

    def process_image(self, image_path):
        """
        Основной метод для распознавания текста на картинке.
        """
        try:
            # Читаем изображение через OpenCV
            img = cv2.imread(image_path)
            if img is None:
                print("Ошибка: не удалось прочитать изображение")
                return []

            # Переводим в градации серого для улучшения распознавания
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Распознаем текст (detail=0 возвращает только список строк)
            results = self.reader.readtext(gray, detail=0)

            return results

        except Exception as e:
            print(f"Критическая ошибка при обработке изображения: {e}")
            return []

    def extract_structured_data(self, raw_data):
        """
        Метод для обработки сырого текста и передачи в интерфейс.
        """
        structured_data = {
            "Распознанные строки": raw_data
        }
        return structured_data