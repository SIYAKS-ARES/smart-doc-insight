#!/usr/bin/env python3
"""
Kullanıcı şifresini sıfırlama scripti
Kullanım: python reset_password.py <email> <yeni_şifre>
"""

import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient
from werkzeug.security import generate_password_hash

# Ortam değişkenlerini yükle
load_dotenv()

def reset_password(email, new_password):
    """Kullanıcı şifresini sıfırla"""
    try:
        # MongoDB bağlantısı
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/smart_doc_insight')
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        db = client.smart_doc_insight
        
        # Kullanıcıyı bul
        user = db.users.find_one({"email": email})
        
        if not user:
            print(f"❌ Hata: {email} adresine sahip kullanıcı bulunamadı!")
            return False
        
        # Şifreyi hash'le
        password_hash = generate_password_hash(new_password)
        
        # Şifreyi güncelle
        db.users.update_one(
            {"email": email},
            {"$set": {"password_hash": password_hash}}
        )
        
        print(f"✅ Başarılı: {email} kullanıcısının şifresi güncellendi!")
        print(f"   Kullanıcı adı: {user.get('username', 'N/A')}")
        print(f"   Rol: {user.get('role', 'N/A')}")
        print(f"   Yeni şifre: {new_password}")
        
        return True
        
    except Exception as e:
        print(f"❌ Hata: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Kullanım: python reset_password.py <email> <yeni_şifre>")
        print("\nÖrnek:")
        print("  python reset_password.py siyaksares-3@example.com yeniSifre123")
        sys.exit(1)
    
    email = sys.argv[1]
    new_password = sys.argv[2]
    
    reset_password(email, new_password)

