from typing import Dict, Generator, Any, Optional

class LMStudioClient:
    """LM Studio LLM sağlayıcısı ile etkileşim için istemci"""
    
    def __init__(self, model_name: str = "deepseek-coder-v2-lite-instruct-mlx"):
        """
        LM Studio istemcisini başlatır
        
        Args:
            model_name: Kullanılacak model adı
        """
        self.model_name = model_name
        self.server_api_host = "localhost:1234"  # LM Studio varsayılan adresi
        self._init_client()
        
    def _init_client(self):
        """LM Studio istemcisini başlatır"""
        try:
            import lmstudio
            
            # İlk olarak istemcinin halihazırda yapılandırılmış olup olmadığını kontrol et
            try:
                # Varsayılan istemciyi yapılandırmayı dene
                lmstudio.configure_default_client(self.server_api_host)
                print(f"LM Studio API bağlantısı yapılandırıldı: {self.server_api_host}")
            except Exception as config_error:
                # Zaten bir varsayılan istemci varsa, bu hatayı görmezden gel ve devam et
                print(f"Varsayılan istemci zaten yapılandırılmış, mevcut yapılandırma kullanılıyor: {str(config_error)}")
                # Hata atma, mevcut yapılandırmayı kullanarak devam et
            
            # Model istemcisi oluştur
            self.client = lmstudio.llm(self.model_name)
            
            # Bağlantıyı test et
            try:
                info = self.client.get_info()
                print(f"LM Studio bağlantısı başarılı. Model: {self._get_model_name(info)}")
            except Exception as e:
                # Eğer model erişilemezse, daha anlaşılır bir hata mesajı oluştur
                if "The model could not be loaded" in str(e):
                    raise ConnectionError(f"LM Studio API'ye bağlantı başarılı, ancak '{self.model_name}' modeli yüklenemedi. Lütfen LM Studio'da modeli yükleyin.")
                else:
                    raise ConnectionError(f"LM Studio API bağlantısı başarılı, ancak model bilgisi alınamadı: {str(e)}")
            
        except ImportError:
            raise ImportError("lmstudio paketi yüklü değil. 'pip install lmstudio' komutu ile yükleyin.")
        except ConnectionError as e:
            raise ConnectionError(f"LM Studio sunucusuna bağlantı kurulamadı ({self.server_api_host}). LM Studio uygulamasının çalıştığından emin olun: {str(e)}")
        except Exception as e:
            raise Exception(f"LM Studio istemcisi başlatılırken hata oluştu: {str(e)}")
        
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Verilen prompt'a göre yanıt üretir
        
        Args:
            prompt: LLM'e gönderilecek istem metni
            **kwargs: LM Studio'ya gönderilebilecek ek parametreler
            
        Returns:
            Üretilen yanıt metni
        """
        try:
            options = kwargs.get("options", {})
            temperature = options.get("temperature", 0.7)
            max_tokens = options.get("max_tokens", 1024)
            
            # API'nin kabul ettiği parametreleri kontrol et
            api_params = {}
            
            # Parametreleri güvenli bir şekilde ekle
            try:
                import inspect
                # respond metodunun parametrelerini kontrol et
                respond_params = inspect.signature(self.client.respond).parameters.keys()
                
                if 'temperature' in respond_params:
                    api_params['temperature'] = temperature
                if 'max_tokens' in respond_params:
                    api_params['max_tokens'] = max_tokens
                    
                print(f"Kullanılan API parametreleri: {api_params}")
            except Exception as param_error:
                print(f"Parametre kontrolü hatası: {str(param_error)}")
                # Hiçbir parametre belirtme
                api_params = {}
            
            # Parametrelerle birlikte yanıt al
            if api_params:
                response = self.client.respond(prompt, **api_params)
            else:
                # Hiç parametre olmadan dene
                response = self.client.respond(prompt)
            
            # PredictionResult nesnesini string'e dönüştür
            try:
                # 1. Öncelikle text veya content özelliği var mı kontrol et
                if hasattr(response, 'text'):
                    return response.text
                elif hasattr(response, 'content'):
                    return response.content
                elif hasattr(response, 'output'):
                    return response.output
                # 2. Response nesnesini string'e dönüştürmeyi dene
                else:
                    return str(response)
            except Exception as str_error:
                print(f"Yanıt dönüştürme hatası: {str(str_error)}")
                # Hata durumunda nesnenin kendisini string olarak döndür
                return str(response)
                
        except Exception as e:
            print(f"LM Studio yanıt üretme hatası: {str(e)}")
            return f"LM Studio Hatası: {str(e)}"
    
    def generate_stream(self, prompt: str, **kwargs) -> Generator[str, None, None]:
        """
        Streaming modunda yanıt üretir
        
        Args:
            prompt: LLM'e gönderilecek istem metni
            **kwargs: LM Studio'ya gönderilebilecek ek parametreler
            
        Yields:
            Parça parça üretilen yanıt metinleri
        """
        try:
            options = kwargs.get("options", {})
            temperature = options.get("temperature", 0.7)
            max_tokens = options.get("max_tokens", 1024)
            
            # API'nin kabul ettiği parametreleri kontrol et
            api_params = {}
            
            # Parametreleri güvenli bir şekilde ekle
            try:
                import inspect
                # respond_stream metodunun parametrelerini kontrol et
                stream_params = inspect.signature(self.client.respond_stream).parameters.keys()
                
                if 'temperature' in stream_params:
                    api_params['temperature'] = temperature
                if 'max_tokens' in stream_params:
                    api_params['max_tokens'] = max_tokens
                    
                print(f"Kullanılan stream API parametreleri: {api_params}")
            except Exception as param_error:
                print(f"Stream parametre kontrolü hatası: {str(param_error)}")
                # Hiçbir parametre belirtme
                api_params = {}
            
            # Parametrelerle birlikte yanıt al
            if api_params:
                for chunk in self.client.respond_stream(prompt, **api_params):
                    # Her parçayı string'e dönüştür
                    try:
                        if hasattr(chunk, 'text'):
                            yield chunk.text
                        elif hasattr(chunk, 'content'):
                            yield chunk.content
                        elif hasattr(chunk, 'output'):
                            yield chunk.output
                        else:
                            yield str(chunk)
                    except:
                        yield str(chunk)
            else:
                # Hiç parametre olmadan dene
                for chunk in self.client.respond_stream(prompt):
                    # Her parçayı string'e dönüştür
                    try:
                        if hasattr(chunk, 'text'):
                            yield chunk.text
                        elif hasattr(chunk, 'content'):
                            yield chunk.content
                        elif hasattr(chunk, 'output'):
                            yield chunk.output
                        else:
                            yield str(chunk)
                    except:
                        yield str(chunk)
                
        except Exception as e:
            print(f"LM Studio streaming hatası: {str(e)}")
            yield f"LM Studio Streaming Hatası: {str(e)}"

    def _get_model_name(self, model_info):
        """Model bilgisinden model adını güvenli bir şekilde alır"""
        try:
            if hasattr(model_info, 'display_name'):
                return model_info.display_name
            elif hasattr(model_info, '__dict__'):
                attrs = model_info.__dict__
                if 'display_name' in attrs:
                    return attrs['display_name']
            
            # Yukarıdaki yöntemler başarısız olursa, string temsilini kullan
            return str(model_info)
        except:
            return self.model_name  # Varsayılan model adına geri dön 