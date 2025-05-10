import requests
import json
import time
from flask import current_app
import ollama  # yeni import
import traceback  # hataları detaylı loglamak için eklenen import

def analyze_text_with_llm(text_chunks):
    """
    Metin parçalarını LLM ile analiz eder ve sonucu döndürür
    """
    base_url = current_app.config.get('OLLAMA_BASE_URL', 'http://localhost:11434')
    # model = "mistral:7b-instruct"
    
    results = []
    
    # Analiz promtu
    prompt_template = """Bu PDF bir öğrenci projesidir. İçeriği analiz et ve şu bilgileri çıkar:
    • Grup üyeleri kimler?
    • Kim hangi bölümden sorumlu?
    • Diyagramları kim çizmiş?
    • Belirgin başlıklar neler?
    • İçerikte eksik görünen bir şey var mı?
    
    İşte PDF'in içeriği:
    
    {content}
    
    Yanıtı madde madde ver."""
    
    # Her parça için Ollama'ya istek gönder
    for chunk in text_chunks:
        prompt = prompt_template.format(content=chunk)
        
        try:
            print("Ollama Python istemcisi kullanılıyor...")
            try:
                # Ollama Python istemcisini kullanarak istek gönder
                response = ollama.generate(
                    model="mistral:latest",
                    prompt=prompt,
                    options={
                        "temperature": 0.7,
                    }
                )
                
                print(f"Ollama API yanıtı: {response}")
                result = response.get('response', '')
                results.append(result)
                
            except Exception as client_error:
                print(f"Ollama Python istemcisi hatası: {str(client_error)}")
                print(traceback.format_exc())
                
                # Python istemcisi başarısız olursa, HTTP isteği ile dene
                print("HTTP isteği ile deneniyor...")
                payload = {
                    "model": "mistral:latest",
                    "prompt": prompt,
                    "stream": False
                }
                print(f"Ollama'ya gönderilen payload: {payload}")
                response = requests.post(
                    f"{base_url}/api/generate",
                    json=payload,
                    timeout=300
                )
                
                print(f"Ollama API yanıtı - durum kodu: {response.status_code}")
                print(f"Ollama API yanıtı - içerik: {response.text}")
                
                if response.status_code == 200:
                    result = response.json().get('response', '')
                    results.append(result)
                else:
                    error_msg = f"API Hatası: {response.status_code}, {response.text}"
                    print(f"Ollama API Hatası: {error_msg}")
                    results.append(error_msg)
                
            # API hız sınırlarını aşmamak için kısa bir bekleme
            time.sleep(1)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"İstek Hatası: {str(e)}"
            print(f"Ollama İstek Hatası: {error_msg}")
            results.append(error_msg)
    
    # Tüm sonuçları birleştir
    combined_result = "\n\n".join(results)
    
    # Sonuçları yapılandırılmış bir şekilde ayrıştır
    final_analysis = parse_llm_results(combined_result)
    
    return final_analysis

