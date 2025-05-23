import os
from dotenv import load_dotenv

# .env dosyasını yükle (varsa)
load_dotenv()

# LLM Ayarları
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")  # "ollama" veya "lmstudio"
LLM_STUDIO_MODEL = os.getenv("LLM_STUDIO_MODEL", "mistral-nemo-instruct-2407")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:latest")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "localhost")
OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", 11434))
OLLAMA_BASE_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"

# MongoDB bağlantı bilgileri
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/smart_doc_insight")
DATABASE_NAME = "smart_doc_insight"

# Dosya yükleme klasörü
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "/tmp/smart_doc_insight_uploads")

# Arayüz dili
UI_LANGUAGE = os.getenv("UI_LANGUAGE", "tr") 