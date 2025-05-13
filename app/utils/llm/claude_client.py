from typing import Dict, Generator, Any, Optional
from anthropic import Anthropic

class ClaudeClient:
    """Anthropic Claude API LLM sağlayıcısı ile etkileşim için istemci"""
    
    def __init__(self, api_key: str, model_name: str = "claude-3-opus-20240229"):
        """
        Claude istemcisini başlatır
        
        Args:
            api_key: Anthropic API anahtarı
            model_name: Kullanılacak model adı
        """
        self.api_key = api_key
        self.model_name = model_name
        self.client = None
        self._init_client()
        
    def _init_client(self):
        """Claude istemcisini başlatır"""
        try:
            self.client = Anthropic(api_key=self.api_key)
            
            # Bağlantıyı test et
            try:
                # Kısa bir istek gönderelim
                test_response = self.client.messages.create(
                    model=self.model_name,
                    max_tokens=10,
                    messages=[{"role": "user", "content": "test"}]
                )
                print(f"Claude bağlantısı başarılı. Model '{self.model_name}' kullanılabilir.")
            except Exception as e:
                if "model" in str(e).lower() and "not found" in str(e).lower():
                    # Model bulunamadı, varsayılan modeli deneyelim
                    print(f"Claude bağlantısı başarılı, ancak '{self.model_name}' modeli bulunamadı.")
                    # Claude'un en güncel modellerine geçmeyi deneyelim
                    try:
                        self.model_name = "claude-3-sonnet-20240229"
                        test_response = self.client.messages.create(
                            model=self.model_name,
                            max_tokens=10,
                            messages=[{"role": "user", "content": "test"}]
                        )
                        print(f"Claude varsayılan model '{self.model_name}' kullanılıyor.")
                    except Exception as e2:
                        print(f"Claude varsayılan model '{self.model_name}' de kullanılamıyor: {str(e2)}")
                else:
                    print(f"Claude model bağlantı hatası: {str(e)}")
                
        except Exception as e:
            raise Exception(f"Claude istemcisi başlatılırken hata oluştu: {str(e)}")
        
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Verilen prompt'a göre yanıt üretir
        
        Args:
            prompt: LLM'e gönderilecek istem metni
            **kwargs: Claude'a gönderilebilecek ek parametreler
            
        Returns:
            Üretilen yanıt metni
        """
        try:
            options = kwargs.get("options", {})
            temperature = options.get("temperature", 0.7)
            max_tokens = options.get("max_tokens", 1024)
            
            response = self.client.messages.create(
                model=self.model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            error_msg = f"Claude yanıt üretme hatası: {str(e)}"
            print(error_msg)
            return error_msg
    
    def generate_stream(self, prompt: str, **kwargs) -> Generator[str, None, None]:
        """
        Streaming modunda yanıt üretir
        
        Args:
            prompt: LLM'e gönderilecek istem metni
            **kwargs: Claude'a gönderilebilecek ek parametreler
            
        Yields:
            Parça parça üretilen yanıt metinleri
        """
        try:
            options = kwargs.get("options", {})
            temperature = options.get("temperature", 0.7)
            max_tokens = options.get("max_tokens", 1024)
            
            with self.client.messages.stream(
                model=self.model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                for chunk in stream:
                    if hasattr(chunk, 'delta') and hasattr(chunk.delta, 'text'):
                        text = chunk.delta.text
                        if text:
                            yield text
                
        except Exception as e:
            error_msg = f"Claude streaming hatası: {str(e)}"
            print(error_msg)
            yield error_msg 