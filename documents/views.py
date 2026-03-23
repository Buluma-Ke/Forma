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

reader = easyocr.Reader(['en'])

def extract_table(img_array):
    result = reader.readtext(img_array)

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

            image = Image.open(doc.image.path).convert('RGB')
            img_array = np.array(image)
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