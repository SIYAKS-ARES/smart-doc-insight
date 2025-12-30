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
    """PDF dosyasını kayıt eder ve dosya yolunu döndürür (mutlak yol)"""
    filename = secure_filename(file.filename)
    # Benzersiz bir isim oluşturmak için timestamp eklenebilir
    upload_folder = current_app.config['UPLOAD_FOLDER']
    
    # Eğer upload_folder göreli ise, mutlak yola çevir
    if not os.path.isabs(upload_folder):
        upload_folder = os.path.join(os.getcwd(), upload_folder)
    
    save_path = os.path.join(upload_folder, filename)
    file.save(save_path)
    
    # Mutlak yolu döndür
    return os.path.abspath(save_path)

def extract_text_from_pdf(pdf_path):
    """PDF dosyasından metin çıkarır"""
    text = ""
    
    # Dosya yolunu mutlak yola çevir
    original_path = pdf_path
    if not os.path.isabs(pdf_path):
        # Göreli yol ise, UPLOAD_FOLDER ile birleştir
        try:
            # Flask context kontrolü
            upload_folder = 'uploads'  # Varsayılan
            try:
                upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
            except RuntimeError:
                # Flask context dışında, varsayılan değeri kullan
                pass
            
            # Eğer upload_folder da göreli ise, çalışma dizini ile birleştir
            if not os.path.isabs(upload_folder):
                upload_folder = os.path.join(os.getcwd(), upload_folder)
            
            # pdf_path'ten başında varsa 'uploads/' veya '/' karakterlerini temizle
            clean_path = pdf_path.lstrip('/').lstrip('\\')
            if clean_path.startswith('uploads'):
                clean_path = clean_path.replace('uploads', '', 1).lstrip('/').lstrip('\\')
            
            pdf_path = os.path.join(upload_folder, clean_path)
        except Exception as e:
            print(f"PDF yolu çözümlenirken hata: {e}")
            # Hata durumunda orijinal yolu kullan
            pass
    
    # Dosyanın varlığını kontrol et
    if not os.path.exists(pdf_path):
        error_msg = f"PDF dosyası bulunamadı: {pdf_path}"
        print(f"PDF işleme hatası: {error_msg}")
        # Alternatif yolları dene
        alternative_paths = []
        
        # 1. Çalışma dizinindeki uploads klasörü
        alt_yol1 = os.path.join(os.getcwd(), 'uploads', os.path.basename(original_path))
        alternative_paths.append(alt_yol1)
        
        # 2. Orijinal yolun kendisi (eğer mutlak yol ise)
        if os.path.isabs(original_path):
            alternative_paths.append(original_path)
        
        # 3. UPLOAD_FOLDER ile birleştirilmiş yol
        try:
            upload_folder = 'uploads'
            try:
                upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
            except RuntimeError:
                pass
            
            if not os.path.isabs(upload_folder):
                upload_folder = os.path.join(os.getcwd(), upload_folder)
            alt_yol2 = os.path.join(upload_folder, os.path.basename(original_path))
            alternative_paths.append(alt_yol2)
        except:
            pass
        
        # Alternatif yolları dene
        found = False
        for alt_path in alternative_paths:
            if os.path.exists(alt_path):
                pdf_path = alt_path
                print(f"Alternatif yol bulundu: {pdf_path}")
                found = True
                break
        
        if not found:
            print(f"PDF dosyası hiçbir konumda bulunamadı. Denenen yollar:")
            print(f"  1. {pdf_path}")
            for i, alt_path in enumerate(alternative_paths, 2):
                print(f"  {i}. {alt_path}")
            return ""
    
    try:
        # PDF dosyasının geçerliliğini kontrol et
        if not os.path.isfile(pdf_path):
            error_msg = f"PDF dosyası bir dosya değil veya erişilemiyor: {pdf_path}"
            print(f"PDF işleme hatası: {error_msg}")
            return ""
        
        # Dosya boyutunu kontrol et
        file_size = os.path.getsize(pdf_path)
        if file_size == 0:
            error_msg = f"PDF dosyası boş: {pdf_path}"
            print(f"PDF işleme hatası: {error_msg}")
            return ""
        
        # PDF'i açmayı dene
        with pdfplumber.open(pdf_path) as pdf:
            # PDF sayfa sayısını kontrol et
            num_pages = len(pdf.pages)
            if num_pages == 0:
                error_msg = f"PDF dosyası sayfa içermiyor: {pdf_path}"
                print(f"PDF işleme hatası: {error_msg}")
                return ""
            
            print(f"PDF açıldı: {pdf_path} ({num_pages} sayfa, {file_size} bytes)")
            
            # Her sayfadan metin çıkar
            extracted_pages = 0
            for page_num, page in enumerate(pdf.pages, 1):
                try:
                    extracted = page.extract_text()
                    if extracted and extracted.strip():
                        text += extracted + "\n\n"
                        extracted_pages += 1
                except Exception as page_error:
                    print(f"Sayfa {page_num} işlenirken hata: {page_error}")
                    continue
            
            if extracted_pages == 0:
                error_msg = f"PDF'den hiçbir sayfada metin çıkarılamadı. PDF sadece görüntü içeriyor olabilir veya metin katmanı yok: {pdf_path}"
                print(f"PDF işleme hatası: {error_msg}")
                return ""
            
            print(f"PDF'den {extracted_pages}/{num_pages} sayfadan metin çıkarıldı")
            
    except pdfplumber.exceptions.PasswordError:
        error_msg = f"PDF şifre korumalı. Şifre gerekiyor: {pdf_path}"
        print(f"PDF işleme hatası: {error_msg}")
        return ""
    except pdfplumber.exceptions.InvalidFileError:
        error_msg = f"PDF dosyası geçersiz veya bozuk: {pdf_path}"
        print(f"PDF işleme hatası: {error_msg}")
        return ""
    except FileNotFoundError:
        error_msg = f"PDF dosyası bulunamadı: {pdf_path}"
        print(f"PDF işleme hatası: {error_msg}")
        return ""
    except PermissionError:
        error_msg = f"PDF dosyasına erişim izni yok: {pdf_path}"
        print(f"PDF işleme hatası: {error_msg}")
        return ""
    except Exception as e:
        error_msg = f"PDF işleme hatası: {type(e).__name__}: {e} (Dosya: {pdf_path})"
        print(f"PDF işleme hatası: {error_msg}")
        import traceback
        print(traceback.format_exc())
        return ""
    
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