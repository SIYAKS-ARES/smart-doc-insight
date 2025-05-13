import os
from dotenv import load_dotenv

# .env dosyasını yükle (varsa)
load_dotenv()

# LLM Ayarları
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")  # "ollama" veya "lmstudio"
LLM_STUDIO_MODEL = os.getenv("LLM_STUDIO_MODEL", "deepseek-coder-v2-lite-instruct-mlx")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:latest")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "localhost")
OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", 11434))
OLLAMA_BASE_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}" 