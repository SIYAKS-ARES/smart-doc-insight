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
DEFAULT_PROMPT_TEMPLATE = """Bu PDF bir öğrenci projesidir. İçeriği detaylı bir şekilde analiz et ve şu bilgileri çıkar:
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
    6. Eksikler bölümünde sadece dokümanda olması gerekip de bulunmayan önemli kısımları belirt"""

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
    
    # Prompt optimizasyon: İçerik zenginliğine ve kategorilere göre prompt uyarla
    if custom_prompt is None:
        # Başlık eşleştirmeleri için anahtar kelimeler tanımla
        keywords = {
            "grup_uyeleri": ["üye", "öğrenci", "grup", "ekip", "takım", "kişi", "isim"],
            "sorumluluklar": ["sorumluluk", "görev", "rol", "bölüm", "iş", "vazife"],
            "diyagramlar": ["diyagram", "şema", "çizim", "grafik", "görsel", "çizen"],
            "basliklar": ["başlık", "bölüm", "kısım", "içindekiler", "konu", "alt başlık"],
            "eksikler": ["eksik", "hata", "yanlış", "olmayan", "ihmal", "unutulmuş"]
        }
        
        # Temel prompt oluştur
        prompt_template = "Bu PDF bir öğrenci projesidir. İçeriği detaylı şekilde analiz et ve aşağıdaki bilgileri çıkar:\n"
        
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
    3. Bilgi bulunamazsa SADECE "Bu konuda bilgi bulunamadı" yaz.
    4. Yanıtını maddeler halinde ver, her maddeyi • işaretiyle başlat.
    5. Kesinlikle başlıkların dışına çıkma ve başlık tekrarı yapma.
    6. Başlıkları tam olarak verilen metinle kullan.
    7. Analiz yaparken öğrenci projelerinde olması gereken resmi format ve standartlara göre değerlendir.
    8. Grup üyelerini tam isim-soyisim olarak çıkarmaya özen göster.
    9. Diyagram çizenler belirtilmişse tam isimleriyle yaz.
    10. Başlıkları belirgin şekilde ayrıştır ve maddelendir.
    11. Eksik kısımları net olarak belirt (diyagramlar, akış şemaları, içindekiler tablosu, sonuç, vb.)."""
    else:
        # Özel prompt varsa, prompt'a yapılandırma talimatlarını ekle
        if not "Yanıtını aşağıdaki şekilde yapılandır:" in custom_prompt:
            prompt_template = custom_prompt.rstrip() + """
    
    Yanıtını aşağıdaki şekilde yapılandır:
    1. Her başlık için yanıtı ayrı bir bölüm olarak ver.
    2. Her bölümü başlık adıyla başlat (örn: "Grup üyeleri:").
    3. Bilgi bulunamazsa SADECE "Bu konuda bilgi bulunamadı" yaz.
    4. Yanıtını maddeler halinde ver, her maddeyi • işaretiyle başlat.
    5. Kesinlikle başlıkların dışına çıkma ve başlık tekrarı yapma.
    6. Başlıkları tam olarak verilen metinle kullan.
    7. Öğrenci projelerinde olması gereken resmi format ve standartlara göre değerlendir."""
        else:
            prompt_template = custom_prompt
    
    # DEBUG: Log prompt template
    with open('/tmp/llm_debug/info.txt', 'a') as f:
        f.write(f"Prompt şablonu: {prompt_template}\n")
    
    try:
        # LLM istemcisini al
        client = get_llm_client()
        
        # Optimizasyon: PDF içeriği zenginliğine göre sorgu yaklaşımını belirle
        # Eğer text_chunks sayısı 1 veya 2 ise, tüm içeriği birleştirebiliriz
        if len(text_chunks) <= 2:
            full_content = "\n\n".join(text_chunks)
            
            # Çok büyük olmadığından emin ol, hala çok büyükse parçala
            if len(full_content) < 50000:  # Yaklaşık token limit güvenliği
                # DEBUG: Log birleştirme bilgisi
                with open('/tmp/llm_debug/info.txt', 'a') as f:
                    f.write(f"Az sayıda chunk olduğu için tüm içerik birleştirildi: {len(full_content)} karakter\n")
                
                prompt = prompt_template.format(content=full_content)
                result = client.generate(prompt, options={"temperature": 0.5})  # Daha düşük sıcaklık, daha tutarlı sonuçlar
                results.append(result)
                
                # DEBUG: Log LLM response
                with open('/tmp/llm_debug/info.txt', 'a') as f:
                    f.write(f"Birleştirilmiş içerik için LLM yanıtı (ilk 200 karakter): {result[:200]}...\n")
            else:
                # Çok büyükse tek tek ilerle
                for chunk in text_chunks:
                    prompt = prompt_template.format(content=chunk)
                    result = client.generate(prompt, options={"temperature": 0.5})
                    results.append(result)
        else:
            # Standard: Her parça için LLM'e istek gönder
            for chunk in text_chunks:
                prompt = prompt_template.format(content=chunk)
                
                # DEBUG: Log current prompt
                with open('/tmp/llm_debug/info.txt', 'a') as f:
                    f.write(f"LLM'e gönderilen prompt (ilk 200 karakter): {prompt[:200]}...\n")
                
                try:
                    # LLM Provider üzerinden yanıt al
                    result = client.generate(prompt, options={"temperature": 0.5})  # Daha düşük sıcaklık, daha tutarlı sonuçlar
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
                clean_title = title.strip().rstrip(':').split('(')[0].strip()  # Parantez içindeki açıklamaları kaldır
                
                # Başlık anahtarı eşleştirmesi
                category_titles[clean_title.lower()] = key
                category_keys_by_order.append(key)
                
                # Debug için başlık eşleştirmelerini logla
                with open('/tmp/llm_debug/info.txt', 'a') as f:
                    f.write(f"Başlık eşleştirmesi: '{clean_title.lower()}' -> {key}\n")
        
        with open('/tmp/llm_debug/info.txt', 'a') as f:
            f.write(f"Aranan kategori başlıkları: {category_titles}\n")
        
        # Her satırı kontrol et
        current_category = None
        current_content = []
        has_valuable_info = {}  # Hangi kategorilerin değerli bilgi içerdiğini izle
        
        for key in category_keys_by_order:
            has_valuable_info[key] = False
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Debug için satırı logla
            with open('/tmp/llm_debug/info.txt', 'a') as f:
                f.write(f"İşlenen satır: '{line}'\n")
            
            # Başlık kontrolü
            found_category = None
            
            # Her kategori başlığı için kontrol et
            for title, key in category_titles.items():
                # Madde işaretli satır kontrolü (• Başlık)
                if line.startswith('•') and title.lower() in line.lower():
                    if current_category and current_content:
                        # Önceki kategoriye içeriği ekle
                        if current_content:
                            # İçerik değerli mi kontrol et
                            if any("bulunamadı" not in content.lower() for content in current_content):
                                has_valuable_info[current_category] = True
                                # Değerli içerikler varsa, "bulunamadı" mesajlarını filtrele
                                filtered_content = [
                                    content for content in current_content 
                                    if not any(not_found in content.lower() for not_found in 
                                              ["bulunamadı", "bulunmamaktadır"])
                                ]
                                analysis[current_category].extend(filtered_content)
                            else:
                                analysis[current_category].extend(current_content)
                            current_content = []
                            
                    found_category = key
                    current_category = key
                    # Debug logunu kaydet
                    with open('/tmp/llm_debug/info.txt', 'a') as f:
                        f.write(f"Başlık bulundu (madde işaretli): '{line}' -> {key}\n")
                    break
                    
                # Title: Content formatını ara
                elif ':' in line:
                    parts = line.split(':', 1)
                    line_title = parts[0].strip().lower()
                    # Tam başlık eşleşmesi veya başlığın bir parçası olarak eşleşme
                    if line_title == title.lower() or title.lower() in line_title:
                        if current_category and current_content:
                            # Önceki kategoriye içeriği ekle
                            if any("bulunamadı" not in content.lower() for content in current_content):
                                has_valuable_info[current_category] = True
                                filtered_content = [
                                    content for content in current_content 
                                    if not any(not_found in content.lower() for not_found in 
                                              ["bulunamadı", "bulunmamaktadır"])
                                ]
                                analysis[current_category].extend(filtered_content)
                            else:
                                analysis[current_category].extend(current_content)
                            current_content = []
                            
                        found_category = key
                        current_category = key
                        content = parts[1].strip()
                        with open('/tmp/llm_debug/info.txt', 'a') as f:
                            f.write(f"Başlık bulundu (başlık:içerik): '{line_title}' -> {key}\n")
                            
                        # "Bu başlıkla ilgili veri bulunamadı" kontrolü
                        if not (any(not_found in content.lower() for not_found in ["veri bulunamadı", "bilgi bulunamadı", "bulunmamaktadır", "bulunamadı"])):
                            current_content.append(content)
                            # Eğer içerik değerliyse, bayrak ayarla
                            has_valuable_info[current_category] = True
                        break
            
            # Eğer mevcut bir kategorideyiz ve bu satır başlık değilse, içerik olarak ekle
            if current_category and not found_category:
                # İçerik önceki satırın devamı olabilir
                content_line = line
                
                # Madde işareti varsa temizle
                if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                    content_line = line[1:].strip()
                    
                # Eğer bir "bilgi bulunamadı" içermiyorsa içeriğe ekle
                if not any(not_found in content_line.lower() for not_found in ["veri bulunamadı", "bilgi bulunamadı", "bulunmamaktadır", "bulunamadı"]):
                    current_content.append(content_line)
                    has_valuable_info[current_category] = True
                    with open('/tmp/llm_debug/info.txt', 'a') as f:
                        f.write(f"İçerik satırı eklendi: '{content_line}'\n")
                # Eğer "bulunamadı" içeriyorsa ve henüz değerli içerik yoksa sakla
                elif not has_valuable_info[current_category]:
                    current_content.append(content_line)
                    with open('/tmp/llm_debug/info.txt', 'a') as f:
                        f.write(f"'Bulunamadı' içeriği eklendi (değerli içerik olmadığından): '{content_line}'\n")
        
        # Son kategorinin içeriğini ekle
        if current_category and current_content:
            if any("bulunamadı" not in content.lower() for content in current_content):
                has_valuable_info[current_category] = True
                filtered_content = [
                    content for content in current_content 
                    if not any(not_found in content.lower() for not_found in 
                             ["bulunamadı", "bulunmamaktadır"])
                ]
                analysis[current_category].extend(filtered_content)
            else:
                analysis[current_category].extend(current_content)
        
        # Tekrar eden içerikleri temizle
        for key in category_keys_by_order:
            # Eğer kategoride içerik varsa
            if analysis[key]:
                # Aynı içerik birden fazla kez eklenmiş olabilir
                unique_items = []
                seen = set()
                
                for item in analysis[key]:
                    # İçeriğin normalize edilmiş hali
                    normalized_item = ' '.join(item.lower().split())
                    
                    if normalized_item not in seen:
                        seen.add(normalized_item)
                        unique_items.append(item)
                
                analysis[key] = unique_items
            
        # LLM'in yanıtını direkt olarak da ekle - hiçbir şey bulunamama durumunda kullanılabilir
        analysis["raw_llm_output"] = results
            
        # Her kategori için ayrı debug bilgisi
        for key in category_keys_by_order:
            with open('/tmp/llm_debug/info.txt', 'a') as f:
                f.write(f"Sonuç kategorisi: {key} -> {analysis[key]}\n")
    else:
        # Standart analiz için ayrı ayrıştırma kodu
        # Özel durumlar için keyword tabanlı kontroller
        
        # Diyagram eksikliği kontrol et
        diyagram_eksik = False
        diyagram_keywords = ["diyagram yok", "diyagram bulunmamaktadır", "diyagram gösterilmemiş", 
                            "diyagramlar yok", "diyagram yer almadı", "bilgi yok", "bulunamadı"]
        
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
        current_content = []
        
        # Kategoriler ve anahtar kelimelerin eşleşmeleri
        category_keywords = {
            "grup_uyeleri": ["grup üyeleri", "öğrenci", "öğrenciler", "üye", "grup", "ekip"],
            "sorumluluklar": ["sorumlu", "sorumluluk", "görev", "bölüm sorumlu"],
            "diyagramlar": ["diyagram", "çizim", "çizen", "şema"],
            "basliklar": ["başlık", "konu", "bölüm", "içindekiler"],
            "eksikler": ["eksik", "bulunmayan", "yetersiz", "yok"]
        }
        
        # Hangi kategorilerin değerli bilgi içerdiğini izle
        has_valuable_info = {}
        for key in analysis_categories.keys():
            has_valuable_info[key] = False
        
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
            
            # Debug için her satırı yazdır
            print(f"İşlenen satır: '{line}'")
            
            # Aktif kategoriyi güncelle - başlık algılama
            found_category = None
            
            # ** işaretiyle veya • ile başlayan başlık satırlarını kontrol et
            if line.startswith('**') or line.startswith('•'):
                # ** işaretlerini temizle
                clean_line = line.strip('*').strip()
                # • işaretini temizle
                if clean_line.startswith('•'):
                    clean_line = clean_line[1:].strip()
                
                # Kategoriyi belirle
                lower_clean = clean_line.lower()
                
                for category, keywords in category_keywords.items():
                    if category in analysis_categories and any(kw in lower_clean for kw in keywords):
                        # Önceki kategorinin içeriğini kaydet
                        if current_category and current_content:
                            if not any("bulunamadı" in content.lower() for content in current_content):
                                has_valuable_info[current_category] = True
                            analysis[current_category].extend(current_content)
                            current_content = []
                            
                        current_category = category
                        found_category = category
                        print(f"Kategori değişti (başlık işareti): {current_category}")
                        break
            
            # "Kategori:" formatındaki satırları kontrol et
            elif ':' in line and not (line.startswith('-') or line.startswith('+')):
                parts = line.split(':', 1)
                header = parts[0].strip().lower()
                
                for category, keywords in category_keywords.items():
                    if category in analysis_categories and any(kw in header for kw in keywords):
                        # Önceki kategorinin içeriğini kaydet
                        if current_category and current_content:
                            if not any("bulunamadı" in content.lower() for content in current_content):
                                has_valuable_info[current_category] = True
                            analysis[current_category].extend(current_content)
                            current_content = []
                            
                        current_category = category
                        found_category = category
                        
                        # İçeriği ekle (başlığın sonrası)
                        content = parts[1].strip()
                        if content and not content.lower() in ["yok", "bulunamadı", "belirtilmemiş"]:
                            current_content.append(content)
                            if not any("bulunamadı" in content.lower() for content in [content]):
                                has_valuable_info[current_category] = True
                                
                        print(f"Kategori değişti (başlık:içerik): {current_category}")
                        break
            
            # Eğer mevcut kategori varsa ve başlık değilse, içerik olarak ekle
            elif current_category:
                # İçerik satırı - temizle
                content_line = line
                
                # Madde işareti varsa temizle
                if content_line.startswith('-') or content_line.startswith('•') or content_line.startswith('*'):
                    content_line = content_line[1:].strip()
                elif content_line.startswith('+'):
                    content_line = content_line[1:].strip()
                    
                # Başlık işaretlerini temizle
                if content_line.startswith('**') and content_line.endswith('**'):
                    content_line = content_line[2:-2].strip()
                elif '**' in content_line:
                    content_line = content_line.replace('**', '').strip()
                
                # Başlık metni veya "Kategori:" formatında olabileceğini kontrol et
                if ":" in content_line and not found_category:
                    parts = content_line.split(':', 1)
                    header = parts[0].strip().lower()
                    
                    # Eğer bu bir başlık ise, önceki kategoriden çık
                    for category, keywords in category_keywords.items():
                        if category in analysis_categories and any(kw in header for kw in keywords):
                            # Önceki kategorinin içeriğini kaydet
                            if current_category and current_content:
                                if not any("bulunamadı" in content.lower() for content in current_content):
                                    has_valuable_info[current_category] = True
                                analysis[current_category].extend(current_content)
                                current_content = []
                                
                            current_category = category
                            found_category = category
                            
                            # İçeriği ekle (başlığın sonrası)
                            content = parts[1].strip()
                            if content and not content.lower() in ["yok", "bulunamadı", "belirtilmemiş"]:
                                current_content.append(content)
                                if not any("bulunamadı" in content.lower() for content in [content]):
                                    has_valuable_info[current_category] = True
                                    
                            print(f"Kategori değişti (içerik içinde başlık): {current_category}")
                            break
                
                # Eğer başlık değilse ve içerik değerliyse ekle
                if not found_category and content_line:
                    # "Bulunamadı" ve benzeri ifadeleri filtrele
                    not_found_phrases = ["bulunamadı", "bulunmamaktadır", "bulunamadı.", "yok", "yoktur"]
                    if current_category == "diyagramlar" and any(phrase in content_line.lower() for phrase in not_found_phrases):
                        # Diyagramlar bulunamadı bilgisi - ekleyelim
                        current_content.append(f"Diyagram bilgisi bulunamadı: {content_line}")
                    elif not any(phrase in content_line.lower() for phrase in not_found_phrases):
                        # Değerli içerik
                        current_content.append(content_line)
                        has_valuable_info[current_category] = True
                        print(f"İçerik eklendi: {current_category} <- '{content_line}'")
        
        # Son kategorinin içeriğini kaydet
        if current_category and current_content:
            analysis[current_category].extend(current_content)
        
        # Tekrarlanan içerikleri temizle
        for category in analysis_categories.keys():
            if category in analysis and analysis[category]:
                # Eğer kategoride içerik varsa
                unique_items = []
                seen = set()
                
                for item in analysis[category]:
                    # İçeriğin normalize edilmiş hali
                    normalized_item = ' '.join(item.lower().split())
                    
                    # ** işaretlerini temizle
                    if normalized_item.startswith('**') and normalized_item.endswith('**'):
                        normalized_item = normalized_item[2:-2].strip()
                    
                    # Başlık sonundaki ':' ve '**' işaretlerini temizle
                    if normalized_item.endswith(':**'):
                        normalized_item = normalized_item[:-3].strip()
                    
                    if normalized_item not in seen and len(normalized_item) > 1:
                        seen.add(normalized_item)
                        # Orijinal öğeyi temizle
                        cleaned_item = item
                        # ** işaretlerini temizle
                        if cleaned_item.startswith('**') and cleaned_item.endswith('**'):
                            cleaned_item = cleaned_item[2:-2].strip()
                        # Başlık sonundaki ':' ve '**' işaretlerini temizle
                        if cleaned_item.endswith(':**'):
                            cleaned_item = cleaned_item[:-3].strip()
                            
                        unique_items.append(cleaned_item)
                
                analysis[category] = unique_items
                
                # "Bulunamadı" ifadelerini filtrele - eğer değerli içerik varsa
                if has_valuable_info[category]:
                    analysis[category] = [
                        item for item in analysis[category]
                        if not any(phrase in item.lower() for phrase in 
                                 ["bulunamadı", "bulunmamaktadır", "yoktur", "bilgi yok"])
                    ]
        
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
        
        # Ham LLM çıktısını da ekle
        analysis["raw_llm_output"] = results
    
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