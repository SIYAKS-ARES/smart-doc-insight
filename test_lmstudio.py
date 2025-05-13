import os
from app import create_app
from flask import g

# LLM sağlayıcısını ayarla
os.environ['LLM_PROVIDER'] = 'lmstudio'

# Uygulamayı oluştur
app = create_app()

# LLM durumunu kontrol edecek bir route ekle
@app.route('/test_llm')
def test_llm():
    result = {
        'active_llm_provider': g.active_llm_provider,
        'lmstudio_available': g.lmstudio_available,
        'ollama_available': g.ollama_available,
        'active_llm_available': g.active_llm_available
    }
    
    print("LLM Durumu:")
    print(f"Active LLM Provider: {g.active_llm_provider}")
    print(f"LM Studio Available: {g.lmstudio_available}")
    print(f"Ollama Available: {g.ollama_available}")
    print(f"Active LLM Available: {g.active_llm_available}")
    
    # LM Studio ile test
    if g.active_llm_provider == 'lmstudio' and g.active_llm_available:
        try:
            from app.utils.llm import get_llm_client
            client = get_llm_client()
            llm_response = client.generate("Merhaba, bu bir test mesajıdır.")
            print(f"LM Studio yanıtı: {llm_response}")
            result['llm_response'] = llm_response
        except Exception as e:
            print(f"LLM Test Hatası: {str(e)}")
            result['error'] = str(e)
    
    return result

# Test için uygulamayı çalıştır
if __name__ == '__main__':
    with app.test_client() as client:
        print("LM Studio entegrasyonu test ediliyor...")
        response = client.get('/test_llm')
        print("\nTest tamamlandı!") 