import os
import pdfplumber
from werkzeug.utils import secure_filename
from flask import current_app
from langchain_text_splitters import RecursiveCharacterTextSplitter

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

def chunk_text(text, max_chunk_size=7500, chunk_overlap=100):
    """
    Metni daha küçük parçalara böler (RecursiveCharacterTextSplitter kullanarak)
    
    Args:
        text: Bölünecek metin
        max_chunk_size: Maksimum chunk boyutu
        chunk_overlap: Chunk'lar arasındaki örtüşme miktarı
        
    Returns:
        Metin parçaları listesi
    """
    try:
        # Önemli başlık kalıplarını koru (başlık metin bölünmelerini engelle)
        başlık_kalıpları = [
            "GRUP ÜYELERİ", "PROJE EKİBİ", "TAKIM ÜYELERİ", "ÖĞRENCİLER",
            "SORUMLULUKLAR", "GÖREVLER", "İŞ BÖLÜMÜ", 
            "BAŞLIKLAR", "İÇİNDEKİLER", "BÖLÜMLER",
            "GİRİŞ", "ÖZET", "ÖNSÖZ", "ABSTRACT", "AMAÇ", "HEDEF",
            "YÖNTEM", "METOD", "METHODOLGY",
            "ARAŞTIRMA", "İNCELEME", "ANALİZ",
            "BULGULAR", "SONUÇLAR", "TARTIŞMA", "ÇIKARIMLAR",
            "EKSİKLER", "KISITLAR", "SINIRLILIKLAR",
            "KAYNAKÇA", "REFERANSLAR", "KAYNAKLAR"
        ]
        
        # RecursiveCharacterTextSplitter kullan
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", ": ", ", ", " ", ""],  # Daha hassas ayırıcılar
            keep_separator=True,  # Ayırıcıları koru
            is_separator_regex=False
        )
        
        # Özel bölümleme stratejisi: Başlıkları korumak için metni ön işle
        processed_text = text
        
        # Başlıkları koruyarak metni parçalara böl
        chunks = text_splitter.split_text(processed_text)
        
        # Özel başlık kontrolü: Parçaların başında/sonunda başlık kalıpları varsa uygun şekilde ayarla
        enhanced_chunks = []
        for i, chunk in enumerate(chunks):
            # Parçanın başında veya sonunda eksik kalan başlık kontrolü
            chunk_clean = chunk.strip()
            
            # Chunk'ı ekle
            if chunk_clean:
                enhanced_chunks.append(chunk_clean)
        
        # Boş chunk'ları filtrele ve minimum chunk boyutunu kontrol et
        min_chunk_size = 50  # Minimum anlamlı chunk boyutu
        final_chunks = [chunk for chunk in enhanced_chunks if len(chunk.strip()) > min_chunk_size]
        
        print(f"{len(final_chunks)} parça oluşturuldu (RecursiveCharacterTextSplitter)")
        return final_chunks
    except Exception as e:
        print(f"Metin bölümleme hatası: {e}")
        # Hata durumunda eski yönteme geri dön
        return _legacy_chunk_text(text, max_chunk_size)

def _legacy_chunk_text(text, max_chunk_size=1000):
    """
    Eski metin bölümleme yöntemi, 
    RecursiveCharacterTextSplitter başarısız olursa yedek olarak kullanılır
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