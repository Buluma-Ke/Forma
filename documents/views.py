import csv
import io
import cv2
import numpy as np
import easyocr
from PIL import Image
from django.shortcuts import render
from django.http import HttpResponse
from .models import Document
from .forms import DocumentForm

reader = easyocr.Reader(
    ['en'],
    gpu=False,          # set True if you have a GPU
    model_storage_directory='models/',
    download_enabled=True,
    recognizer=True,
    verbose=False
)

def preprocess_image(image):
    img = np.array(image.convert('RGB'))
    
    # Resize if image is too small — EasyOCR struggles under 1000px wide
    height, width = img.shape[:2]
    if width < 1000:
        scale = 1000 / width
        img = cv2.resize(img, None, fx=scale, fy=scale, 
                        interpolation=cv2.INTER_CUBIC)
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    
    # Increase contrast using CLAHE (better than basic equalizeHist)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)
    
    # Sharpen the image
    kernel = np.array([[-1,-1,-1],
                       [-1, 9,-1],
                       [-1,-1,-1]])
    sharpened = cv2.filter2D(enhanced, -1, kernel)
    
    # Denoise
    denoised = cv2.fastNlMeansDenoising(sharpened, h=10)
    
    # Convert back to RGB (EasyOCR expects 3 channels)
    return cv2.cvtColor(denoised, cv2.COLOR_GRAY2RGB)

def extract_table(img_array):
    result = reader.readtext(
    img_array,
    detail=1,
    paragraph=False,     # keep individual words separate
    contrast_ths=0.1,    # lower = detects more text in low contrast areas
    adjust_contrast=0.5, # auto contrast adjustment
    text_threshold=0.7,  # confidence threshold — raise to reduce wrong chars
    low_text=0.4,
    link_threshold=0.4,
    width_ths=0.7,
    slope_ths=0.1
)

    rows = {}
    for (box, text, confidence) in result:
        if not text.strip():
            continue

        top = int((box[0][1] + box[2][1]) / 2)
        left = int(box[0][0])
        row_key = top // 15

        if row_key not in rows:
            rows[row_key] = []
        rows[row_key].append((left, text.strip()))

    table = []
    for row_key in sorted(rows.keys()):
        row_words = sorted(rows[row_key], key=lambda x: x[0])
        table.append([word for _, word in row_words])

    return table

def upload(request):
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save()

            image = Image.open(doc.image.path)
            img_array = preprocess_image(image)
            table = extract_table(img_array)

            output = io.StringIO()
            writer = csv.writer(output)
            for row in table:
                writer.writerow(row)

            response = HttpResponse(output.getvalue(), content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="output.csv"'
            return response
    else:
        form = DocumentForm()
    return render(request, 'documents/upload.html', {'form': form})