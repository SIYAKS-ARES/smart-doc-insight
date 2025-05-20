from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, jsonify, g
from flask_login import login_required, current_user
from bson.objectid import ObjectId
import os
import ollama
import datetime
import traceback
import uuid
import dotenv

from app.models.project import Project
from app.utils.pdf_utils import extract_text_from_pdf, chunk_text
from app.utils.llm_utils import analyze_text_with_llm, check_ollama_availability, get_available_models
from app.utils.llm import get_llm_client
from app.utils.settings import LLM_PROVIDER, LLM_STUDIO_MODEL, OLLAMA_MODEL, OLLAMA_HOST, OLLAMA_PORT
from app.utils.api_key_manager import APIKeyManager
from app.utils.auth_utils import teacher_required

teacher = Blueprint('teacher', __name__)

@teacher.before_request
def set_debug_mode():
    """Her istek öncesinde çalışır ve debug_mode değişkenini g nesnesine ekler."""
    # Üretim ortamında False olmalı, geliştirme ortamında True olabilir
    g.debug_mode = current_app.config.get('DEBUG', False)
    
    # Öğretmenler için debug_mode'u etkinleştir (isteğe bağlı)
    if current_user.is_authenticated and current_user.is_teacher():
        # Bu bayrağı query string'den al (örn: ?debug=1)
        if request.args.get('debug') == '1':
            g.debug_mode = True

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
    
    # Şablon için os ve APIKeyManager modüllerini ekle
    from app.utils.api_key_manager import APIKeyManager
    
    # Model bilgilerini al
    models = {
        'ollama_model': os.getenv('OLLAMA_MODEL', 'mistral:latest'),
        'lmstudio_model': os.getenv('LM_STUDIO_MODEL', 'deepseek-coder-v2-lite-instruct-mlx'),
        'openai_model': APIKeyManager.get_model('openai') or os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'),
        'gemini_model': APIKeyManager.get_model('gemini') or os.getenv('GEMINI_MODEL', 'gemini-2.0-flash'),
        'claude_model': APIKeyManager.get_model('claude') or os.getenv('CLAUDE_MODEL', 'claude-3-opus-20240229')
    }
    
    return render_template('teacher/view_file.html', 
                          project=project, 
                          file_data=file_data,
                          file_index=file_index,
                          analysis=analysis,
                          models=models)

