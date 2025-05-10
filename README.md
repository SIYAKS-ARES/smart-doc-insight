# Smart Doc Insight

Smart Doc Insight, öğrencilerin PDF formatındaki proje dokümanlarını yükleyebildiği ve öğretmenlerin bu dokümanları yapay zeka ile analiz edebildiği bir web uygulamasıdır.

## 🌐 Proje Özellikleri

- Öğrenci ve öğretmen rollerine sahip kullanıcı sistemi
- PDF doküman yükleme ve saklama
- Ollama üzerinden yerel LLM (mistral:instruct) ile PDF analizi
- MongoDB veritabanı entegrasyonu
- Flask web framework kullanımı

## 🔧 Kurulum

### Gereksinimleri

- Python 3.8+
- MongoDB
- [Ollama](https://ollama.ai/) (mistral:instruct modeli ile)

### Adımlar

1. Miniconda ile yeni bir ortam oluşturun:
```bash
conda create -n flask_llm_app python=3.10
conda activate flask_llm_app
```

2. Proje deposunu klonlayın:
```bash
git clone https://github.com/kullaniciadi/smart-doc-insight.git
cd smart-doc-insight
```

3. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

4. Ollama'yı kurun ve mistral modelini indirin:
```bash
# Ollama'yı işletim sisteminize göre kurun: https://ollama.ai/download
ollama pull mistral:instruct
```

5. MongoDB'yi başlatın:
```bash
# MongoDB'nin çalıştığından emin olun
```

6. `.env` dosyasını düzenleyin:
```
MONGO_URI=mongodb://localhost:27017/smart_doc_insight
SECRET_KEY=gizli_anahtarinizi_degistirin
OLLAMA_BASE_URL=http://localhost:11434
```

7. Uygulamayı başlatın:
```bash
python run.py
```

8. Tarayıcınızdan `http://localhost:5000` adresine gidin.

## 📁 Proje Yapısı

```
smart-doc-insight/
├── app/                      # Ana uygulama paketi
│   ├── routes/               # API ve sayfa yönlendirmeleri
│   │   ├── __init__.py
│   │   ├── auth.py           # Kimlik doğrulama rotaları
│   │   ├── main.py           # Ana sayfalar
│   │   ├── student.py        # Öğrenci işlemleri
│   │   └── teacher.py        # Öğretmen işlemleri
│   ├── static/               # Statik dosyalar (CSS, JS)
│   │   ├── css/
│   │   └── js/
│   ├── templates/            # HTML şablonları
│   │   ├── auth/
│   │   ├── student/
│   │   ├── teacher/
│   │   └── base.html
│   ├── utils/                # Yardımcı fonksiyonlar
│   │   ├── __init__.py
│   │   ├── pdf_utils.py      # PDF işleme
│   │   └── llm_utils.py      # LLM entegrasyonu
│   ├── models/               # Veritabanı modelleri
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── project.py
│   └── __init__.py           # Uygulama yapılandırması
├── uploads/                  # Yüklenen PDF'ler için klasör
├── .env                      # Ortam değişkenleri
├── requirements.txt          # Gerekli paketler
└── run.py                    # Uygulama başlatma dosyası
```

## 🧪 Kullanım

1. Hesap oluşturun (öğrenci veya öğretmen rolü seçin)
2. Öğrenci hesabıyla giriş yapıp PDF yükleyin
3. Öğretmen hesabıyla giriş yapıp PDF'leri görüntüleyin ve analiz edin

## 🔒 Güvenlik

- Kullanıcı şifreleri güvenli bir şekilde hash'lenir
- Oturum yönetimi Flask-Login ile sağlanır
- Sadece izin verilen dosya türleri yüklenebilir

## 📄 Lisans

Bu proje [MIT lisansı](LICENSE) altında lisanslanmıştır.

