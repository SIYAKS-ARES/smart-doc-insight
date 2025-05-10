from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from bson.objectid import ObjectId
import os
import uuid
from werkzeug.utils import secure_filename

from app.models.project import Project
from app.utils.pdf_utils import allowed_file, save_pdf, extract_text_from_pdf, chunk_text

student = Blueprint('student', __name__)

@student.route('/student/dashboard')
@login_required
def dashboard():
    if not current_user.is_student():
        flash('Bu sayfaya erişim yetkiniz yok', 'danger')
        return redirect(url_for('main.index'))
    
    # Öğrencinin projelerini getir
    projects = Project.get_by_created_by(current_user.get_id())
    
    return render_template('student/dashboard.html', projects=projects)

@student.route('/student/projects/new', methods=['GET', 'POST'])
@login_required
def new_project():
    if not current_user.is_student():
        flash('Bu sayfaya erişim yetkiniz yok', 'danger')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        # Grup üyelerini al
        group_members = []
        for i in range(1, 5):  # En fazla 5 grup üyesi
            member_name = request.form.get(f'member_name_{i}')
            member_resp = request.form.get(f'member_resp_{i}')
            
            if member_name and member_resp:
                group_members.append({
                    "name": member_name,
                    "responsibility": member_resp
                })
        
        if not name:
            flash('Proje adı gereklidir', 'danger')
            return render_template('student/new_project.html')
        
        # Projeyi oluştur
        project = Project(
            name=name,
            description=description,
            group_members=group_members,
            created_by=ObjectId(current_user.get_id())
        )
        project.save()
        
        flash('Proje başarıyla oluşturuldu', 'success')
        return redirect(url_for('student.view_project', project_id=project._id))
    
    return render_template('student/new_project.html')

@student.route('/student/projects/<project_id>')
@login_required
def view_project(project_id):
    if not current_user.is_student():
        flash('Bu sayfaya erişim yetkiniz yok', 'danger')
        return redirect(url_for('main.index'))
    
    project = Project.get_by_id(project_id)
    
    if not project:
        flash('Proje bulunamadı', 'danger')
        return redirect(url_for('student.dashboard'))
    
    # Proje sahibi mi kontrol et
    if str(project.created_by) != current_user.get_id():
        flash('Bu projeyi görüntüleme yetkiniz yok', 'danger')
        return redirect(url_for('student.dashboard'))
    
    return render_template('student/view_project.html', project=project)

