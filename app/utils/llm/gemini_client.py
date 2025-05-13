from typing import Dict, Generator, Any, Optional
import google.generativeai as genai

class GeminiClient:
    """Google Gemini API LLM sağlayıcısı ile etkileşim için istemci"""
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        """
        Gemini istemcisini başlatır
        
        Args:
            api_key: Google API anahtarı
            model_name: Kullanılacak model adı
        """
        self.api_key = api_key
        self.model_name = model_name
        self.client = None
        self._init_client()
        
    def _init_client(self):
        """Gemini istemcisini başlatır"""
        try:
            # API anahtarını yapılandır
            genai.configure(api_key=self.api_key)
            
            # Modelleri listele ve seçilen modelin varlığını kontrol et
            try:
                models = genai.list_models()
                model_names = [model.name.split('/')[-1] for model in models]
                
                # Modelin kullanılabilir olup olmadığını kontrol et
                available_model = next((model for model in models if self.model_name in model.name), None)
                
                if available_model:
                    print(f"Gemini bağlantısı başarılı. Model '{self.model_name}' kullanılabilir.")
                    self.client = genai.GenerativeModel(self.model_name)
                else:
                    available_models = ", ".join(model_names[:5]) + "..." if len(model_names) > 5 else ", ".join(model_names)
                    print(f"Gemini bağlantısı başarılı, ancak '{self.model_name}' modeli bulunamadı. Kullanılabilir modeller: {available_models}")
                    # Varsayılan modeli kullan - gemini-2.0-flash kullanılıyor
                    self.model_name = "gemini-2.0-flash"
                    self.client = genai.GenerativeModel(self.model_name)
                    print(f"Varsayılan model '{self.model_name}' kullanılıyor.")
            except Exception as e:
                print(f"Gemini model listesi alınamadı: {str(e)}")
                # Hata alsa bile modeli başlatmaya çalış
                self.client = genai.GenerativeModel(self.model_name)
                
        except Exception as e:
            raise Exception(f"Gemini istemcisi başlatılırken hata oluştu: {str(e)}")
        
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Verilen prompt'a göre yanıt üretir
        
        Args:
            prompt: LLM'e gönderilecek istem metni
            **kwargs: Gemini'ye gönderilebilecek ek parametreler
            
        Returns:
            Üretilen yanıt metni
        """
        try:
            options = kwargs.get("options", {})
            temperature = options.get("temperature", 0.7)
            max_tokens = options.get("max_tokens", 1024)
            
            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
                "top_p": 0.95,
                "top_k": 40
            }
            
            response = self.client.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            return response.text
            
        except Exception as e:
            error_msg = f"Gemini yanıt üretme hatası: {str(e)}"
            print(error_msg)
            return error_msg
    
    def generate_stream(self, prompt: str, **kwargs) -> Generator[str, None, None]:
        """
        Streaming modunda yanıt üretir
        
        Args:
            prompt: LLM'e gönderilecek istem metni
            **kwargs: Gemini'ye gönderilebilecek ek parametreler
            
        Yields:
            Parça parça üretilen yanıt metinleri
        """
        try:
            options = kwargs.get("options", {})
            temperature = options.get("temperature", 0.7)
            max_tokens = options.get("max_tokens", 1024)
            
            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
                "top_p": 0.95,
                "top_k": 40
            }
            
            response = self.client.generate_content(
                prompt,
                generation_config=generation_config,
                stream=True
            )
            
            for chunk in response:
                if hasattr(chunk, 'text') and chunk.text:
                    yield chunk.text
                
        except Exception as e:
            error_msg = f"Gemini streaming hatası: {str(e)}"
            print(error_msg)
            yield error_msg 