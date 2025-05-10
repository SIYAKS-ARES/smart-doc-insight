from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from app.models.user import User
from bson.objectid import ObjectId

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_teacher():
            return redirect(url_for('teacher.dashboard'))
        else:
            return redirect(url_for('student.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        user = User.get_by_email(email)
        
        if not user or not user.check_password(password):
            flash('Lütfen e-posta ve şifrenizi kontrol edin', 'danger')
            return render_template('auth/login.html')
        
        login_user(user, remember=remember)
        
        if user.is_teacher():
            return redirect(url_for('teacher.dashboard'))
        else:
            return redirect(url_for('student.dashboard'))
    
    return render_template('auth/login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm')
        role = request.form.get('role')
        
        if password != confirm:
            flash('Şifreler eşleşmiyor', 'danger')
            return render_template('auth/register.html')
        
        if User.get_by_email(email):
            flash('Bu e-posta adresi zaten kullanılıyor', 'danger')
            return render_template('auth/register.html')
        
        if User.get_by_username(username):
            flash('Bu kullanıcı adı zaten kullanılıyor', 'danger')
            return render_template('auth/register.html')
        
        if role not in ['student', 'teacher']:
            flash('Geçersiz kullanıcı rolü', 'danger')
            return render_template('auth/register.html')
        
        user = User(username=username, email=email, role=role)
        user.set_password(password)
        user.save()
        
        flash('Hesabınız başarıyla oluşturuldu, şimdi giriş yapabilirsiniz', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@auth.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html') 