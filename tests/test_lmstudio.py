import os
import pytest
from app.utils.llm import get_llm_client

@pytest.mark.parametrize("provider,model", [
    ("lmstudio", "llama-3.2-1b-instruct"),
])
def test_lmstudio_generate(provider, model):
    """LM Studio istemcisiyle metin oluşturulabildiğini test eder"""
    os.environ["LLM_PROVIDER"] = provider
    os.environ["LLM_STUDIO_MODEL"] = model
    
    client = get_llm_client()
    resp = client.generate("Merhaba dünya")
    
    assert isinstance(resp, str) and len(resp) > 0
    
    print(f"LM Studio yanıtı: {resp[:100]}...")  # İlk 100 karakteri göster

@pytest.mark.parametrize("provider,model", [
    ("lmstudio", "llama-3.2-1b-instruct"),
])
def test_lmstudio_generate_stream(provider, model):
    """LM Studio istemcisiyle streaming modunda metin oluşturulabildiğini test eder"""
    os.environ["LLM_PROVIDER"] = provider
    os.environ["LLM_STUDIO_MODEL"] = model
    
    client = get_llm_client()
    chunks = []
    
    for chunk in client.generate_stream(
        "Merhaba dünya", 
        options={
            "temperature": 0.7,
            "max_tokens": 50
        }
    ):
        chunks.append(chunk)
        
    # En az bir parça dönmüş olmalı
    assert len(chunks) > 0
    
    # Tüm parçaları birleştir
    full_response = "".join(chunks)
    assert len(full_response) > 0
    
    print(f"LM Studio stream yanıtı: {full_response[:100]}...")  # İlk 100 karakteri göster
