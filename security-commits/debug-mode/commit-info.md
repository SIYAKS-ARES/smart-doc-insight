# Debug Modu Güvenlik İyileştirmesi

## Güvenlik Açığı Bilgileri

- **İlgili CVE**: CVE-2024-34069 (Werkzeug Debugger RCE)
- **Önem Derecesi**: Yüksek

## Yapılan Değişiklikler

- Debug modu ortam değişkeni ile kontrol edilecek şekilde güncellendi
- Üretim ortamında debugger varsayılan olarak devre dışı bırakıldı
- `run.py` dosyası güncellendi

## Commit Bilgileri

```bash
git commit -m "Fix: Debug modunu ortam değişkeniyle kontrol et" \
          -m "- Flask uygulamasının debug modunu FLASK_ENV ortam değişkeni ile kontrol edilecek şekilde güncellendi" \
          -m "- Üretim ortamında debugger kapalı olacak (FLASK_ENV=production)" \
          -m "- Bu değişiklik Werkzeug RCE güvenlik açığına karşı ek koruma sağlıyor (GH-#4)"
```

## Açıklama

Werkzeug hata ayıklayıcısı (debugger) üzerinden uzaktan kod çalıştırma (RCE) güvenlik açığını hafifletmeye yönelik önemli bir iyileştirmedir. Hata ayıklayıcının üretim ortamında varsayılan olarak açık kalması ciddi bir güvenlik riski oluşturmaktadır.

Bu güncelleme ile Flask uygulamasının debug modu, `FLASK_ENV` ortam değişkeni aracılığıyla kontrol edilmektedir:

- Geliştirme ortamında (`FLASK_ENV=development`): Debug modu açık
- Üretim ortamında (`FLASK_ENV=production`): Debug modu kapalı

Bu değişiklik, Werkzeug debugger'ının güvenlik açıklarına karşı korunmayı sağlar ve web uygulamasının üretim ortamında daha güvenli şekilde çalışmasını garantiler.
