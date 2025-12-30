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

# Prompt şablonlarını XML veya JSON dosyasından yükle
def load_prompt_templates():
    """
    XML veya JSON dosyasından prompt şablonlarını yükler
    Önce XML dosyasını dener, yoksa JSON'a bakar
    
    Returns:
        dict: Prompt şablonları sözlüğü
    """
    import xml.etree.ElementTree as ET
    
    # Önce XML dosyasını dene
    xml_file = os.path.join(os.path.dirname(__file__), 'prompt_templates.xml')
    if os.path.exists(xml_file):
        try:
            # XML dosyasını text olarak oku (XML parse etmeden, çünkü prompt içinde XML örnekleri var)
            with open(xml_file, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            # XML dosyasından prompt'u çıkar
            # Yeni format: system_instruction, output_schema, input_document, analysis_instruction
            templates = {}
            
            # Tüm içeriği birleştir (XML etiketlerini koruyarak)
            # {content} placeholder'ını koru
            templates["default_prompt_template"] = xml_content
            
            print("XML prompt şablonu başarıyla yüklendi")
            return templates
        except ET.ParseError as e:
            print(f"Uyarı: XML dosyası parse edilemedi: {e}. JSON dosyasına geçiliyor.")
        except Exception as e:
            print(f"Uyarı: XML dosyası okunurken hata: {e}. JSON dosyasına geçiliyor.")
    
    # XML yoksa veya hata varsa JSON dosyasını dene
    json_file = os.path.join(os.path.dirname(__file__), 'prompt_templates.json')
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            templates = json.load(f)
        
        # Eğer array formatındaysa, string'e çevir
        processed_templates = {}
        for key, value in templates.items():
            if isinstance(value, list):
                # Array'i newline ile birleştir
                processed_templates[key] = '\n'.join(value)
            else:
                # Zaten string ise olduğu gibi kullan
                processed_templates[key] = value
        
        print("JSON prompt şablonu başarıyla yüklendi")
        return processed_templates
    except FileNotFoundError:
        print(f"Uyarı: {prompt_file} dosyası bulunamadı. Varsayılan prompt kullanılıyor.")
        # Fallback: Eğer JSON dosyası yoksa varsayılan prompt'u döndür
        return {
            "default_prompt_template": """Bu PDF bir öğrenci projesidir.
    İçeriği detaylı bir şekilde analiz et ve şu bilgileri çıkar:
    • Grup üyeleri kimler?
    • Kim hangi bölümden sorumlu?
    • Diyagramları kim çizmiş?
    • Belirgin başlıklar neler?
    • İçerikte eksik görünen bir şey var mı?

    İşte PDF'in içeriği:

    {content}

    Yanıtı şu format ve kurallara göre ver:
    1. Her kategori için açık ve net bilgiler ver
    2. Her kategori için maddeler halinde yanıtla (• işareti kullan)
    3. Eğer bilgi bulunamazsa "Bu konuda bilgi bulunamadı" yaz
    4. Grup üyeleri için isimleri tam olarak al
    5. Başlıkları dokümanın içindekiler kısmından veya metin içindeki belirgin alt bölümlerden al
    6. Eksikler bölümünde sadece dokümanda olması gerekip de bulunmayan önemli kısımları belirt
    7. Başlık adını yaz ve ardından iki nokta üst üste koy
    8. Evet/Hayır ile başla
    9. Çok kısa açıklama ekle (maksimum 1-2 cümle)
    10. Fazla detaya girme, sadece temel bilgiyi ver

    Örnek:
    Proje Tanımı:
    Evet, 2. sayfada "Proje Tanımı" başlığı altında kapsamlı bir şekilde ele alınmıştır.

    GitHub Linki:
    Evet, 5. bölümde repository linki paylaşılmıştır (https://github.com/example/repo).

    Grup Üyeleri:
    Hayır, grup üyeleri dokümanda belirtilmemiştir.

    SADECE istenen formatta ve sadece gerekiyorsa kısa (bir iki cümlelik) açıklamayla yanıtla."""
        }
    except json.JSONDecodeError as e:
        print(f"Uyarı: {prompt_file} dosyası geçersiz JSON formatında. Hata: {e}. Varsayılan prompt kullanılıyor.")
        return {
            "default_prompt_template": """Bu PDF bir öğrenci projesidir.
    İçeriği detaylı bir şekilde analiz et ve şu bilgileri çıkar:
    • Grup üyeleri kimler?
    • Kim hangi bölümden sorumlu?
    • Diyagramları kim çizmiş?
    • Belirgin başlıklar neler?
    • İçerikte eksik görünen bir şey var mı?

    İşte PDF'in içeriği:

    {content}

    Yanıtı şu format ve kurallara göre ver:
    1. Her kategori için açık ve net bilgiler ver
    2. Her kategori için maddeler halinde yanıtla (• işareti kullan)
    3. Eğer bilgi bulunamazsa "Bu konuda bilgi bulunamadı" yaz
    4. Grup üyeleri için isimleri tam olarak al
    5. Başlıkları dokümanın içindekiler kısmından veya metin içindeki belirgin alt bölümlerden al
    6. Eksikler bölümünde sadece dokümanda olması gerekip de bulunmayan önemli kısımları belirt
    7. Başlık adını yaz ve ardından iki nokta üst üste koy
    8. Evet/Hayır ile başla
    9. Çok kısa açıklama ekle (maksimum 1-2 cümle)
    10. Fazla detaya girme, sadece temel bilgiyi ver

    Örnek:
    Proje Tanımı:
    Evet, 2. sayfada "Proje Tanımı" başlığı altında kapsamlı bir şekilde ele alınmıştır.

    GitHub Linki:
    Evet, 5. bölümde repository linki paylaşılmıştır (https://github.com/example/repo).

    Grup Üyeleri:
    Hayır, grup üyeleri dokümanda belirtilmemiştir.

    SADECE istenen formatta ve sadece gerekiyorsa kısa (bir iki cümlelik) açıklamayla yanıtla."""
        }
    except Exception as e:
        print(f"Uyarı: Prompt şablonları yüklenirken hata oluştu: {e}. Varsayılan prompt kullanılıyor.")
        return {
            "default_prompt_template": """Bu PDF bir öğrenci projesidir.
    İçeriği detaylı bir şekilde analiz et ve şu bilgileri çıkar:
    • Grup üyeleri kimler?
    • Kim hangi bölümden sorumlu?
    • Diyagramları kim çizmiş?
    • Belirgin başlıklar neler?
    • İçerikte eksik görünen bir şey var mı?

    İşte PDF'in içeriği:

    {content}

    Yanıtı şu format ve kurallara göre ver:
    1. Her kategori için açık ve net bilgiler ver
    2. Her kategori için maddeler halinde yanıtla (• işareti kullan)
    3. Eğer bilgi bulunamazsa "Bu konuda bilgi bulunamadı" yaz
    4. Grup üyeleri için isimleri tam olarak al
    5. Başlıkları dokümanın içindekiler kısmından veya metin içindeki belirgin alt bölümlerden al
    6. Eksikler bölümünde sadece dokümanda olması gerekip de bulunmayan önemli kısımları belirt
    7. Başlık adını yaz ve ardından iki nokta üst üste koy
    8. Evet/Hayır ile başla
    9. Çok kısa açıklama ekle (maksimum 1-2 cümle)
    10. Fazla detaya girme, sadece temel bilgiyi ver

    Örnek:
    Proje Tanımı:
    Evet, 2. sayfada "Proje Tanımı" başlığı altında kapsamlı bir şekilde ele alınmıştır.

    GitHub Linki:
    Evet, 5. bölümde repository linki paylaşılmıştır (https://github.com/example/repo).

    Grup Üyeleri:
    Hayır, grup üyeleri dokümanda belirtilmemiştir.

    SADECE istenen formatta ve sadece gerekiyorsa kısa (bir iki cümlelik) açıklamayla yanıtla."""
        }

# Prompt şablonlarını yükle
_PROMPT_TEMPLATES = load_prompt_templates()

# Varsayılan analiz şablonu (JSON'dan yüklenir)
DEFAULT_PROMPT_TEMPLATE = _PROMPT_TEMPLATES.get("default_prompt_template", "")

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
        f.write(f"Özel prompt verildi mi: {custom_prompt is not None}\n")

    # Kullanılacak kategorileri belirle
    analysis_categories = categories if categories is not None else DEFAULT_ANALYSIS_CATEGORIES

    # DEBUG: Log kategorileri
    with open('/tmp/llm_debug/info.txt', 'a') as f:
        f.write(f"Kullanılan kategoriler: {analysis_categories}\n")

    # Özel kategoriler mi kontrol et
    is_custom_analysis = any(key.startswith('custom_') for key in analysis_categories.keys())

    # Prompt oluşturma
    if custom_prompt is not None:
        # Özel prompt verilmişse onu kullan
        prompt_template = custom_prompt
        with open('/tmp/llm_debug/info.txt', 'a') as f:
            f.write("Özel prompt kullanılıyor\n")
    elif is_custom_analysis:
        # Özel kategoriler var ama prompt verilmemişse, JSON'dan şablonu al ve oluştur
        custom_prefix = _PROMPT_TEMPLATES.get("custom_categories_prompt_template", 
            "Bu PDF bir öğrenci projesidir. Aşağıdaki soruları analiz et ve her biri için\n        KISA VE NET cevap ver:")
        custom_suffix = _PROMPT_TEMPLATES.get("custom_categories_prompt_suffix", """
            İşte PDF'in içeriği:

            {content}

            Her soru için şu formatta KISA cevap ver:
            1. Başlık adını yaz ve ardından iki nokta üst üste koy
            2. Evet/Hayır ile başla
            3. Çok kısa açıklama ekle (maksimum 1-2 cümle)
            4. Fazla detaya girme, sadece temel bilgiyi ver

            Örnek:
            Proje Tanımı:
            Evet, 2. sayfada "Proje Tanımı" başlığı altında kapsamlı bir şekilde ele alınmıştır.

            GitHub Linki:
            Evet, 5. bölümde repository linki paylaşılmıştır (https://github.com/example/repo).

            Grup Üyeleri:
            Hayır, grup üyelerinin listesi dokümanda belirtilmemiştir.

            SADECE istenen formatta yanıtla, ekstra açıklama yapma.""")
        
        prompt_template = custom_prefix

        # Kategorileri prompt'a ekle
        for category_key, category_title in analysis_categories.items():
            if category_key.startswith('custom_'):
                # Başlık adını temizle
                clean_title = category_title.strip().rstrip(':').rstrip('?')
                prompt_template += f"• {clean_title}\n"

        prompt_template += custom_suffix

        with open('/tmp/llm_debug/info.txt', 'a') as f:
            f.write("Özel kategoriler için otomatik prompt oluşturuldu\n")
    else:
        # Varsayılan kategoriler için mevcut prompt'u kullan
        prompt_template = DEFAULT_PROMPT_TEMPLATE
        with open('/tmp/llm_debug/info.txt', 'a') as f:
            f.write("Varsayılan prompt kullanılıyor\n")

    # DEBUG: Log prompt template
    with open('/tmp/llm_debug/info.txt', 'a') as f:
        f.write(f"Kullanılan prompt türü: {'ÖZEL' if custom_prompt else ('ÖZEL_KATEGORI' if is_custom_analysis else 'VARSAYILAN')}\n")
        f.write(f"Prompt şablonu (ilk 300 karakter): {prompt_template[:300]}...\n")

    try:
        # LLM istemcisini al
        client = get_llm_client()

        # Optimizasyon: PDF içeriği zenginliğine göre sorgu yaklaşımını belirle
        if len(text_chunks) <= 2:
            full_content = "\n\n".join(text_chunks)

            if len(full_content) < 50000:  # Token limit güvenliği
                # DEBUG: Log birleştirme bilgisi
                with open('/tmp/llm_debug/info.txt', 'a') as f:
                    f.write(f"Az sayıda chunk olduğu için tüm içerik birleştirildi: {len(full_content)} karakter\n")

                prompt = prompt_template.format(content=full_content)
                result = client.generate(prompt, options={"temperature": 0.3})  # Daha düşük sıcaklık
                results.append(result)

                # DEBUG: Log LLM response
                with open('/tmp/llm_debug/info.txt', 'a') as f:
                    f.write(f"Birleştirilmiş içerik için LLM yanıtı (ilk 300 karakter): {result[:300]}...\n")
            else:
                # Çok büyükse tek tek ilerle
                for chunk in text_chunks:
                    prompt = prompt_template.format(content=chunk)
                    result = client.generate(prompt, options={"temperature": 0.3})
                    results.append(result)
        else:
            # Standard: Her parça için LLM'e istek gönder
            for chunk in text_chunks:
                prompt = prompt_template.format(content=chunk)

                # DEBUG: Log current prompt
                with open('/tmp/llm_debug/info.txt', 'a') as f:
                    f.write(f"LLM'e gönderilen prompt (ilk 200 karakter): {prompt[:200]}...\n")

                try:
                    result = client.generate(prompt, options={"temperature": 0.3})
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
        print(f"LLM analiz hatası: {str(e)}")
        print(traceback.format_exc())

        error_msg = f"LLM Sistem Hatası: {str(e)}"
        results.append(error_msg)

        # DEBUG: Log error
        with open('/tmp/llm_debug/info.txt', 'a') as f:
            f.write(f"Sistem hatası: {error_msg}\n")

    # Sonuçları birleştir ve analiz et
    # Eğer XML veya JSON formatındaysa, sonuçları birleştirmek yerine ilk geçerli XML/JSON'u kullan
    combined_results = None
    if len(results) > 1:
        # Birden fazla sonuç varsa, XML veya JSON formatında olan ilkini bul
        import xml.etree.ElementTree as ET
        for result in results:
            try:
                cleaned = result.strip()
                # Markdown code block temizle
                if cleaned.startswith('```'):
                    lines = cleaned.split('\n')
                    cleaned = '\n'.join(lines[1:-1])
                
                # Önce XML olup olmadığını kontrol et
                try:
                    ET.fromstring(cleaned)
                    combined_results = cleaned
                    break
                except:
                    # XML değilse JSON'u dene
                    try:
                        json.loads(cleaned)
                        combined_results = cleaned
                        break
                    except:
                        continue
            except:
                continue
        # XML/JSON bulunamadıysa birleştir
        if combined_results is None:
            combined_results = " ".join(results)
    else:
        combined_results = results[0] if results else "Analiz sonucu alınamadı."

    # Sonuçları ayrıştır
    final_analysis = parse_llm_results(combined_results, analysis_categories)

    # DEBUG: Final log
    with open('/tmp/llm_debug/info.txt', 'a') as f:
        f.write(f"Final analiz: {final_analysis}\n")
        f.write("--- LLM ANALIZ TAMAMLANDI ---\n")

    return final_analysis

def parse_llm_results(results, categories=None):
    """
    LLM sonuçlarını ayrıştırır ve yapılandırılmış bir veri oluşturur
    JSON formatında yanıt bekler ve parse eder

    Args:
        results: LLM'den gelen sonuç metni (JSON formatında olmalı)
        categories: Kullanılacak kategoriler (None ise varsayılan kategoriler kullanılır)
    """
    print(f"Ayrıştırılacak LLM sonucu: {results}")

    # Debug dizininin varlığını kontrol et, yoksa oluştur
    debug_dir = '/tmp/llm_debug'
    if not os.path.exists(debug_dir):
        os.makedirs(debug_dir)

    # Kullanılacak kategorileri belirle
    if categories is None:
        analysis_categories = DEFAULT_ANALYSIS_CATEGORIES
    else:
        analysis_categories = categories

    # Sonuç şablonunu oluştur - tüm kategoriler için boş liste oluştur
    analysis = {}
    analysis["ham_sonuc"] = results if results else "Sonuç alınamadı."

    # Tüm kategori anahtarlarını ekle
    for key in analysis_categories.keys():
        analysis[key] = []

    # Sonuç boşsa veya None ise, boş analiz döndür
    if not results:
        return analysis

    # Önce XML formatında yanıt olup olmadığını kontrol et
    xml_data = None
    json_data = None
    
    try:
        import xml.etree.ElementTree as ET
        
        # Markdown code block içinde XML olabilir, temizle
        cleaned_results = results.strip()
        if cleaned_results.startswith('```'):
            # Markdown code block'u temizle
            lines = cleaned_results.split('\n')
            # İlk ve son satırları (```xml ve ```) atla
            cleaned_results = '\n'.join(lines[1:-1])
        elif cleaned_results.startswith('```xml'):
            lines = cleaned_results.split('\n')
            cleaned_results = '\n'.join(lines[1:-1])
        
        # XML parse et
        root = ET.fromstring(cleaned_results)
        
        # Yeni format: <analysis_result> root elementi olabilir
        analysis_result = root if root.tag == 'analysis_result' else root.find('analysis_result')
        if analysis_result is None:
            # Eski format: direkt root'tan oku
            analysis_result = root
        
        # XML'i dict'e çevir
        xml_data = {}
        
        # Yeni format: group_members, responsibilities, diagrams_info, main_headings, missing_sections
        # Eski format: grup_uyeleri, sorumluluk_paylasimi, diyagram_cizenler, ana_basliklar, eksik_analizi
        
        # Grup üyeleri
        group_members = analysis_result.find('group_members')
        if group_members is not None:
            xml_data['grup_uyeleri'] = [member.text.strip() for member in group_members.findall('member') if member.text]
        else:
            # Eski format
            grup_uyeleri = analysis_result.find('grup_uyeleri')
            if grup_uyeleri is not None:
                xml_data['grup_uyeleri'] = [uye.text.strip() for uye in grup_uyeleri.findall('uye') if uye.text]
        
        # Sorumluluklar
        responsibilities = analysis_result.find('responsibilities')
        if responsibilities is not None:
            xml_data['sorumluluk_paylasimi'] = [item.text.strip() for item in responsibilities.findall('item') if item.text]
        else:
            # Eski format
            sorumluluk = analysis_result.find('sorumluluk_paylasimi')
            if sorumluluk is not None:
                xml_data['sorumluluk_paylasimi'] = [gorev.text.strip() for gorev in sorumluluk.findall('gorev') if gorev.text]
        
        # Diyagramlar
        diagrams_info = analysis_result.find('diagrams_info')
        if diagrams_info is not None:
            diyagram_text = diagrams_info.text.strip() if diagrams_info.text else ""
            # Eğer "Belirtilmemiş" ise boş string olarak işaretle (sonra boş liste olacak)
            if diyagram_text.lower() in ['belirtilmemiş', 'bilgi bulunamadı', '']:
                xml_data['diyagram_cizenler'] = ""
            else:
                xml_data['diyagram_cizenler'] = diyagram_text
        else:
            # Eski format
            diyagram = analysis_result.find('diyagram_cizenler')
            if diyagram is not None:
                diyagram_text = diyagram.text.strip() if diyagram.text else ""
                if diyagram_text.lower() in ['belirtilmemiş', 'bilgi bulunamadı', '']:
                    xml_data['diyagram_cizenler'] = ""
                else:
                    xml_data['diyagram_cizenler'] = diyagram_text
        
        # Ana başlıklar
        main_headings = analysis_result.find('main_headings')
        if main_headings is not None:
            xml_data['ana_basliklar'] = [heading.text.strip() for heading in main_headings.findall('heading') if heading.text]
        else:
            # Eski format
            basliklar = analysis_result.find('ana_basliklar')
            if basliklar is not None:
                xml_data['ana_basliklar'] = [baslik.text.strip() for baslik in basliklar.findall('baslik') if baslik.text]
        
        # Eksik analizi
        missing_sections = analysis_result.find('missing_sections')
        if missing_sections is not None:
            eksik_text = missing_sections.text.strip() if missing_sections.text else ""
            # Eğer "Bilgi bulunamadı" ise boş string olarak işaretle
            if eksik_text.lower() in ['bilgi bulunamadı', '']:
                xml_data['eksik_analizi'] = ""
            else:
                xml_data['eksik_analizi'] = eksik_text
        else:
            # Eski format
            eksik = analysis_result.find('eksik_analizi')
            if eksik is not None:
                eksik_text = eksik.text.strip() if eksik.text else ""
                if eksik_text.lower() in ['bilgi bulunamadı', '']:
                    xml_data['eksik_analizi'] = ""
                else:
                    xml_data['eksik_analizi'] = eksik_text
        
        # Debug log
        with open('/tmp/llm_debug/info.txt', 'a') as f:
            f.write(f"\n--- XML PARSING BAŞARILI ---\n")
            f.write(f"Parse edilen XML: {xml_data}\n")
        
    except ET.ParseError as e:
        # XML parse edilemedi, JSON'a geç
        with open('/tmp/llm_debug/info.txt', 'a') as f:
            f.write(f"\n--- XML PARSING BAŞARISIZ, JSON'A GEÇİLİYOR ---\n")
            f.write(f"XML hatası: {e}\n")
        xml_data = None
    except Exception as e:
        # Diğer hatalar
        with open('/tmp/llm_debug/info.txt', 'a') as f:
            f.write(f"\n--- XML PARSING BAŞARISIZ (Genel hata), JSON'A GEÇİLİYOR ---\n")
            f.write(f"Hata: {e}\n")
        xml_data = None
    
    # XML parse edilemediyse JSON'u dene
    if xml_data is None:
        try:
            # Markdown code block içinde JSON olabilir, temizle
            cleaned_results = results.strip()
            if cleaned_results.startswith('```'):
                # Markdown code block'u temizle
                lines = cleaned_results.split('\n')
                # İlk ve son satırları (```json ve ```) atla
                cleaned_results = '\n'.join(lines[1:-1])
            elif cleaned_results.startswith('```json'):
                lines = cleaned_results.split('\n')
                cleaned_results = '\n'.join(lines[1:-1])
            
            # JSON parse et
            json_data = json.loads(cleaned_results)
            
            # Debug log
            with open('/tmp/llm_debug/info.txt', 'a') as f:
                f.write(f"\n--- JSON PARSING BAŞARILI ---\n")
                f.write(f"Parse edilen JSON: {json_data}\n")
            
        except json.JSONDecodeError as e:
            # JSON parse edilemedi, eski text parsing yöntemine geri dön
            with open('/tmp/llm_debug/info.txt', 'a') as f:
                f.write(f"\n--- JSON PARSING BAŞARISIZ, TEXT PARSING'E GEÇİLİYOR ---\n")
                f.write(f"JSON hatası: {e}\n")
            json_data = None

    # XML başarıyla parse edildiyse, direkt kullan
    if xml_data:
        # Yeni XML formatından eski kategori formatına mapping
        xml_to_category_mapping = {
            "grup_uyeleri": "grup_uyeleri",  # Aynı
            "sorumluluk_paylasimi": "sorumluluklar",
            "diyagram_cizenler": "diyagramlar",
            "ana_basliklar": "basliklar",
            "eksik_analizi": "eksikler"
        }
        
        # XML'den gelen verileri analiz dict'ine aktar
        for xml_key, xml_value in xml_data.items():
            # Kategori mapping'i yap
            category_key = xml_to_category_mapping.get(xml_key, xml_key)
            
            # Eğer kategori mevcut kategoriler arasındaysa ekle
            if category_key in analysis_categories:
                if isinstance(xml_value, list):
                    # Liste ise direkt ekle
                    analysis[category_key] = xml_value
                elif isinstance(xml_value, str):
                    # String ise liste olarak ekle
                    if xml_value and xml_value.lower() not in ['bilgi bulunamadı', 'belirtilmemiş', 'null', 'none', '']:
                        analysis[category_key] = [xml_value]
                    else:
                        analysis[category_key] = []
                else:
                    # Diğer tipler için string'e çevir
                    analysis[category_key] = [str(xml_value)] if xml_value else []
        
        # Grup üyeleri için temizleme yap
        if "grup_uyeleri" in analysis:
            cleaned_members = []
            for item in analysis["grup_uyeleri"]:
                cleaned = clean_group_member_name(str(item))
                if cleaned:
                    cleaned_members.append(cleaned)
            analysis["grup_uyeleri"] = cleaned_members
        
        # Debug log
        with open('/tmp/llm_debug/info.txt', 'a') as f:
            f.write(f"\n--- XML PARSING SONUÇLARI ---\n")
            for category, items in analysis.items():
                if category != "ham_sonuc":
                    f.write(f"{category}: {len(items)} madde - {items}\n")
            f.write("--- XML PARSING TAMAMLANDI ---\n\n")
        
        return analysis
    
    # JSON başarıyla parse edildiyse, direkt kullan
    if json_data:
        # Yeni JSON formatından eski kategori formatına mapping
        json_to_category_mapping = {
            "grup_uyeleri": "grup_uyeleri",  # Aynı
            "sorumluluk_paylasimi": "sorumluluklar",
            "diyagram_cizenler": "diyagramlar",
            "ana_basliklar": "basliklar",
            "eksik_analizi": "eksikler"
        }
        
        # JSON'dan gelen verileri analiz dict'ine aktar
        for json_key, json_value in json_data.items():
            # Kategori mapping'i yap
            category_key = json_to_category_mapping.get(json_key, json_key)
            
            # Eğer kategori mevcut kategoriler arasındaysa ekle
            if category_key in analysis_categories:
                if isinstance(json_value, list):
                    # Liste ise direkt ekle
                    analysis[category_key] = json_value
                elif isinstance(json_value, str):
                    # String ise liste olarak ekle
                    if json_value and json_value.lower() not in ['bilgi bulunamadı', 'belirtilmemiş', 'null', 'none']:
                        analysis[category_key] = [json_value]
                    else:
                        analysis[category_key] = []
                else:
                    # Diğer tipler için string'e çevir
                    analysis[category_key] = [str(json_value)] if json_value else []
        
        # Grup üyeleri için temizleme yap
        if "grup_uyeleri" in analysis:
            cleaned_members = []
            for item in analysis["grup_uyeleri"]:
                cleaned = clean_group_member_name(str(item))
                if cleaned:
                    cleaned_members.append(cleaned)
            analysis["grup_uyeleri"] = cleaned_members
        
        # Debug log
        with open('/tmp/llm_debug/info.txt', 'a') as f:
            f.write(f"\n--- JSON PARSING SONUÇLARI ---\n")
            for category, items in analysis.items():
                if category != "ham_sonuc":
                    f.write(f"{category}: {len(items)} madde - {items}\n")
            f.write("--- JSON PARSING TAMAMLANDI ---\n\n")
        
        return analysis

    # Özel kategoriler için ayrıştırma kontrolü (JSON parse edilemediyse eski yöntem)
    is_custom_analysis = any(key.startswith('custom_') for key in analysis_categories.keys())

    # Debug log
    with open('/tmp/llm_debug/info.txt', 'a') as f:
        f.write(f"\n--- PARSING BAŞLADI ---\n")
        f.write(f"Özel analiz mi: {is_custom_analysis}\n")
        f.write(f"Kategoriler: {analysis_categories}\n")
        f.write(f"Ham sonuç (ilk 500 karakter): {results[:500]}...\n")

    if is_custom_analysis:
        # Özel başlıklar için geliştirilmiş ayrıştırma
        lines = results.split('\n')
        current_category = None
        current_content = []

        # Kategori başlıklarını ve karşılık gelen anahtarları hazırla
        category_mapping = {}
        for key, title in analysis_categories.items():
            if key.startswith('custom_'):
                # Başlığı temizle ve farklı varyasyonlarını kaydet
                clean_title = title.strip().rstrip(':').rstrip('?').lower()
                category_mapping[clean_title] = key

                # Daha fazla alternatif format ekle
                if clean_title.endswith(' nedir'):
                    alt_title = clean_title[:-6].strip()
                    category_mapping[alt_title] = key
                if clean_title.endswith(' kimler'):
                    alt_title = clean_title[:-7].strip()
                    category_mapping[alt_title] = key
                if clean_title.endswith(' nelerdir'):
                    alt_title = clean_title[:-8].strip()
                    category_mapping[alt_title] = key
                if clean_title.endswith(' var mı'):
                    alt_title = clean_title[:-6].strip()
                    category_mapping[alt_title] = key
                if clean_title.endswith(' mı'):
                    alt_title = clean_title[:-3].strip()
                    category_mapping[alt_title] = key

                # Orijinal başlığı da ekle (büyük-küçük harf duyarlı olmadan)
                category_mapping[title.strip().rstrip(':').rstrip('?').lower()] = key

        # Debug log
        with open('/tmp/llm_debug/info.txt', 'a') as f:
            f.write(f"Kategori eşlemeleri: {category_mapping}\n")

        # Her satırı işle - KISA YANITLAR İÇİN OPTİMİZE EDİLMİŞ
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue

            # Debug log her satır için
            with open('/tmp/llm_debug/info.txt', 'a') as f:
                f.write(f"Satır {i}: '{line}'\n")

            # Başlık kontrolü - iki nokta üst üste içeren satırları ara
            if ':' in line and not line.startswith('•') and not line.startswith('-'):
                parts = line.split(':', 1)
                potential_title = parts[0].strip().lower()
                content_part = parts[1].strip() if len(parts) > 1 else ""

                # Debug log
                with open('/tmp/llm_debug/info.txt', 'a') as f:
                    f.write(f"  Potansiyel başlık: '{potential_title}', içerik: '{content_part}'\n")

                # Başlık eşleşmesi ara - daha esnek eşleştirme
                matched_category = None
                best_match_score = 0

                for title_key, category_key in category_mapping.items():
                    # Tam eşleşme kontrolü
                    if potential_title == title_key:
                        matched_category = category_key
                        best_match_score = 100
                        break

                    # Kısmi eşleşme kontrolü - kelimeleri karşılaştır
                    title_words = set(title_key.split())
                    potential_words = set(potential_title.split())

                    # Ortak kelime sayısını hesapla
                    common_words = title_words.intersection(potential_words)
                    if common_words:
                        # Eşleşme puanı: ortak kelimeler / toplam benzersiz kelimeler
                        match_score = len(common_words) / len(title_words.union(potential_words)) * 100
                        if match_score > best_match_score and match_score > 40:  # %40'tan fazla eşleşme
                            matched_category = category_key
                            best_match_score = match_score

                if matched_category:
                    # Önceki kategorinin içeriğini kaydet
                    if current_category and current_content:
                        # Kısa yanıtları birleştir
                        combined_response = " ".join(current_content).strip()
                        if combined_response and not any(skip in combined_response.lower() for skip in ['bu konuda bilgi bulunamadı', 'bilgi bulunamadı', 'veri bulunamadı']):
                            # Eğer grup üyeleri kategorisindeyse temizle
                            if current_category == "grup_uyeleri" or (isinstance(current_category, str) and "grup" in current_category.lower() and "üye" in current_category.lower()):
                                combined_response = clean_group_member_name(combined_response)
                                if combined_response:  # Sadece temizlenmiş değer varsa ekle
                                    analysis[current_category].append(combined_response)
                            else:
                                analysis[current_category].append(combined_response)

                        # Debug log
                        with open('/tmp/llm_debug/info.txt', 'a') as f:
                            f.write(f"  Kaydedilen kategori: {current_category}, birleştirilmiş yanıt: {combined_response}\n")

                    # Yeni kategoriyi ayarla
                    current_category = matched_category
                    current_content = []

                    # Bu satırda başlığın yanında içerik varsa, onu da ekle
                    if content_part and not any(skip in content_part.lower() for skip in ['bu konuda bilgi bulunamadı', 'bilgi bulunamadı', 'veri bulunamadı']):
                        current_content.append(content_part)

                    # Sonraki satırları da bu başlığa ait olarak kontrol et (kısa yanıtlarda genellikle tek satırda biter)
                    j = i + 1
                    while j < len(lines) and j < i + 3:  # Maksimum 2 satır daha kontrol et
                        next_line = lines[j].strip()
                        # Eğer sonraki satır yeni bir başlık değilse ve boş değilse, mevcut içeriğe ekle
                        if next_line and ':' not in next_line and not next_line.startswith('•'):
                            current_content.append(next_line)
                            j += 1
                        else:
                            break

                    # Debug log
                    with open('/tmp/llm_debug/info.txt', 'a') as f:
                        f.write(f"  Yeni kategori: {current_category} (eşleşme puanı: {best_match_score:.1f})\n")
                        f.write(f"  Başlangıç içeriği: {current_content}\n")

                    # i'yi son işlenen satıra kadar ilerlet
                    i = j - 1

            i += 1

        # Son kategorinin içeriğini kaydet
        if current_category and current_content:
            combined_response = " ".join(current_content).strip()
            if combined_response and not any(skip in combined_response.lower() for skip in ['bu konuda bilgi bulunamadı', 'bilgi bulunamadı', 'veri bulunamadı']):
                # Eğer grup üyeleri kategorisindeyse temizle
                if current_category == "grup_uyeleri" or (isinstance(current_category, str) and "grup" in current_category.lower() and "üye" in current_category.lower()):
                    combined_response = clean_group_member_name(combined_response)
                    if combined_response:  # Sadece temizlenmiş değer varsa ekle
                        analysis[current_category].append(combined_response)
                else:
                    analysis[current_category].append(combined_response)

            # Debug log
            with open('/tmp/llm_debug/info.txt', 'a') as f:
                f.write(f"Son kategori kaydedildi: {current_category}, birleştirilmiş yanıt: {combined_response}\n")
        
        # Özel kategoriler için grup üyeleri temizlemesi
        for category_key in analysis_categories.keys():
            if category_key == "grup_uyeleri" or (isinstance(category_key, str) and "grup" in category_key.lower() and "üye" in category_key.lower()):
                if category_key in analysis:
                    cleaned_items = []
                    for item in analysis[category_key]:
                        cleaned = clean_group_member_name(item)
                        if cleaned:
                            cleaned_items.append(cleaned)
                    analysis[category_key] = cleaned_items

    else:
        # Standart kategoriler için mevcut ayrıştırma mantığı
        lines = results.split('\n')
        current_category = None
        current_content = []

        # Kategoriler ve anahtar kelimelerin eşleşmeleri
        category_keywords = {
            "grup_uyeleri": ["grup üyeleri", "öğrenci", "öğrenciler", "üye", "grup", "ekip"],
            "sorumluluklar": ["sorumlu", "sorumluluk", "görev", "bölüm sorumlu"],
            "diyagramlar": ["diyagramları kim çizmiş", "diyagram", "çizim", "çizen", "şema"],
            "basliklar": ["başlık", "konu", "bölüm"],
            "eksikler": ["eksik kısımlar", "eksik", "bulunmayan", "yetersiz", "yok"]
        }

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Debug için satırı yazdır
            print(f"İşlenen satır: '{line}'")

            # Kategori başlıklarını tespit et
            lower_line = line.lower()

            # Aktif kategoriyi güncelle
            for category, keywords in category_keywords.items():
                if category in analysis_categories:
                    # Numaralı başlık kontrolü
                    if line[0].isdigit() and '. ' in line:
                        number, rest = line.split('. ', 1)
                        if any(kw.lower() in rest.lower() for kw in keywords):
                            if current_category and current_content:
                                analysis[current_category].extend(current_content)
                                current_content = []
                            current_category = category
                            print(f"Kategori değişti: {current_category}")
                            break
                    # Normal başlık kontrolü
                    elif any(kw.lower() in lower_line for kw in keywords):
                        if current_category and current_content:
                            analysis[current_category].extend(current_content)
                            current_content = []
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
                if line and len(line) > 2:
                    # Kategori başlığı içermeyen satırları ekle
                    if not any(kw.lower() in line.lower() for kw in category_keywords[current_category]):
                        # Eğer grup üyeleri kategorisindeyse temizle
                        if current_category == "grup_uyeleri":
                            cleaned_line = clean_group_member_name(line)
                            if cleaned_line:  # Sadece temizlenmiş değer varsa ekle
                                current_content.append(cleaned_line)
                                print(f"Eklendi (temizlenmiş): {current_category} <- '{cleaned_line}'")
                        else:
                            current_content.append(line)
                            print(f"Eklendi: {current_category} <- '{line}'")

        # Son kategorinin içeriğini kaydet
        if current_category and current_content:
            # Eğer grup üyeleri kategorisindeyse temizle
            if current_category == "grup_uyeleri":
                cleaned_content = []
                for item in current_content:
                    cleaned = clean_group_member_name(item)
                    if cleaned:
                        cleaned_content.append(cleaned)
                analysis[current_category].extend(cleaned_content)
            else:
                analysis[current_category].extend(current_content)

        # Diyagramlar için özel işlem
        if "diyagramlar" in analysis_categories and not analysis["diyagramlar"]:
            for line in lines:
                if "diyagram" in line.lower() and ":" in line:
                    parts = line.split(":", 1)
                    if len(parts) > 1 and "tarafından" in parts[1].lower():
                        analysis["diyagramlar"].append(parts[1].strip())

        # Eksikler için özel işlem
        if "eksikler" in analysis_categories and not analysis["eksikler"]:
            for line in lines:
                lower_line = line.lower()
                if any(kw in lower_line for kw in ["eksik", "yapılmamış", "bulunmamaktadır", "yok"]):
                    # Madde işaretini temizle
                    if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                        line = line[1:].strip()
                    # Kategori başlığı değilse ekle
                    if not any(kw in lower_line for kw in category_keywords["eksikler"]):
                        analysis["eksikler"].append(line)

    # Grup üyeleri için temizleme yap (şehir, kurum gibi ekstra bilgileri kaldır)
    if "grup_uyeleri" in analysis:
        cleaned_members = []
        for item in analysis["grup_uyeleri"]:
            cleaned = clean_group_member_name(item)
            if cleaned:
                cleaned_members.append(cleaned)
        analysis["grup_uyeleri"] = cleaned_members

    # Her kategori için sonuçları yazdır (hata ayıklama)
    with open('/tmp/llm_debug/info.txt', 'a') as f:
        f.write(f"\n--- PARSING SONUÇLARI ---\n")
        for category, items in analysis.items():
            if category != "ham_sonuc":
                f.write(f"{category}: {len(items)} madde - {items}\n")
        f.write("--- PARSING TAMAMLANDI ---\n\n")

    return analysis

def clean_group_member_name(member_text):
    """
    Grup üyesi isimlerinden şehir, kurum, üniversite gibi ekstra bilgileri temizler
    
    Args:
        member_text: Ham grup üyesi metni (örn: "Ahmet Yılmaz: İstanbul, Türkiye")
    
    Returns:
        str: Temizlenmiş sadece isim (örn: "Ahmet Yılmaz")
    """
    if not member_text:
        return ""
    
    # Madde işaretlerini temizle
    text = member_text.strip()
    if text.startswith('•') or text.startswith('-') or text.startswith('*'):
        text = text[1:].strip()
    
    # İki nokta üst üste varsa, sadece öncesini al (isim kısmı)
    if ':' in text:
        text = text.split(':')[0].strip()
    
    # Virgül varsa kontrol et
    if ',' in text:
        parts = [p.strip() for p in text.split(',')]
        # Eğer 2 parça varsa ve ikincisi kısa ise (soyadı, adı formatı olabilir)
        if len(parts) == 2 and len(parts[1].split()) <= 2:
            # İkinci parçanın şehir/kurum olup olmadığını kontrol et
            second_part_lower = parts[1].lower()
            # Şehir, üniversite, kurum gibi kelimeler içeriyorsa ilk parçayı al
            unwanted_keywords = ['üniversite', 'university', 'fakülte', 'faculty', 'bölüm', 'department', 
                                'türkiye', 'turkey', 'kurum', 'institution', 'adres', 'address', 'şehir', 'city']
            if any(keyword in second_part_lower for keyword in unwanted_keywords):
                text = parts[0]
            else:
                # Muhtemelen "Soyadı, Adı" formatı, birleştir
                text = f"{parts[1]} {parts[0]}"
        else:
            # İlk kısmı al (isim)
            text = parts[0]
    
    # Şehir, üniversite, kurum gibi kelimeleri içeriyorsa temizle
    import re
    # Türkçe şehir isimleri (en yaygın olanlar)
    turkish_cities = ['istanbul', 'ankara', 'izmir', 'bursa', 'antalya', 'adana', 'gaziantep', 'konya', 
                     'kayseri', 'mersin', 'eskisehir', 'diyarbakir', 'samsun', 'denizli', 'sanliurfa', 
                     'malatya', 'erzurum', 'van', 'batman', 'elazig', 'sivas', 'trabzon', 'manisa', 
                     'kocaeli', 'balikesir', 'tekirdag', 'aydin', 'osmaniye', 'kilis', 'kirikkale', 
                     'aksaray', 'duzce', 'sakarya', 'afyon', 'isparta', 'burdur', 'mugla', 'usak', 
                     'kutahya', 'bilecik', 'bolu', 'bartin', 'karabuk', 'zonguldak', 'kastamonu', 
                     'sinop', 'ordu', 'giresun', 'rize', 'artvin', 'ardahan', 'kars', 'agri', 'igdir', 
                     'erzincan', 'bingol', 'mus', 'bitlis', 'siirt', 'hakkari', 'mardin', 'sirnak', 
                     'hatay', 'nevsehir', 'nigde', 'yozgat', 'corum', 'amasya', 'tokat', 'gumushane', 
                     'bayburt', 'tunceli', 'adiyaman', 'canakkale', 'edirne', 'kirklareli']
    
    # Kelimeleri kontrol et
    words = text.split()
    cleaned_words = []
    for word in words:
        word_lower = word.lower().strip('.,;:()[]{}')
        # Şehir ismi, üniversite, kurum gibi kelimeleri atla
        if (word_lower in turkish_cities or 
            any(keyword in word_lower for keyword in ['üniversite', 'university', 'üniv', 'univ', 'fakülte', 
                                                      'faculty', 'bölüm', 'department', 'türkiye', 'turkey', 
                                                      'kurum', 'institution', 'adres', 'address', 'şehir', 'city', 'il'])):
            continue
        cleaned_words.append(word)
    
    text = ' '.join(cleaned_words)
    
    # Fazla boşlukları temizle
    text = ' '.join(text.split())
    
    # Eğer çok kısa kaldıysa (2 karakterden az) veya sadece noktalama varsa, boş döndür
    if len(text.strip()) < 2 or text.strip() in ['.', ',', ':', ';', '-']:
        return ""
    
    return text.strip()

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