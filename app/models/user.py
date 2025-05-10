from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId

class User(UserMixin):
    def __init__(self, username, email, role, password_hash=None, _id=None):
        self.username = username
        self.email = email
        self.role = role  # 'student' veya 'teacher'
        self.password_hash = password_hash
        self._id = _id

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self._id)

    def is_teacher(self):
        return self.role == 'teacher'

    def is_student(self):
        return self.role == 'student'

    @staticmethod
    def get_by_id(user_id):
        try:
            user_data = current_app.db.users.find_one({"_id": ObjectId(user_id)})
            if user_data:
                return User(
                    username=user_data.get('username'),
                    email=user_data.get('email'),
                    role=user_data.get('role'),
                    password_hash=user_data.get('password_hash'),
                    _id=user_data.get('_id')
                )
        except:
            return None
        return None

    @staticmethod
    def get_by_email(email):
        user_data = current_app.db.users.find_one({"email": email})
        if user_data:
            return User(
                username=user_data.get('username'),
                email=user_data.get('email'),
                role=user_data.get('role'),
                password_hash=user_data.get('password_hash'),
                _id=user_data.get('_id')
            )
        return None

    @staticmethod
    def get_by_username(username):
        user_data = current_app.db.users.find_one({"username": username})
        if user_data:
            return User(
                username=user_data.get('username'),
                email=user_data.get('email'),
                role=user_data.get('role'),
                password_hash=user_data.get('password_hash'),
                _id=user_data.get('_id')
            )
        return None

    def save(self):
        user_data = {
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'password_hash': self.password_hash
        }
        
        if self._id:
            current_app.db.users.update_one(
                {'_id': self._id},
                {'$set': user_data}
            )
        else:
            result = current_app.db.users.insert_one(user_data)
            self._id = result.inserted_id
        
        return self 