import easyocr
import cv2
import os
import fitz
import pandas as pd

class DocumentProcessor:
    def __init__(self):
        self.model_storage = os.path.expanduser('~/.EasyOCR')
        self.reader = easyocr.Reader(['ru', 'en'], gpu=False, model_storage_directory=self.model_storage)

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
        # ВАЖНО: Присваиваем каждому товару уникальный ID (i)
        return [{'item': str(line), 'qty': 1.0, 'price': 0.0, 'id': i} for i, line in enumerate(raw_data) if len(str(line)) > 2]