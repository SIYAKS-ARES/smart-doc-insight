# Smart Doc Insight

Smart Doc Insight, öğrencilerin PDF formatındaki proje dokümanlarını yükleyebildiği ve öğretmenlerin bu dokümanları yapay zeka ile analiz edebildiği bir web uygulamasıdır.

## 🌐 Proje Özellikleri

- Öğrenci ve öğretmen rollerine sahip kullanıcı sistemi
- PDF doküman yükleme ve saklama
- Yerel ve API tabanlı LLM entegrasyonları:
  - **Yerel LLM'ler:** Ollama, LM Studio
  - **API Tabanlı LLM'ler:** OpenAI GPT, Google Gemini, Anthropic Claude
- MongoDB veritabanı entegrasyonu
- Flask web framework kullanımı

## 🔧 Kurulum

### Gereksinimleri

- Python 3.8+
- MongoDB
- LLM Sağlayıcıları (Aşağıdaki seçeneklerden birini kurabilirsiniz):
  - **Yerel LLM Seçenekleri:**
    - [Ollama](https://ollama.ai/) (mistral modeli ile)
    - [LM Studio](https://lmstudio.ai/) (deepseek-coder-v2-lite-instruct-mlx modeli ile)
  - **API Tabanlı LLM Seçenekleri:**
    - [OpenAI API](https://platform.openai.com/api-keys) (API anahtarı gerekli)
    - [Google Gemini API](https://makersuite.google.com/app/apikey) (API anahtarı gerekli)
    - [Anthropic Claude API](https://console.anthropic.com/account/keys) (API anahtarı gerekli)

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

4. Tercih ettiğiniz LLM sağlayıcısını kurun:

   - **Yerel LLM'ler için:**

     - **Ollama kullanmak için:**
       ```bash
       # Ollama'yı işletim sisteminize göre kurun: https://ollama.ai/download
       ollama pull mistral
       ```
     - **LM Studio kullanmak için:**
       ```bash
       # LM Studio'yu indirin: https://lmstudio.ai/
       # Python bağlantı kurabilmek için:
       pip install lmstudio
       ```
   - **API Tabanlı LLM'ler için:**

     - OpenAI: API anahtarınızı [buradan](https://platform.openai.com/api-keys) alın
     - Google Gemini: API anahtarınızı [Google AI Studio'dan](https://makersuite.google.com/app/apikey) alın
     - Anthropic Claude: API anahtarınızı [Anthropic Console'dan](https://console.anthropic.com/account/keys) alın
5. MongoDB'yi başlatın:

```bash
# MongoDB'nin çalıştığından emin olun
```

6. `.env` dosyasını düzenleyin:

```
MONGO_URI=mongodb://localhost:27017/smart_doc_insight
SECRET_KEY=gizli_anahtarinizi_degistirin

# LLM Sağlayıcı seçeneği (ollama, lmstudio, openai, gemini, claude)
LLM_PROVIDER=ollama

# Yerel LLM ayarları
# Ollama ayarları
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral:latest

# LM Studio ayarları 
LLM_STUDIO_MODEL=deepseek-coder-v2-lite-instruct-mlx

# API Tabanlı LLM ayarları
# OpenAI
OPENAI_API_KEY=sk-xxxxxxxxxxxx
OPENAI_MODEL=gpt-3.5-turbo

# Google Gemini
GOOGLE_API_KEY=xxxxxxxxxxxxxx
GEMINI_MODEL=gemini-pro

# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx
CLAUDE_MODEL=claude-3-opus-20240229
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
│   │   ├── llm_utils.py      # LLM entegrasyonu
│   │   └── llm/              # LLM sağlayıcı istemcileri
│   │       ├── __init__.py
│   │       ├── ollama_client.py
│   │       ├── lmstudio_client.py
│   │       ├── openai_client.py
│   │       ├── gemini_client.py
│   │       └── claude_client.py
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
4. **LLM Sağlayıcı Seçimi:**
   - Öğretmen panelinden "LLM Sağlayıcısı Seçimi" menüsüne tıklayın
   - Yerel veya API tabanlı bir LLM sağlayıcısı seçin
   - API tabanlı bir seçenek için API anahtarınızı girin

## 🔒 Güvenlik

- Kullanıcı şifreleri güvenli bir şekilde hash'lenir
- Oturum yönetimi Flask-Login ile sağlanır
- Sadece izin verilen dosya türleri yüklenebilir
- API anahtarları güvenli bir şekilde saklanır
- CORS yapılandırması kısıtlayıcı bir şekilde ayarlanmıştır
- URL yönlendirme güvenliği sağlanmıştır
- Debug modu ortam değişkeni ile kontrol edilir
- Tüm bağımlılıklar güvenlik açıkları için düzenli olarak güncellenir (Werkzeug ≥3.0.6, Gunicorn ≥23.0.0, Flask-CORS ≥4.0.1)

## 📄 Lisans

Bu proje [MIT lisansı](LICENSE) altında lisanslanmıştır.

## LLM Sağlayıcıları

Sistem beş farklı LLM sağlayıcı ile çalışabilmektedir:

### Yerel LLM Sağlayıcıları

#### Ollama

- **Kurulum:** https://ollama.ai/download
- **Kullanım:**
  1. Ollama servisini çalıştırın: `ollama serve`
  2. Modeli indirin: `ollama pull mistral`
  3. Çevre değişkeni: `LLM_PROVIDER=ollama`

#### LM Studio

- **Kurulum:** https://lmstudio.ai/
- **Kullanım:**
  1. `pip install lmstudio`
  2. Uygulamayı açın ve modelleri yükleyin
  3. Settings > API Server bölümünden API sunucusunu etkinleştirin
  4. Çevre değişkeni: `LLM_PROVIDER=lmstudio`, `LLM_STUDIO_MODEL=deepseek-coder-v2-lite-instruct-mlx`
  5. Dokümantasyon: https://lmstudio.ai/docs/python

### API Tabanlı LLM Sağlayıcıları

#### OpenAI

- **Kurulum:** API anahtarınızı [OpenAI Dashboard](https://platform.openai.com/api-keys)'dan alın
- **Kullanım:**
  1. `pip install openai>=1.0.0`
  2. Çevre değişkeni: `LLM_PROVIDER=openai`, `OPENAI_API_KEY=sk-xxxxxxxxxxxx`
  3. Uygulama içinden API anahtarınızı girebilirsiniz

#### Google Gemini

- **Kurulum:** API anahtarınızı [Google AI Studio](https://makersuite.google.com/app/apikey)'dan alın
- **Kullanım:**
  1. `pip install google-generativeai>=0.3.0`
  2. Çevre değişkeni: `LLM_PROVIDER=gemini`, `GOOGLE_API_KEY=xxxxxxxxxxxxxx`
  3. Uygulama içinden API anahtarınızı girebilirsiniz

#### Anthropic Claude

- **Kurulum:** API anahtarınızı [Anthropic Console](https://console.anthropic.com/account/keys)'dan alın
- **Kullanım:**
  1. `pip install anthropic>=0.5.0`
  2. Çevre değişkeni: `LLM_PROVIDER=claude`, `ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx`
  3. Uygulama içinden API anahtarınızı girebilirsiniz
