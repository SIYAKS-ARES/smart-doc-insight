import requests
import json
import time
from flask import current_app
import traceback  # hataları detaylı loglamak için eklenen import
import os
import re


from app.utils.llm import get_llm_client

# Varsayılan analiz kategorileri
DEFAULT_ANALYSIS_CATEGORIES = {
    "grup_uyeleri": "Grup üyeleri kimler?",
    "sorumluluklar": "Kim hangi bölümden sorumlu?",
    "diyagramlar": "Diyagramları kim çizmiş?",
    "basliklar": "Belirgin başlıklar neler?",
    "eksikler": "İçerikte eksik görünen bir şey var mı?"
}

# Varsayılan analiz şablonu
DEFAULT_PROMPT_TEMPLATE = """Bu PDF bir öğrenci projesidir. İçeriği analiz et ve şu bilgileri çıkar:
    • Grup üyeleri kimler?
    • Kim hangi bölümden sorumlu?
    • Diyagramları kim çizmiş?
    • Belirgin başlıklar neler?
    • İçerikte eksik görünen bir şey var mı?
    
    İşte PDF'in içeriği:
    
    {content}
    
    Yanıtı madde madde ver."""

def analyze_text_with_llm(text_chunks, categories=None, custom_prompt=None):
    """
    Metin parçalarını LLM ile analiz eder ve sonucu döndürür
    
    Args:
        text_chunks: Analiz edilecek metin parçaları
        categories: Özel kategoriler sözlüğü (None ise varsayılan kategoriler kullanılır)
        custom_prompt: Özel prompt şablonu (None ise varsayılan şablon kullanılır)
    """
    results = []
    
    # Debug dizininin varlığını kontrol et, yoksa oluştur
    debug_dir = '/tmp/llm_debug'
    if not os.path.exists(debug_dir):
        os.makedirs(debug_dir)
    
    # DEBUG: Log dosyasına bilgileri yaz
    with open('/tmp/llm_debug/info.txt', 'a') as f:
        f.write("\n\n--- LLM ANALIZ BAŞLADI ---\n")
        f.write(f"Kategoriler: {categories}\n")
        f.write(f"Text chunks sayısı: {len(text_chunks)}\n")
        if custom_prompt:
            f.write(f"Özel prompt kullanılıyor: {custom_prompt}\n")
    
    # Kullanılacak kategorileri belirle
    analysis_categories = categories if categories is not None else DEFAULT_ANALYSIS_CATEGORIES
    
    # DEBUG: Log kategorileri
    with open('/tmp/llm_debug/info.txt', 'a') as f:
        f.write(f"Kullanılan kategoriler: {analysis_categories}\n")
    
    # Özel prompt yoksa kategorilere göre dinamik prompt oluştur
    if custom_prompt is None:
        prompt_template = "Bu PDF bir öğrenci projesidir. İçeriği analiz et ve şu bilgileri çıkar:\n"
        # Kategorilerdeki başlıkları prompt'a ekle
        for category_key, category_question in analysis_categories.items():
            # Kategori anahtarı ve sorusu arasında ':' karakteri varsa, açıklama olarak değerlendir
            if isinstance(category_question, str) and ':' in category_question:
                # Format: "Soru: Açıklama" -> "Soru (Açıklama)"
                question_parts = category_question.split(':', 1)
                category_title = question_parts[0].strip()
                category_desc = question_parts[1].strip() if len(question_parts) > 1 else ""
                
                if category_desc:
                    prompt_template += f"    • {category_title} ({category_desc})\n"
                else:
                    prompt_template += f"    • {category_title}\n"
            else:
                prompt_template += f"    • {category_question}\n"
        
        prompt_template += """    
    İşte PDF'in içeriği:
    
    {content}
    
    Yanıtını aşağıdaki şekilde yapılandır:
    1. Her başlık için yanıtı ayrı bir bölüm olarak ver.
    2. Her bölümü başlık adıyla başlat (örn: "Grup üyeleri:").
    3. Bilgi bulunamazsa "Bu konuda bilgi bulunamadı" yaz.
    4. Yanıtını maddeler halinde ver, her maddeyi • veya - ile başlat.
    5. Kesinlikle başlıkların dışına çıkma ve başlık tekrarı yapma.
    6. Başlıkları tam olarak verilen metinle kullan."""
    else:
        # Özel prompt varsa, prompt'a yapılandırma talimatlarını ekle
        if not "Yanıtını aşağıdaki şekilde yapılandır:" in custom_prompt:
            prompt_template = custom_prompt.rstrip() + """
    
    Yanıtını aşağıdaki şekilde yapılandır:
    1. Her başlık için yanıtı ayrı bir bölüm olarak ver.
    2. Her bölümü başlık adıyla başlat (örn: "Grup üyeleri:").
    3. Bilgi bulunamazsa "Bu konuda bilgi bulunamadı" yaz.
    4. Yanıtını maddeler halinde ver, her maddeyi • veya - ile başlat.
    5. Kesinlikle başlıkların dışına çıkma ve başlık tekrarı yapma.
    6. Başlıkları tam olarak verilen metinle kullan."""
        else:
            prompt_template = custom_prompt
    
    # DEBUG: Log prompt template
    with open('/tmp/llm_debug/info.txt', 'a') as f:
        f.write(f"Prompt şablonu: {prompt_template}\n")
    
    try:
        # LLM istemcisini al
        client = get_llm_client()
        
        # Her parça için LLM'e istek gönder
        for chunk in text_chunks:
            prompt = prompt_template.format(content=chunk)
            
            # DEBUG: Log current prompt
            with open('/tmp/llm_debug/info.txt', 'a') as f:
                f.write(f"LLM'e gönderilen prompt (ilk 200 karakter): {prompt[:200]}...\n")
            
            try:
                # LLM Provider üzerinden yanıt al
                result = client.generate(prompt, options={"temperature": 0.7})
                results.append(result)
                
                # DEBUG: Log LLM response
                with open('/tmp/llm_debug/info.txt', 'a') as f:
                    f.write(f"LLM yanıtı (ilk 200 karakter): {result[:200]}...\n")
                    
            except Exception as client_error:
                print(f"LLM istemci hatası: {str(client_error)}")
                print(traceback.format_exc())
                
                error_msg = f"LLM Hatası: {str(client_error)}"
                print(error_msg)
                results.append(error_msg)
                
                # DEBUG: Log error
                with open('/tmp/llm_debug/info.txt', 'a') as f:
                    f.write(f"LLM hatası: {error_msg}\n")
                
            # API hız sınırlarını aşmamak için kısa bir bekleme
            time.sleep(1)
            
    except Exception as e:
        error_msg = f"Genel Hata: {str(e)}"
        print(error_msg)
        results.append(error_msg)
        
        # DEBUG: Log general error
        with open('/tmp/llm_debug/info.txt', 'a') as f:
            f.write(f"Genel hata: {error_msg}\n")
    
    # Tüm sonuçları birleştir
    combined_result = "\n\n".join(results)
    
    # DEBUG: Log combined result
    with open('/tmp/llm_debug/info.txt', 'a') as f:
        f.write(f"Birleştirilmiş sonuç (ilk 200 karakter): {combined_result[:200]}...\n")
    
    # Sonuçları yapılandırılmış bir şekilde ayrıştır
    final_analysis = parse_llm_results(combined_result, categories)
    
    # DEBUG: Log final analysis
    with open('/tmp/llm_debug/info.txt', 'a') as f:
        f.write(f"Final analiz: {final_analysis}\n")
        f.write("--- LLM ANALIZ TAMAMLANDI ---\n")
    
    return final_analysis

