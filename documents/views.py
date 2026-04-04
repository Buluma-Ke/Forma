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
from groq import Groq

reader = easyocr.Reader(['en'])

groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))


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
        text_threshold=0.85,
        low_text=0.4,
        link_threshold=0.4,
        width_ths=0.7,
        slope_ths=0.1
    )
    rows = {}
    for (box, text, confidence) in result:
        if not text.strip():
            continue
        if len(text.strip()) < 2:
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


def correct_table_with_ai(table):
    raw_text = '\n'.join([' | '.join(row) for row in table])

    print('--- RAW TABLE SENT TO GROQ ---')
    print(raw_text)
    print('------------------------------')

    prompt = f"""You are correcting OCR output from a scanned table.
The text below was extracted by OCR and may contain garbled characters, 
misread letters, broken words, or noise.

Rules:
- Correct obvious OCR errors (e.g. '0' vs 'O', '1' vs 'l', 'rn' vs 'm')
- Preserve the table structure — same number of rows and columns
- Keep numbers, codes, abbreviations and proper nouns as-is unless clearly wrong
- If a cell looks like pure noise (random characters), leave it empty
- Return ONLY the corrected table in the same pipe-separated format, nothing else

Raw OCR output:
{raw_text}"""

    try:
        print('--- CALLING GROQ API ---')
        response = groq_client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.1,
        )
        corrected_text = response.choices[0].message.content.strip()

        print('--- GROQ RESPONSE ---')
        print(corrected_text)
        print('--------------------')

        corrected_table = []
        for line in corrected_text.splitlines():
            if line.strip():
                corrected_table.append([
                    cell.strip() for cell in line.split('|')
                ])

        print('--- CORRECTED TABLE ---')
        for row in corrected_table:
            print(row)
        print('----------------------')

        # Clean leading 'I' that are misread pipe characters
        cleaned_table = []
        for row in corrected_table:
            cleaned_row = []
            for cell in row:
                # If cell starts with 'I ' it's likely a misread pipe
                if cell.startswith('I '):
                    cell = cell[2:]
                cleaned_row.append(cell)
            cleaned_table.append(cleaned_row)
        return cleaned_table

        

    except Exception as e:
        print(f'--- GROQ ERROR: {e} ---')

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

            # AI correction pass
            table = correct_table_with_ai(table)

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
    


