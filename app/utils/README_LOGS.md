# MongoDB Tabanlı Loglama Sistemi

Smart Doc Insight projesi, güvenlik, izleme ve hata ayıklama için MongoDB tabanlı gelişmiş bir loglama sistemine sahiptir. Bu sistem, özellikle API anahtarları gibi hassas verilerin güvenli şekilde işlenmesi için kullanılır.

## Özellikler

- **Asenkron Loglama**: Yüksek performans için loglar bir kuyrukta toplanır ve arka planda kaydedilir
- **Hassas Veri Maskeleme**: API anahtarları gibi hassas veriler otomatik olarak maskelenir
- **Yapılandırılmış Loglar**: Loglar JSON formatında saklanır, kolay sorgulama ve analiz sağlar
- **Otomatik Temizleme**: Eski loglar belirli bir süre sonra otomatik olarak temizlenir
- **Kullanıcı Takibi**: Hangi kullanıcının hangi işlemi yaptığı kaydedilir
- **Hata Yakalama**: İstisnalar ve hatalar detaylı olarak kaydedilir

## Yapılandırma

MongoDB loglama sistemi `.env` dosyasında aşağıdaki değişkenlerle yapılandırılabilir:

```
# MongoDB Loglama Ayarları
ENABLE_MONGODB_LOGGING=true        # MongoDB loglamayı etkinleştirme (true/false)
LOG_COLLECTION_NAME=system_logs    # Logların saklanacağı koleksiyon adı
LOG_ASYNC_MODE=true                # Asenkron mod (true/false)
LOG_MAX_QUEUE_SIZE=1000            # Asenkron modda maksimum kuyruk boyutu
LOG_CLEANUP_DAYS=30                # Kaç günden eski logların temizleneceği (0: temizleme kapalı)
```

## Kullanım

MongoDB loglaması, uygulama başlatıldığında otomatik olarak etkinleştirilir. Global `logger` nesnesi kullanılarak kodunuzda log kayıtları oluşturabilirsiniz:

```python
from app.utils.log_utils import logger

# Farklı log seviyelerinde kayıt
logger.info("Bilgi mesajı")
logger.warning("Uyarı mesajı")
logger.error("Hata mesajı")
logger.critical("Kritik hata mesajı")
logger.debug("Debug mesajı")
logger.exception("Hata ile birlikte detaylı log")
```

## Log Yapısı

MongoDB'de saklanan log kayıtları aşağıdaki yapıya sahiptir:

```json
{
  "timestamp": ISODate("2023-05-20T14:30:00.000Z"),
  "level": "INFO",
  "message": "API anahtarı isteniyor - sağlayıcı: openai, kullanıcı: 123456",
  "module": "api_key_manager",
  "function": "get_api_key",
  "line": 25,
  "process": 12345,
  "user_id": "123456",
  "username": "test_user", 
  "user_role": "teacher",
  "request": {
    "ip_address": "127.0.0.1",
    "path": "/select-llm-provider",
    "method": "POST",
    "user_agent": "Mozilla/5.0..."
  },
  "exception": {
    "type": "ValueError",
    "message": "API anahtarı bulunamadı",
    "traceback": "..."
  }
}
```

## Log Sorgulaması

MongoDB'deki log kayıtları, MongoDB Compass gibi araçlarla veya komut satırından sorgulanabilir:

```javascript
// Hata loglarını son eklenenler en üstte olacak şekilde bul
db.system_logs.find({ level: "ERROR" }).sort({ timestamp: -1 })

// Belirli bir kullanıcının API anahtarı işlemlerini bul
db.system_logs.find({ 
  user_id: "123456", 
  message: { $regex: "API anahtarı" } 
})

// Son 24 saatteki kritik hatalar
db.system_logs.find({ 
  level: "CRITICAL", 
  timestamp: { $gt: new Date(Date.now() - 24*60*60*1000) } 
})
```

## Güvenlik Notu

Log kayıtları hassas bilgiler içerebilir, bu nedenle:

1. MongoDB veritabanı erişimi sadece yetkili kişilerle sınırlandırılmalıdır
2. Üretim ortamında MongoDB kimlik doğrulama aktif edilmelidir
3. `mask_sensitive_data()` fonksiyonu hassas verileri maskeler, ancak ek kontroller yapılmalıdır

## Performans İyileştirmeleri

Yüksek trafik durumlarında aşağıdaki ayarlar optimize edilebilir:

- **LOG_ASYNC_MODE=true**: Asenkron mod performansı artırır
- **LOG_MAX_QUEUE_SIZE**: Kuyruk boyutu arttırılabilir
- **Indeksler**: MongoDB koleksiyonu için timestamp, level ve user_id alanlarına indeks eklenir 