@student.route('/student/projects/<project_id>/upload', methods=['GET', 'POST'])
@login_required
def upload_file(project_id):
    if not current_user.is_student():
        flash('Bu sayfaya erişim yetkiniz yok', 'danger')
        return redirect(url_for('main.index'))
    
    project = Project.get_by_id(project_id)
    
    if not project:
        flash('Proje bulunamadı', 'danger')
        return redirect(url_for('student.dashboard'))
    
    # Proje sahibi mi kontrol et
    if str(project.created_by) != current_user.get_id():
        flash('Bu projeye dosya yükleme yetkiniz yok', 'danger')
        return redirect(url_for('student.dashboard'))
    
    if request.method == 'POST':
        # Dosya var mı kontrol et
        if 'file' not in request.files:
            flash('Dosya kısmı eksik', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        # Dosya adı boş mu kontrol et
        if file.filename == '':
            flash('Dosya seçilmedi', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # Dosyayı kaydet
            file_path = save_pdf(file)
            
            # PDF bilgisini projeye ekle
            file_data = project.add_file(secure_filename(file.filename), file_path)
            project.save()
            
            flash('Dosya başarıyla yüklendi', 'success')
            return redirect(url_for('student.view_project', project_id=project_id))
        else:
            flash('Geçersiz dosya türü. Sadece PDF dosyaları kabul edilir', 'danger')
            return redirect(request.url)
    
    return render_template('student/upload_file.html', project=project)

@student.route('/student/projects/<project_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    if not current_user.is_student():
        flash('Bu sayfaya erişim yetkiniz yok', 'danger')
        return redirect(url_for('main.index'))
    
    project = Project.get_by_id(project_id)
    
    if not project:
        flash('Proje bulunamadı', 'danger')
        return redirect(url_for('student.dashboard'))
    
    # Proje sahibi mi kontrol et
    if str(project.created_by) != current_user.get_id():
        flash('Bu projeyi düzenleme yetkiniz yok', 'danger')
        return redirect(url_for('student.dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        # Grup üyelerini al
        group_members = []
        for i in range(1, 5):  # En fazla 5 grup üyesi
            member_name = request.form.get(f'member_name_{i}')
            member_resp = request.form.get(f'member_resp_{i}')
            
            if member_name and member_resp:
                group_members.append({
                    "name": member_name,
                    "responsibility": member_resp
                })
        
        if not name:
            flash('Proje adı gereklidir', 'danger')
            return render_template('student/edit_project.html', project=project)
        
        # Projeyi güncelle
        project.name = name
        project.description = description
        project.group_members = group_members
        project.save()
        
        flash('Proje başarıyla güncellendi', 'success')
        return redirect(url_for('student.view_project', project_id=project._id))
    
    return render_template('student/edit_project.html', project=project)

@student.route('/student/projects/<project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    if not current_user.is_student():
        flash('Bu sayfaya erişim yetkiniz yok', 'danger')
        return redirect(url_for('main.index'))
    
    project = Project.get_by_id(project_id)
    
    if not project:
        flash('Proje bulunamadı', 'danger')
        return redirect(url_for('student.dashboard'))
    
    # Proje sahibi mi kontrol et
    if str(project.created_by) != current_user.get_id():
        flash('Bu projeyi silme yetkiniz yok', 'danger')
        return redirect(url_for('student.dashboard'))
    
    # Projeyi sil
    project.delete()
    
    flash('Proje başarıyla silindi', 'success')
    return redirect(url_for('student.dashboard'))

@student.route('/student/projects/<project_id>/file/<int:file_index>/delete', methods=['POST'])
@login_required
def delete_file(project_id, file_index):
    if not current_user.is_student():
        flash('Bu sayfaya erişim yetkiniz yok', 'danger')
        return redirect(url_for('main.index'))
    
    project = Project.get_by_id(project_id)
    
    if not project:
        flash('Proje bulunamadı', 'danger')
        return redirect(url_for('student.dashboard'))
    
    # Proje sahibi mi kontrol et
    if str(project.created_by) != current_user.get_id():
        flash('Bu dosyayı silme yetkiniz yok', 'danger')
        return redirect(url_for('student.dashboard'))
    
    if file_index >= len(project.files):
        flash('Dosya bulunamadı', 'danger')
        return redirect(url_for('student.view_project', project_id=project_id))
    
    # Dosya bilgilerini al
    file_data = project.files[file_index]
    filename = file_data['filename']
    
    # Dosyayı projeden kaldır
    if project.remove_file(file_index):
        flash(f'"{filename}" dosyası başarıyla silindi', 'success')
    else:
        flash(f'Dosya silinirken bir hata oluştu', 'danger')
    
    return redirect(url_for('student.view_project', project_id=project_id))

@student.route('/student/projects/<project_id>/file/<int:file_index>', methods=['GET'])
@login_required
def view_file(project_id, file_index):
    if not current_user.is_student():
        flash('Bu sayfaya erişim yetkiniz yok', 'danger')
        return redirect(url_for('main.index'))
    
    project = Project.get_by_id(project_id)
    
    if not project:
        flash('Proje bulunamadı', 'danger')
        return redirect(url_for('student.dashboard'))
    
    # Proje sahibi mi kontrol et
    if str(project.created_by) != current_user.get_id():
        flash('Bu projeyi görüntüleme yetkiniz yok', 'danger')
        return redirect(url_for('student.dashboard'))
    
    if file_index >= len(project.files):
        flash('Dosya bulunamadı', 'danger')
        return redirect(url_for('student.view_project', project_id=project_id))
    
    file_data = project.files[file_index]
    
    # Yeni metod ile dosya analizini al
    analysis = project.get_analysis_for_file(file_index)
    
    return render_template('student/view_file.html', 
                          project=project, 
                          file_data=file_data,
                          file_index=file_index,
                          analysis=analysis) 