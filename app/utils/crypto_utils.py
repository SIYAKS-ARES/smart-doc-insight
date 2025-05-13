import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional, Tuple

class CryptoHelper:
    """
    API anahtarları gibi hassas verileri şifrelemek ve çözmek için yardımcı sınıf
    """
    
    @staticmethod
    def _get_encryption_key(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """
        Şifreleme anahtarı oluşturur
        
        Args:
            password: Şifreleme parolası
            salt: Tuz değeri (None ise yeni oluşturulur)
            
        Returns:
            Tuple[bytes, bytes]: (key, salt)
        """
        if salt is None:
            salt = os.urandom(16)
            
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt
    
    @staticmethod
    def encrypt(data: str, password: str) -> Tuple[str, str]:
        """
        Veriyi şifreler
        
        Args:
            data: Şifrelenecek veri
            password: Şifreleme parolası
            
        Returns:
            Tuple[str, str]: (encrypted_data, salt_base64)
        """
        if not data:
            return "", ""
            
        key, salt = CryptoHelper._get_encryption_key(password)
        
        f = Fernet(key)
        encrypted_data = f.encrypt(data.encode())
        
        # Base64 formatına dönüştür
        encrypted_str = base64.urlsafe_b64encode(encrypted_data).decode()
        salt_str = base64.urlsafe_b64encode(salt).decode()
        
        return encrypted_str, salt_str
    
    @staticmethod
    def decrypt(encrypted_data: str, salt_str: str, password: str) -> str:
        """
        Şifrelenmiş veriyi çözer
        
        Args:
            encrypted_data: Şifrelenmiş veri (base64)
            salt_str: Tuz değeri (base64)
            password: Şifreleme parolası
            
        Returns:
            str: Çözülmüş veri
        """
        if not encrypted_data or not salt_str:
            return ""
            
        try:
            # Base64'ten dönüştür
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data)
            salt = base64.urlsafe_b64decode(salt_str)
            
            key, _ = CryptoHelper._get_encryption_key(password, salt)
            
            f = Fernet(key)
            decrypted_data = f.decrypt(encrypted_bytes).decode()
            
            return decrypted_data
        except Exception as e:
            print(f"Decrypt error: {str(e)}")
            return "" 