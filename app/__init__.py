import os
from flask import Flask, g
from flask_login import LoginManager, current_user
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv

from app.models.user import User
from app.utils.log_utils import logger
from app.utils.llm_utils import check_ollama_availability, check_lmstudio_availability, check_api_llm_availability

# Ortam değişkenlerini yükle
load_dotenv()

# MongoDB bağlantısı kurma
def get_db():
    try:
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/smart_doc_insight')
        print(f"MongoDB bağlantısı yapılıyor: {mongo_uri}")
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)  # 5 saniyelik timeout ekle
        
        # Bağlantıyı test et
        client.admin.command('ping')
        
        print("MongoDB bağlantısı başarılı")
        return client.smart_doc_insight
    except Exception as e:
        error_msg = f"MongoDB bağlantı hatası: {str(e)}"
        print(error_msg)
        import traceback
        print(traceback.format_exc())
        
        # Bağlantı olmasa da uygulamanın çalışmaya devam etmesi için
        # hata fırlatmak yerine None dönebiliriz, ancak bu API anahtarı kaydı gibi
        # veritabanı gerektiren işlemlerde sorunlara yol açacaktır
        raise Exception(error_msg)

def create_app(config=None):
    """Uygulama oluşturma fabrikası"""
    app = Flask(__name__)
    
    # Jinja2 eklentilerini etkinleştir
    app.jinja_env.add_extension('jinja2.ext.do')
    
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'gizli_anahtarinizi_degistirin')
    app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
    app.config['OLLAMA_BASE_URL'] = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    app.config['LLM_PROVIDER'] = os.getenv('LLM_PROVIDER', 'ollama')
    app.config['LLM_STUDIO_MODEL'] = os.getenv('LLM_STUDIO_MODEL', 'mistral-nemo-instruct-2407')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB maksimum dosya boyutu

    # CORS yapılandırması
    # Geliştirme ortamında izin verilen kaynakları tanımla 
    # Üretim ortamında bu listeyi gerçek alan adlarınızla güncellemelisiniz
    allowed_origins = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000')
    origins = allowed_origins.split(',')
    
    # Daha güvenli ve spesifik CORS yapılandırması
    CORS(app, 
         resources={r"/*": {"origins": origins}},
         supports_credentials=True,
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization"])

    # Veritabanı bağlantısını app objesine ekle
    app.db = get_db()

    # MongoDB log sistemini başlat
    setup_mongodb_logging(app)

    # Flask-Login yapılandırması
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        # User modelinin get_by_id metodunu kullan
        return User.get_by_id(user_id)

    # LLM servislerinin durumunu her istekte kontrol et
    from app.utils.llm_utils import check_openai_availability, check_gemini_availability, check_claude_availability
    
    @app.before_request
    def before_request():
        # Aktif LLM sağlayıcısını belirle
        llm_provider = os.getenv('LLM_PROVIDER', 'ollama')
        g.active_llm_provider = llm_provider
        
        # Tüm sağlayıcıları başlangıçta kullanılamaz olarak ayarla
        g.ollama_available = False
        g.lmstudio_available = False
        g.openai_available = False
        g.gemini_available = False
        g.claude_available = False
        g.active_llm_available = False
        
        # Yalnızca aktif sağlayıcının durumunu kontrol et
        if llm_provider == 'ollama':
            g.ollama_available = check_ollama_availability()
            g.active_llm_available = g.ollama_available
        elif llm_provider == 'lmstudio':
            g.lmstudio_available = check_lmstudio_availability()
            g.active_llm_available = g.lmstudio_available
        elif llm_provider == 'openai':
            g.openai_available = check_openai_availability()
            g.active_llm_available = g.openai_available
        elif llm_provider == 'gemini':
            g.gemini_available = check_gemini_availability()
            g.active_llm_available = g.gemini_available
        elif llm_provider == 'claude':
            g.claude_available = check_claude_availability()
            g.active_llm_available = g.claude_available
        else:
            g.active_llm_available = False

        # Kullanıcı bilgisini global değişkene ekle (loglama için)
        if current_user.is_authenticated:
            g.user = current_user

    # Blueprint'leri kaydet
    from app.routes.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from app.routes.main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from app.routes.student import student as student_blueprint
    app.register_blueprint(student_blueprint)

    from app.routes.teacher import teacher as teacher_blueprint
    app.register_blueprint(teacher_blueprint)

    # Uploads klasörü yoksa oluştur
    os.makedirs(os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER']), exist_ok=True)

    return app 

def setup_mongodb_logging(app):
    """
    MongoDB tabanlı loglama sistemini yapılandırır
    """
    try:
        # Loglama aktif mi kontrol et
        if os.getenv('ENABLE_MONGODB_LOGGING', 'true').lower() == 'true':
            # Loglama ayarlarını al
            collection_name = os.getenv('LOG_COLLECTION_NAME', 'system_logs')
            async_mode = os.getenv('LOG_ASYNC_MODE', 'true').lower() == 'true'
            max_queue_size = int(os.getenv('LOG_MAX_QUEUE_SIZE', '1000'))
            cleanup_days = int(os.getenv('LOG_CLEANUP_DAYS', '30'))
            
            # MongoDB loglamasını kur
            logger.setup_mongodb_logging(
                collection_name=collection_name,
                async_mode=async_mode,
                max_queue_size=max_queue_size,
                cleanup_days=cleanup_days
            )
            
            # Uygulama kapatıldığında log sistemini düzgünce kapat
            @app.teardown_appcontext
            def close_mongodb_logger(error):
                logger.disable_mongodb_logging()
                
            app.logger.info("MongoDB loglama sistemi başlatıldı")
        else:
            app.logger.info("MongoDB loglama devre dışı (ENABLE_MONGODB_LOGGING=false)")
    except Exception as e:
        app.logger.error(f"MongoDB loglama sistemi başlatılamadı: {str(e)}") 