from flask import Blueprint, render_template, current_app
from flask_login import current_user
from app.utils.llm_utils import check_ollama_availability

main = Blueprint('main', __name__)

@main.route('/')
def index():
    # Giriş yapmış kullanıcıları doğru panele yönlendirelim
    if current_user.is_authenticated:
        from flask import redirect, url_for
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
    # Sistemin durumunu kontrol et
    ollama_running = check_ollama_availability()
    
    # MongoDB bağlantısını kontrol et
    mongo_running = True
    try:
        # Basit bir sorgu ile bağlantıyı test et
        current_app.db.command('ping')
    except:
        mongo_running = False
    
    return render_template('system_status.html', 
                          ollama_running=ollama_running,
                          mongo_running=mongo_running) 