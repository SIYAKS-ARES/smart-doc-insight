import os
import pdfplumber
from werkzeug.utils import secure_filename
from flask import current_app

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    """Dosya uzantısının izin verilen türde olup olmadığını kontrol eder"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_pdf(file):
    """PDF dosyasını kayıt eder ve dosya yolunu döndürür"""
    filename = secure_filename(file.filename)
    # Benzersiz bir isim oluşturmak için timestamp eklenebilir
    save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(save_path)
    return save_path

def extract_text_from_pdf(pdf_path):
    """PDF dosyasından metin çıkarır"""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n\n"
    except Exception as e:
        print(f"PDF işleme hatası: {e}")
        text = ""
    
    return text

def chunk_text(text, max_chunk_size=1000):
    """
    Metni daha küçük parçalara böler
    LLM token limiti için parçalama
    """
    chunks = []
    current_chunk = ""
    
    # Paragrafları böler
    paragraphs = text.split("\n\n")
    
    for paragraph in paragraphs:
        # Eğer paragraf fazla uzunsa, cümlelere böl
        if len(paragraph) > max_chunk_size:
            sentences = paragraph.split(". ")
            for sentence in sentences:
                if len(current_chunk) + len(sentence) <= max_chunk_size:
                    current_chunk += sentence + ". "
                else:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence + ". "
        else:
            if len(current_chunk) + len(paragraph) <= max_chunk_size:
                current_chunk += paragraph + "\n\n"
            else:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph + "\n\n"
    
    # Son parçayı ekleyin
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks 