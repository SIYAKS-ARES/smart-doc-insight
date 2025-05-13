from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user

def teacher_required(f):
    """
    Sadece öğretmen rolündeki kullanıcıların erişebileceği rotalar için dekoratör
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Bu sayfaya erişmek için giriş yapmalısınız', 'warning')
            return redirect(url_for('auth.login'))
            
        if not current_user.is_teacher():
            flash('Bu sayfaya erişim yetkiniz yok', 'danger')
            return redirect(url_for('main.index'))
            
        return f(*args, **kwargs)
    return decorated_function 