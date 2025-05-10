from app import create_app

app = create_app()
 
if __name__ == '__main__':
    # Gunicorn veya başka bir WSGI sunucusu kullanmıyorsanız debug modunu kullanabilirsiniz
    app.run(debug=True) 