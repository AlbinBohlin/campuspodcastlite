# Helper functions (e.g., range request handling)

from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'mp3', 'wav', 'm4a', 'ogg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# utils.py (or wherever)
from werkzeug.security import generate_password_hash, check_password_hash

def hash_password(password):
    return generate_password_hash(password)

def check_password(stored_hash, password):
    return check_password_hash(stored_hash, password)