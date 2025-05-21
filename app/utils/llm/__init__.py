from typing import Protocol, Union
import os
import traceback

class LLMProvider(Protocol):
    """LLM sağlayıcıları için ortak arayüz"""
    
    def generate(self, prompt: str) -> str:
        """Metin istemcisine göre yanıt üretir"""
        ...
        
    def generate_stream(self, prompt: str, **kwargs):
        """Streaming yanıt üretir (jeneratör olarak)"""
        ...

from .ollama_client import OllamaClient
from .lmstudio_client import LMStudioClient

# API tabanlı LLM'ler
from .openai_client import OpenAIClient
from .gemini_client import GeminiClient
from .claude_client import ClaudeClient

# Güvenlik için API anahtarı yöneticisini ekle
from app.utils.api_key_manager import APIKeyManager

def get_llm_client(force_provider=None, api_key=None, user_id=None):
    """
    Yapılandırma ayarlarına göre uygun LLM istemcisini döndürür
    
    Args:
        force_provider: Özellikle belirtilen sağlayıcıyı zorla (yapılandırmayı yok sayar)
        api_key: API tabanlı LLM'ler için API anahtarı (None ise API anahtarı yöneticisinden alınır)
        user_id: API anahtarını almak için kullanıcı ID'si (None ise mevcut kullanıcı kullanılır)
    """
    provider = force_provider or os.getenv("LLM_PROVIDER", "ollama")
    primary_failed = False
    error_message = ""
    
    # İlk olarak yapılandırılmış veya zorlanmış sağlayıcıyı dene
    try:
        # Yerel LLM sağlayıcıları
        if provider == "ollama":
            from ollama import Client
            return OllamaClient(
                model=os.getenv("OLLAMA_MODEL", "mistral:latest"), 
                host=os.getenv("OLLAMA_HOST", "localhost"), 
                port=int(os.getenv("OLLAMA_PORT", 11434))
            )
        elif provider == "lmstudio":
            # LM Studio istemcisini oluştur
            from .lmstudio_client import LMStudioClient
            
            # Varsayılan model adını ayarla
            model_name = os.getenv("LM_STUDIO_MODEL", "mistral-nemo-instruct-2407")
            
            # İstemciyi başlat
            try:
                client = LMStudioClient(model_name=model_name)
                print(f"LM Studio istemcisi başlatıldı, model: {model_name}")
                return client
            except Exception as e:
                print(f"LM Studio istemci hatası: {str(e)}")
                raise
        
        # API tabanlı LLM sağlayıcıları
        elif provider == "openai":
            # API anahtarını al: parametre > API yöneticisi > çevre değişkeni
            openai_api_key = api_key or APIKeyManager.get_api_key("openai", user_id)
            if not openai_api_key:
                raise ValueError("OpenAI API anahtarı bulunamadı. API anahtarını girin veya sistem ayarlarından yapılandırın.")
                
            model_name = APIKeyManager.get_model("openai", user_id) or os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
            return OpenAIClient(api_key=openai_api_key, model_name=model_name)
            
        elif provider == "gemini":
            # API anahtarını al: parametre > API yöneticisi > çevre değişkeni
            gemini_api_key = api_key or APIKeyManager.get_api_key("gemini", user_id)
            if not gemini_api_key:
                raise ValueError("Google Gemini API anahtarı bulunamadı. API anahtarını girin veya sistem ayarlarından yapılandırın.")
                
            model_name = APIKeyManager.get_model("gemini", user_id) or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
            return GeminiClient(api_key=gemini_api_key, model_name=model_name)
            
        elif provider == "claude":
            # API anahtarını al: parametre > API yöneticisi > çevre değişkeni
            claude_api_key = api_key or APIKeyManager.get_api_key("claude", user_id)
            if not claude_api_key:
                raise ValueError("Anthropic Claude API anahtarı bulunamadı. API anahtarını girin veya sistem ayarlarından yapılandırın.")
                
            model_name = APIKeyManager.get_model("claude", user_id) or os.getenv("CLAUDE_MODEL", "claude-3-opus-20240229")
            return ClaudeClient(api_key=claude_api_key, model_name=model_name)
            
        else:
            raise ValueError(f"Bilinmeyen LLM_PROVIDER: {provider}")
    except ImportError as e:
        error_message = f"İstemci kütüphanesi yüklenemedi: {str(e)}"
        primary_failed = True
        print(error_message)
    except Exception as e:
        error_message = f"LLM istemcisi ({provider}) oluşturulurken hata: {str(e)}"
        primary_failed = True
        print(error_message)
        print(traceback.format_exc())
    
    # İlk sağlayıcı başarısız olduysa, alternatifi dene
    if primary_failed:
        # Mevcut hata bilgisini kaydet
        print(f"İlk sağlayıcı ({provider}) başarısız oldu, alternatif deneniyor...")
        
        try:
            # API tabanlı sağlayıcıları yerine yerel sağlayıcıları alternatif olarak kullan
            if provider in ["openai", "gemini", "claude"]:
                alt_providers = ["ollama", "lmstudio"]
            else:
                alt_providers = ["lmstudio" if provider == "ollama" else "ollama"]
                
            # Alternatifleri dene
            for alt_provider in alt_providers:
                try:
                    if alt_provider == "ollama":
                        from ollama import Client
                        return OllamaClient(
                            model=os.getenv("OLLAMA_MODEL", "mistral:latest"), 
                            host=os.getenv("OLLAMA_HOST", "localhost"), 
                            port=int(os.getenv("OLLAMA_PORT", 11434))
                        )
                    elif alt_provider == "lmstudio":
                        model_name = os.getenv("LM_STUDIO_MODEL", "mistral-nemo-instruct-2407")
                        return LMStudioClient(model_name=model_name)
                    
                except Exception as alt_error:
                    print(f"Alternatif sağlayıcı ({alt_provider}) da başarısız oldu: {str(alt_error)}")
                    continue
            
            # Tüm alternatifler başarısız oldu, ilk hatayı yeniden oluştur
            raise Exception(f"Tüm LLM sağlayıcıları başarısız oldu. İlk hata: {error_message}")
                
        except Exception as alt_error:
            # Her iki sağlayıcı da başarısız oldu, ilk hatayı yeniden oluştur
            print(f"Alternatif sağlayıcılar da başarısız oldu: {str(alt_error)}")
            raise Exception(f"Tüm LLM sağlayıcıları başarısız oldu. İlk hata: {error_message}")
    
    # Asla buraya ulaşmamalı
    raise Exception("Beklenmeyen durum: LLM sağlayıcısı belirlenemedi") 