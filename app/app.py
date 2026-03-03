from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from models import Collection, db
from routes import bp
from flask_cors import CORS
import os

app = Flask(__name__)

CORS(app, supports_credentials=True, origins="http://localhost:5173")

basedir = os.path.abspath(os.path.dirname(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///podcasts.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MEDIA_FOLDER'] = os.path.join(basedir, '..', 'media_test')


# ── JWT Config ────────────────────────────────────────
app.config['SECRET_KEY'] = 'my-very-long-noy-so-secret-or-random-key'   # required for Flask sessions (can be same or different)

# JWT settings
app.config['JWT_SECRET_KEY'] = 'another-very-long-random-secret-key-yes-yes-yes'  # must be different from SECRET_KEY
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 900          # 15 minutes (recommended)
# app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 3600       # 1 hour (also common)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = 604800      # 7 days
app.config['JWT_TOKEN_LOCATION'] = ['cookies']        # store tokens in cookies
app.config['JWT_COOKIE_CSRF_PROTECT'] = True          # enables CSRF protection (recommended)
app.config['JWT_COOKIE_SECURE'] = False               # ← False for localhost (http), True in production (https)
app.config['JWT_COOKIE_SAMESITE'] = 'Lax'             # good default
app.config['JWT_ACCESS_CSRF_HEADER_NAME'] = "X-CSRF-TOKEN"
app.config['JWT_REFRESH_CSRF_HEADER_NAME'] = "X-CSRF-TOKEN"

# Initialize JWT
jwt = JWTManager(app)


UPLOAD_FOLDER = app.config['MEDIA_FOLDER']
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER



db.init_app(app)

app.register_blueprint(bp)


# Optional: root route for testing
@app.route('/')
def index():
    return "Podcast API running. Try /shows or /episodes"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='localhost', port=5001 )

