# Kullanıcıları bulma

users = current_app.db.users.find()  # Tüm kullanıcılar
user = current_app.db.users.find_one({"email": "ornek@email.com"})  # Tek kullanıcı

# Projeleri bulma

projects = current_app.db.projects.find({"created_by": user_id})  # Kullanıcının projeleri
project = current_app.db.projects.find_one({"_id": ObjectId(project_id)})  # Tek proje

# API anahtarlarını bulma

api_keys = current_app.db.api_keys.find({"user_id": user_id})  # Kullanıcının API anahtarları

# Son eklenen projeleri bulma

recent_projects = current_app.db.projects.find().sort("created_at", -1).limit(5)

# Belirli bir tarihten sonraki projeler

from datetime import datetime
date = datetime(2024, 1, 1)
new_projects = current_app.db.projects.find({"created_at": {"$gt": date}})

# Öğretmen kullanıcıları bulma

teachers = current_app.db.users.find({"role": "teacher"})

# Son eklenen projeleri bulma

recent_projects = current_app.db.projects.find().sort("created_at", -1).limit(5)

# Belirli bir tarihten sonraki projeler

from datetime import datetime
date = datetime(2024, 1, 1)
new_projects = current_app.db.projects.find({"created_at": {"$gt": date}})

# Öğretmen kullanıcıları bulma

teachers = current_app.db.users.find({"role": "teacher"})

# Birden fazla koşul ile arama

projects = current_app.db.projects.find({
    "created_by": user_id,
    "files": {"$exists": True, "$ne": []},
    "created_at": {"$gt": date}
})

# Regex ile arama

users = current_app.db.users.find({
    "username": {"$regex": "^a", "$options": "i"}  # 'a' ile başlayan kullanıcılar
})

# Proje istatistikleri

stats = current_app.db.projects.aggregate([
    {
        "$group": {
            "_id": "$created_by",
            "total_projects": {"$sum": 1},
            "total_files": {"$sum": {"$size": "$files"}}
        }
    }
])

# Kullanıcı rolleri dağılımı

role_stats = current_app.db.users.aggregate([
    {
        "$group": {
            "_id": "$role",
            "count": {"$sum": 1}
        }
    }
])

# Proje güncelleme

current_app.db.projects.update_one(
    {"_id": ObjectId(project_id)},
    {
        "$set": {
            "name": "Yeni İsim",
            "description": "Yeni Açıklama"
        }
    }
)

# Dosya ekleme

current_app.db.projects.update_one(
    {"_id": ObjectId(project_id)},
    {
        "$push": {
            "files": {
                "filename": "yeni_dosya.pdf",
                "path": "uploads/yeni_dosya.pdf",
                "upload_date": datetime.now()
            }
        }
    }
)

# Proje silme

current_app.db.projects.delete_one({"_id": ObjectId(project_id)})

# Kullanıcının tüm projelerini silme

current_app.db.projects.delete_many({"created_by": user_id})

#Terminal

mongosh

// Mevcut veritabanlarını listele
show dbs

// Veritabanı seç
use smart_doc_insight

// Koleksiyonları listele
show collections

// Tüm kullanıcıları listele
db.users.find()

// Daha okunaklı çıktı için
db.users.find().pretty()

// Belirli bir kullanıcıyı bul
db.users.findOne({email: "ornek@email.com"})

// Öğretmenleri bul
db.users.find({role: "teacher"})

// Son eklenen 5 projeyi bul
db.projects.find().sort({created_at: -1}).limit(5)

// Belirli bir tarihten sonraki projeler
db.projects.find({
    created_at: {
        $gt: new Date("2024-01-01")
    }
})

// Kullanıcı rollerinin dağılımını göster
db.users.aggregate([
    {
        $group: {
            _id: "$role",
            count: { $sum: 1 }
        }
    }
])

// Proje istatistikleri
db.projects.aggregate([
    {
        $group: {
            _id: "$created_by",
            total_projects: { $sum: 1 },
            total_files: { $sum: { $size: "$files" } }
        }
    }
])

// Proje güncelleme
db.projects.updateOne(
    { _id: ObjectId("proje_id") },
    {
        $set: {
            name: "Yeni İsim",
            description: "Yeni Açıklama"
        }
    }
)

// Dosya ekleme
db.projects.updateOne(
    { _id: ObjectId("proje_id") },
    {
        $push: {
            files: {
                filename: "yeni_dosya.pdf",
                path: "uploads/yeni_dosya.pdf",
                upload_date: new Date()
            }
        }
    }
)

// Proje silme
db.projects.deleteOne({ _id: ObjectId("proje_id") })

// Kullanıcının tüm projelerini silme
db.projects.deleteMany({ created_by: "kullanici_id" })

// Email alanı için indeks
db.users.createIndex({ email: 1 }, { unique: true })

// Tarih alanı için indeks
db.projects.createIndex({ created_at: -1 })

// Koleksiyon istatistikleri
db.projects.stats()

// İndeks kullanım istatistikleri
db.projects.aggregate([{ $indexStats: {} }])
