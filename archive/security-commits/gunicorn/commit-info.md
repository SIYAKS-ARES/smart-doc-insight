# Gunicorn Güvenlik Güncellemesi

## CVE Bilgileri
- **CVE-ID 1**: CVE-2024-6827 (HTTP Request/Response Smuggling)
- **GHSA-ID 1**: GHSA-hc5x-x2vx-497g
- **CVE-ID 2**: CVE-2024-1135 (Endpoint Kısıtlama Atlatma)
- **GHSA-ID 2**: GHSA-w3h3-4rj7-4ph4
- **Önem Derecesi**: Yüksek

## Yapılan Değişiklikler
- Gunicorn sürümü 21.2.0'dan 23.0.0'a yükseltildi
- `requirements.txt` dosyası güncellendi

## Commit Bilgileri
```bash
git commit -m "Fix: Gunicorn HTTP Request Smuggling Güvenlik Açıklarını Giderme (GH-#12, GH-#2)" \
          -m "- Gunicorn sürümü 21.2.0'dan güvenli sürüm olan 23.0.0'a yükseltildi" \
          -m "- CVE-2024-6827: HTTP Request/Response Smuggling açığı giderildi (uyarı #12)" \
          -m "- CVE-2024-1135: Endpoint kısıtlama atlatma açığı giderildi (uyarı #2)" \
          -m "- Bu güncelleme her iki güvenlik açığını da tek seferde çözüyor"
```

## Açıklama

### HTTP Request/Response Smuggling (CVE-2024-6827)
Gunicorn'da Transfer-Encoding başlığının RFC standartlarına göre düzgün doğrulanmaması, TE.CL request smuggling saldırılarına yol açabilmekteydi. Bu açık, önbellek zehirlenmesi, veri sızması, oturum manipülasyonu, SSRF, XSS, DoS ve diğer birçok güvenlik sorununa neden olabilirdi.

### Endpoint Kısıtlama Atlatma (CVE-2024-1135)
Transfer-Encoding başlıklarının yanlış doğrulanması nedeniyle HTTP Request Smuggling (HRS) saldırıları, kısıtlı endpoint'lere erişime olanak tanıyabiliyordu. Saldırganlar, çelişkili Transfer-Encoding başlıkları içeren özel istekler oluşturarak güvenlik kısıtlamalarını aşabilirlerdi.

Bu güncelleme, her iki güvenlik açığını da gidermek için Gunicorn 23.0.0 sürümünü kullanmaktadır. 