# Forma

A Django web app that extracts text from uploaded document images and converts them into downloadable CSV files using EasyOCR.

## Features

- Upload an image of any document or table
- Automatic text extraction using EasyOCR
- Intelligent row and column detection
- Download results as a CSV file

## Tech Stack

- Python 3.13
- Django 6.0
- EasyOCR
- OpenCV
- Pillow

## Getting Started

### Prerequisites

- Python 3.13+
- Git

### Installation

1. Clone the repository
```bash
   git clone https://github.com/yourusername/forma.git
   cd forma
```

2. Create and activate a virtual environment
```bash
   python -m venv .env
   .env\Scripts\activate  # Windows
```

3. Install dependencies
```bash
   pip install -r requirements.txt
```

4. Run migrations
```bash
   python manage.py migrate
```

5. Start the development server
```bash
   python manage.py runserver
```

6. Visit `http://127.0.0.1:8000` in your browser

## Usage

1. Open the app in your browser
2. Upload an image of a document or table
3. Click **Extract to CSV**
4. Your CSV file will download automatically

## Roadmap

- [ ] Async processing with Celery
- [ ] Cloud storage with S3
- [ ] REST API with Django REST Framework
- [ ] Support for PDF uploads
- [ ] BI agent for analytics

## License

MIT