def parse_llm_results(results, categories=None):
    """
    LLM sonuçlarını ayrıştırır ve yapılandırılmış bir veri oluşturur
    
    Args:
        results: LLM'den gelen sonuç metni
        categories: Kullanılacak kategoriler (None ise varsayılan kategoriler kullanılır)
    """
    print(f"Ayrıştırılacak LLM sonucu: {results}")
    
    # Debug dizininin varlığını kontrol et, yoksa oluştur
    debug_dir = '/tmp/llm_debug'
    if not os.path.exists(debug_dir):
        os.makedirs(debug_dir)
    
    # DEBUG: Log parsing start
    with open('/tmp/llm_debug/info.txt', 'a') as f:
        f.write("\n--- PARSE LLM RESULTS BAŞLADI ---\n")
        f.write(f"Kategoriler: {categories}\n")
    
    # Kullanılacak kategorileri belirle
    if categories is None:
        analysis_categories = DEFAULT_ANALYSIS_CATEGORIES
    else:
        analysis_categories = categories
    
    # DEBUG: Log analysis categories
    with open('/tmp/llm_debug/info.txt', 'a') as f:
        f.write(f"Ayrıştırma için kullanılan kategoriler: {analysis_categories}\n")
    
    # Sonuç şablonunu oluştur - tüm kategoriler için boş liste oluştur
    analysis = {}
    analysis["ham_sonuc"] = results if results else "Sonuç alınamadı."
    
    # Tüm kategori anahtarlarını ekle
    for key in analysis_categories.keys():
        analysis[key] = []
    
    # Sonuç boşsa veya None ise, boş analiz döndür
    if not results:
        # DEBUG: Log empty result
        with open('/tmp/llm_debug/info.txt', 'a') as f:
            f.write("Sonuç boş, boş analiz döndürülüyor\n")
        return analysis
    
    # Özel kategoriler için ayrıştırma
    is_custom_analysis = any(key.startswith('custom_') for key in analysis_categories.keys())
    
    # DEBUG: Log custom analysis detection
    with open('/tmp/llm_debug/info.txt', 'a') as f:
        f.write(f"Özel kategorili analiz mi? {is_custom_analysis}\n")
    
    if is_custom_analysis:
        # Özel başlıklar için ayrıştırma kodu
        with open('/tmp/llm_debug/info.txt', 'a') as f:
            f.write(f"Özel başlıklarla analiz başlatılıyor\n")
        
        # Boş olmayan kategorileri ekle
        for category_key in analysis_categories.keys():
            if category_key.startswith('custom_'):
                analysis[category_key] = []
        
        # Tüm satırları işle
        lines = results.split('\n')
        
        # Kategori başlıklarını ve karşılık gelen anahtarları al
        category_titles = {}
        category_keys_by_order = []  # Sıralı kategori anahtarlarını tut
        
        for i, (key, title) in enumerate(analysis_categories.items()):
            if key.startswith('custom_'):
                # Başlığı temizle
                clean_title = title.strip().rstrip(':')
                # Başlık anahtarı eşleştirmesi
                category_titles[clean_title.lower()] = key
                category_keys_by_order.append(key)
        
        with open('/tmp/llm_debug/info.txt', 'a') as f:
            f.write(f"Aranan kategori başlıkları: {category_titles}\n")
        
        # Her satırı kontrol et
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Debug için satırı logla
            with open('/tmp/llm_debug/info.txt', 'a') as f:
                f.write(f"İşlenen satır: '{line}'\n")
            
            # Başlık kontrolü
            found_category = None
            content = None
            
            # Her kategori başlığı için kontrol et
            for title, key in category_titles.items():
                # Title: Content formatını ara
                if ':' in line:
                    parts = line.split(':', 1)
                    line_title = parts[0].strip().lower()
                    # Tam başlık eşleşmesi
                    if line_title == title.lower():
                        found_category = key
                        content = parts[1].strip()
                        with open('/tmp/llm_debug/info.txt', 'a') as f:
                            f.write(f"Başlık bulundu: '{line_title}' -> {key}\n")
                        break
            
            # Eğer bir kategori eşleşmesi varsa
            if found_category and content:
                # "Bu başlıkla ilgili veri bulunamadı" kontrolü
                if "veri bulunamadı" in content.lower():
                    # Bulunamadı durumunda boş liste kal
                    with open('/tmp/llm_debug/info.txt', 'a') as f:
                        f.write(f"Veri bulunamadı bilgisi: {found_category}\n")
                    continue
                
                # İçerik bulunduğunda ekle
                if content.lower().startswith("evet,"):
                    # "Evet, dökümanda..." kısmını temizle
                    for prefix in ["evet, ", "evet,"]:
                        if content.lower().startswith(prefix):
                            content = content[len(prefix):].strip()
                            break
                
                # İçeriği kaydet
                if content:
                    analysis[found_category].append(content)
                    with open('/tmp/llm_debug/info.txt', 'a') as f:
                        f.write(f"İçerik eklendi: {found_category} <- '{content}'\n")
        
        # Her kategori için ayrı debug bilgisi
        for key in category_keys_by_order:
            with open('/tmp/llm_debug/info.txt', 'a') as f:
                f.write(f"Sonuç kategorisi: {key} -> {analysis[key]}\n")
    else:
        # Standart analiz için mevcut kod bloğunu kullan
        # Özel durumlar için keyword tabanlı kontroller
        
        # Diyagram eksikliği kontrol et
        diyagram_eksik = False
        diyagram_keywords = ["diyagram yok", "diyagram bulunmamaktadır", "diyagram gösterilmemiş", 
                            "diyagramlar yok", "diyagram yer almadı", "bilgi yok"]
        
        for keyword in diyagram_keywords:
            if keyword in results.lower():
                diyagram_eksik = True
                break
        
        # Her kategori için kalıpları topla
        patterns = {}
        for key in analysis_categories.keys():
            patterns[key] = []
        
        # Grup üyeleri işleme
        if "grup_uyeleri" in analysis_categories:
            grup_uyeleri_keywords = ["grup üyeleri", "öğrenci isimleri", "öğrenciler", "grup elemanları"]
            
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
                                patterns["grup_uyeleri"].append(uye)
        
        # Sorumluluklar işleme
        if "sorumluluklar" in analysis_categories:
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
                                patterns["sorumluluklar"].append(sorumluluk)
        
        # Başlıklar işleme
        if "basliklar" in analysis_categories:
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
                                patterns["basliklar"].append(baslik)
        
        # Satır bazlı analiz
        lines = results.split('\n')
        current_category = None
        
        # Kategoriler ve anahtar kelimelerin eşleşmeleri
        category_keywords = {
            "grup_uyeleri": ["grup üyeleri", "öğrenci", "öğrenciler", "üye", "grup", "ekip"],
            "sorumluluklar": ["sorumlu", "sorumluluk", "görev", "bölüm sorumlu"],
            "diyagramlar": ["diyagram", "çizim", "çizen", "şema"],
            "basliklar": ["başlık", "konu", "bölüm"],
            "eksikler": ["eksik", "bulunmayan", "yetersiz", "yok"]
        }
        
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
            
            # Debug için her satırı yazdır
            print(f"İşlenen satır: '{line}'")
            
            # Kategori başlıklarını tespit et
            lower_line = line.lower()
            
            # Aktif kategoriyi güncelle
            for category, keywords in category_keywords.items():
                if category in analysis_categories and any(kw in lower_line for kw in keywords):
                    current_category = category
                    print(f"Kategori değişti: {current_category}")
                    break
                
            # Eğer bir kategori belirlediyse
            if current_category and current_category in analysis_categories:
                # Madde işaretleri veya numaralandırma varsa temizle
                if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                    line = line[1:].strip()
                elif len(line) > 1 and line[0].isdigit() and line[1:].startswith('. '):
                    line = line[line.find('.')+1:].strip()
                    
                # Satır boş değilse ve anlamlı bir içerik varsa ekle
                if line and len(line) > 2:  # En az 3 karakter
                    # Ekstra madde işaretlerini temizle
                    while line.startswith('-') or line.startswith('•') or line.startswith('*'):
                        line = line[1:].strip()
                    
                    analysis[current_category].append(line)
                    print(f"Eklendi: {current_category} <- '{line}'")
        
        # Direkt eşleşenler varsa onları da ekle
        for category, pattern_list in patterns.items():
            if category in analysis_categories and pattern_list and not analysis[category]:
                analysis[category] = pattern_list
                print(f"Direkt eşleşme eklendi - {category}: {pattern_list}")
        
        # Diyagram eksikliği tespit edildiyse ve "eksikler" kategorisi varsa ekle
        if "eksikler" in analysis_categories and diyagram_eksik:
            eksik_msg = "Dokümanda diyagram bulunmamaktadır"
            
            # Eksikler listesinde diyagram ile ilgili bir kayıt var mı kontrol et
            has_diagram_missing = False
            for item in analysis["eksikler"]:
                if "diyagram" in item.lower():
                    has_diagram_missing = True
                    break
            
            # Yoksa ve liste boşsa ekle
            if not has_diagram_missing:
                analysis["eksikler"].append(eksik_msg)
                print(f"Eksiklere eklendi: '{eksik_msg}'")
    
    # Her kategori için sonuçları yazdır (hata ayıklama)
    for category, items in analysis.items():
        if category != "ham_sonuc":
            print(f"{category}: {items}")
            # DEBUG: Log category items
            with open('/tmp/llm_debug/info.txt', 'a') as f:
                f.write(f"{category}: {items}\n")
    
    # DEBUG: Log parsing end
    with open('/tmp/llm_debug/info.txt', 'a') as f:
        f.write("--- PARSE LLM RESULTS TAMAMLANDI ---\n")
    
    return analysis

