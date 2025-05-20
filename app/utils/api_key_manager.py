import os
from flask import current_app, g
from flask_login import current_user

from app.models.api_key import APIKey
from app.utils.log_utils import logger

class APIKeyManager:
    """API anahtarlarını yönetmek için kullanılan sınıf"""
    
    @staticmethod
    def get_api_key(provider, user_id=None):
        """
        Belirli bir sağlayıcı için API anahtarını döndürür
        
        Args:
            provider: API sağlayıcı adı (openai, gemini, claude)
            user_id: Kullanıcı ID'si (None ise current_user kullanılır)
            
        Returns:
            str: API anahtarı veya boş string
        """
        try:
            # Kullanıcı ID'sini belirle
            if user_id is None and current_user and current_user.is_authenticated:
                # current_user'da id değil _id kullanılıyor
                user_id = str(current_user._id) if hasattr(current_user, '_id') else current_user.get_id()
            
            if not user_id:
                return ""
                
            # Log kaydı başlat
            logger.info(f"API anahtarı isteniyor - sağlayıcı: {provider}, kullanıcı: {user_id}")
                
            # Önce veritabanından API anahtarını kontrol et
            api_key_obj = APIKey.get_by_user_provider(user_id, provider)
            
            if api_key_obj and api_key_obj.key:
                logger.info(f"{provider} API anahtarı kullanıcı {user_id} için veritabanından alındı")
                return api_key_obj.key
                
            # Veritabanında yoksa, çevre değişkenlerini kontrol et
            env_var_name = f"{provider.upper()}_API_KEY"
            api_key = os.environ.get(env_var_name, "")
            
            if api_key:
                logger.info(f"{provider} API anahtarı çevre değişkenlerinden alındı")
            else:
                logger.warning(f"{provider} API anahtarı bulunamadı")
                
            return api_key
            
        except Exception as e:
            logger.exception(f"API anahtarı alınırken hata: {str(e)}")
            return ""
    
    @staticmethod
    def save_api_key(provider, api_key, model="", user_id=None):
        """
        API anahtarını kaydeder
        
        Args:
            provider: API sağlayıcı adı (openai, gemini, claude)
            api_key: API anahtarı
            model: Varsayılan model adı
            user_id: Kullanıcı ID'si (None ise current_user kullanılır)
            
        Returns:
            bool: Başarılı mı?
        """
        try:
            # Kullanıcı ID'sini belirle
            if user_id is None and current_user and current_user.is_authenticated:
                # current_user'da id değil _id kullanılıyor
                user_id = str(current_user._id) if hasattr(current_user, '_id') else current_user.get_id()
                print(f"Kullanıcı ID'si belirlendi: {user_id}")
            
            if not user_id:
                logger.warning(f"API anahtarı kaydedilemedi: Geçerli bir kullanıcı ID'si yok")
                return False
            
            # Log kaydı başlat
            logger.info(f"API anahtarı kaydediliyor - sağlayıcı: {provider}, kullanıcı: {user_id}, model: {model}")
            
            # Veritabanı bağlantısını kontrol et
            if not hasattr(current_app, 'db'):
                error_msg = "MongoDB bağlantısı bulunamadı (current_app.db yok)"
                logger.error(error_msg)
                print(error_msg)
                return False
                
            # Mevcut API anahtarını kontrol et
            try:
                api_key_obj = APIKey.get_by_user_provider(user_id, provider)
                logger.info(f"Mevcut API anahtarı kontrol ediliyor: {api_key_obj is not None}")
            except Exception as e:
                error_msg = f"API anahtarı kontrol edilirken hata: {str(e)}"
                logger.error(error_msg)
                print(error_msg)
                import traceback
                print(traceback.format_exc())
                return False
            
            if not api_key_obj:
                # Yeni API anahtarı oluştur
                try:
                    api_key_obj = APIKey(user_id, provider, key=api_key, model=model)
                    logger.info(f"Yeni {provider} API anahtarı oluşturuldu, kullanıcı: {user_id}")
                except Exception as e:
                    error_msg = f"Yeni API anahtarı oluşturulurken hata: {str(e)}"
                    logger.error(error_msg)
                    print(error_msg)
                    import traceback
                    print(traceback.format_exc())
                    return False
            else:
                # Mevcut API anahtarını güncelle
                try:
                    api_key_obj.key = api_key
                    if model:
                        api_key_obj.model = model
                    logger.info(f"Mevcut {provider} API anahtarı güncellendi, kullanıcı: {user_id}")
                except Exception as e:
                    error_msg = f"API anahtarı güncellenirken hata: {str(e)}"
                    logger.error(error_msg)
                    print(error_msg)
                    import traceback
                    print(traceback.format_exc())
                    return False
            
            # Kaydet
            try:
                api_key_obj.save()
                logger.info(f"{provider} API anahtarı veritabanına kaydedildi")
            except Exception as e:
                error_msg = f"API anahtarı veritabanına kaydedilirken hata: {str(e)}"
                logger.error(error_msg)
                print(error_msg)
                import traceback
                print(traceback.format_exc())
                return False
            
            # Çevre değişkenini de güncelle (geçici olarak)
            env_var_name = f"{provider.upper()}_API_KEY"
            os.environ[env_var_name] = api_key
            logger.info(f"{provider} API anahtarı çevre değişkenine kaydedildi")
            
            return True
            
        except Exception as e:
            error_msg = f"API anahtarı kaydedilirken beklenmeyen hata: {str(e)}"
            logger.exception(error_msg)
            print(error_msg)
            import traceback
            print(traceback.format_exc())
            return False
    
    @staticmethod
    def delete_api_key(provider, user_id=None):
        """
        API anahtarını siler
        
        Args:
            provider: API sağlayıcı adı (openai, gemini, claude)
            user_id: Kullanıcı ID'si (None ise current_user kullanılır)
            
        Returns:
            bool: Başarılı mı?
        """
        try:
            # Kullanıcı ID'sini belirle
            if user_id is None and current_user and current_user.is_authenticated:
                user_id = current_user.id
            
            if not user_id:
                logger.warning(f"API anahtarı silinemedi: Geçerli bir kullanıcı ID'si yok")
                return False
            
            # Log kaydı başlat
            logger.info(f"API anahtarı siliniyor - sağlayıcı: {provider}, kullanıcı: {user_id}")
                
            # API anahtarını bul
            api_key_obj = APIKey.get_by_user_provider(user_id, provider)
            
            if api_key_obj:
                # Sil
                api_key_obj.delete()
                logger.info(f"{provider} API anahtarı silindi, kullanıcı: {user_id}")
            else:
                logger.warning(f"{provider} API anahtarı bulunamadı, silme işlemi yapılmadı, kullanıcı: {user_id}")
            
            # Çevre değişkenini temizle (geçici olarak)
            env_var_name = f"{provider.upper()}_API_KEY"
            if env_var_name in os.environ:
                os.environ[env_var_name] = ""
                logger.info(f"{provider} API anahtarı çevre değişkeninden temizlendi")
            
            return True
            
        except Exception as e:
            logger.exception(f"API anahtarı silinirken hata: {str(e)}")
            return False
    
    @staticmethod
    def get_model(provider, user_id=None):
        """
        Belirli bir sağlayıcı için varsayılan model adını döndürür
        
        Args:
            provider: API sağlayıcı adı (openai, gemini, claude)
            user_id: Kullanıcı ID'si (None ise current_user kullanılır)
            
        Returns:
            str: Model adı veya varsayılan değer
        """
        try:
            # Kullanıcı ID'sini belirle
            if user_id is None and current_user and current_user.is_authenticated:
                # current_user'da id değil _id kullanılıyor
                user_id = str(current_user._id) if hasattr(current_user, '_id') else current_user.get_id()
            
            if not user_id:
                return APIKeyManager._get_default_model(provider)
            
            # Log kaydı başlat
            logger.info(f"Model bilgisi isteniyor - sağlayıcı: {provider}, kullanıcı: {user_id}")
                
            # API anahtarını bul
            api_key_obj = APIKey.get_by_user_provider(user_id, provider)
            
            if api_key_obj and api_key_obj.model:
                logger.info(f"{provider} model adı kullanıcı {user_id} için veritabanından alındı: {api_key_obj.model}")
                return api_key_obj.model
            
            # Varsayılan değeri döndür
            model = APIKeyManager._get_default_model(provider)
            logger.info(f"{provider} için varsayılan model kullanılıyor: {model}")
            return model
            
        except Exception as e:
            logger.exception(f"Model adı alınırken hata: {str(e)}")
            return APIKeyManager._get_default_model(provider)
    
    @staticmethod
    def _get_default_model(provider):
        """Sağlayıcı için varsayılan model adını döndürür"""
        defaults = {
            "openai": "gpt-3.5-turbo",
            "gemini": "gemini-2.0-flash",
            "claude": "claude-3-opus-20240229"
        }
        return defaults.get(provider, "")
        
    @staticmethod
    def update_model(provider, model, user_id=None):
        """
        Belirli bir sağlayıcı için kullanılan modeli günceller
        
        Args:
            provider: API sağlayıcı adı (openai, gemini, claude)
            model: Model adı
            user_id: Kullanıcı ID'si (None ise current_user kullanılır)
            
        Returns:
            bool: Başarılı mı?
        """
        try:
            # Kullanıcı ID'sini belirle
            if user_id is None and current_user and current_user.is_authenticated:
                # current_user'da id değil _id kullanılıyor
                user_id = str(current_user._id) if hasattr(current_user, '_id') else current_user.get_id()
            
            if not user_id:
                logger.warning(f"Model güncellenemedi: Geçerli bir kullanıcı ID'si yok")
                return False
            
            # Log kaydı başlat
            logger.info(f"Model bilgisi güncelleniyor - sağlayıcı: {provider}, model: {model}, kullanıcı: {user_id}")
            
            # API anahtarı objesini bul
            api_key_obj = APIKey.get_by_user_provider(user_id, provider)
            
            if not api_key_obj:
                logger.warning(f"Model güncellenemedi: {provider} için API anahtarı bulunamadı, kullanıcı: {user_id}")
                return False
            
            # Model bilgisini güncelle
            api_key_obj.model = model
            api_key_obj.save()
            
            logger.info(f"{provider} model bilgisi başarıyla güncellendi: {model}, kullanıcı: {user_id}")
            return True
            
        except Exception as e:
            logger.exception(f"Model güncellenirken hata: {str(e)}")
            return False 