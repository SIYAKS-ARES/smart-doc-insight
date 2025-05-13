# Pull Request (PR) Şablonları

Bu dosya, güvenlik açıklarını gidermek için oluşturulan dallar için PR oluştururken kullanmanız gereken şablonları içermektedir.

## 1. Werkzeug PR Açıklaması

PR Başlığı: `Fix: Werkzeug Debugger RCE Güvenlik Açığını Giderme (GH-#4)`

```markdown
# Werkzeug Debugger RCE Güvenlik Açığını Giderme

Bu PR, Werkzeug debugger'ında bulunan ve uzaktan kod çalıştırmaya (RCE) izin verebilecek güvenlik açığını giderir.

## Yapılan değişiklikler
- Werkzeug sürümü 2.3.7'den güvenli sürüm olan 3.0.6'ya yükseltildi
- Debug modu ortam değişkeni ile kontrol edilecek şekilde güncellendi
- Üretim ortamında debugger varsayılan olarak devre dışı bırakıldı

Bu değişiklik CVE-2024-34069 ve GHSA-2g68-c3qc-8985 güvenlik açıklarını çözmektedir.

Closes #4
```

PR Linki: https://github.com/SIYAKS-ARES/smart-doc-insight/pull/new/fix/werkzeug-rce-alert-4

## 2. Gunicorn PR Açıklaması

PR Başlığı: `Fix: Gunicorn HTTP Request Smuggling Güvenlik Açıklarını Giderme (GH-#12, GH-#2)`

```markdown
# Gunicorn HTTP Request Smuggling Güvenlik Açıklarını Giderme

Bu PR, Gunicorn'da bulunan iki farklı HTTP Request Smuggling güvenlik açığını giderir.

## Yapılan değişiklikler
- Gunicorn sürümü 21.2.0'dan güvenli sürüm olan 23.0.0'a yükseltildi
   
Bu güncelleme iki farklı güvenlik açığını çözmektedir:
- CVE-2024-6827 (GHSA-hc5x-x2vx-497g): HTTP Request/Response Smuggling (Uyarı #12)
- CVE-2024-1135 (GHSA-w3h3-4rj7-4ph4): Endpoint kısıtlama atlatma (Uyarı #2)

Closes #12
Closes #2
```

PR Linki: https://github.com/SIYAKS-ARES/smart-doc-insight/pull/new/fix/gunicorn-smuggling-alert-12-2

## Üretim Ortamına Geçiş İçin Kontrol Listesi

PR'lar birleştirildikten sonra, üretim ortamına geçmeden önce yapılması gerekenler:

1. Test ortamında güncellenen bağımlılıklarla uygulamayı çalıştırın:
   ```
   pip install -r requirements.txt
   export FLASK_ENV=production
   # Gunicorn ile çalıştırma
   gunicorn -w 4 -b 0.0.0.0:5000 'run:app'
   ```

2. Werkzeug debug modunun production ortamında kapalı olduğunu doğrulayın

3. Uygulamanın tüm kritik fonksiyonlarını test edin

4. Eğer bir alt yapı yapılandırmanız varsa (Nginx, Apache gibi) bunları da güncelleyin ve test edin

5. Uygulamayı güvenli şekilde üretim ortamına dağıtın 