from flask import Blueprint, render_template, current_app, redirect, url_for, g
from flask_login import current_user
from app.utils.llm_utils import check_ollama_availability, check_lmstudio_availability
import os


main = Blueprint('main', __name__)

@main.route('/')
def index():
    # Giriş yapmış kullanıcıları doğru panele yönlendirelim
    if current_user.is_authenticated:
        if current_user.is_teacher():
            return redirect(url_for('teacher.dashboard'))
        else:
            return redirect(url_for('student.dashboard'))
    
    return render_template('index.html')

@main.route('/about')
def about():
    return render_template('about.html')

@main.route('/system-status')
def system_status():
    """Sistem durumu sayfası"""
    # MongoDB bağlantısını kontrol et
    try:
        mongo_db = current_app.db
        mongo_running = True
    except:
        mongo_running = False
    
    # LLM servislerini kontrol et
    ollama_running = check_ollama_availability()
    lmstudio_running = check_lmstudio_availability()
    
    # Mevcut LLM sağlayıcısı bilgisini al
    llm_provider = os.getenv('LLM_PROVIDER', 'ollama')
    llm_info = {
        'provider': llm_provider,
        'ollama_model': os.getenv('OLLAMA_MODEL', 'mistral:latest'),
        'lmstudio_model': os.getenv('LLM_STUDIO_MODEL', 'mistral-nemo-instruct-2407')
    }
    
    return render_template('system_status.html', 
                          mongo_running=mongo_running, 
                          ollama_running=ollama_running,
                          lmstudio_running=lmstudio_running,
                          llm_info=llm_info) 