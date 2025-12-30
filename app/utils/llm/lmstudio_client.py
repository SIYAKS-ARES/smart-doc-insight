from typing import Dict, Generator, Any, Optional
import requests
import json


class LMStudioClient:
    """LM Studio LLM saglayicisi ile etkilesim icin istemci (HTTP API)"""
    
    def __init__(self, model_name: str = "mistral-nemo-instruct-2407"):
        """
        LM Studio istemcisini baslatir
        
        Args:
            model_name: Kullanilacak model adi
        """
        self.model_name = model_name
        self.base_url = "http://localhost:1234/v1"
        self._verify_connection()
        
    def _verify_connection(self):
        """LM Studio sunucusuna baglanti kontrolu yapar"""
        try:
            response = requests.get(f"{self.base_url}/models", timeout=5)
            if response.status_code == 200:
                models = response.json().get("data", [])
                model_ids = [m.get("id", "") for m in models]
                if models:
                    print(f"LM Studio API baglantisi basarili. Modeller: {model_ids}")
                else:
                    print("LM Studio API'ye baglanildi, ancak hic yuklu model bulunamadi.")
            else:
                raise ConnectionError(f"LM Studio API yanit verdi ancak hata kodu: {response.status_code}")
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"LM Studio sunucusuna baglanamadi ({self.base_url}). "
                "LM Studio uygulamasinin calistigindan emin olun."
            )
        except Exception as e:
            raise Exception(f"LM Studio baglanti kontrolu sirasinda hata: {str(e)}")
    
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Verilen prompt'a gore yanit uretir
        
        Args:
            prompt: LLM'e gonderilecek istem metni
            **kwargs: Ek parametreler (options icinde temperature, max_tokens vb.)
            
        Returns:
            Uretilen yanit metni
        """
        try:
            options = kwargs.get("options", {})
            temperature = options.get("temperature", 0.7)
            max_tokens = options.get("max_tokens", 4096)
            
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=300  # 5 dakika timeout (uzun yanitlar icin)
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                error_msg = response.text
                print(f"LM Studio API hatasi ({response.status_code}): {error_msg}")
                return f"LM Studio Hatasi: {error_msg}"
                
        except requests.exceptions.Timeout:
            print("LM Studio yanit suresi doldu (timeout)")
            return "LM Studio Hatasi: Yanit suresi doldu"
        except requests.exceptions.ConnectionError:
            print("LM Studio baglantisi kesildi")
            return "LM Studio Hatasi: Baglanti kesildi"
        except Exception as e:
            print(f"LM Studio yanit uretme hatasi: {str(e)}")
            return f"LM Studio Hatasi: {str(e)}"
    
    def generate_stream(self, prompt: str, **kwargs) -> Generator[str, None, None]:
        """
        Streaming modunda yanit uretir
        
        Args:
            prompt: LLM'e gonderilecek istem metni
            **kwargs: Ek parametreler
            
        Yields:
            Parca parca uretilen yanit metinleri
        """
        try:
            options = kwargs.get("options", {})
            temperature = options.get("temperature", 0.7)
            max_tokens = options.get("max_tokens", 4096)
            
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                stream=True,
                timeout=300
            )
            
            if response.status_code != 200:
                yield f"LM Studio Hatasi: {response.text}"
                return
            
            # SSE (Server-Sent Events) formatinda gelen veriyi isle
            for line in response.iter_lines():
                if line:
                    line_text = line.decode('utf-8')
                    if line_text.startswith("data: "):
                        data_str = line_text[6:]  # "data: " kismini kaldir
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
                            
        except requests.exceptions.Timeout:
            yield "LM Studio Streaming Hatasi: Yanit suresi doldu"
        except requests.exceptions.ConnectionError:
            yield "LM Studio Streaming Hatasi: Baglanti kesildi"
        except Exception as e:
            print(f"LM Studio streaming hatasi: {str(e)}")
            yield f"LM Studio Streaming Hatasi: {str(e)}"
