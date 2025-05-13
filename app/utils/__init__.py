"""
Smart Doc Insight - Yardımcı Modüller

Bu paket, Smart Doc Insight uygulaması için çeşitli yardımcı modüller içerir:
- PDF işleme araçları
- LLM entegrasyonu
- Güvenlik ve şifreleme araçları
- Log sistemi
- API anahtarı yönetimi

MongoDB Tabanlı Loglama:
Proje, MongoDB tabanlı bir loglama sistemine sahiptir. Detaylı bilgi için:
./README_LOGS.md dosyasını inceleyebilirsiniz.

Örnek log kullanımı:
```python
from app.utils.log_utils import logger

# Farklı log seviyeleri
logger.info("Bilgi mesajı")
logger.warning("Uyarı mesajı") 
logger.error("Hata mesajı")
logger.exception("Hata ile birlikte detaylı log")
```
""" 