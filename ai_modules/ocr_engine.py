import easyocr
import cv2
import os


class DocumentProcessor:
    def __init__(self):
        """
        Инициализируем класс, но модель пока не загружаем.
        Это экономит оперативную память при запуске приложения.
        """
        self.reader = None
        # Указываем путь для кэширования моделей, если это необходимо
        self.model_storage = os.path.expanduser('~/.EasyOCR')

    def get_reader(self):
        """
        Метод «ленивой загрузки»:
        Модель загружается в память только в момент первого распознавания.
        """
        if self.reader is None:
            print("--- Загрузка моделей EasyOCR в память ---")
            # gpu=False обязательно для серверного окружения
            self.reader = easyocr.Reader(['ru', 'en'], gpu=False, model_storage_directory=self.model_storage)
        return self.reader

    def process_image(self, image_path):
        """
        Основной метод для распознавания текста на картинке.
        """
        try:
            # Получаем ридер (загрузится, если еще не был загружен)
            reader = self.get_reader()

            # Читаем изображение через OpenCV
            img = cv2.imread(image_path)
            if img is None:
                print("Ошибка: не удалось прочитать изображение")
                return []

            # Переводим в градации серого для улучшения распознавания
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Распознаем текст
            # detail=0 возвращает только список строк
            results = reader.readtext(gray, detail=0)

            return results

        except Exception as e:
            print(f"Критическая ошибка при обработке изображения: {e}")
            return []


# Пример использования (для отладки)
if __name__ == "__main__":
    processor = DocumentProcessor()
    # Замени на путь к твоему файлу для теста
    # result = processor.process_image("test_invoice.jpg")
    # print(result)