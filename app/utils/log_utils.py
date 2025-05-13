import logging
import re
import traceback
from functools import wraps

# Loglama formatını ayarla
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Maskeler
API_KEY_PATTERN = re.compile(r'([\'"]?(?:api[_-]?key|auth[_-]?token)[\'"]?\s*[=:]\s*[\'"]?)([a-zA-Z0-9_\-\.]+)')
SECRET_KEY_PATTERN = re.compile(r'([\'"]?(?:secret[_-]?key|secret|password|passwd)[\'"]?\s*[=:]\s*[\'"]?)([a-zA-Z0-9_\-\.]+)')

def mask_sensitive_data(text):
    """
    Hassas verileri maskeleyerek güvenli loglama sağlar
    
    Args:
        text: Maskelenecek metin
        
    Returns:
        str: Maskelenmiş metin
    """
    if not text or not isinstance(text, str):
        return str(text)
    
    # API anahtarlarını maskele
    text = API_KEY_PATTERN.sub(r'\1xxx...xxx', text)
    
    # Diğer gizli anahtarları maskele
    text = SECRET_KEY_PATTERN.sub(r'\1xxx...xxx', text)
    
    return text

def get_logger(name):
    """
    Belirli bir isimle logger oluşturur
    
    Args:
        name: Logger ismi
        
    Returns:
        Logger: Logger nesnesi
    """
    return logging.getLogger(name)

class SafeLogger:
    """
    Hassas verileri maskeleyen güvenli loglama sınıfı
    """
    
    def __init__(self, name=None):
        self.logger = logging.getLogger(name or __name__)
        self.mongo_handler = None
    
    def setup_mongodb_logging(self, collection_name="system_logs", async_mode=True, 
                              max_queue_size=1000, cleanup_days=30, connection_string=None):
        """
        MongoDB'ye loglama için ayarları yapar
        
        Args:
            collection_name: Log kayıtlarının saklanacağı koleksiyon adı
            async_mode: Asenkron modda çalışıp çalışmayacağı
            max_queue_size: Asenkron modda maksimum kuyruk boyutu
            cleanup_days: Kaç günden eski logların temizleneceği (0 ise temizleme yapılmaz)
            connection_string: MongoDB bağlantı URL'si (None ise Flask uygulamasının bağlantısı kullanılır)
        """
        try:
            from app.utils.mongodb_log_handler import MongoDBLogHandler
            
            # Önceki bir MongoDB handler varsa kaldır
            if self.mongo_handler:
                self.logger.removeHandler(self.mongo_handler)
                self.mongo_handler.close()
            
            # Yeni MongoDB log handler'ı oluştur
            self.mongo_handler = MongoDBLogHandler(
                collection_name=collection_name,
                async_mode=async_mode,
                max_queue_size=max_queue_size,
                cleanup_days=cleanup_days,
                connection_string=connection_string
            )
            
            # Handler formatını ayarla
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            self.mongo_handler.setFormatter(formatter)
            
            # Handler'ı logger'a ekle
            self.logger.addHandler(self.mongo_handler)
            
            print(f"MongoDB loglama başarıyla aktif edildi - Koleksiyon: {collection_name} "
                  f"(Asenkron: {async_mode}, Temizleme: {cleanup_days} gün)")
        except Exception as e:
            print(f"MongoDB loglama kurulumu başarısız oldu: {str(e)}")
    
    def disable_mongodb_logging(self):
        """MongoDB logging'i devre dışı bırakır"""
        if self.mongo_handler:
            try:
                self.logger.removeHandler(self.mongo_handler)
                self.mongo_handler.close()
                self.mongo_handler = None
                print("MongoDB loglama devre dışı bırakıldı")
            except Exception as e:
                print(f"MongoDB loglama devre dışı bırakma hatası: {str(e)}")
    
    def info(self, message, *args, **kwargs):
        """Bilgi seviyesinde log"""
        self.logger.info(mask_sensitive_data(message), *args, **kwargs)
    
    def warning(self, message, *args, **kwargs):
        """Uyarı seviyesinde log"""
        self.logger.warning(mask_sensitive_data(message), *args, **kwargs)
    
    def error(self, message, *args, **kwargs):
        """Hata seviyesinde log"""
        self.logger.error(mask_sensitive_data(message), *args, **kwargs)
    
    def exception(self, message, *args, **kwargs):
        """İstisna durumunda log (traceback ile)"""
        # Traceback'i maskele
        safe_tb = mask_sensitive_data(traceback.format_exc())
        kwargs['exc_info'] = False  # Otomatik traceback'i devre dışı bırak
        self.logger.error(f"{mask_sensitive_data(message)}\n{safe_tb}", *args, **kwargs)
    
    def critical(self, message, *args, **kwargs):
        """Kritik seviyede log"""
        self.logger.critical(mask_sensitive_data(message), *args, **kwargs)
    
    def debug(self, message, *args, **kwargs):
        """Debug seviyesinde log"""
        self.logger.debug(mask_sensitive_data(message), *args, **kwargs)

# Global logger
logger = SafeLogger('smart_doc_insight') 