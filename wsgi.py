from app import create_app
from app.middleware import IngressMiddleware

app = create_app()
app.wsgi_app = IngressMiddleware(app.wsgi_app)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