@teacher.route('/teacher/projects/<project_id>/file/<int:file_index>/analyze', methods=['POST'])
@login_required
def analyze_file(project_id, file_index):
    if not current_user.is_teacher():
        flash('Bu sayfaya erişim yetkiniz yok', 'danger')
        return redirect(url_for('main.index'))
    
    # LLM sağlayıcı bilgilerini al
    llm_provider = os.getenv('LLM_PROVIDER', 'ollama')
    
    # Sağlayıcıya göre standart isim ve model bilgilerini ayarla
    provider_display_names = {
        'ollama': 'Ollama',
        'lmstudio': 'LM Studio',
        'openai': 'OpenAI GPT',
        'gemini': 'Google Gemini',
        'claude': 'Anthropic Claude'
    }
    
    # Sağlayıcı görünen adını al, bulunamazsa teknik adını kullan
    provider_display_name = provider_display_names.get(llm_provider, llm_provider.capitalize())
    
    # Model bilgilerini al
    if llm_provider == 'ollama':
        # Ollama için model kontrolü
        if not check_ollama_availability():
            flash('Ollama LLM servisi şu anda çalışmıyor. Lütfen servisin çalıştığından emin olun veya başka bir LLM sağlayıcısı seçin.', 'danger')
            return redirect(url_for('teacher.view_file', project_id=project_id, file_index=file_index))
        model_name = os.getenv('OLLAMA_MODEL', 'mistral:latest')
    elif llm_provider == 'lmstudio':
        # LM Studio için model kontrolü
        from app.utils.llm_utils import check_lmstudio_availability
        if not check_lmstudio_availability():
            flash('LM Studio servisi şu anda çalışmıyor. Lütfen LM Studio uygulamasının çalıştığından ve API Server özelliğinin etkin olduğundan emin olun.', 'danger')
            return redirect(url_for('teacher.view_file', project_id=project_id, file_index=file_index))
        model_name = os.getenv('LM_STUDIO_MODEL', 'deepseek-coder-v2-lite-instruct-mlx')
    elif llm_provider == 'openai':
        # OpenAI için model ve API anahtarı kontrolü
        from app.utils.api_key_manager import APIKeyManager
        api_key = APIKeyManager.get_api_key('openai')
        if not api_key:
            flash('OpenAI API anahtarı bulunamadı. Lütfen API anahtarınızı ayarlar sayfasından ekleyin.', 'danger')
            return redirect(url_for('teacher.view_file', project_id=project_id, file_index=file_index))
        model_name = APIKeyManager.get_model('openai') or os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    elif llm_provider == 'gemini':
        # Gemini için model ve API anahtarı kontrolü
        from app.utils.api_key_manager import APIKeyManager
        api_key = APIKeyManager.get_api_key('gemini')
        if not api_key:
            flash('Google Gemini API anahtarı bulunamadı. Lütfen API anahtarınızı ayarlar sayfasından ekleyin.', 'danger')
            return redirect(url_for('teacher.view_file', project_id=project_id, file_index=file_index))
        model_name = APIKeyManager.get_model('gemini') or os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
    elif llm_provider == 'claude':
        # Claude için model ve API anahtarı kontrolü
        from app.utils.api_key_manager import APIKeyManager
        api_key = APIKeyManager.get_api_key('claude')
        if not api_key:
            flash('Anthropic Claude API anahtarı bulunamadı. Lütfen API anahtarınızı ayarlar sayfasından ekleyin.', 'danger')
            return redirect(url_for('teacher.view_file', project_id=project_id, file_index=file_index))
        model_name = APIKeyManager.get_model('claude') or os.getenv('CLAUDE_MODEL', 'claude-3-opus-20240229')
    else:
        flash('Bilinmeyen LLM sağlayıcısı. Lütfen geçerli bir sağlayıcı seçin.', 'danger')
        return redirect(url_for('teacher.view_file', project_id=project_id, file_index=file_index))
    
    # Projeyi al
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
    
    # LLM bilgisini kullanıcıya göster
    flash(f'{provider_display_name} sistemi ile "{model_name}" modeli kullanılarak analiz yapılıyor...', 'info')
    
    try:
        # Varsayılan analiz için DEFAULT_ANALYSIS_CATEGORIES ve DEFAULT_PROMPT_TEMPLATE kullanılır
        # analyze_text_with_llm fonksiyonu parametresiz çağrıldığında varsayılan başlıkları kullanır
        analysis_result = analyze_text_with_llm(text_chunks)
        
        # Analiz sonucuna LLM sağlayıcı ve model bilgilerini ekle
        analysis_result['llm_info'] = {
            'provider': llm_provider,
            'provider_name': provider_display_name,
            'model': model_name,
        }
        
        # Analizi projeye ekle
        project.add_analysis(file_index, analysis_result)
        project.save()
        
        flash(f'Dosya başarıyla analiz edildi ({provider_display_name} - {model_name})', 'success')
    except Exception as e:
        flash(f'Analiz sırasında hata oluştu: {str(e)}', 'danger')
        print(f"Analiz hatası: {str(e)}")
        print(traceback.format_exc())
    
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
    analysis = project.get_analysis_for_file(file_index)
    
    if not analysis:
        flash('Bu dosya için henüz analiz yapılmamış', 'danger')
        return redirect(url_for('teacher.view_file', project_id=project_id, file_index=file_index))
    
    from flask import Response
    
    # LLM sağlayıcı bilgisini al
    llm_info = analysis.get('content', {}).get('llm_info', {})
    provider_name = llm_info.get('provider_name', 'Bilinmiyor')
    model_name = llm_info.get('model', 'Bilinmiyor')
    
    # Okunaklı tarih formatı
    from datetime import datetime
    analysis_date = analysis.get('analyzed_at', '')
    if isinstance(analysis_date, datetime):
        formatted_date = analysis_date.strftime('%d.%m.%Y %H:%M')
    else:
        formatted_date = str(analysis_date)
    
    # Listeleri birleştir ve döndür
    def format_list(items, indent='    '):
        if not items:
            return f"{indent}• Belirtilmemiş"
        return "\n".join([f"{indent}• {item}" for item in items])
    
    # Özel başlık analizi mi kontrol et
    custom_headings = analysis.get('content', {}).get('custom_headings', [])
    is_custom_analysis = len(custom_headings) > 0
    
    # Analiz raporunu başlat
    report_sections = [
        f"""
PDF ANALİZ RAPORU
=================
Proje: {project.name}
Dosya: {project.files[file_index]['filename']}
Analiz Tarihi: {formatted_date}
LLM Sistemi: {provider_name} / {model_name}
"""
    ]
    
    # Özel başlıklarla analiz yapılmışsa, o başlıkları göster
    if is_custom_analysis:
        report_sections.append("\nÖZEL BAŞLIKLARLA ANALİZ\n")
        
        for i, heading in enumerate(custom_headings):
            section_title = heading.get('title', f"Başlık {i+1}")
            section_desc = heading.get('description', '')
            category_key = f"custom_{i+1}"
            
            # Başlık bölümünü ekle
            section_content = f"\n{section_title.upper()}\n"
            section_content += "-" * len(section_title) + "\n"
            
            # Açıklama varsa ekle
            if section_desc:
                section_content += f"(Not: {section_desc})\n"
                
            # Bu başlığa ait analiz sonuçlarını ekle
            section_items = analysis.get('content', {}).get(category_key, [])
            section_content += format_list(section_items)
            
            report_sections.append(section_content)
    else:
        # Standart başlıklarla analiz için klasik format
        section_mappings = [
            ("GRUP ÜYELERİ", "grup_uyeleri"),
            ("SORUMLULUKLAR", "sorumluluklar"),
            ("DİYAGRAMLAR", "diyagramlar"),
            ("BAŞLIKLAR", "basliklar"),
            ("EKSİKLER", "eksikler")
        ]
        
        for title, key in section_mappings:
            section_content = f"\n{title}\n"
            section_content += "-" * len(title) + "\n"
            section_items = analysis.get('content', {}).get(key, [])
            section_content += format_list(section_items)
            report_sections.append(section_content)
    
    # En son ham çıktıyı ekle
    report_sections.append("""
ÖZET
----
""" + analysis.get('content', {}).get('ham_sonuc', ''))
    
    # Analizi metin dosyası olarak dışa aktar
    response_text = "\n".join(report_sections)
    
    # Dosya adını oluştur
    filename = f"analiz_{project.name.replace(' ', '_')}_{file_index}.txt"
    
    return Response(
        response_text,
        mimetype="text/plain",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
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

@teacher.route('/teacher/test-llm')
@login_required
def test_llm():
    if not current_user.is_teacher():
        flash('Bu sayfaya erişim yetkiniz yok', 'danger')
        return redirect(url_for('main.index'))
    
    try:
        # LLM sağlayıcı bilgilerini al
        provider = os.getenv('LLM_PROVIDER', 'ollama')
        
        test_result = {
            "provider": provider,
            "provider_name": "LM Studio" if provider == "lmstudio" else "Ollama",
            "test_time": datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
            "model_response": None,
            "error": None
        }
        
        # Model adını belirle
        if provider == 'lmstudio':
            model_name = os.getenv('LM_STUDIO_MODEL', 'deepseek-coder-v2-lite-instruct-mlx')
        else:
            model_name = os.getenv('OLLAMA_MODEL', 'mistral:latest')
            
        test_result["model_name"] = model_name
        
        # LLM istemcisini al
        try:
            # Özellikle mevcut sağlayıcıyı zorlayarak istemci oluştur
            client = get_llm_client(force_provider=provider)
            
            # Test istemi gönder
            response = client.generate(
                "Merhaba, bu bir test mesajıdır. Lütfen kısa bir cevap verin.",
                options={"temperature": 0.7}
            )
            test_result["model_response"] = response
        except Exception as e:
            test_result["error"] = str(e)
            test_result["traceback"] = traceback.format_exc()
            
            # İstemciye özel daha anlaşılır hata mesajları ekle
            if provider == "lmstudio":
                if "connect" in str(e).lower():
                    test_result["error_tip"] = "LM Studio API sunucusuna bağlanılamadı. Lütfen LM Studio uygulamasının çalıştığından ve API Server özelliğinin aktif olduğundan emin olun."
                elif "model" in str(e).lower():
                    test_result["error_tip"] = f"'{model_name}' modeli yüklenemedi. LM Studio'da belirtilen modelin yüklü olduğundan emin olun."
            elif provider == "ollama":
                if "connect" in str(e).lower():
                    test_result["error_tip"] = "Ollama servisine bağlanılamadı. Lütfen Ollama servisinin çalıştığından emin olun."
                elif "model" in str(e).lower():
                    test_result["error_tip"] = f"'{model_name}' modeli bulunamadı. 'ollama pull {model_name}' komutu ile modeli indirin."
        
        return render_template('teacher/test_llm.html', test_result=test_result)
    
    except Exception as e:
        flash(f'Hata oluştu: {str(e)}', 'danger')
        return redirect(url_for('teacher.dashboard'))

@teacher.route('/select-llm-provider', methods=['GET', 'POST'])
@login_required
@teacher_required
def select_llm_provider():
    """LLM sağlayıcısını seçme sayfası"""
    if request.method == 'POST':
        provider = request.form.get('llm_provider')
        
        # Sağlayıcı bilgisi gelmezse yönlendir
        if not provider:
            flash('Lütfen bir LLM sağlayıcısı seçin.', 'error')
            return redirect(url_for('teacher.select_llm_provider'))
        
        print(f"Seçilen LLM sağlayıcı: {provider}")
        print(f"Form verileri: {request.form}")
        
        # API tabanlı sağlayıcılar için özel işlemler
        if provider in ['openai', 'gemini', 'claude']:
            # API anahtarını ve model bilgisini al
            api_key = request.form.get('api_key', '').strip()
            api_model = request.form.get('api_model', '')
            
            print(f"API anahtarı(gizli): {'*'*(len(api_key) if api_key else 0)}")
            print(f"API model: {api_model}")
            
            # API anahtarı boş ise hata ver
            if not api_key:
                # Mevcut API anahtarını kontrol et
                existing_key = APIKeyManager.get_api_key(provider)
                # Mevcut API anahtarı yoksa uyarı ver
                if not existing_key:
                    flash(f'{provider.capitalize()} API anahtarı boş olamaz. Lütfen geçerli bir API anahtarı girin.', 'error')
                    return redirect(url_for('teacher.select_llm_provider'))
                else:
                    # Mevcut API anahtarı var, bu durumda sadece model güncellemesi yap
                    if api_model:
                        APIKeyManager.update_model(provider, api_model)
                        flash(f'{provider.capitalize()} model bilgisi güncellendi.', 'success')
            else:
                # API anahtarını şifreli olarak kaydet
                success = APIKeyManager.save_api_key(provider, api_key, api_model)
                
                if not success:
                    flash(f'API anahtarı kaydedilirken bir hata oluştu.', 'error')
                    return redirect(url_for('teacher.select_llm_provider'))
                else:
                    flash(f'{provider.capitalize()} API anahtarı başarıyla kaydedildi.', 'success')
        
        # Geçerli bir sağlayıcı seçilmişse ayarla
        if provider in ['ollama', 'lmstudio', 'openai', 'gemini', 'claude']:
            # Çevre değişkenini güncelle ve .env dosyasını da güncelle
            try:
                # Çevre değişkenini ayarla
                os.environ['LLM_PROVIDER'] = provider
                
                # .env dosyasını güncelle (kalıcı olması için)
                dotenv_file = os.path.join(os.getcwd(), '.env')
                
                # Mevcut .env dosyasını oku
                env_vars = {}
                if os.path.exists(dotenv_file):
                    with open(dotenv_file, 'r') as f:
                        for line in f:
                            if '=' in line and not line.startswith('#'):
                                key, value = line.strip().split('=', 1)
                                env_vars[key] = value
                
                # LLM_PROVIDER değişkenini güncelle
                env_vars['LLM_PROVIDER'] = provider
                
                # .env dosyasını yeniden yaz
                with open(dotenv_file, 'w') as f:
                    for key, value in env_vars.items():
                        f.write(f"{key}={value}\n")
                
                # dotenv değişkenlerini yeniden yükle
                dotenv.load_dotenv(override=True)
                print(f"LLM_PROVIDER .env dosyasında '{provider}' olarak güncellendi")
                
                flash(f'LLM sağlayıcısı "{provider}" olarak ayarlandı (kalıcı olarak)', 'success')
            except Exception as e:
                # Çevre değişkenini yine de ayarla ama hata mesajı da ver
                os.environ['LLM_PROVIDER'] = provider
                flash(f'LLM sağlayıcısı "{provider}" olarak ayarlandı (geçici olarak, .env güncellenemedi: {str(e)})', 'warning')
        else:
            flash('Geçersiz LLM sağlayıcısı', 'error')
        
        # Temiz bir sayfa yüklenmesi için doğrudan dashboard'a yönlendir
        # Bu, tarayıcının önbelleğini temizler ve mevcut LLM durumunu yeniden yükler
        return redirect(url_for('teacher.dashboard'))
        
    # GET isteği ise, mevcut ayarları göster ve form sayfasını render et
    current_provider = os.getenv('LLM_PROVIDER', 'ollama')
    
    # API sağlayıcı modelleri
    openai_models = ['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo']
    gemini_models = ['gemini-2.0-flash', 'gemini-2.0-pro', 'gemini-2.0-pro-vision']
    claude_models = ['claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307']
    
    # Seçili API anahtarları ve modeller
    # Güvenlik için burada sadece API anahtarlarının varlığını kontrol ediyoruz
    # Gerçek anahtarlar görüntülenmiyor, sadece yenileriyle değiştirilebilir
    has_openai_key = bool(APIKeyManager.get_api_key("openai"))
    has_gemini_key = bool(APIKeyManager.get_api_key("gemini"))
    has_claude_key = bool(APIKeyManager.get_api_key("claude"))
    
    selected_openai_model = APIKeyManager.get_model("openai")
    selected_gemini_model = APIKeyManager.get_model("gemini")
    selected_claude_model = APIKeyManager.get_model("claude")
    
    return render_template(
        'teacher/select_llm_provider.html',
        current_provider=current_provider,
        openai_models=openai_models,
        gemini_models=gemini_models,
        claude_models=claude_models,
        selected_openai_model=selected_openai_model,
        selected_gemini_model=selected_gemini_model,
        selected_claude_model=selected_claude_model,
        has_openai_key=has_openai_key,
        has_gemini_key=has_gemini_key,
        has_claude_key=has_claude_key
    )

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
    
    if request.method == 'POST':
        try:
            # Tüm projeleri getir
            projects = Project.get_all()
            fixed_count = 0
            updated_ids_count = 0
            updated_names_count = 0
            updated_status_count = 0
            api_based_count = 0
            custom_heading_count = 0
            
            for project in projects:
                # Projenin tüm dosyalarını kontrol et
                for file_index, file in enumerate(project.files):
                    # Dosya ID'si yoksa oluştur
                    file_id_fixed = False
                    if not file.get('file_id'):
                        file['file_id'] = str(uuid.uuid4())
                        file_id_fixed = True
                        updated_ids_count += 1
                    
                    # Dosya için analiz var mı kontrol et
                    for analysis in project.analysis:
                        # Herhangi bir eşleşme durumu kontrol et
                        if (analysis.get('file_index') == file_index or 
                           (analysis.get('file_name') and analysis.get('file_name') == file.get('filename')) or
                           (analysis.get('file_id') and analysis.get('file_id') == file.get('file_id'))):
                            
                            # file_id güncelleme
                            if not analysis.get('file_id') or (file_id_fixed and analysis.get('file_index') == file_index):
                                analysis['file_id'] = file.get('file_id')
                                updated_ids_count += 1
                            
                            # file_name güncelleme
                            if not analysis.get('file_name'):
                                analysis['file_name'] = file.get('filename')
                                updated_names_count += 1
                                
                            # Durum bilgisi ekle
                            if not analysis.get('status'):
                                analysis['status'] = 'completed'
                                updated_status_count += 1
                            
                            # Analiz türlerini kontrol et ve güncelle
                            content = analysis.get('content', {})
                            
                            # API tabanlı analizleri kontrol et
                            if content.get('llm_info', {}).get('provider') in ['openai', 'gemini', 'claude']:
                                # API tabanlı analiz, özel alanları kontrol et
                                api_based_count += 1
                            
                            # Özel başlıklı analizleri kontrol et
                            if content.get('custom_headings', []):
                                custom_heading_count += 1
                                
                            fixed_count += 1
                
                # Değişiklikleri kaydet
                project.save()
            
            # Detaylı rapor oluştur
            report_message = f'Toplam {fixed_count} analiz kaydı işlendi:'
            if updated_ids_count > 0:
                report_message += f' {updated_ids_count} benzersiz ID güncellendi,'
            if updated_names_count > 0:
                report_message += f' {updated_names_count} dosya adı güncellendi,'
            if updated_status_count > 0:
                report_message += f' {updated_status_count} durum bilgisi eklendi,'
            if api_based_count > 0:
                report_message += f' {api_based_count} API tabanlı analiz güncellendi,'
            if custom_heading_count > 0:
                report_message += f' {custom_heading_count} özel başlıklı analiz güncellendi,'
            
            # Son virgülü kaldır
            if report_message.endswith(','):
                report_message = report_message[:-1]
                
            flash(report_message, 'success')
            return redirect(url_for('teacher.dashboard'))
        except Exception as e:
            flash(f'Analiz bakımı yapılırken hata oluştu: {str(e)}', 'danger')
            print(f"Analiz bakım hatası: {str(e)}")
            print(traceback.format_exc())
    
    return render_template('teacher/fix_analyses.html')

@teacher.route('/teacher/test-api-llm', methods=['GET', 'POST'])
@login_required
@teacher_required
def test_api_llm():
    """API tabanlı LLM'leri test etme sayfası"""
    
    if request.method == 'POST':
        # Formdan gelen bilgileri al
        provider = request.form.get('provider', '')
        api_key = request.form.get('api_key', '')
        model = request.form.get('model', '')
        
        if not provider or provider not in ['openai', 'gemini', 'claude']:
            flash('Geçersiz LLM sağlayıcı seçimi', 'danger')
            return redirect(url_for('teacher.test_api_llm'))
            
        # API anahtarı kontrolü
        if not api_key and not APIKeyManager.get_api_key(provider):
            flash('API anahtarı girin veya kayıtlı bir API anahtarı seçin', 'danger')
            return redirect(url_for('teacher.test_api_llm'))
            
        # Test sonuçlarını kaydet
        test_result = {
            "provider": provider,
            "provider_name": {
                "openai": "OpenAI GPT",
                "gemini": "Google Gemini",
                "claude": "Anthropic Claude"
            }.get(provider, provider),
            "model_name": model,
            "test_time": datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
            "model_response": None,
            "error": None,
            "use_saved_key": not api_key
        }
        
        # API anahtarını kaydetme isteği var mı kontrol et
        save_key_requested = request.form.get('save_key') == 'on'
        key_saved_success = False
        
        try:
            # Eğer API anahtarı girildiyse, mevcut anahtarı kullan
            # Girildiyse, test için geçici olarak kullan (kaydetme)
            client = get_llm_client(
                force_provider=provider, 
                api_key=api_key if api_key else None
            )
            
            # Test istemi gönder
            response = client.generate(
                "Merhaba, bu bir test mesajıdır. Lütfen kısa bir cevap verin.",
                options={"temperature": 0.7, "max_tokens": 100}
            )
            test_result["model_response"] = response
            
            # Başarılı ise ve kullanıcı istemişse bilgiyi kaydet
            if api_key and save_key_requested:
                try:
                    success = APIKeyManager.save_api_key(provider, api_key, model)
                    if success:
                        flash('API anahtarı başarıyla kaydedildi', 'success')
                        key_saved_success = True
                    else:
                        flash('API anahtarı kaydedilirken bir hata oluştu: Veritabanına kayıt başarısız', 'warning')
                except Exception as save_error:
                    flash(f'API anahtarı kaydedilirken bir hata oluştu: {str(save_error)}', 'warning')
            
        except Exception as e:
            test_result["error"] = str(e)
            test_result["traceback"] = traceback.format_exc()
            
            # Hata var ama yine de anahtarı kaydetmeye çalışalım mı?
            if api_key and save_key_requested:
                try:
                    success = APIKeyManager.save_api_key(provider, api_key, model)
                    if success:
                        flash('API testinde hata oluştu ancak anahtarınız başarıyla kaydedildi', 'info')
                        key_saved_success = True
                    else:
                        flash('API anahtarı kaydedilirken bir hata oluştu: Veritabanına kayıt başarısız', 'warning')
                except Exception as save_error:
                    flash(f'API anahtarı kaydedilirken bir hata oluştu: {str(save_error)}', 'warning')
            
            # İstemciye özel daha anlaşılır hata mesajları ekle
            if "API key" in str(e).lower() or "api_key" in str(e).lower() or "apikey" in str(e).lower():
                test_result["error_tip"] = "API anahtarı geçersiz veya hatalı formatlanmış olabilir. Doğru formatta bir API anahtarı girdiğinizden emin olun."
            elif "timeout" in str(e).lower() or "time out" in str(e).lower():
                test_result["error_tip"] = "Sunucu yanıt vermedi. İnternet bağlantınızı kontrol edin ve daha sonra tekrar deneyin."
            elif "rate limit" in str(e).lower() or "ratelimit" in str(e).lower():
                test_result["error_tip"] = "API istek limiti aşıldı. Bir süre bekleyip tekrar deneyin veya başka bir API anahtarı kullanın."
            elif "permission" in str(e).lower() or "access" in str(e).lower():
                test_result["error_tip"] = "API anahtarınız bu modeli kullanmak için gerekli izinlere sahip değil. Hesabınızı ve izinlerinizi kontrol edin."
                
        # Model bilgilerine göre seçimleri yap
        openai_models = ['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo']
        gemini_models = ['gemini-2.0-flash', 'gemini-2.0-pro', 'gemini-2.0-pro-vision']
        claude_models = ['claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307']
        
        # API anahtarlarının varlığını kontrol et
        has_openai_key = bool(APIKeyManager.get_api_key("openai"))
        has_gemini_key = bool(APIKeyManager.get_api_key("gemini"))
        has_claude_key = bool(APIKeyManager.get_api_key("claude"))
        
        # Anahtar kaydedildiyse durumu test_result'a ekle
        test_result["key_saved"] = key_saved_success
        
        return render_template(
            'teacher/test_api_llm.html', 
            test_result=test_result,
            openai_models=openai_models,
            gemini_models=gemini_models,
            claude_models=claude_models,
            has_openai_key=has_openai_key,
            has_gemini_key=has_gemini_key,
            has_claude_key=has_claude_key,
            selected_provider=provider,
            selected_model=model
        )
    
    # GET isteği - form sayfasını göster
    # Seçenekleri ve mevcut API anahtarlarını hazırla
    openai_models = ['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo']
    gemini_models = ['gemini-2.0-flash', 'gemini-2.0-pro', 'gemini-2.0-pro-vision']
    claude_models = ['claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307']
    
    # API anahtarlarının varlığını kontrol et
    has_openai_key = bool(APIKeyManager.get_api_key("openai"))
    has_gemini_key = bool(APIKeyManager.get_api_key("gemini"))
    has_claude_key = bool(APIKeyManager.get_api_key("claude"))
    
    return render_template(
        'teacher/test_api_llm.html',
        openai_models=openai_models,
        gemini_models=gemini_models,
        claude_models=claude_models,
        has_openai_key=has_openai_key,
        has_gemini_key=has_gemini_key,
        has_claude_key=has_claude_key,
        selected_provider='',
        selected_model='',
        test_result=None
    ) 

@teacher.route('/teacher/projects/<project_id>/file/<int:file_index>/analyze-custom', methods=['POST'])
@login_required
def analyze_file_with_custom_headings(project_id, file_index):
    if not current_user.is_teacher():
        flash('Bu sayfaya erişim yetkiniz yok', 'danger')
        return redirect(url_for('main.index'))
    
    # Debug dizininin varlığını kontrol et, yoksa oluştur
    debug_dir = '/tmp/llm_debug'
    if not os.path.exists(debug_dir):
        os.makedirs(debug_dir)
    
    # Debug dosyasına bilgi yaz
    with open('/tmp/llm_debug/info.txt', 'a', encoding='utf-8') as f:
        f.write("\n\n--- CUSTOM HEADINGS ANALIZ BAŞLADI ---\n")
        f.write(f"Proje ID: {project_id}, Dosya indeksi: {file_index}\n")
    
    # Formdan gelen başlık verilerini al
    heading_titles = request.form.getlist('heading_title[]')
    heading_descriptions = request.form.getlist('heading_description[]')
    
    # Debug log
    with open('/tmp/llm_debug/info.txt', 'a', encoding='utf-8') as f:
        f.write(f"Başlık sayısı: {len(heading_titles)}\n")
        f.write(f"Başlıklar: {heading_titles}\n")
        f.write(f"Açıklamalar: {heading_descriptions}\n")
    
    # Boş başlıkları kontrol et
    if not heading_titles or not any(title.strip() for title in heading_titles):
        flash('En az bir başlık girmelisiniz', 'danger')
        with open('/tmp/llm_debug/info.txt', 'a', encoding='utf-8') as f:
            f.write("HATA: Başlık girişi yok\n")
        return redirect(url_for('teacher.view_file', project_id=project_id, file_index=file_index))
    
    # Başlık ve açıklamaları birleştirerek özel kategoriler oluştur
    custom_categories = {}
    custom_headings_data = []
    
    for i, title in enumerate(heading_titles):
        title = title.strip()
        if title:  # Boş başlıkları atla
            # Eğer açıklama varsa başlığa ekle, yoksa sadece başlığı kullan
            description = heading_descriptions[i].strip() if i < len(heading_descriptions) else ""
            category_key = f"custom_{i+1}"
            
            # İki nokta üst üste içeren başlıklar için özel işlem
            if not title.endswith(':'):
                # Başlığı LLM'e sorulacak soru formatında kullan
                custom_categories[category_key] = title
            else:
                # İki nokta üst üste içeren başlığı temizleyerek kullan
                custom_categories[category_key] = title[:-1]
            
            # Başlık ve açıklama bilgilerini kaydet
            custom_headings_data.append({
                'title': title,
                'description': description
            })
    
    # Debug log
    with open('/tmp/llm_debug/info.txt', 'a', encoding='utf-8') as f:
        f.write(f"Oluşturulan kategoriler: {custom_categories}\n")
        f.write(f"Başlık verileri: {custom_headings_data}\n")
    
    # LLM sağlayıcı bilgilerini al
    llm_provider = os.getenv('LLM_PROVIDER', 'ollama')
    
    # Sağlayıcıya göre standart isim ve model bilgilerini ayarla
    provider_display_names = {
        'ollama': 'Ollama',
        'lmstudio': 'LM Studio',
        'openai': 'OpenAI GPT',
        'gemini': 'Google Gemini',
        'claude': 'Anthropic Claude'
    }
    
    # Sağlayıcı görünen adını al, bulunamazsa teknik adını kullan
    provider_display_name = provider_display_names.get(llm_provider, llm_provider.capitalize())
    
    # Model bilgilerini al
    if llm_provider == 'ollama':
        # Ollama için model kontrolü
        if not check_ollama_availability():
            flash('Ollama LLM servisi şu anda çalışmıyor. Lütfen servisin çalıştığından emin olun veya başka bir LLM sağlayıcısı seçin.', 'danger')
            return redirect(url_for('teacher.view_file', project_id=project_id, file_index=file_index))
        model_name = os.getenv('OLLAMA_MODEL', 'mistral:latest')
    elif llm_provider == 'lmstudio':
        # LM Studio için model kontrolü
        from app.utils.llm_utils import check_lmstudio_availability
        if not check_lmstudio_availability():
            flash('LM Studio servisi şu anda çalışmıyor. Lütfen LM Studio uygulamasının çalıştığından ve API Server özelliğinin etkin olduğundan emin olun.', 'danger')
            return redirect(url_for('teacher.view_file', project_id=project_id, file_index=file_index))
        model_name = os.getenv('LM_STUDIO_MODEL', 'deepseek-coder-v2-lite-instruct-mlx')
    elif llm_provider == 'openai':
        # OpenAI için model ve API anahtarı kontrolü
        from app.utils.api_key_manager import APIKeyManager
        api_key = APIKeyManager.get_api_key('openai')
        if not api_key:
            flash('OpenAI API anahtarı bulunamadı. Lütfen API anahtarınızı ayarlar sayfasından ekleyin.', 'danger')
            return redirect(url_for('teacher.view_file', project_id=project_id, file_index=file_index))
        model_name = APIKeyManager.get_model('openai') or os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    elif llm_provider == 'gemini':
        # Gemini için model ve API anahtarı kontrolü
        from app.utils.api_key_manager import APIKeyManager
        api_key = APIKeyManager.get_api_key('gemini')
        if not api_key:
            flash('Google Gemini API anahtarı bulunamadı. Lütfen API anahtarınızı ayarlar sayfasından ekleyin.', 'danger')
            return redirect(url_for('teacher.view_file', project_id=project_id, file_index=file_index))
        model_name = APIKeyManager.get_model('gemini') or os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
    elif llm_provider == 'claude':
        # Claude için model ve API anahtarı kontrolü
        from app.utils.api_key_manager import APIKeyManager
        api_key = APIKeyManager.get_api_key('claude')
        if not api_key:
            flash('Anthropic Claude API anahtarı bulunamadı. Lütfen API anahtarınızı ayarlar sayfasından ekleyin.', 'danger')
            return redirect(url_for('teacher.view_file', project_id=project_id, file_index=file_index))
        model_name = APIKeyManager.get_model('claude') or os.getenv('CLAUDE_MODEL', 'claude-3-opus-20240229')
    else:
        flash('Bilinmeyen LLM sağlayıcısı. Lütfen geçerli bir sağlayıcı seçin.', 'danger')
        return redirect(url_for('teacher.view_file', project_id=project_id, file_index=file_index))
    
    # Projeyi al
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
    
    # Özel başlıklarla dinamik prompt oluştur
    custom_prompt = "Bu PDF bir öğrenci projesidir. İçeriği analiz et ve şu başlıkların dökümanda olup olmadığını kontrol et:\n"
    for i, title in enumerate(heading_titles):
        if title.strip():
            # Açıklamayı kontrol et
            description = heading_descriptions[i].strip() if i < len(heading_descriptions) else ""
            
            # Başlık zaten iki nokta üst üste içeriyorsa olduğu gibi kullan
            if title.strip().endswith(':'):
                prompt_title = title.strip()
            else:
                prompt_title = f"{title.strip()}"
                
            # Başlığı ekle
            custom_prompt += f"    • {prompt_title}"
            
            # Açıklama varsa, açıklamayı başlığa ekle
            if description:
                custom_prompt += f" ({description})"
                
            custom_prompt += "\n"
    
    custom_prompt += """    
    İşte PDF'in içeriği:
    
    {content}
    
    Yanıtını aşağıdaki şekilde yapılandır:
    1. Her başlık için şu formatta yanıt ver:
       - Eğer başlıkla ilgili içerik varsa: "Evet, dökümanda bu başlığa yer verilmiştir." ifadesiyle başla ve 1-3 cümlelik kısa bir özet sun.
       - Eğer başlıkla ilgili içerik yoksa: "Bu başlıkla ilgili veri bulunamadı" ifadesini kullan.
    2. Her bölümü başlık adıyla AYNEN başlat ve başlık sonuna ":" ekle (örneğin "Proje Özeti:" şeklinde).
    3. Yanıtlarını kısa ve öz tut, uzun açıklamalardan kaçın.
    4. Her başlığı yeni bir satırda başlat.
    5. Özet bilgilerini maddeler halinde değil, düz metin olarak 1-3 cümle ile sınırla.
    6. Başlık ile yanıt arasına yeni satır veya boşluk ekleme.
    
    ÖRNEK YANIT FORMATI:
    Proje Özeti: Evet, dökümanda bu başlığa yer verilmiştir. [Kısa özet burada yer alacak]
    Problem Tanımı: Bu başlıkla ilgili veri bulunamadı.
    Çözüm Önerisi: Evet, dökümanda bu başlığa yer verilmiştir. [Kısa özet burada yer alacak]
    """
    
    # Debug log
    with open('/tmp/llm_debug/info.txt', 'a', encoding='utf-8') as f:
        f.write(f"Oluşturulan prompt: {custom_prompt}\n")
    
    # LLM bilgisini kullanıcıya göster
    flash(f'{provider_display_name} sistemi ile "{model_name}" modeli kullanılarak özel başlıklarla analiz yapılıyor...', 'info')
    
    try:
        # LLM ile analiz yap (özel kategoriler ve özel prompt ile)
        analysis_result = analyze_text_with_llm(text_chunks, categories=custom_categories, custom_prompt=custom_prompt)
        
        # Debug log
        with open('/tmp/llm_debug/info.txt', 'a', encoding='utf-8') as f:
            f.write(f"Analiz sonucu: {analysis_result}\n")
        
        # Analiz sonucuna LLM sağlayıcı ve model bilgilerini ekle
        analysis_result['llm_info'] = {
            'provider': llm_provider,
            'provider_name': provider_display_name,
            'model': model_name,
        }
        
        # Başlık ve açıklamaları da kaydet
        analysis_result['custom_headings'] = custom_headings_data
        
        # Debug log
        with open('/tmp/llm_debug/info.txt', 'a', encoding='utf-8') as f:
            f.write(f"Sonuca eklenen başlık verileri: {custom_headings_data}\n")
        
        # Analizi projeye ekle
        project.add_analysis(file_index, analysis_result)
        project.save()
        
        with open('/tmp/llm_debug/info.txt', 'a', encoding='utf-8') as f:
            f.write("Analiz başarıyla kaydedildi\n")
        
        flash(f'Dosya başarıyla özel başlıklarla analiz edildi ({provider_display_name} - {model_name})', 'success')
    except Exception as e:
        flash(f'Analiz sırasında hata oluştu: {str(e)}', 'danger')
        print(f"Analiz hatası: {str(e)}")
        print(traceback.format_exc())
        
        # Debug log
        with open('/tmp/llm_debug/info.txt', 'a', encoding='utf-8') as f:
            f.write(f"HATA: {str(e)}\n")
            f.write(f"Traceback: {traceback.format_exc()}\n")
    
    with open('/tmp/llm_debug/info.txt', 'a', encoding='utf-8') as f:
        f.write("--- CUSTOM HEADINGS ANALIZ TAMAMLANDI ---\n")
    
    return redirect(url_for('teacher.view_file', project_id=project_id, file_index=file_index)) 

@teacher.route('/teacher/projects/<project_id>/file/<int:file_index>/view_debug', methods=['GET'])
@login_required
@teacher_required
def view_file_debug(project_id, file_index):
    """Hata ayıklama bilgilerini göstermek için özel bir rota."""
    # Normal dosya görüntüleme sayfasına yönlendir, ama debug parametresiyle
    return redirect(url_for('teacher.view_file', project_id=project_id, file_index=file_index, debug=1)) 