from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, jsonify
from flask_login import login_required, current_user
from bson.objectid import ObjectId
import os
import ollama
import datetime
import traceback
import uuid

from app.models.project import Project
from app.utils.pdf_utils import extract_text_from_pdf, chunk_text
from app.utils.llm_utils import analyze_text_with_llm, check_ollama_availability, get_available_models

teacher = Blueprint('teacher', __name__)

@teacher.route('/teacher/dashboard')
@login_required
def dashboard():
    if not current_user.is_teacher():
        flash('Bu sayfaya erişim yetkiniz yok', 'danger')
        return redirect(url_for('main.index'))
    
    # Tüm projeleri getir
    projects = Project.get_all()
    
    return render_template('teacher/dashboard.html', projects=projects)

@teacher.route('/teacher/projects/<project_id>')
@login_required
def view_project(project_id):
    if not current_user.is_teacher():
        flash('Bu sayfaya erişim yetkiniz yok', 'danger')
        return redirect(url_for('main.index'))
    
    project = Project.get_by_id(project_id)
    
    if not project:
        flash('Proje bulunamadı', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    return render_template('teacher/view_project.html', project=project)

@teacher.route('/teacher/projects/<project_id>/file/<int:file_index>')
@login_required
def view_file(project_id, file_index):
    if not current_user.is_teacher():
        flash('Bu sayfaya erişim yetkiniz yok', 'danger')
        return redirect(url_for('main.index'))
    
    project = Project.get_by_id(project_id)
    
    if not project or file_index >= len(project.files):
        flash('Dosya bulunamadı', 'danger')
        return redirect(url_for('teacher.view_project', project_id=project_id))
    
    file_data = project.files[file_index]
    
    # Yeni metod ile dosya analizini al
    analysis = project.get_analysis_for_file(file_index)
    
    # Eğer analiz varsa ve hatalı bir model içeriyorsa uyarı göster
    if analysis and "content" in analysis and "ham_sonuc" in analysis["content"]:
        if "model 'mistral:instruct' not found" in analysis["content"]["ham_sonuc"]:
            flash('Bu analiz eski model ile yapılmış ve hatalı görünüyor. Lütfen yeniden analiz edin.', 'warning')
    
    return render_template('teacher/view_file.html', 
                          project=project, 
                          file_data=file_data,
                          file_index=file_index,
                          analysis=analysis)

@teacher.route('/teacher/projects/<project_id>/file/<int:file_index>/analyze', methods=['POST'])
@login_required
def analyze_file(project_id, file_index):
    if not current_user.is_teacher():
        flash('Bu sayfaya erişim yetkiniz yok', 'danger')
        return redirect(url_for('main.index'))
    
    # Ollama LLM servisinin çalışıp çalışmadığını kontrol et
    if not check_ollama_availability():
        flash('LLM servisi (Ollama) şu anda çalışmıyor. Lütfen servisin çalıştığından emin olun.', 'danger')
        return redirect(url_for('teacher.view_file', project_id=project_id, file_index=file_index))
    
    # Mevcut modelleri kontrol et
    available_models = get_available_models()
    print(f"Ollama'dan alınan mevcut modeller: {available_models}")
    flash(f"Ollama'dan alınan mevcut modeller: {available_models}")
    if not available_models:
        flash('Ollama\'da hiç model bulunamadı. Lütfen en az bir model yüklediğinizden emin olun.', 'danger')
        return redirect(url_for('teacher.view_file', project_id=project_id, file_index=file_index))
    
    # Mistral modeli var mı kontrol et
    model_names = [model.get('name') for model in available_models]
    target_model = "mistral"
    valid_model_names = ["mistral", "mistral:latest"]  # Herhangi biri olsa yeterli
    
    if not any(name in model_names for name in valid_model_names):
        flash(f'"mistral" modeli bulunamadı. Mevcut modeller: {", ".join(model_names)}', 'warning')
    
    project = Project.get_by_id(project_id)
    
    if not project or file_index >= len(project.files):
        flash('Dosya bulunamadı', 'danger')
        return redirect(url_for('teacher.view_project', project_id=project_id))
    
    file_data = project.files[file_index]
    
    # PDF'den metin çıkar
    pdf_text = extract_text_from_pdf(file_data['path'])
    
    if not pdf_text:
        flash('PDF\'den metin çıkarılamadı', 'danger')
        return redirect(url_for('teacher.view_file', project_id=project_id, file_index=file_index))
    
    # Metni parçalara böl (LLM token limiti için)
    text_chunks = chunk_text(pdf_text)
    
    # LLM ile analiz yap
    analysis_result = analyze_text_with_llm(text_chunks)
    
    # Analizi projeye ekle
    project.add_analysis(file_index, analysis_result)
    project.save()
    
    flash('Dosya başarıyla analiz edildi', 'success')
    return redirect(url_for('teacher.view_file', project_id=project_id, file_index=file_index))

@teacher.route('/teacher/projects/<project_id>/file/<int:file_index>/download-analysis')
@login_required
def download_analysis(project_id, file_index):
    if not current_user.is_teacher():
        flash('Bu sayfaya erişim yetkiniz yok', 'danger')
        return redirect(url_for('main.index'))
    
    project = Project.get_by_id(project_id)
    
    if not project or file_index >= len(project.files):
        flash('Dosya bulunamadı', 'danger')
        return redirect(url_for('teacher.view_project', project_id=project_id))
    
    # Dosya için bir analiz var mı kontrol et
    analysis = None
    for a in project.analysis:
        if a.get('file_id') == file_index:
            analysis = a
            break
    
    if not analysis:
        flash('Bu dosya için henüz analiz yapılmamış', 'danger')
        return redirect(url_for('teacher.view_file', project_id=project_id, file_index=file_index))
    
    from flask import Response
    
    # Analizi metin dosyası olarak dışa aktar
    response_text = f"""
PDF ANALİZ RAPORU
=================
Proje: {project.name}
Dosya: {project.files[file_index]['filename']}
Analiz Tarihi: {analysis.get('analyzed_at')}

GRUP ÜYELERİ
------------
{chr(10).join(['• ' + ü for ü in analysis.get('content', {}).get('grup_uyeleri', [])])}

SORUMLULUKLAR
------------
{chr(10).join(['• ' + s for s in analysis.get('content', {}).get('sorumluluklar', [])])}

DİYAGRAMLAR
-----------
{chr(10).join(['• ' + d for d in analysis.get('content', {}).get('diyagramlar', [])])}

BAŞLIKLAR
---------
{chr(10).join(['• ' + b for b in analysis.get('content', {}).get('basliklar', [])])}

EKSİKLER
--------
{chr(10).join(['• ' + e for e in analysis.get('content', {}).get('eksikler', [])])}

HAM ÇIKTI
---------
{analysis.get('content', {}).get('ham_sonuc', '')}
    """
    
    return Response(
        response_text,
        mimetype="text/plain",
        headers={"Content-Disposition": f"attachment;filename=analiz_{project.name}_{file_index}.txt"}
    )

@teacher.route('/teacher/test-ollama')
@login_required
def test_ollama():
    if not current_user.is_teacher():
        flash('Bu sayfaya erişim yetkiniz yok', 'danger')
        return redirect(url_for('main.index'))
    
    try:
        # Ollama bağlantısını test et
        test_result = {
            "ollama_check": check_ollama_availability(),
            "available_models": get_available_models(),
            "test_time": datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
            "model_response": None,
            "error": None
        }
        
        # Basit bir test isteği gönder
        try:
            response = ollama.generate(
                model="mistral:latest",
                prompt="Merhaba, bu bir test mesajıdır. Lütfen kısa bir cevap verin.",
                options={"temperature": 0.7}
            )
            test_result["model_response"] = response.get('response', '')
        except Exception as e:
            test_result["error"] = str(e)
            test_result["traceback"] = traceback.format_exc()
        
        return render_template('teacher/test_ollama.html', test_result=test_result)
    
    except Exception as e:
        flash(f'Hata oluştu: {str(e)}', 'danger')
        return redirect(url_for('teacher.dashboard'))

@teacher.route('/teacher/projects/<project_id>/file/<int:file_index>/delete', methods=['POST'])
@login_required
def delete_file(project_id, file_index):
    if not current_user.is_teacher():
        flash('Bu sayfaya erişim yetkiniz yok', 'danger')
        return redirect(url_for('main.index'))
    
    project = Project.get_by_id(project_id)
    
    if not project or file_index >= len(project.files):
        flash('Dosya bulunamadı', 'danger')
        return redirect(url_for('teacher.view_project', project_id=project_id))
    
    # Dosya bilgilerini al
    file_data = project.files[file_index]
    filename = file_data['filename']
    
    # Dosyayı projeden kaldır
    if project.remove_file(file_index):
        flash(f'"{filename}" dosyası başarıyla silindi', 'success')
    else:
        flash(f'Dosya silinirken bir hata oluştu', 'danger')
    
    return redirect(url_for('teacher.view_project', project_id=project_id))

@teacher.route('/teacher/fix-old-analyses', methods=['GET', 'POST'])
@login_required
def fix_old_analyses():
    if not current_user.is_teacher():
        flash('Bu sayfaya erişim yetkiniz yok', 'danger')
        return redirect(url_for('main.index'))
    
    # MongoDB'deki eski analizleri düzeltelim
    fixed_count = 0
    error_count = 0
    updated_count = 0
    
    if request.method == 'POST':
        projects = Project.get_all()
        
        for project in projects:
            # 1. Mevcut dosyalara benzersiz ID ekle (eğer yoksa)
            for i, file_data in enumerate(project.files):
                if 'file_id' not in file_data or not file_data['file_id']:
                    project.files[i]['file_id'] = str(uuid.uuid4())
                    updated_count += 1
            
            # 2. Hatalı analizleri temizle
            for i, analysis in enumerate(project.analysis[:]):  # Listeyi kopyala çünkü içeriğini değiştireceğiz
                content = analysis.get('content', {})
                ham_sonuc = content.get('ham_sonuc', '')
                
                # "mistral:instruct not found" hatası içeren analizleri temizle
                if "model 'mistral:instruct' not found" in ham_sonuc:
                    try:
                        # Analizi kaldır
                        project.analysis.remove(analysis)
                        fixed_count += 1
                        print(f"Hatalı analiz temizlendi: Proje {project.name}")
                    except Exception as e:
                        print(f"Hata: {str(e)}")
                        error_count += 1
            
            # 3. Eski analiz kayıtlarında geçiş - file_id kullan
            for i, analysis in enumerate(project.analysis[:]):
                file_index = analysis.get('file_index')
                
                # file_id yoksa ve file_index varsa, file_id'yi ayarla
                if ('file_id' not in analysis or not analysis['file_id']) and file_index is not None:
                    # Belirtilen dosyayı bul
                    if file_index < len(project.files):
                        file_id = project.files[file_index].get('file_id')
                        if file_id:
                            project.analysis[i]['file_id'] = file_id
                            updated_count += 1
            
            # Projeyi kaydet
            project.save()
            
        
        flash(f'Toplam {fixed_count} hatalı analiz temizlendi, {updated_count} kayıt güncellendi. {error_count} hata oluştu.', 'success')
        return redirect(url_for('teacher.dashboard'))
    
    return render_template('teacher/fix_analyses.html') 