def extract_bullet_points(lines):
    """
    Metin satırlarından madde işaretlerini (bullet points) ayıklar
    
    Args:
        lines: Satır listesi veya tek bir metin bloğu
    
    Returns:
        Ayıklanmış madde listesi
    """
    bullet_items = []
    current_item = None
    
    # Eğer input tek bir string ise, satırlara böl
    if isinstance(lines, str):
        lines = lines.split('\n')
    elif len(lines) == 1 and isinstance(lines[0], str) and '\n' in lines[0]:
        lines = lines[0].split('\n')
    
    for line in lines:
        if isinstance(line, str):
            line = line.strip()
        else:
            continue
            
        if not line:
            continue
        
        # Madde işareti ile başlayan satırları bul
        if line.startswith('-') or line.startswith('•') or line.startswith('*') or (len(line) > 1 and line[0].isdigit() and line[1:3].strip().startswith('.')):
            # Önceki maddeyi ekle
            if current_item:
                bullet_items.append(current_item)
            
            # Madde işaretini temizle
            if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                current_item = line[1:].strip()
            elif len(line) > 1 and line[0].isdigit() and line[1:3].strip().startswith('.'):
                current_item = line[line.find('.')+1:].strip()
            else:
                current_item = line
        # Eğer madde işareti yoksa ve aktif bir madde varsa, bu satırı aktif maddeye ekle
        elif current_item:
            current_item += " " + line
    
    # Son maddeyi ekle
    if current_item:
        bullet_items.append(current_item)
    
    # Boş maddeleri filtrele
    return [item for item in bullet_items if item.strip()]

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

