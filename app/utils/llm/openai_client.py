from typing import Dict, Generator, Any, Optional
import openai

class OpenAIClient:
    """OpenAI API LLM sağlayıcısı ile etkileşim için istemci"""
    
    def __init__(self, api_key: str, model_name: str = "gpt-3.5-turbo"):
        """
        OpenAI istemcisini başlatır
        
        Args:
            api_key: OpenAI API anahtarı
            model_name: Kullanılacak model adı
        """
        self.api_key = api_key
        self.model_name = model_name
        self.client = None
        self._init_client()
        
    def _init_client(self):
        """OpenAI istemcisini başlatır"""
        try:
            self.client = openai.OpenAI(api_key=self.api_key)
            # Bağlantıyı test et (modelleri listele)
            try:
                models = self.client.models.list()
                model_names = [model.id for model in models.data]
                available = self.model_name in model_names
                if available:
                    print(f"OpenAI bağlantısı başarılı. Model '{self.model_name}' kullanılabilir.")
                else:
                    available_models = ", ".join(model_names[:5]) + "..." if len(model_names) > 5 else ", ".join(model_names)
                    print(f"OpenAI bağlantısı başarılı, ancak '{self.model_name}' modeli kullanılamıyor. Kullanılabilir modeller: {available_models}")
            except Exception as e:
                print(f"OpenAI model listesi alınamadı: {str(e)}")
            
        except Exception as e:
            raise Exception(f"OpenAI istemcisi başlatılırken hata oluştu: {str(e)}")
        
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Verilen prompt'a göre yanıt üretir
        
        Args:
            prompt: LLM'e gönderilecek istem metni
            **kwargs: OpenAI'ya gönderilebilecek ek parametreler
            
        Returns:
            Üretilen yanıt metni
        """
        try:
            options = kwargs.get("options", {})
            temperature = options.get("temperature", 0.7)
            max_tokens = options.get("max_tokens", 1024)
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            error_msg = f"OpenAI yanıt üretme hatası: {str(e)}"
            print(error_msg)
            return error_msg
    
    def generate_stream(self, prompt: str, **kwargs) -> Generator[str, None, None]:
        """
        Streaming modunda yanıt üretir
        
        Args:
            prompt: LLM'e gönderilecek istem metni
            **kwargs: OpenAI'ya gönderilebilecek ek parametreler
            
        Yields:
            Parça parça üretilen yanıt metinleri
        """
        try:
            options = kwargs.get("options", {})
            temperature = options.get("temperature", 0.7)
            max_tokens = options.get("max_tokens", 1024)
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
                
        except Exception as e:
            error_msg = f"OpenAI streaming hatası: {str(e)}"
            print(error_msg)
            yield error_msg 