def parse_llm_results(results):
    """
    LLM sonuçlarını ayrıştırır ve yapılandırılmış bir veri oluşturur
    """
    print(f"Ayrıştırılacak LLM sonucu: {results}")
    
    # Sonuç boşsa veya None ise, boş bir analiz döndür
    if not results:
        return {
            "grup_uyeleri": [],
            "sorumluluklar": [],
            "diyagramlar": [],
            "basliklar": [],
            "eksikler": [],
            "ham_sonuc": "Sonuç alınamadı."
        }
    
    # Özel durumlar için keyword tabanlı kontroller
    # Diyagram eksikliği
    diyagram_eksik = False
    diyagram_keywords = ["diyagram yok", "diyagram bulunmamaktadır", "diyagram gösterilmemiş", 
                        "diyagramlar yok", "diyagram yer almadı", "bilgi yok"]
    
    for keyword in diyagram_keywords:
        if keyword in results.lower():
            diyagram_eksik = True
            break
    
    # Grup üyeleri
    grup_uyeleri_patterns = []
    grup_uyeleri_keywords = ["grup üyeleri", "öğrenci isimleri", "öğrenciler", "grup elemanları"]
    lower_results = results.lower()
    
    for line in results.split('\n'):
        line = line.strip()
        lower_line = line.lower()
        
        # Grup üyeleri satırını bul
        if any(kw in lower_line for kw in grup_uyeleri_keywords) and ":" in line:
            # "Grup üyeleri: Ali, Veli, Ayşe" formatında olanları al
            uye_part = line.split(':', 1)[1].strip()
            if uye_part and not uye_part.lower() in ["yok", "bulunamadı", "belirtilmemiş"]:
                # Virgülle ayrılmış isimleri ayırarak listeye ekle
                for uye in uye_part.split(','):
                    uye = uye.strip()
                    if uye and not uye.lower() in ["yok", "bulunamadı"]:
                        grup_uyeleri_patterns.append(uye)
    
    # Sorumluluklar
    sorumluluk_patterns = []
    sorumluluk_keywords = ["sorumlu", "sorumluluk", "görev", "bölüm sorumlusu"]
    
    for line in results.split('\n'):
        line = line.strip()
        lower_line = line.lower()
        
        # Sorumluluk satırını bul
        if any(kw in lower_line for kw in sorumluluk_keywords) and ":" in line:
            # "Sorumluluklar: Frontend, Backend" formatında olanları al
            sorumluluk_part = line.split(':', 1)[1].strip()
            if sorumluluk_part and not sorumluluk_part.lower() in ["yok", "bulunamadı", "belirtilmemiş"]:
                # Virgülle ayrılmış görevleri ayırarak listeye ekle
                for sorumluluk in sorumluluk_part.split(','):
                    sorumluluk = sorumluluk.strip()
                    if sorumluluk and not sorumluluk.lower() in ["yok", "bulunamadı"]:
                        sorumluluk_patterns.append(sorumluluk)
    
    # Başlıklar
    baslik_patterns = []
    baslik_keywords = ["başlık", "başlıklar", "konu", "konular", "bölüm", "bölümler"]
    
    for line in results.split('\n'):
        line = line.strip()
        lower_line = line.lower()
        
        # Başlık satırını bul
        if any(kw in lower_line for kw in baslik_keywords) and ":" in line:
            # "Başlıklar: Giriş, Yöntem, Sonuç" formatında olanları al
            baslik_part = line.split(':', 1)[1].strip()
            if baslik_part and not baslik_part.lower() in ["yok", "bulunamadı", "belirtilmemiş"]:
                # Virgülle ayrılmış başlıkları ayırarak listeye ekle
                for baslik in baslik_part.split(','):
                    baslik = baslik.strip()
                    if baslik and not baslik.lower() in ["yok", "bulunamadı"]:
                        baslik_patterns.append(baslik)
    
    # Basit bir ayrıştırma yaklaşımı
    analysis = {
        "grup_uyeleri": [],
        "sorumluluklar": [],
        "diyagramlar": [],
        "basliklar": [],
        "eksikler": [],
        "ham_sonuc": results
    }
    
    lines = results.split('\n')
    current_category = None
    
    for line in lines:
        line = line.strip()
        
        if not line:
            continue
        
        # Debug için her satırı yazdır
        print(f"İşlenen satır: '{line}'")
            
        # Kategori başlıklarını tespit et (daha esnek bir yaklaşım)
        lower_line = line.lower()
        
        if any(kw in lower_line for kw in ["grup üyeleri", "öğrenci", "öğrenciler", "üye", "grup", "ekip"]):
            current_category = "grup_uyeleri"
            print(f"Kategori değişti: {current_category}")
            continue
        elif any(kw in lower_line for kw in ["sorumlu", "sorumluluk", "görev", "bölüm sorumlu"]):
            current_category = "sorumluluklar"
            print(f"Kategori değişti: {current_category}")
            continue
        elif any(kw in lower_line for kw in ["diyagram", "çizim", "çizen", "şema"]):
            current_category = "diyagramlar"
            print(f"Kategori değişti: {current_category}")
            continue
        elif any(kw in lower_line for kw in ["başlık", "konu", "bölüm"]):
            current_category = "basliklar"
            print(f"Kategori değişti: {current_category}")
            continue
        elif any(kw in lower_line for kw in ["eksik", "bulunmayan", "yetersiz", "yok"]):
            current_category = "eksikler"
            print(f"Kategori değişti: {current_category}")
            continue
            
        # Eğer bir kategori belirlediyse
        if current_category:
            # Madde işaretleri veya numaralandırma varsa temizle
            if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                line = line[1:].strip()
            elif line[0].isdigit() and line[1:].startswith('. '):
                line = line[line.find('.')+1:].strip()
                
            # Satır boş değilse ve anlamlı bir içerik varsa ekle
            if line and len(line) > 2:  # En az 3 karakter
                # Ekstra madde işaretlerini temizle
                while line.startswith('-') or line.startswith('•') or line.startswith('*'):
                    line = line[1:].strip()
                
                analysis[current_category].append(line)
                print(f"Eklendi: {current_category} <- '{line}'")
    
    # Direkt eşleşenler varsa onları da ekle
    if grup_uyeleri_patterns and not analysis["grup_uyeleri"]:
        analysis["grup_uyeleri"] = grup_uyeleri_patterns
        print(f"Direkt eşleşme eklendi - grup_uyeleri: {grup_uyeleri_patterns}")
    
    if sorumluluk_patterns and not analysis["sorumluluklar"]:
        analysis["sorumluluklar"] = sorumluluk_patterns
        print(f"Direkt eşleşme eklendi - sorumluluklar: {sorumluluk_patterns}")
    
    if baslik_patterns and not analysis["basliklar"]:
        analysis["basliklar"] = baslik_patterns
        print(f"Direkt eşleşme eklendi - basliklar: {baslik_patterns}")
    
    # Diyagram eksikliği tespit edildiyse ve "eksikler" listesinde belirtilmemişse ekle
    if diyagram_eksik and not any("diyagram" in item.lower() for item in analysis["eksikler"]):
        analysis["eksikler"].append("Dokümanda diyagram bulunmamaktadır")
        print("Eksiklere eklendi: 'Dokümanda diyagram bulunmamaktadır'")
    
    # "Eksikler" kısmı boşsa ve diyagram eksikliği tespit edildiyse onu ekle
    if len(analysis["eksikler"]) == 0 and diyagram_eksik:
        analysis["eksikler"].append("Dokümanda diyagram bulunmamaktadır")
        print("Eksik listesi boştu, eklendi: 'Dokümanda diyagram bulunmamaktadır'")
    
    # Her kategori için sonuçları yazdır (hata ayıklama)
    for category, items in analysis.items():
        if category != "ham_sonuc":
            print(f"{category}: {items}")
    
    return analysis

def check_ollama_availability():
    """
    Ollama servisinin çalışıp çalışmadığını kontrol eder
    """
    base_url = current_app.config.get('OLLAMA_BASE_URL', 'http://localhost:11434')
    
    try:
        response = requests.get(base_url, timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False 

def get_available_models():
    """
    Ollama'da mevcut modelleri listeler
    """
    base_url = current_app.config.get('OLLAMA_BASE_URL', 'http://localhost:11434')
    
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        if response.status_code == 200:
            return response.json().get('models', [])
        return []
    except requests.exceptions.RequestException:
        return [] 