def check_lmstudio_availability():
    """
    LM Studio servisinin çalışıp çalışmadığını kontrol eder
    """
    try:
        # Dinamik içe aktarma - IDE linter hatası gösterse bile çalışma zamanında hata vermez
        lmstudio = __import__('lmstudio')
        
        # Mevcut konfigürasyon hatasını yakala ve görmezden gel
        try:
            lmstudio.configure_default_client("localhost:1234")
            print("LM Studio API bağlantısı başarıyla yapılandırıldı")
        except Exception as e:
            # Eğer yapılandırma zaten mevcutsa, bu hatayı yok sayabiliriz
            print(f"LM Studio yapılandırma kontrolü: {str(e)}")
        
        # Bağlantıyı test etmek için modelleri listele
        try:
            models = lmstudio.list_loaded_models()
            if models:
                # Model bilgilerini güvenli bir şekilde erişmeye çalış
                model_names = []
                for model in models:
                    try:
                        if hasattr(model, 'display_name'):
                            model_names.append(model.display_name)
                        else:
                            # Alternatif olarak model.__dict__ içeriklerine bak
                            model_attrs = getattr(model, '__dict__', {})
                            if 'display_name' in model_attrs:
                                model_names.append(model_attrs['display_name'])
                            else:
                                model_names.append(str(model))
                    except:
                        model_names.append("bilinmeyen_model")
                
                if model_names:
                    print(f"LM Studio bağlantısı başarılı. Yüklü modeller: {', '.join(model_names)}")
                else:
                    print("LM Studio API'ye bağlanıldı, yüklü modeller tespit edildi ancak isimleri alınamadı")
            else:
                print("LM Studio API'ye bağlanıldı, ancak hiç yüklü model bulunamadı.")
            return True
        except Exception as e:
            print(f"LM Studio model listesi alınamadı: {str(e)}")
            return False
            
    except Exception as e:
        print(f"LM Studio erişim hatası: {str(e)}")
        return False

