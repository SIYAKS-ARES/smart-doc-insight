import ollama
from typing import Dict, Generator, Any, Optional

class OllamaClient:
    """Ollama LLM sağlayıcısı ile etkileşim için istemci"""
    
    def __init__(self, model: str = "mistral:latest", host: str = "localhost", port: int = 11434):
        """
        Ollama istemcisini başlatır
        
        Args:
            model: Kullanılacak model adı
            host: Ollama sunucu adresi
            port: Ollama sunucu portu
        """
        self.model = model
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.client = ollama.Client(host=self.base_url)
        
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Verilen prompt'a göre yanıt üretir
        
        Args:
            prompt: LLM'e gönderilecek istem metni
            **kwargs: Ollama'ya gönderilebilecek ek parametreler
            
        Returns:
            Üretilen yanıt metni
        """
        options = kwargs.get("options", {})
        response = self.client.generate(
            model=self.model,
            prompt=prompt,
            options=options
        )
        return response.get('response', '')
    
    def generate_stream(self, prompt: str, **kwargs) -> Generator[str, None, None]:
        """
        Streaming modunda yanıt üretir
        
        Args:
            prompt: LLM'e gönderilecek istem metni
            **kwargs: Ollama'ya gönderilebilecek ek parametreler
            
        Yields:
            Parça parça üretilen yanıt metinleri
        """
        options = kwargs.get("options", {})
        
        for chunk in self.client.generate(
            model=self.model,
            prompt=prompt,
            options=options,
            stream=True
        ):
            if 'response' in chunk:
                yield chunk['response'] 