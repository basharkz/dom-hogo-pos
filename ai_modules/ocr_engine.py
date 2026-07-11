import easyocr
import cv2
import os
import fitz  # PyMuPDF
import pandas as pd


class DocumentProcessor:
    def __init__(self):
        self.model_storage = os.path.expanduser('~/.EasyOCR')
        self.reader = easyocr.Reader(['ru', 'en'], gpu=False, model_storage_directory=self.model_storage)

    def process_file(self, file_path):
        """
        Универсальный метод: определяет тип файла и извлекает текст.
        """
        ext = os.path.splitext(file_path)[1].lower()

        if ext in ['.jpg', '.jpeg', '.png']:
            return self._process_image(file_path)

        elif ext == '.pdf':
            return self._process_pdf(file_path)

        elif ext in ['.xlsx', '.xls']:
            return self._process_excel(file_path)

        else:
            return ["Неподдерживаемый формат"]

    def _process_image(self, path):
        img = cv2.imread(path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return self.reader.readtext(gray, detail=0)

    def _process_pdf(self, path):
        # Превращаем первую страницу PDF в картинку и распознаем
        doc = fitz.open(path)
        page = doc.load_page(0)
        pix = page.get_pixmap()
        pix.save("temp_pdf_page.jpg")
        return self._process_image("temp_pdf_page.jpg")

    def _process_excel(self, path):
        # Читаем таблицу и превращаем всё содержимое в список строк
        df = pd.read_excel(path)
        text_list = []
        for col in df.columns:
            text_list.append(str(col))
            text_list.extend(df[col].astype(str).tolist())
        return text_list

    def extract_structured_data(self, raw_data):
        return [{'item': str(line), 'qty': 1.0} for line in raw_data if len(str(line)) > 2]