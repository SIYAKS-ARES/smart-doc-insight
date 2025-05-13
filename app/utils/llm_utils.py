import requests
import json
import time
from flask import current_app
import traceback  # hataları detaylı loglamak için eklenen import
import os

from app.utils.llm import get_llm_client

def analyze_text_with_llm(text_chunks):
    """
    Metin parçalarını LLM ile analiz eder ve sonucu döndürür
    """
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
    
    try:
        # LLM istemcisini al
        client = get_llm_client()
        
        # Her parça için LLM'e istek gönder
        for chunk in text_chunks:
            prompt = prompt_template.format(content=chunk)
            
            try:
                # LLM Provider üzerinden yanıt al
                result = client.generate(prompt, options={"temperature": 0.7})
                results.append(result)
                    
            except Exception as client_error:
                print(f"LLM istemci hatası: {str(client_error)}")
                print(traceback.format_exc())
                
                error_msg = f"LLM Hatası: {str(client_error)}"
                print(error_msg)
                results.append(error_msg)
                
            # API hız sınırlarını aşmamak için kısa bir bekleme
            time.sleep(1)
            
    except Exception as e:
        error_msg = f"Genel Hata: {str(e)}"
        print(error_msg)
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

def check_lmstudio_availability():
    """
    LM Studio servisinin çalışıp çalışmadığını kontrol eder
    """
    try:
        import lmstudio
        
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
            
    except ImportError:
        print("LM Studio paketi yüklü değil")
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