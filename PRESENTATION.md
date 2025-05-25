# Smart Doc Insight - Proje Sunumu

## 📋 İçindekiler
1. [Proje Hakkında](#proje-hakkında)
2. [Teknik Altyapı](#teknik-altyapı)
3. [Özellikler](#özellikler)
4. [Veritabanı Yapısı](#veritabanı-yapısı)
5. [API ve Endpoint'ler](#api-ve-endpointler)
6. [Güvenlik Önlemleri](#güvenlik-önlemleri)
7. [Kullanım Senaryoları](#kullanım-senaryoları)
8. [Teknik Detaylar](#teknik-detaylar)
9. [Gelecek Planları](#gelecek-planları)
10. [SSS](#sss)

## 🎯 Proje Hakkında

Smart Doc Insight, öğrencilerin PDF formatındaki proje dokümanlarını yükleyebildiği ve öğretmenlerin bu dokümanları yapay zeka ile analiz edebildiği bir web uygulamasıdır.

### Hedef Kitle
- Öğrenciler
- Öğretmenler
- Eğitim Kurumları
- Proje Yöneticileri

### Projenin Amacı
- Öğrenci projelerinin hızlı ve etkili değerlendirilmesi
- Yapay zeka destekli doküman analizi
- Proje takibi ve yönetimi
- Eğitim süreçlerinin dijitalleştirilmesi

## 🛠 Teknik Altyapı

### Backend
- **Framework:** Flask (Python)
- **Veritabanı:** MongoDB
- **Kimlik Doğrulama:** Flask-Login
- **API Güvenliği:** CORS, JWT
- **Dosya İşleme:** PDF Plumber

### Frontend
- **Framework:** Flask Templates
- **CSS Framework:** Bootstrap
- **JavaScript:** Vanilla JS
- **Responsive Tasarım:** Bootstrap Grid

### Yapay Zeka Entegrasyonları
- **Yerel LLM'ler:**
  - Ollama
  - LM Studio
- **API Tabanlı LLM'ler:**
  - OpenAI GPT
  - Google Gemini
  - Anthropic Claude

## ✨ Özellikler

### Kullanıcı Yönetimi
- Öğrenci ve öğretmen rolleri
- Güvenli giriş/çıkış sistemi
- Profil yönetimi
- Şifre sıfırlama

### Doküman İşleme
- PDF yükleme ve saklama
- Otomatik doküman analizi
- Çoklu dosya desteği
- Dosya organizasyonu

### Proje Yönetimi
- Proje oluşturma ve düzenleme
- Grup çalışması desteği
- İlerleme takibi
- Geri bildirim sistemi

### Analiz Özellikleri
- Yapay zeka destekli içerik analizi
- Özetleme ve önemli noktaların çıkarılması
- Plagiarism kontrolü
- Öneriler ve geri bildirimler

## 💾 Veritabanı Yapısı

### Koleksiyonlar

#### Users
```javascript
{
    _id: ObjectId,
    username: String,
    email: String,
    password_hash: String,
    role: String, // "student" veya "teacher"
    created_at: Date
}
```

#### Projects
```javascript
{
    _id: ObjectId,
    name: String,
    description: String,
    group_members: [{
        user_id: ObjectId,
        name: String,
        responsibility: String
    }],
    created_by: ObjectId,
    files: [{
        filename: String,
        path: String,
        upload_date: Date,
        file_id: String
    }],
    analysis: [{
        file_id: String,
        content: String,
        analyzed_at: Date
    }],
    created_at: Date
}
```

#### API Keys
```javascript
{
    _id: ObjectId,
    user_id: ObjectId,
    provider: String,
    api_key: String,
    model: String,
    created_at: Date,
    updated_at: Date
}
```

### Örnek Sorgular

#### Kullanıcı Sorguları
```javascript
// Tüm öğretmenleri bul
db.users.find({role: "teacher"})

// Email ile kullanıcı bul
db.users.findOne({email: "ornek@email.com"})
```

#### Proje Sorguları
```javascript
// Son eklenen projeler
db.projects.find().sort({created_at: -1}).limit(5)

// Kullanıcının projeleri
db.projects.find({created_by: ObjectId("user_id")})
```

#### Analiz Sorguları
```javascript
// Belirli bir dosyanın analizlerini bul
db.projects.find({
    "files.file_id": "file_id"
}, {
    "analysis": 1
})
```

## 🔌 API ve Endpoint'ler

### Kimlik Doğrulama
- `POST /auth/login` - Giriş
- `POST /auth/register` - Kayıt
- `POST /auth/logout` - Çıkış
- `POST /auth/reset-password` - Şifre sıfırlama

### Proje Yönetimi
- `GET /projects` - Projeleri listele
- `POST /projects` - Yeni proje oluştur
- `GET /projects/<id>` - Proje detayı
- `PUT /projects/<id>` - Proje güncelle
- `DELETE /projects/<id>` - Proje sil

### Dosya İşlemleri
- `POST /projects/<id>/files` - Dosya yükle
- `GET /projects/<id>/files` - Dosyaları listele
- `DELETE /projects/<id>/files/<file_id>` - Dosya sil

### Analiz İşlemleri
- `POST /projects/<id>/analyze` - Analiz başlat
- `GET /projects/<id>/analysis` - Analiz sonuçları

## 🔒 Güvenlik Önlemleri

### Kimlik Doğrulama
- JWT token kullanımı
- Şifre hashleme (Werkzeug)
- Oturum yönetimi
- Güvenli çıkış

### Veri Güvenliği
- API anahtarı şifreleme
- Hassas veri maskeleme
- CORS yapılandırması
- Rate limiting

### Dosya Güvenliği
- Dosya tipi kontrolü
- Boyut sınırlaması
- Güvenli dosya isimlendirme
- Antivirüs taraması

## 👥 Kullanım Senaryoları

### Öğrenci Senaryosu
1. Sisteme giriş yap
2. Yeni proje oluştur
3. PDF dokümanları yükle
4. Analiz sonuçlarını görüntüle
5. Geri bildirimleri al

### Öğretmen Senaryosu
1. Sisteme giriş yap
2. Öğrenci projelerini görüntüle
3. Yapay zeka analizlerini incele
4. Geri bildirim sağla
5. İlerlemeyi takip et

## 🔧 Teknik Detaylar

### Kurulum Gereksinimleri
- Python 3.8+
- MongoDB
- LLM Sağlayıcıları
- Gerekli Python paketleri

### Bağımlılıklar
```python
flask==2.3.3
flask-login==0.6.2
flask-cors==6.0.0
pymongo>=4.6.3
python-dotenv==1.0.0
pdfplumber==0.10.1
requests>=2.32.0
Werkzeug==2.3.8
```

### Çevre Değişkenleri
```env
MONGO_URI=mongodb://localhost:27017/smart_doc_insight
SECRET_KEY=your_secret_key
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
```

## 🚀 Gelecek Planları

### Kısa Vadeli
- Mobil uygulama geliştirme
- Daha fazla LLM entegrasyonu
- Gelişmiş analiz özellikleri
- Performans optimizasyonları

### Uzun Vadeli
- Çoklu dil desteği
- Gerçek zamanlı işbirliği
- Gelişmiş raporlama
- API geliştirme

## ❓ SSS

### Genel Sorular
1. **Proje kimler için uygundur?**
   - Eğitim kurumları
   - Öğrenciler
   - Öğretmenler
   - Proje yöneticileri

2. **Hangi dosya formatları destekleniyor?**
   - Şu an için sadece PDF
   - Gelecekte diğer formatlar eklenecek

3. **Yapay zeka analizi nasıl çalışıyor?**
   - Yerel veya API tabanlı LLM'ler kullanılıyor
   - Doküman içeriği analiz ediliyor
   - Önemli noktalar çıkarılıyor
   - Geri bildirimler oluşturuluyor

### Teknik Sorular
1. **Veritabanı yedekleme nasıl yapılıyor?**
   - MongoDB'nin yerleşik yedekleme araçları
   - Otomatik yedekleme planlaması
   - Yedekleme doğrulama

2. **Ölçeklenebilirlik nasıl sağlanıyor?**
   - MongoDB sharding
   - Load balancing
   - Caching mekanizmaları

3. **Güvenlik nasıl sağlanıyor?**
   - JWT token kullanımı
   - Şifreleme
   - Rate limiting
   - CORS yapılandırması

### Kullanım Soruları
1. **Nasıl başlayabilirim?**
   - Kayıt ol
   - Giriş yap
   - Proje oluştur
   - Dosya yükle

2. **Analiz sonuçları nasıl yorumlanır?**
   - Önemli noktalar
   - Öneriler
   - Geri bildirimler
   - İyileştirme alanları

3. **Grup çalışması nasıl yapılır?**
   - Proje oluştur
   - Üye ekle
   - Görev dağılımı yap
   - İlerlemeyi takip et

### Sunum İpuçları
1. **Önemli Noktalar**
   - Projenin amacını vurgula
   - Teknik detayları basit anlat
   - Canlı demo göster
   - Kullanım senaryolarını paylaş

2. **Hazırlık**
   - Test verileri hazırla
   - Demo senaryoları planla
   - Sorulara hazırlan
   - Teknik sorunlara karşı yedek planlar oluştur

3. **Sunum Sırası**
   - Proje tanıtımı
   - Teknik altyapı
   - Özellikler
   - Demo
   - Soru-cevap 