def check_llm_availability():
    """
    Yapılandırılmış LLM sağlayıcısının çalışıp çalışmadığını kontrol eder
    """
    provider = os.getenv('LLM_PROVIDER', 'ollama')
    
    if provider == 'ollama':
        return check_ollama_availability()
    elif provider == 'lmstudio':
        return check_lmstudio_availability()
    else:
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

def check_api_llm_availability(provider, api_key=None, user_id=None):
    """
    API tabanlı LLM sağlayıcısının çalışıp çalışmadığını kontrol eder
    
    Args:
        provider: LLM sağlayıcı adı ('openai', 'gemini', 'claude')
        api_key: Kullanılacak API anahtarı (None ise APIKeyManager'dan alınır)
        user_id: Kullanıcı ID'si (None ise current_user kullanılır)
        
    Returns:
        bool: Sağlayıcı kullanılabilir mi
    """
    try:
        from app.utils.llm import get_llm_client
        from app.utils.api_key_manager import APIKeyManager
        
        # API anahtarını al (parametre > APIKeyManager)
        if api_key is None:
            api_key = APIKeyManager.get_api_key(provider, user_id)
            
        if not api_key:
            print(f"{provider.capitalize()} API anahtarı bulunamadı")
            return False
        
        # API anahtarını kullanarak istemciyi başlat
        client = get_llm_client(force_provider=provider, api_key=api_key, user_id=user_id)
        
        # Kısa bir test isteği gönder
        response = client.generate("Merhaba, bu bir test mesajıdır.", options={"max_tokens": 20})
        
        # Eğer hata içeren yanıt döndüyse, başarısız olarak değerlendir
        if response.startswith(f"{provider.capitalize()} Hatası:"):
            print(f"API bağlantı testi yanıtı hata içeriyor: {response}")
            return False
            
        print(f"{provider.capitalize()} API bağlantı testi başarılı")
        return True
    except Exception as e:
        print(f"{provider.capitalize()} API bağlantı testi başarısız: {str(e)}")
        return False

