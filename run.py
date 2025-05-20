from app import create_app
import os

app = create_app()
 
if __name__ == '__main__':
    # Debug modunu ortam değişkeniyle kontrol et
    # Üretim ortamında FLASK_ENV=production olarak ayarlanmalı
    debug_mode = os.getenv('FLASK_ENV', 'development') == 'development'
    app.run(debug=debug_mode, host='0.0.0.0', port=int(os.getenv('PORT', 8088)))