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
DEFAULT_PROMPT_TEMPLATE = """Bu PDF'i analiz et ve aşağıdaki kategoriler için bilgi çıkar.

İçerik:
{content}

ZORUNLU FORMAT - Aşağıdaki formatı TAM OLARAK takip et:

**Grup Üyeleri:**
• [İsimleri ve rollerini bul, yoksa "Grup üyeleri belirtilmemiştir"]

**Sorumluluk Alanları:**
• [Kim hangi görevden sorumlu, yoksa "Sorumluluklar belirtilmemiştir"]

**Diyagramlar:**  
• [Diyagram yapan kişiler, yoksa "Diyagram bilgisi bulunamadı"]

**Belirgin Başlıklar:**
• [Dokümandaki tüm başlıkları listele]
• [Her başlığı ayrı satırda yaz]
• [İçindekiler tablosundan veya metin içindeki başlıklardan al]

**Eksikler:**
• [Eksik olan önemli bilgiler, yoksa "Belirgin eksiklik tespit edilmedi"]

ÖNEMLİ: Her kategori için tam olarak ** işaretleri ile başlık yaz, ardından : koy."""

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
        # Özel kategoriler var ama prompt verilmemişse, basit prompt oluştur
        prompt_template = """Bu PDF bir öğrenci projesidir. Aşağıdaki soruları analiz et ve her biri için KISA VE NET cevap ver:

"""

        # Kategorileri prompt'a ekle
        for category_key, category_title in analysis_categories.items():
            if category_key.startswith('custom_'):
                # Başlık adını temizle
                clean_title = category_title.strip().rstrip(':').rstrip('?')
                prompt_template += f"• {clean_title}\n"

        prompt_template += """
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

            SADECE istenen formatta yanıtla, ekstra açıklama yapma."""

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
                result = client.generate(prompt, options={"temperature": 0.1})  # Çok düşük sıcaklık - tutarlılık için
                results.append(result)

                # DEBUG: Log LLM response
                with open('/tmp/llm_debug/info.txt', 'a') as f:
                    f.write(f"Birleştirilmiş içerik için LLM yanıtı (ilk 300 karakter): {result[:300]}...\n")
            else:
                # Çok büyükse tek tek ilerle
                for chunk in text_chunks:
                    prompt = prompt_template.format(content=chunk)
                    result = client.generate(prompt, options={"temperature": 0.1})
                    results.append(result)
        else:
            # Standard: Her parça için LLM'e istek gönder
            for chunk in text_chunks:
                prompt = prompt_template.format(content=chunk)

                # DEBUG: Log current prompt
                with open('/tmp/llm_debug/info.txt', 'a') as f:
                    f.write(f"LLM'e gönderilen prompt (ilk 200 karakter): {prompt[:200]}...\n")

                try:
                    result = client.generate(prompt, options={"temperature": 0.1})
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
    combined_results = " ".join(results) if len(results) > 1 else (results[0] if results else "Analiz sonucu alınamadı.")

    # Sonuçları ayrıştır
    final_analysis = parse_llm_results(combined_results, analysis_categories)

    # DEBUG: Final log
    with open('/tmp/llm_debug/info.txt', 'a') as f:
        f.write(f"Final analiz: {final_analysis}\n")
        f.write("--- LLM ANALIZ TAMAMLANDI ---\n")

    return final_analysis