def check_openai_availability(api_key=None, user_id=None):
    """
    OpenAI API'sinin çalışıp çalışmadığını kontrol eder
    
    Args:
        api_key: Kullanılacak API anahtarı (None ise APIKeyManager'dan alınır)
        user_id: Kullanıcı ID'si (None ise current_user kullanılır)
        
    Returns:
        bool: OpenAI API kullanılabilir mi
    """
    from app.utils.api_key_manager import APIKeyManager
    
    # API anahtarı verilmemişse APIKeyManager'dan al
    if api_key is None:
        api_key = APIKeyManager.get_api_key("openai", user_id)
        
    if not api_key:
        print("OpenAI API anahtarı bulunamadı")
        return False
    
    return check_api_llm_availability("openai", api_key, user_id)

def check_gemini_availability(api_key=None, user_id=None):
    """
    Google Gemini API'sinin çalışıp çalışmadığını kontrol eder
    
    Args:
        api_key: Kullanılacak API anahtarı (None ise APIKeyManager'dan alınır)
        user_id: Kullanıcı ID'si (None ise current_user kullanılır)
        
    Returns:
        bool: Gemini API kullanılabilir mi
    """
    from app.utils.api_key_manager import APIKeyManager
    
    # API anahtarı verilmemişse APIKeyManager'dan al
    if api_key is None:
        api_key = APIKeyManager.get_api_key("gemini", user_id)
        
    if not api_key:
        print("Google API anahtarı bulunamadı")
        return False
    
    return check_api_llm_availability("gemini", api_key, user_id)

def check_claude_availability(api_key=None, user_id=None):
    """
    Anthropic Claude API'sinin çalışıp çalışmadığını kontrol eder
    
    Args:
        api_key: Kullanılacak API anahtarı (None ise APIKeyManager'dan alınır)
        user_id: Kullanıcı ID'si (None ise current_user kullanılır)
        
    Returns:
        bool: Claude API kullanılabilir mi
    """
    from app.utils.api_key_manager import APIKeyManager
    
    # API anahtarı verilmemişse APIKeyManager'dan al
    if api_key is None:
        api_key = APIKeyManager.get_api_key("claude", user_id)
        
    if not api_key:
        print("Anthropic API anahtarı bulunamadı")
        return False
    
    return check_api_llm_availability("claude", api_key, user_id) 