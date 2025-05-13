import logging
import threading
import queue
from datetime import datetime, timedelta
from pymongo import MongoClient, DESCENDING
from flask import current_app, request, g, has_request_context
from app.utils.log_utils import mask_sensitive_data

class MongoDBLogHandler(logging.Handler):
    """
    MongoDB'ye log kayıtlarını yazan özel bir handler.
    Performans için asenkron kayıt ve belirli aralıklarla log temizleme özellikleri içerir.
    """
    
    def __init__(self, collection_name="system_logs", async_mode=True, max_queue_size=1000, 
                 cleanup_days=30, connection_string=None, db_name="smart_doc_insight"):
        """
        MongoDB log handler'ı başlatır
        
        Args:
            collection_name (str): Log kayıtlarının saklanacağı koleksiyon adı
            async_mode (bool): Asenkron modda çalışıp çalışmayacağı
            max_queue_size (int): Asenkron modda maksimum kuyruk boyutu
            cleanup_days (int): Kaç günden eski logların temizleneceği (0 ise temizleme yapılmaz)
            connection_string (str): MongoDB bağlantı URL'si (None ise Flask uygulamasının bağlantısı kullanılır)
            db_name (str): Veritabanı adı (connection_string verildiğinde kullanılır)
        """
        logging.Handler.__init__(self)
        self.collection_name = collection_name
        self.async_mode = async_mode
        self.connection_string = connection_string
        self.db_name = db_name
        self.cleanup_days = cleanup_days
        self.mongo = None
        self.is_initialized = False
        self._stopping = False
        
        # Asenkron mod için
        if async_mode:
            self._queue = queue.Queue(maxsize=max_queue_size)
            self._thread = threading.Thread(target=self._async_writer, daemon=True)
            self._thread.start()
    
    def _init_db(self):
        """Veritabanı bağlantısını ve indeksleri başlatır"""
        try:
            if self.connection_string:
                # Özel bağlantı kullan
                client = MongoClient(self.connection_string)
                self.mongo = client[self.db_name][self.collection_name]
            else:
                # Flask uygulamasının veritabanını kullan
                try:
                    if current_app and hasattr(current_app, 'db'):
                        self.mongo = current_app.db[self.collection_name]
                    else:
                        # Flask bağlamı dışındaysa veya mevcut değilse varsayılan bağlantı
                        client = MongoClient("mongodb://localhost:27017")
                        self.mongo = client["smart_doc_insight"][self.collection_name]
                except:
                    # Flask bağlamı dışında olabilir, doğrudan bağlan
                    client = MongoClient("mongodb://localhost:27017")
                    self.mongo = client["smart_doc_insight"][self.collection_name]
            
            # Indeksleri oluştur
            self.mongo.create_index([("timestamp", DESCENDING)])
            self.mongo.create_index([("level", DESCENDING)])
            self.mongo.create_index([("user_id", DESCENDING)])
            
            # Eski logları temizle (ilk başlatmada)
            if self.cleanup_days > 0:
                self._cleanup_old_logs()
                
            self.is_initialized = True
            print(f"MongoDB log handler başarıyla başlatıldı: {self.collection_name}")
            
        except Exception as e:
            print(f"MongoDB log handler başlatma hatası: {str(e)}")
    
    def _ensure_connection(self):
        """MongoDB bağlantısını sağlar"""
        if not self.is_initialized:
            self._init_db()
    
    def _async_writer(self):
        """Asenkron mod için arka plan iş parçacığı"""
        last_cleanup_time = datetime.now()
        
        while not self._stopping:
            try:
                # Kuyruktaki bir sonraki log kaydını al (bloke olmaz)
                try:
                    log_entry = self._queue.get(block=True, timeout=5.0)
                except queue.Empty:
                    # 5 saniye içinde yeni log yoksa, periyodik temizlik kontrolü yap
                    if self.cleanup_days > 0:
                        current_time = datetime.now()
                        # Günde bir kez temizlik yap
                        if (current_time - last_cleanup_time).total_seconds() > 86400:  # 24 saat
                            self._cleanup_old_logs()
                            last_cleanup_time = current_time
                    continue
                
                # Veritabanı bağlantısını kontrol et
                self._ensure_connection()
                
                # MongoDB'ye kaydet
                try:
                    self.mongo.insert_one(log_entry)
                    self._queue.task_done()
                except Exception as e:
                    print(f"Asenkron MongoDB log yazma hatası: {str(e)}")
                    print(f"Log içeriği: {log_entry}")
                    # Kuyruk işlemini tamamla, kaybolan log olabilir ama sistem bloke olmaz
                    self._queue.task_done()
                    
            except Exception as e:
                print(f"Asenkron log işleme hatası: {str(e)}")
    
    def _cleanup_old_logs(self):
        """Belirli bir süre geçmiş eski logları temizler"""
        try:
            if self.cleanup_days > 0 and self.mongo:
                cutoff_date = datetime.now() - timedelta(days=self.cleanup_days)
                result = self.mongo.delete_many({"timestamp": {"$lt": cutoff_date}})
                if result.deleted_count > 0:
                    print(f"{result.deleted_count} eski log kaydı temizlendi (> {self.cleanup_days} gün)")
        except Exception as e:
            print(f"Log temizleme hatası: {str(e)}")
    
    def emit(self, record):
        """Log kaydını MongoDB'ye gönderir"""
        # Log kaydını formatla
        log_entry = {
            "timestamp": datetime.now(),
            "level": record.levelname,
            "message": mask_sensitive_data(self.format(record)),  # Hassas verileri maskele
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process": record.process,
        }
        
        # Hata durumunda ek bilgiler
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else "",
                "message": str(record.exc_info[1]) if record.exc_info[1] else "",
                "traceback": mask_sensitive_data(self.formatter.formatException(record.exc_info))
            }
        
        # Flask bağlamı varsa isteğe bağlı ek bilgileri ekle
        if has_request_context():
            try:
                log_entry["request"] = {
                    "ip_address": request.remote_addr,
                    "path": request.path,
                    "method": request.method,
                    "user_agent": request.user_agent.string if request.user_agent else "",
                }
            except:
                pass
        
        # Kullanıcı bilgisi varsa ekle
        try:
            if has_request_context() and hasattr(g, 'user') and g.user:
                log_entry["user_id"] = g.user.id
                log_entry["username"] = g.user.username
                log_entry["user_role"] = "teacher" if g.user.is_teacher() else "student"
        except:
            pass
            
        # Asenkron veya senkron olarak MongoDB'ye kaydet
        if self.async_mode:
            try:
                # Asenkron mod: kuyruğa ekle
                self._queue.put(log_entry, block=False)
            except queue.Full:
                print("MongoDB log kuyruğu dolu, log kaydı atlandı!")
        else:
            # Senkron mod: doğrudan kaydet
            self._ensure_connection()
            try:
                self.mongo.insert_one(log_entry)
            except Exception as e:
                print(f"MongoDB log yazma hatası: {str(e)}")
                print(f"Log içeriği: {log_entry}")
    
    def close(self):
        """Handler'ı kapatır"""
        if self.async_mode:
            self._stopping = True
            # Kuyruktaki tüm logların işlenmesini bekle
            if hasattr(self, '_queue'):
                try:
                    self._queue.join()
                except:
                    pass
            
            # Thread'in sonlanmasını bekle
            if hasattr(self, '_thread') and self._thread.is_alive():
                self._thread.join(timeout=5.0)
                
        logging.Handler.close(self) 