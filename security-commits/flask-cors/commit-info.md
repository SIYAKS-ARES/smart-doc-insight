# Flask-CORS Güvenlik Güncellemesi

## Güvenlik Açığı Bilgileri
- **GitHub Dependabot Uyarısı**: #10
- **Açık Adı**: Flask-CORS allows for inconsistent CORS matching
- **Önem Derecesi**: Orta

## Yapılan Değişiklikler
- Flask-CORS sürümü 4.0.0'dan 4.0.1'e yükseltildi
- CORS yapılandırması daha güvenli ve spesifik hale getirildi:
  - Tüm kaynaklara erişim (`*`) yerine belirli kaynaklar listelendi
  - İzin verilen HTTP metotları ve başlıklar belirtildi
  - CORS yapılandırması ortam değişkeni ile kontrol edilebilir hale getirildi
- `app/__init__.py` dosyası güncellendi
- `requirements.txt` dosyası güncellendi

## Commit Bilgileri
```bash
git commit -m "Fix: Update Flask-CORS to v4.0.1 to address inconsistent matching (GH-#10)" \
          -m "- Flask-CORS güncellemesi: 4.0.0 -> 4.0.1" \
          -m "- CORS yapılandırması güvenlik iyileştirmesi:" \
          -m "  - Spesifik ve kısıtlayıcı origin kuralları tanımlandı" \
          -m "  - İzin verilen HTTP metotları ve başlıklar belirtildi" \
          -m "  - Ortam değişkeni kullanılarak yapılandırılabilir hale getirildi" \
          -m "Bu değişiklik, flask-cors paketindeki tutarsız CORS eşleşmesi güvenlik açığını çözen 4.0.1 sürümüne yükseltmeyi içerir."
```

## Açıklama
Flask-CORS kütüphanesinde tespit edilen "tutarsız CORS eşleşmesi" güvenlik açığı, potansiyel olarak uygulamanın CORS politikalarının beklenmedik şekilde davranmasına ve yetkisiz kaynaklardan erişime veya meşru kaynakların engellenmesine yol açabilmekteydi.

Bu güncelleme ile hem Flask-CORS sürümü güvenli bir sürüme yükseltildi hem de CORS yapılandırması daha güvenli hale getirildi. Artık tüm kaynaklara (`*`) erişim yerine, spesifik olarak izin verilen alan adları ve kaynaklar belirtilmektedir. 