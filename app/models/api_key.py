from datetime import datetime
from flask import current_app
from bson.objectid import ObjectId
import uuid

from app.utils.crypto_utils import CryptoHelper

class APIKey:
    """API anahtarlarını güvenli bir şekilde saklayan model sınıfı"""
    
    def __init__(self, user_id, provider, key="", model="", encrypted_key="", salt="", _id=None, created_at=None, updated_at=None):
        self._id = _id or str(uuid.uuid4())
        self.user_id = user_id
        self.provider = provider  # openai, gemini, claude, etc.
        self.model = model        # default model for this provider
        
        # API anahtarı (geçici olarak saklanır, kaydedilmez)
        self._key = key
        
        # Şifrelenmiş API anahtarı ve tuz değeri
        self.encrypted_key = encrypted_key
        self.salt = salt
        
        # Tarihler
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
    
    @property
    def key(self):
        """Şifresi çözülmüş API anahtarını döndürür"""
        if self._key:
            return self._key
            
        # API anahtarını çöz
        if self.encrypted_key and self.salt:
            try:
                app_secret = current_app.config.get('SECRET_KEY', 'default-secret-key')
                self._key = CryptoHelper.decrypt(self.encrypted_key, self.salt, app_secret)
                return self._key
            except Exception as e:
                print(f"API anahtarı şifre çözme hatası: {str(e)}")
                return ""
            
        return ""
    
    @key.setter
    def key(self, value):
        """API anahtarını ayarlar ve şifreler"""
        self._key = value
        
        if value:
            try:
                # API anahtarını şifrele
                app_secret = current_app.config.get('SECRET_KEY', 'default-secret-key')
                self.encrypted_key, self.salt = CryptoHelper.encrypt(value, app_secret)
            except Exception as e:
                print(f"API anahtarı şifreleme hatası: {str(e)}")
                self.encrypted_key = ""
                self.salt = ""
        else:
            self.encrypted_key = ""
            self.salt = ""
    
    def to_dict(self):
        """Model verisini sözlük olarak döndürür (veritabanına kaydetmek için)"""
        # _key değişkenini dict'e koymuyoruz çünkü bu şifresi çözülmüş anahtarı içeriyor
        data = {
            "_id": self._id,
            "user_id": self.user_id,
            "provider": self.provider,
            "model": self.model,
            "encrypted_key": self.encrypted_key,
            "salt": self.salt,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
        
        # _key değişkenini veri sözlüğüne dahil etmemek için kontrol
        if hasattr(self, '_key'):
            # _key değişkeni to_dict çıktısına eklenmeyecek
            pass
            
        return data
    
    @classmethod
    def from_dict(cls, data):
        """Sözlükten model nesnesi oluşturur"""
        if not data:
            return None
            
        return cls(
            _id=data.get("_id"),
            user_id=data.get("user_id"),
            provider=data.get("provider"),
            model=data.get("model"),
            encrypted_key=data.get("encrypted_key", ""),
            salt=data.get("salt", ""),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )
    
    @classmethod
    def get_by_user_provider(cls, user_id, provider):
        """Kullanıcı ve sağlayıcıya göre API anahtarını bulur"""
        db = current_app.db.api_keys
        data = db.find_one({"user_id": user_id, "provider": provider})
        return cls.from_dict(data)
    
    @classmethod
    def get_by_id(cls, key_id):
        """ID'ye göre API anahtarını bulur"""
        db = current_app.db.api_keys
        data = db.find_one({"_id": key_id})
        return cls.from_dict(data)
    
    def save(self):
        """API anahtarını veritabanına kaydeder"""
        try:
            # Veritabanı bağlantısını kontrol et
            if not hasattr(current_app, 'db'):
                raise Exception("Veritabanı bağlantısı bulunamadı (current_app.db yok)")
                
            db = current_app.db.api_keys
            
            # Güncelleme zamanını ayarla
            self.updated_at = datetime.now()
            
            # MongoDB'ye kaydet
            data = self.to_dict()
            
            # _id'nin string tipinde olduğunu doğrula
            if not isinstance(data["_id"], str):
                data["_id"] = str(data["_id"])
                
            print(f"MongoDB kaydı yapılıyor: {self._id}, sağlayıcı: {self.provider}")
                
            # Filtreyi ayrı, güncellenecek veriyi ayrı hazırla
            filter_doc = {"_id": data["_id"]}
            
            # MongoDB'ye kaydet
            result = db.update_one(
                filter_doc,
                {"$set": data},
                upsert=True
            )
            
            print(f"MongoDB kayıt sonucu: acknowledged={result.acknowledged}, modified={result.modified_count}, upserted_id={result.upserted_id}")
            
            return self
            
        except Exception as e:
            error_msg = f"API anahtarı kaydedilirken veritabanı hatası: {str(e)}"
            print(error_msg)
            import traceback
            print(traceback.format_exc())
            raise Exception(error_msg)
    
    def delete(self):
        """API anahtarını veritabanından siler"""
        db = current_app.db.api_keys
        db.delete_one({"_id": self._id})
        return True 