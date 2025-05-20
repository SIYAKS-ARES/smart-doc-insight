from flask import current_app
from datetime import datetime
from bson.objectid import ObjectId
import os
from pytz import timezone
import uuid

class Project:
    def __init__(self, name, description, group_members, created_by, files=None, analysis=None, _id=None, created_at=None):
        self.name = name
        self.description = description
        self.group_members = group_members  # [{"user_id": id, "name": "İsim", "responsibility": "Sorumluluk"}]
        self.created_by = created_by  # Oluşturan kullanıcının ObjectId'si
        self.files = files or []  # [{"filename": "dosya.pdf", "path": "uploads/dosya.pdf", "upload_date": datetime, "file_id": "benzersiz_id"}]
        self.analysis = analysis or []  # [{"file_id": "benzersiz_id", "content": "LLM analizi", "analyzed_at": datetime}]
        self._id = _id
        self.created_at = created_at or datetime.now()

    def add_file(self, filename, path):
        file_data = {
            "filename": filename,
            "path": path,
            "upload_date": datetime.now(),
            "file_id": str(uuid.uuid4())  # Benzersiz bir ID oluştur
        }
        if self.files is None:
            self.files = []
        self.files.append(file_data)
        return file_data

    def remove_file(self, file_index):
        """Belirtilen indeksteki dosyayı projeden kaldırır ve diskten siler"""
        try:
            if file_index < 0 or file_index >= len(self.files):
                return False
            
            # Dosya yolunu ve ID'sini al
            file_path = self.files[file_index]['path']
            file_id = self.files[file_index].get('file_id')
            
            # Dosyayı diskten sil
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Dosya silinirken hata: {str(e)}")
                
            # İlişkili analizleri de sil
            if file_id:
                # Eğer dosyanın file_id'si varsa ona göre analizleri filtrele
                new_analysis = [a for a in self.analysis if a.get('file_id') != file_id]
                self.analysis = new_analysis
            else:
                # Eski yöntemle (indeks tabanlı) sil
                new_analysis = [a for a in self.analysis if a.get('file_index') != file_index]
                self.analysis = new_analysis
            
            # Dosyayı listeden kaldır
            del self.files[file_index]
            
            # Projeyi kaydet
            self.save()
            
            return True
        except Exception as e:
            print(f"Dosya kaldırma hatası: {str(e)}")
            return False

    def add_analysis(self, file_index, content):
        # Tarih oluşturma işlemini doğrudan burada yapıyoruz
        current_time = datetime.now()
        
        # Hata ayıklama: Tarih kaydedilmeden önce kontrol et
        print(f"Kaydedilen analiz tarihi: {current_time}")
        
        # Dosya bilgilerini al
        file_id = None
        file_name = None
        if file_index < len(self.files):
            file_data = self.files[file_index]
            file_id = file_data.get('file_id')
            file_name = file_data.get('filename')
            
            # Eğer dosyanın file_id'si yoksa, ona bir ID ekleyin
            if not file_id:
                file_id = str(uuid.uuid4())
                self.files[file_index]['file_id'] = file_id
        
        # Eski analizleri temizle (aynı dosya için)
        if file_id:
            self.analysis = [a for a in self.analysis if a.get('file_id') != file_id]
        else:
            # file_id yoksa file_index ile eşleşenleri temizle
            self.analysis = [a for a in self.analysis if a.get('file_index') != file_index]
        
        analysis_data = {
            "file_id": file_id,
            "file_index": file_index,
            "file_name": file_name,  # Dosya adını da ekleyelim
            "content": content,
            "analyzed_at": current_time,
            "status": "completed"  # Açık bir durum bilgisi ekleyelim
        }
        
        if self.analysis is None:
            self.analysis = []
        
        self.analysis.append(analysis_data)
        return analysis_data

    def get_analysis_for_file(self, file_index):
        """Dosya indeksine göre analizi bulur"""
        if file_index < 0 or file_index >= len(self.files):
            return None
            
        file_data = self.files[file_index]
        file_id = file_data.get('file_id')
        file_name = file_data.get('filename')
        
        # 1. Önce file_id ile bulmayı dene
        if file_id:
            for analysis in self.analysis:
                if analysis.get('file_id') == file_id:
                    return analysis
        
        # 2. Geriye dönük uyumluluk için file_index ile dene
        for analysis in self.analysis:
            if analysis.get('file_index') == file_index:
                return analysis
        
        # 3. Son çare olarak dosya adıyla eşleşmeyi dene
        if file_name:
            for analysis in self.analysis:
                if analysis.get('file_name') == file_name:
                    return analysis
                
        return None

    def is_file_analyzed(self, file_index):
        """Dosyanın analiz edilip edilmediğini kontrol eder"""
        if file_index < 0 or file_index >= len(self.files):
            return False
            
        file_data = self.files[file_index]
        file_id = file_data.get('file_id')
        file_name = file_data.get('filename')
        
        # Herhangi bir eşleşme durumunda true döndür
        for analysis in self.analysis:
            # file_id ile kontrol
            if file_id and analysis.get('file_id') == file_id:
                return True
                
            # file_index ile kontrol (geriye dönük uyumluluk)
            if analysis.get('file_index') == file_index:
                return True
                
            # file_name ile kontrol
            if file_name and analysis.get('file_name') == file_name:
                return True
        
        return False

    def save(self):
        project_data = {
            'name': self.name,
            'description': self.description,
            'group_members': self.group_members,
            'created_by': self.created_by,
            'files': self.files,
            'analysis': self.analysis,
            'created_at': self.created_at
        }
        
        if self._id:
            current_app.db.projects.update_one(  # type: ignore
                {'_id': self._id},
                {'$set': project_data}
            )
        else:
            result = current_app.db.projects.insert_one(project_data)  # type: ignore
            self._id = result.inserted_id
        
        return self

    @staticmethod
    def get_by_id(project_id):
        try:
            project_data = current_app.db.projects.find_one({"_id": ObjectId(project_id)})  # type: ignore
            if project_data:
                return Project(
                    name=project_data.get('name'),
                    description=project_data.get('description'),
                    group_members=project_data.get('group_members', []),
                    created_by=project_data.get('created_by'),
                    files=project_data.get('files', []),
                    analysis=project_data.get('analysis', []),
                    _id=project_data.get('_id'),
                    created_at=project_data.get('created_at')
                )
        except:
            return None
        return None

    @staticmethod
    def get_by_created_by(user_id):
        projects = []
        cursor = current_app.db.projects.find({"created_by": ObjectId(user_id)})  # type: ignore
        
        for project_data in cursor:
            projects.append(Project(
                name=project_data.get('name'),
                description=project_data.get('description'),
                group_members=project_data.get('group_members', []),
                created_by=project_data.get('created_by'),
                files=project_data.get('files', []),
                analysis=project_data.get('analysis', []),
                _id=project_data.get('_id'),
                created_at=project_data.get('created_at')
            ))
        
        return projects

    @staticmethod
    def get_all():
        projects = []
        cursor = current_app.db.projects.find()  # type: ignore
        
        for project_data in cursor:
            projects.append(Project(
                name=project_data.get('name'),
                description=project_data.get('description'),
                group_members=project_data.get('group_members', []),
                created_by=project_data.get('created_by'),
                files=project_data.get('files', []),
                analysis=project_data.get('analysis', []),
                _id=project_data.get('_id'),
                created_at=project_data.get('created_at')
            ))
        
        return projects

    def delete(self):
        """Projeyi ve ilişkili dosyaları siler"""
        if self._id:
            # Dosyaları diskten sil
            for file in self.files:
                try:
                    os.remove(file['path'])
                except:
                    pass
            
            # Veritabanından sil
            current_app.db.projects.delete_one({'_id': self._id})  # type: ignore
            return True
        return False 