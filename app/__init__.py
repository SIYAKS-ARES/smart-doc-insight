import os
from flask import Flask, g
from flask_login import LoginManager
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv

# Ortam değişkenlerini yükle
load_dotenv()

# MongoDB bağlantısı kurma
def get_db():
    client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/smart_doc_insight'))
    return client.smart_doc_insight

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'gizli_anahtarinizi_degistirin')
    app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
    app.config['OLLAMA_BASE_URL'] = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB maksimum dosya boyutu

    # CORS yapılandırması
    CORS(app)

    # Veritabanı bağlantısını app objesine ekle
    app.db = get_db()

    # Flask-Login yapılandırması
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.get_by_id(user_id)

    # Ollama durumunu her istekte kontrol et
    from app.utils.llm_utils import check_ollama_availability
    @app.before_request
    def before_request():
        g.ollama_available = check_ollama_availability()

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