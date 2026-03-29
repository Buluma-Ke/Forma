import csv
import io
import os
import cv2
import numpy as np
import easyocr
from PIL import Image
from django.shortcuts import render
from django.http import HttpResponse
from .models import Document
from .forms import DocumentForm

reader = easyocr.Reader(['en'])

def preprocess_image(image):
    img = np.array(image.convert('RGB'))
    height, width = img.shape[:2]
    if width < 1000:
        scale = 1000 / width
        img = cv2.resize(img, None, fx=scale, fy=scale,
                        interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)
    kernel = np.array([[-1,-1,-1],[-1,9,-1],[-1,-1,-1]])
    sharpened = cv2.filter2D(enhanced, -1, kernel)
    denoised = cv2.fastNlMeansDenoising(sharpened, h=10)
    return cv2.cvtColor(denoised, cv2.COLOR_GRAY2RGB)

def extract_table(img_array):
    result = reader.readtext(
        img_array,
        detail=1,
        paragraph=False,
        contrast_ths=0.1,
        adjust_contrast=0.5,
        text_threshold=0.7,
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
    form = DocumentForm()
    if request.method == 'POST' and 'image' in request.FILES:
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save()
            image = Image.open(doc.image.path)
            img_array = preprocess_image(image)
            table = extract_table(img_array)
            # Pad rows to equal length
            max_cols = max(len(row) for row in table) if table else 0
            table = [row + [''] * (max_cols - len(row)) for row in table]
            return render(request, 'documents/upload.html', {
                'form': DocumentForm(),
                'table': table,
                'num_cols': max_cols,
            })
    return render(request, 'documents/upload.html', {'form': form})

def download(request):
    if request.method == 'POST':
        output = io.StringIO()
        writer = csv.writer(output)
        row_index = 0
        while True:
            row = []
            col_index = 0
            while True:
                key = f'cell_{row_index}_{col_index}'
                if key not in request.POST:
                    break
                row.append(request.POST[key])
                col_index += 1
            if not row:
                break
            writer.writerow(row)
            row_index += 1
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="forma_output.csv"'
        return response