def resolve_contradictions(responses):
    """
    Çelişkili cevapları çözer (Evet/Hayır çelişkilerini temizler)
    
    Args:
        responses: Cevap listesi
        
    Returns:
        list: Temizlenmiş cevap listesi
    """
    if not responses:
        return responses
    
    # Evet ile başlayan ve Hayır ile başlayan cevapları ayır
    yes_responses = [r for r in responses if r.lower().startswith('evet')]
    no_responses = [r for r in responses if r.lower().startswith('hayır')]
    other_responses = [r for r in responses if not r.lower().startswith('evet') and not r.lower().startswith('hayır')]
    
    # Eğer hem Evet hem Hayır varsa, Evet olanları tercih et (daha detaylı bilgi içerme eğiliminde)
    if yes_responses and no_responses:
        # En uzun ve detaylı Evet cevabını seç
        best_yes = max(yes_responses, key=len)
        return [best_yes] + other_responses
    
    # Çelişki yoksa hepsini geri döndür
    return responses

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

    # Kullanılacak kategorileri belirle
    if categories is None:
        analysis_categories = DEFAULT_ANALYSIS_CATEGORIES
    else:
        analysis_categories = categories

    # Sonuç şablonunu oluştur - tüm kategoriler için boş liste oluştur
    analysis = {}
    analysis["ham_sonuc"] = results if results else "Sonuç alınamadı."

    # Tüm kategori anahtarlarını ekle
    if isinstance(analysis_categories, dict):
        # Özel kategoriler durumu (dictionary)
        for key in analysis_categories.keys():
            analysis[key] = []
        is_custom_analysis = any(key.startswith('custom_') for key in analysis_categories.keys())
    else:
        # Varsayılan kategoriler durumu (list)
        for key in analysis_categories:
            analysis[key] = []
        is_custom_analysis = False

    # Sonuç boşsa veya None ise, boş analiz döndür
    if not results:
        return analysis

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
                # Başlığı temizle - her türlü formatting'i kaldır
                clean_title = title.strip()
                clean_title = clean_title.replace('*', '').replace('#', '').strip()
                clean_title = clean_title.rstrip(':').rstrip('?').strip()
                clean_title = clean_title.lower()
                category_mapping[clean_title] = key
                
                # Ana kelimeleri de ekle (ilk 1-2 kelime)
                words = clean_title.split()
                if len(words) >= 1:
                    category_mapping[words[0]] = key
                if len(words) >= 2:
                    category_mapping[f"{words[0]} {words[1]}"] = key
                    
                # Orijinal başlığı da ekle 
                original_clean = title.strip().rstrip(':').rstrip('?').lower()
                category_mapping[original_clean] = key

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
                # ** işaretlerini ve diğer markdown formatlarını tamamen temizle
                potential_title = parts[0].strip()
                # Tüm * ve # karakterlerini kaldır
                potential_title = potential_title.replace('*', '').replace('#', '').strip()
                potential_title = potential_title.lower()
                content_part = parts[1].strip() if len(parts) > 1 else ""

                # Debug log
                with open('/tmp/llm_debug/info.txt', 'a') as f:
                    f.write(f"  Potansiyel başlık: '{potential_title}', içerik: '{content_part}'\n")

                # Başlık eşleşmesi ara - daha basit ve etkili eşleştirme
                matched_category = None

                for title_key, category_key in category_mapping.items():
                    # Tam eşleşme kontrolü
                    if potential_title == title_key:
                        matched_category = category_key
                        break
                    # İçinde geçme kontrolü (kısmi eşleşme)
                    elif title_key in potential_title or potential_title in title_key:
                        matched_category = category_key
                        break

                if matched_category:
                    # Önceki kategorinin içeriğini kaydet
                    if current_category and current_content:
                        # Kısa yanıtları birleştir
                        combined_response = " ".join(current_content).strip()
                        if (combined_response and 
                            not any(skip in combined_response.lower() for skip in ['bu konuda bilgi bulunamadı', 'bilgi bulunamadı', 'veri bulunamadı']) and 
                            combined_response.strip() != '**' and
                            len(combined_response.strip()) > 10 and  # Çok kısa cevapları filtrele
                            not combined_response.startswith('-') and  # Liste öğelerini filtrele
                            not combined_response.startswith('+') and  # Liste öğelerini filtrele
                            not combined_response.strip()[0:2].replace('.', '').replace(')', '').isdigit()):  # Sayısal liste öğelerini filtrele
                            analysis[current_category].append(combined_response)

                        # Debug log
                        with open('/tmp/llm_debug/info.txt', 'a') as f:
                            f.write(f"  Kaydedilen kategori: {current_category}, birleştirilmiş yanıt: {combined_response}\n")

                    # Yeni kategoriyi ayarla
                    current_category = matched_category
                    current_content = []

                    # Bu satırda başlığın yanında içerik varsa, onu da ekle
                    if (content_part and 
                        not any(skip in content_part.lower() for skip in ['bu konuda bilgi bulunamadı', 'bilgi bulunamadı', 'veri bulunamadı']) and 
                        content_part.strip() != '**' and
                        len(content_part.strip()) > 10 and  # Çok kısa içerikleri filtrele
                        not content_part.strip().startswith('-') and  # Liste öğelerini filtrele
                        not content_part.strip().startswith('+') and  # Liste öğelerini filtrele
                        not content_part.strip()[0:2].replace('.', '').replace(')', '').isdigit()):  # Sayısal liste öğelerini filtrele
                        current_content.append(content_part)

                    # Sonraki satırları da bu başlığa ait olarak kontrol et (kısa yanıtlarda genellikle tek satırda biter)
                    j = i + 1
                    while j < len(lines) and j < i + 3:  # Maksimum 2 satır daha kontrol et
                        next_line = lines[j].strip()
                        # Eğer sonraki satır yeni bir başlık değilse ve boş değilse, mevcut içeriğe ekle
                        if (next_line and 
                            ':' not in next_line and 
                            not next_line.startswith('•') and
                            not next_line.startswith('-') and
                            not next_line.startswith('+') and
                            len(next_line) > 10 and  # Çok kısa satırları da filtrele
                            not next_line[0:2].replace('.', '').replace(')', '').isdigit()):  # Sayısal liste öğelerini filtrele
                            current_content.append(next_line)
                            j += 1
                        else:
                            break

                    # Debug log
                    with open('/tmp/llm_debug/info.txt', 'a') as f:
                        f.write(f"  Yeni kategori: {current_category}\n")
                        f.write(f"  Başlangıç içeriği: {current_content}\n")

                    # i'yi son işlenen satıra kadar ilerlet
                    i = j - 1

            i += 1

        # Son kategorinin içeriğini kaydet
        if current_category and current_content:
            combined_response = " ".join(current_content).strip()
            if (combined_response and 
                not any(skip in combined_response.lower() for skip in ['bu konuda bilgi bulunamadı', 'bilgi bulunamadı', 'veri bulunamadı']) and 
                combined_response.strip() != '**' and
                len(combined_response.strip()) > 10 and  # Çok kısa cevapları filtrele
                not combined_response.startswith('-') and  # Liste öğelerini filtrele
                not combined_response.startswith('+') and  # Liste öğelerini filtrele
                not combined_response.strip()[0:2].replace('.', '').replace(')', '').isdigit()):  # Sayısal liste öğelerini filtrele
                analysis[current_category].append(combined_response)

                    # Debug log
        with open('/tmp/llm_debug/info.txt', 'a') as f:
            f.write(f"Son kategori kaydedildi: {current_category}, birleştirilmiş yanıt: {combined_response}\n")

    # Çelişkili cevapları temizle
    if is_custom_analysis:
        for category_key in analysis:
            if category_key.startswith('custom_') and analysis[category_key]:
                # Evet/Hayır çelişkilerini çöz
                analysis[category_key] = resolve_contradictions(analysis[category_key])

    else:
        # Standart kategoriler için mevcut ayrıştırma mantığı
        lines = results.split('\n')
        current_category = None
        current_content = []

        # Kategoriler ve anahtar kelimelerin eşleşmeleri
        category_keywords = {
            "grup_uyeleri": ["grup üyeleri", "grup üyesi", "öğrenci", "öğrenciler", "üye", "grup", "ekip"],
            "sorumluluklar": ["kim hangisi bölümden sorumlu", "sorumlu", "sorumluluk", "görev", "bölüm sorumlu", "sorumluluk alanları"],
            "diyagramlar": ["diyagramları kim çizmiş", "diyagramlar kim çizmiş", "diyagram", "çizim", "çizen", "şema"],
            "basliklar": ["belirgin başlıklar nelerdir", "belirgin başlıklar", "başlık", "konu", "bölüm"],
            "eksikler": ["içerikte eksik görünen bir şey var mı", "eksik kısımlar", "eksik", "bulunmayan", "yetersiz", "yok"]
        }

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Debug için satırı yazdır
            print(f"İşlenen satır: '{line}'")

            # Kategori başlıklarını tespit et - Markdown temizleme ile
            # Markdown formatting'i temizle
            clean_line = line.replace('*', '').replace('#', '').strip()
            lower_line = clean_line.lower()

            # Aktif kategoriyi güncelle (önce kategori kontrolü yapalım)
            for category, keywords in category_keywords.items():
                if category in analysis_categories:
                    # Numaralı başlık kontrolü
                    if clean_line and clean_line[0].isdigit() and '. ' in clean_line:
                        number, rest = clean_line.split('. ', 1)
                        if any(kw.lower() in rest.lower() for kw in keywords):
                            if current_category and current_content:
                                analysis[current_category].extend(current_content)
                                current_content = []
                            current_category = category
                            print(f"Kategori değişti: {current_category}")
                            break
                    # Başlık kontrolü - : ile bitmeli veya anahtar kelime eşleşmeli
                    elif clean_line.endswith(':') and any(kw.lower() in lower_line.rstrip(':') for kw in keywords):
                        if current_category and current_content:
                            analysis[current_category].extend(current_content)
                            current_content = []
                        current_category = category
                        print(f"Kategori değişti: {current_category}")
                        break

            # Eğer bir kategori belirlediyse ve bu satır başlık değilse içerik olarak ekle
            if current_category and current_category in analysis_categories:
                # Madde işaretleri veya numaralandırma varsa temizle
                if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                    line = line[1:].strip()
                elif len(line) > 1 and line[0].isdigit() and line[1:].startswith('. '):
                    line = line[line.find('.')+1:].strip()

                # Satır boş değilse ve anlamlı bir içerik varsa ekle
                if line and len(line) > 2:
                    # Başlık satırlarını filtrele ve kategori başlığı olmayan satırları ekle
                    clean_check_line = line.replace('*', '').strip()
                    is_category_title = clean_check_line.endswith(':') and any(kw.lower() in clean_check_line.lower().rstrip(':') for kw in category_keywords.get(current_category, []))
                    
                    # Çok uzun açıklayıcı metinleri filtrele (>200 karakter)
                    is_too_long = len(line) > 200
                    
                    if not line.endswith(':') and not is_category_title and not is_too_long:
                        current_content.append(line)
                        print(f"Eklendi: {current_category} <- '{line}'")

        # Son kategorinin içeriğini kaydet
        if current_category and current_content:
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

    # Her kategori için sonuçları yazdır (hata ayıklama)
    with open('/tmp/llm_debug/info.txt', 'a') as f:
        f.write(f"\n--- PARSING SONUÇLARI ---\n")
        for category, items in analysis.items():
            if category != "ham_sonuc":
                f.write(f"{category}: {len(items)} madde - {items}\n")
        f.write("--- PARSING TAMAMLANDI ---\n\n")

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