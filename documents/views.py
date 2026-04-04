import csv
import io
import os
import base64
import cv2
import numpy as np
from PIL import Image
from groq import Groq
from django.shortcuts import render
from django.http import HttpResponse
from .models import Document
from .forms import DocumentForm

groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))

def encode_image(image_path):
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def preprocess_image(image_path):
    img = cv2.imread(image_path)

    # Step 1 — upscale if image is too small
    height, width = img.shape[:2]
    if width < 1000:
        scale = 1000 / width
        img = cv2.resize(img, None, fx=scale, fy=scale,
                        interpolation=cv2.INTER_CUBIC)
        print(f'--- UPSCALED from {width}px to {int(width*scale)}px ---')

    # Step 2 — deskew
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    coords = np.column_stack(np.where(gray > 0))
    if len(coords) > 0:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        if abs(angle) > 0.5:  # only deskew if significantly tilted
            (h, w) = img.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            img = cv2.warpAffine(img, M, (w, h),
                                flags=cv2.INTER_CUBIC,
                                borderMode=cv2.BORDER_REPLICATE)
            print(f'--- DESKEWED by {angle:.2f} degrees ---')

    # Step 3 — enhance contrast using CLAHE
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge((l, a, b))
    img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    # Save preprocessed image temporarily
    preprocessed_path = image_path + '_preprocessed.jpg'
    cv2.imwrite(preprocessed_path, img)
    print(f'--- PREPROCESSED IMAGE SAVED ---')

    return preprocessed_path


def extract_table_with_vision(image_path):
    # Preprocess before sending to Groq
    preprocessed_path = preprocess_image(image_path)
    base64_image = encode_image(preprocessed_path)

    # Clean up temp file after encoding
    if os.path.exists(preprocessed_path):
        os.remove(preprocessed_path)
        
    print('--- SENDING IMAGE TO GROQ VISION ---')

    prompt = """This image contains a table. Extract all the data from it.

Rules:
- Return ONLY the table data in pipe-separated format like: col1 | col2 | col3
- First row should be the headers if they exist
- One row per line
- Preserve all numbers exactly as they appear
- If a cell is empty leave it blank but keep the pipes
- Do not include any explanation, markdown, or extra text
- Do not wrap in code blocks"""

    try:
        response = groq_client.chat.completions.create(
            model='meta-llama/llama-4-scout-17b-16e-instruct',
            messages=[
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'image_url',
                            'image_url': {
                                'url': f'data:image/jpeg;base64,{base64_image}'
                            }
                        },
                        {
                            'type': 'text',
                            'text': prompt
                        }
                    ]
                }
            ],
            temperature=0.1,
        )

        result_text = response.choices[0].message.content.strip()

        print('--- GROQ VISION RESPONSE ---')
        print(result_text)
        print('----------------------------')

        # Parse pipe separated response into table
        table = []
        for line in result_text.splitlines():
            if line.strip():
                row = [cell.strip() for cell in line.split('|')]
                # Filter out completely empty rows
                if any(cell for cell in row):
                    table.append(row)

        print('--- PARSED TABLE ---')
        for row in table:
            print(row)
        print('--------------------')

        return table

    except Exception as e:
        print(f'--- GROQ VISION ERROR: {e} ---')
        return []


def upload(request):
    form = DocumentForm()
    if request.method == 'POST' and 'image' in request.FILES:
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save()

            print('--- PROCESSING IMAGE ---')
            table = extract_table_with_vision(doc.image.path)

            if not table:
                return render(request, 'documents/upload.html', {
                    'form': DocumentForm(),
                    'error': 'Could not extract any table from this image. Please try a clearer image.',
                })

            max_cols = max(len(row) for row in table) if table else 0
            table = [row + [''] * (max_cols - len(row)) for row in table]

            original_name = os.path.splitext(
                request.FILES['image'].name
            )[0]

            return render(request, 'documents/upload.html', {
                'form': DocumentForm(),
                'table': table,
                'num_cols': max_cols,
                'original_name': original_name,
            })
    return render(request, 'documents/upload.html', {'form': form})


def download(request):
    if request.method == 'POST':
        filename = request.POST.get('filename', 'forma_output').strip()
        if not filename:
            filename = 'forma_output'

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
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response