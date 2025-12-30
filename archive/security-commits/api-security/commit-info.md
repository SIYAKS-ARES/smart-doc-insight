# API Anahtarı Güvenlik İyileştirmeleri

## Yapılan İyileştirmeler

1. **API Anahtarı Şifreleme**:
   - API anahtarları AES-256 ile şifrelenerek veritabanında saklanıyor
   - Her kullanıcı için ayrı tuz (salt) değeri kullanılıyor
   - Şifreli anahtarlar ve tuz değerleri ayrı alanlar olarak saklanıyor

2. **Hassas Veri Maskeleme**:
   - Log kayıtlarında API anahtarları ve gizli bilgiler otomatik maskeleniyor
   - Regex ile hassas veri tespiti ve maskeleme yapılıyor
   - Exception backtrace bilgilerindeki gizli değerler temizleniyor

3. **API Anahtarı Yönetimi**:
   - Kullanıcı bazlı API anahtarı saklama ve yönetme sistemi
   - Veritabanı temelli güvenli anahtar yönetimi
   - API anahtarı varlık kontrolü ve uyarı mekanizmaları

## Commit Bilgileri

```bash
git commit -m "Security: API anahtarı güvenliği iyileştirmeleri" \
          -m "- API anahtarlarını güvenli bir şekilde saklayan model eklendi" \
          -m "- Şifreleme ve çözme işlemleri için crypto_utils.py modülü eklendi" \
          -m "- Hassas veriler AES-256 ile şifrelenerek veritabanında saklanıyor"
```

```bash
git commit -m "Security: Güvenli loglama sistemi eklendi" \
          -m "- Hassas verileri maskeleyerek loglama yapan SafeLogger sınıfı eklendi" \
          -m "- API anahtarları ve gizli bilgiler otomatik olarak maskeleniyor" \
          -m "- Regex ile hassas veri tespiti ve maskeleme yapılıyor"
```

## Açıklama

Bu değişiklikler, OpenAI, Google Gemini ve Anthropic Claude gibi harici API sağlayıcılarına ait API anahtarları gibi hassas verilerin güvenliğini artırmayı amaçlamaktadır. Uygulama, kullanıcıların bu API sağlayıcılarını kullanabilmesini sağlarken, aynı zamanda API anahtarlarının güvenli bir şekilde saklanması ve işlenmesini de garanti etmektedir.

### Şifreleme Mekanizması

API anahtarları, kullanıcı hesabına özgü bir şifreleme anahtarı kullanılarak AES-256 şifreleme algoritması ile şifrelenir. Her şifreleme işlemi için benzersiz bir tuz değeri oluşturulur ve bu değer, şifrelenmiş veri ile birlikte saklanır. Bu, aynı API anahtarı için bile farklı şifrelenmiş değerler oluşmasını sağlayarak, gökkuşağı tablosu (rainbow table) saldırılarına karşı koruma sağlar.

### Güvenli Loglama

İlave olarak, SafeLogger sınıfı, log kayıtlarında görünmemesi gereken hassas verileri otomatik olarak tespit eder ve maskeler. Bu, API anahtarları, şifreler ve diğer gizli bilgilerin log dosyalarına sızmasını önler. Bu özellikle hata raporlarında ve istisna durumlarında önemlidir, çünkü bu tür durumlarda genellikle hassas bilgileri içeren ayrıntılı bilgiler loglanır. 