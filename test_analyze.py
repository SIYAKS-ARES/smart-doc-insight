import os
from app.utils.llm_utils import analyze_text_with_llm

# LM Studio'yu kullan
os.environ['LLM_PROVIDER'] = 'lmstudio'

# Test metni
test_text = """
Özet
Bu projede, Veri Tabanı Yönetim Sistemleri dersinde öğrenilen bilgilerin pratiğe
dökülmesi amacıyla RestauPOS isimli bir restoran otomasyonu geliştirilmiştir. Bu 
otomasyon, restoranların müşteri siparişlerini, stok takibini, fatura oluşturma 
işlemlerini yönetmeye yöneliktir.

Grup Üyeleri:
- Ahmet Yılmaz (Backend kodlama)
- Ayşe Kaya (Veritabanı tasarımı)
- Mehmet Demir (Arayüz tasarımı)

Görev Dağılımı:
Ahmet: Backend kodlama, API entegrasyonu
Ayşe: Veritabanı tasarımı, SQL sorguları
Mehmet: Frontend arayüzü, UX/UI tasarımı

Diyagramlar:
Veritabanı ER diyagramı: Ayşe Kaya tarafından çizilmiştir.
Kullanım akış diyagramı: Mehmet Demir tarafından hazırlanmıştır.

1. Giriş
2. Sistem Analizi
3. Veri Tabanı Tasarımı
4. Kullanıcı Arayüzü
5. Sonuç ve Öneriler
"""

# Metin parçalarını oluştur
text_chunks = [test_text]

# Analizi çalıştır
print("Analiz başlıyor...")
result = analyze_text_with_llm(text_chunks)

# Sonuçları göster
print("\nANALİZ SONUÇLARI:")
print("Grup Üyeleri:", result["grup_uyeleri"])
print("Sorumluluklar:", result["sorumluluklar"])
print("Diyagramlar:", result["diyagramlar"])
print("Başlıklar:", result["basliklar"])
print("Eksikler:", result["eksikler"])
print("\nHam Sonuç:")
print(result["ham_sonuc"]) 