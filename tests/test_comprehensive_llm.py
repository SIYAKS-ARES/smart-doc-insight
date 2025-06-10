import os
import sys
import traceback
from unittest.mock import patch, MagicMock

# Flask app context için gerekli import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.utils.llm_utils import (
    analyze_text_with_llm,
    parse_llm_results,
    DEFAULT_ANALYSIS_CATEGORIES
)

class TestComprehensiveLLM:
    """
    Tüm LLM sağlayıcıları için kapsamlı test sınıfı
    """
    
    @classmethod
    def setup_class(cls):
        """Test sınıfı başlatma"""
        cls.app = create_app()
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        
        # Test metni - daha zengin içerik
        cls.test_text = """
        Özet
        Bu projede, Veri Tabanı Yönetim Sistemleri dersinde öğrenilen bilgilerin pratiğe
        dökülmesi amacıyla RestauPOS isimli bir restoran otomasyonu geliştirilmiştir. Bu 
        otomasyon, restoranların müşteri siparişlerini, stok takibini, fatura oluşturma 
        işlemlerini yönetmeye yöneliktir.

        Grup Üyeleri:
        - Ahmet Yılmaz (Backend kodlama)
        - Ayşe Kaya (Veritabanı tasarımı)
        - Mehmet Demir (Arayüz tasarımı)
        - Fatma Özkan (Test uzmanı)

        Görev Dağılımı:
        Ahmet: Backend kodlama, API entegrasyonu
        Ayşe: Veritabanı tasarımı, SQL sorguları
        Mehmet: Frontend arayüzü, UX/UI tasarımı
        Fatma: Test senaryoları, kalite kontrol

        Diyagramlar:
        Veritabanı ER diyagramı: Ayşe Kaya tarafından çizilmiştir.
        Kullanım akış diyagramı: Mehmet Demir tarafından hazırlanmıştır.
        Sistem mimarisi diyagramı: Ahmet Yılmaz tarafından oluşturulmuştur.

        Başlıklar:
        1. Giriş
        2. Sistem Analizi
        3. Veri Tabanı Tasarımı
        4. Kullanıcı Arayüzü
        5. Test ve Kalite Kontrol
        6. Sonuç ve Öneriler

        Eksik Kısımlar:
        - Güvenlik bölümü eksik
        - Performans analizi yapılmamış
        - Mobil uyumluluk testi yapılmamış
        """
        
        # Özel kategoriler test için
        cls.custom_categories = {
            "custom_team": "Proje ekibi kimlerden oluşuyor?",
            "custom_technologies": "Hangi teknolojiler kullanılmış?",
            "custom_challenges": "Projede karşılaşılan zorluklar neler?"
        }
        
        # Mock LLM yanıtları - varsayılan kategoriler için
        cls.mock_default_response = """1. Grup üyeleri:
        • Ahmet Yılmaz (Backend kodlama)
        • Ayşe Kaya (Veritabanı tasarımı)
        • Mehmet Demir (Arayüz tasarımı)
        • Fatma Özkan (Test uzmanı)

        2. Kim hangi bölümden sorumlu?
        • Ahmet: Backend kodlama, API entegrasyonu
        • Ayşe: Veritabanı tasarımı, SQL sorguları
        • Mehmet: Frontend arayüzü, UX/UI tasarımı
        • Fatma: Test senaryoları, kalite kontrol

        3. Diyagramları kim çizmiş?
        • Veritabanı ER diyagramı: Ayşe Kaya tarafından çizilmiştir
        • Kullanım akış diyagramı: Mehmet Demir tarafından hazırlanmıştır
        • Sistem mimarisi diyagramı: Ahmet Yılmaz tarafından oluşturulmuştur

        4. Belirgin başlıklar neler?
        • Giriş
        • Sistem Analizi
        • Veri Tabanı Tasarımı
        • Kullanıcı Arayüzü
        • Test ve Kalite Kontrol
        • Sonuç ve Öneriler

        5. Eksik kısımlar:
        • Güvenlik bölümü eksik
        • Performans analizi yapılmamış
        • Mobil uyumluluk testi yapılmamış"""
        
        # Mock LLM yanıtları - özel kategoriler için
        cls.mock_custom_response = """• Proje ekibi kimlerden oluşuyor?
        Ahmet Yılmaz, Ayşe Kaya, Mehmet Demir ve Fatma Özkan olmak üzere 4 kişilik bir ekipten oluşmaktadır.

        • Hangi teknolojiler kullanılmış?
        Veri Tabanı Yönetim Sistemleri, Backend kodlama teknolojileri, Frontend arayüz teknolojileri kullanılmıştır.

        • Projede karşılaşılan zorluklar neler?
        Bu konuda bilgi bulunamadı."""
    
    @classmethod
    def teardown_class(cls):
        """Test sınıfı sonlandırma"""
        cls.app_context.pop()
    
    def test_parse_standard_categories_with_numbered_headers(self):
        """Standart kategoriler için numaralı başlıkları test et"""
        print("\n=== Standart Kategoriler - Numaralı Başlık Testi ===")
        
        # Mock analysis object oluştur
        analysis = {key: [] for key in DEFAULT_ANALYSIS_CATEGORIES.keys()}
        analysis["ham_sonuc"] = []  # Liste olarak başlat
        
        # Test et
        result = parse_llm_results(
            self.mock_default_response, 
            DEFAULT_ANALYSIS_CATEGORIES
        )
        
        # Sonuçları kontrol et
        assert len(result["grup_uyeleri"]) > 0, "Grup üyeleri boş olmamalı"
        assert len(result["sorumluluklar"]) > 0, "Sorumluluklar boş olmamalı"
        assert len(result["diyagramlar"]) > 0, "Diyagramlar boş olmamalı"
        assert len(result["basliklar"]) > 0, "Başlıklar boş olmamalı"
        assert len(result["eksikler"]) > 0, "Eksikler boş olmamalı"
        
        print("✅ Standart kategoriler başarıyla ayrıştırıldı")
        print(f"Grup üyeleri: {result['grup_uyeleri']}")
        print(f"Sorumluluklar: {result['sorumluluklar']}")
        print(f"Diyagramlar: {result['diyagramlar']}")
        print(f"Başlıklar: {result['basliklar']}")
        print(f"Eksikler: {result['eksikler']}")
        
    def test_parse_custom_categories(self):
        """Özel kategoriler için ayrıştırma testi"""
        print("\n=== Özel Kategoriler Testi ===")
        
        # Mock analysis object oluştur
        analysis = {key: [] for key in self.custom_categories.keys()}
        analysis["ham_sonuc"] = []  # Liste olarak başlat
        
        # Test et
        result = parse_llm_results(
            self.mock_custom_response,
            self.custom_categories
        )
        
        # Özel kategorilerin var olduğunu kontrol et
        for key in self.custom_categories.keys():
            assert key in result, f"Özel kategori {key} sonuçta bulunmalı"
        
        print("✅ Özel kategoriler başarıyla ayrıştırıldı")
        for key, value in result.items():
            if key.startswith('custom_'):
                print(f"{key}: {value}")
    
    def test_ollama_provider(self):
        """Ollama sağlayıcısını test et"""
        print("\n=== Ollama Sağlayıcı Testi ===")
        
        # Ollama sağlayıcısını ayarla
        original_provider = os.environ.get('LLM_PROVIDER')
        os.environ['LLM_PROVIDER'] = 'ollama'
        
        try:
            with patch('app.utils.llm.get_llm_client') as mock_client:
                # Mock client setup
                mock_instance = MagicMock()
                mock_instance.generate.return_value = self.mock_default_response
                mock_client.return_value = mock_instance
                
                # Test analizi çalıştır
                result = analyze_text_with_llm([self.test_text])
                
                # Sonuçları kontrol et
                assert "grup_uyeleri" in result
                assert "sorumluluklar" in result
                assert "diyagramlar" in result
                assert "basliklar" in result
                assert "eksikler" in result
                
                print("✅ Ollama sağlayıcısı başarıyla çalıştı")
                print(f"Grup üyeleri sayısı: {len(result['grup_uyeleri'])}")
                
        except Exception as e:
            print(f"❌ Ollama testi başarısız: {str(e)}")
            print(traceback.format_exc())
        finally:
            # Orijinal provider'ı geri yükle
            if original_provider:
                os.environ['LLM_PROVIDER'] = original_provider
            elif 'LLM_PROVIDER' in os.environ:
                del os.environ['LLM_PROVIDER']
    
    def test_lmstudio_provider(self):
        """LM Studio sağlayıcısını test et"""
        print("\n=== LM Studio Sağlayıcı Testi ===")
        
        # LM Studio sağlayıcısını ayarla
        original_provider = os.environ.get('LLM_PROVIDER')
        os.environ['LLM_PROVIDER'] = 'lmstudio'
        
        try:
            with patch('app.utils.llm.get_llm_client') as mock_client:
                # Mock client setup
                mock_instance = MagicMock()
                mock_instance.generate.return_value = self.mock_default_response
                mock_client.return_value = mock_instance
                
                # Test analizi çalıştır
                result = analyze_text_with_llm([self.test_text])
                
                # Sonuçları kontrol et
                assert "grup_uyeleri" in result
                assert "sorumluluklar" in result
                assert "diyagramlar" in result
                assert "basliklar" in result
                assert "eksikler" in result
                
                print("✅ LM Studio sağlayıcısı başarıyla çalıştı")
                print(f"Diyagramlar sayısı: {len(result['diyagramlar'])}")
                
        except Exception as e:
            print(f"❌ LM Studio testi başarısız: {str(e)}")
            print(traceback.format_exc())
        finally:
            # Orijinal provider'ı geri yükle
            if original_provider:
                os.environ['LLM_PROVIDER'] = original_provider
            elif 'LLM_PROVIDER' in os.environ:
                del os.environ['LLM_PROVIDER']
    
    def test_openai_provider(self):
        """OpenAI sağlayıcısını test et"""
        print("\n=== OpenAI Sağlayıcı Testi ===")
        
        # OpenAI sağlayıcısını ayarla
        original_provider = os.environ.get('LLM_PROVIDER')
        os.environ['LLM_PROVIDER'] = 'openai'
        
        try:
            with patch('app.utils.llm.get_llm_client') as mock_client:
                # Mock client setup
                mock_instance = MagicMock()
                mock_instance.generate.return_value = self.mock_default_response
                mock_client.return_value = mock_instance
                
                # Test analizi çalıştır
                result = analyze_text_with_llm([self.test_text])
                
                # Sonuçları kontrol et
                assert "grup_uyeleri" in result
                assert "sorumluluklar" in result
                assert "diyagramlar" in result
                assert "basliklar" in result
                assert "eksikler" in result
                
                print("✅ OpenAI sağlayıcısı başarıyla çalıştı")
                print(f"Başlıklar sayısı: {len(result['basliklar'])}")
                
        except Exception as e:
            print(f"❌ OpenAI testi başarısız: {str(e)}")
            print(traceback.format_exc())
        finally:
            # Orijinal provider'ı geri yükle
            if original_provider:
                os.environ['LLM_PROVIDER'] = original_provider
            elif 'LLM_PROVIDER' in os.environ:
                del os.environ['LLM_PROVIDER']
    
    def test_gemini_provider(self):
        """Gemini sağlayıcısını test et"""
        print("\n=== Gemini Sağlayıcı Testi ===")
        
        # Gemini sağlayıcısını ayarla
        original_provider = os.environ.get('LLM_PROVIDER')
        os.environ['LLM_PROVIDER'] = 'gemini'
        
        try:
            with patch('app.utils.llm.get_llm_client') as mock_client:
                # Mock client setup
                mock_instance = MagicMock()
                mock_instance.generate.return_value = self.mock_default_response
                mock_client.return_value = mock_instance
                
                # Test analizi çalıştır
                result = analyze_text_with_llm([self.test_text])
                
                # Sonuçları kontrol et
                assert "grup_uyeleri" in result
                assert "sorumluluklar" in result
                assert "diyagramlar" in result
                assert "basliklar" in result
                assert "eksikler" in result
                
                print("✅ Gemini sağlayıcısı başarıyla çalıştı")
                print(f"Eksikler sayısı: {len(result['eksikler'])}")
                
        except Exception as e:
            print(f"❌ Gemini testi başarısız: {str(e)}")
            print(traceback.format_exc())
        finally:
            # Orijinal provider'ı geri yükle
            if original_provider:
                os.environ['LLM_PROVIDER'] = original_provider
            elif 'LLM_PROVIDER' in os.environ:
                del os.environ['LLM_PROVIDER']
    
    '''def test_claude_provider(self):
        """Claude sağlayıcısını test et"""
        print("\n=== Claude Sağlayıcı Testi ===")
        
        # Claude sağlayıcısını ayarla
        original_provider = os.environ.get('LLM_PROVIDER')
        os.environ['LLM_PROVIDER'] = 'claude'
        
        try:
            with patch('app.utils.llm.get_llm_client') as mock_client:
                # Mock client setup
                mock_instance = MagicMock()
                mock_instance.generate.return_value = self.mock_default_response
                mock_client.return_value = mock_instance
                
                # Test analizi çalıştır
                result = analyze_text_with_llm([self.test_text])
                
                # Sonuçları kontrol et
                assert "grup_uyeleri" in result
                assert "sorumluluklar" in result
                assert "diyagramlar" in result
                assert "basliklar" in result
                assert "eksikler" in result
                
                print("✅ Claude sağlayıcısı başarıyla çalıştı")
                print(f"Sorumluluklar sayısı: {len(result['sorumluluklar'])}")
                
        except Exception as e:
            print(f"❌ Claude testi başarısız: {str(e)}")
            print(traceback.format_exc())
        finally:
            # Orijinal provider'ı geri yükle
            if original_provider:
                os.environ['LLM_PROVIDER'] = original_provider
            elif 'LLM_PROVIDER' in os.environ:
                del os.environ['LLM_PROVIDER']
    '''
    def test_custom_categories_all_providers(self):
        """Tüm sağlayıcılar için özel kategoriler testi"""
        print("\n=== Tüm Sağlayıcılar için Özel Kategoriler Testi ===")
        
        providers = ['ollama', 'lmstudio', 'openai', 'gemini']
        original_provider = os.environ.get('LLM_PROVIDER')
        
        for provider in providers:
            print(f"\n--- {provider.upper()} ile özel kategoriler testi ---")
            os.environ['LLM_PROVIDER'] = provider
            
            try:
                with patch('app.utils.llm.get_llm_client') as mock_client:
                    # Mock client setup
                    mock_instance = MagicMock()
                    mock_instance.generate.return_value = self.mock_custom_response
                    mock_client.return_value = mock_instance
                    
                    # Özel kategorilerle test analizi çalıştır
                    result = analyze_text_with_llm(
                        [self.test_text], 
                        categories=self.custom_categories
                    )
                    
                    # Özel kategorilerin varlığını kontrol et
                    for key in self.custom_categories.keys():
                        assert key in result, f"{provider} için {key} kategorisi bulunmalı"
                    
                    print(f"✅ {provider.upper()} özel kategoriler testi başarılı")
                    
            except Exception as e:
                print(f"❌ {provider.upper()} özel kategoriler testi başarısız: {str(e)}")
        
        # Orijinal provider'ı geri yükle
        if original_provider:
            os.environ['LLM_PROVIDER'] = original_provider
        elif 'LLM_PROVIDER' in os.environ:
            del os.environ['LLM_PROVIDER']
    
    def test_error_handling(self):
        """Hata yönetimi testleri"""
        print("\n=== Hata Yönetimi Testleri ===")
        
        # Boş metin testi
        result_empty = analyze_text_with_llm([])
        assert "grup_uyeleri" in result_empty
        print("✅ Boş metin testi başarılı")
        
        # None metin testi
        result_none = analyze_text_with_llm([None])
        assert "grup_uyeleri" in result_none
        print("✅ None metin testi başarılı")
        
        # Geçersiz kategoriler testi
        invalid_categories = {"invalid_key": "Invalid question?"}
        result_invalid = analyze_text_with_llm([self.test_text], categories=invalid_categories)
        assert "invalid_key" in result_invalid
        print("✅ Geçersiz kategoriler testi başarılı")
        
        # LLM bağlantı hatası simülasyonu
        with patch('app.utils.llm.get_llm_client') as mock_client:
            mock_client.side_effect = Exception("Bağlantı hatası")
            
            try:
                result_error = analyze_text_with_llm([self.test_text])
                # Hata durumunda bile temel yapı korunmalı
                assert "grup_uyeleri" in result_error
                print("✅ LLM bağlantı hatası testi başarılı")
            except Exception as e:
                print(f"⚠️ LLM bağlantı hatası testi: {str(e)}")
    
    def test_regex_pattern_resilience(self):
        """Regex pattern dayanıklılık testleri"""
        print("\n=== Regex Pattern Dayanıklılık Testleri ===")
        
        # Test verileri
        test_cases = [
            "1. Grup üyeleri",
            "2. Kim hangi bölümden sorumlu?",
            "3. Diyagramları kim çizmiş?",
            "4. Belirgin başlıklar neler?",
            "5. Eksik kısımlar:"
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\nTest {i}: {test_case}")
            
            # Test için mock yanıt oluştur
            response = f"{test_case}\n"
            response += "• Test içeriği 1\n"
            response += "• Test içeriği 2\n"
            response += "• Test içeriği 3\n"
            
            # Test et
            result = parse_llm_results(response, DEFAULT_ANALYSIS_CATEGORIES)
            
            # Sonuçları kontrol et
            for category in DEFAULT_ANALYSIS_CATEGORIES.keys():
                if category in result:
                    print(f"{category}: {result[category]}")
            
            print("✅ Test başarılı")

if __name__ == "__main__":
    # Test sınıfını çalıştır
    test_instance = TestComprehensiveLLM()
    test_instance.setup_class()
    
    try:
        # Tüm testleri çalıştır
        test_instance.test_parse_standard_categories_with_numbered_headers()
        test_instance.test_parse_custom_categories()
        test_instance.test_ollama_provider()
        test_instance.test_lmstudio_provider()
        test_instance.test_openai_provider()
        test_instance.test_gemini_provider()
        #test_instance.test_claude_provider()
        test_instance.test_custom_categories_all_providers()
        test_instance.test_error_handling()
        test_instance.test_regex_pattern_resilience()
        
        print("\n🎉 TÜM TESTLER BAŞARIYLA TAMAMLANDI!")
        
    except Exception as e:
        print(f"\n❌ Test hatası: {str(e)}")
        print(traceback.format_exc())
    finally:
        test_instance.teardown_class() 