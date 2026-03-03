# API Endpoints

from flask import Blueprint, jsonify, request, send_file, abort, current_app
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, set_access_cookies, set_refresh_cookies, unset_jwt_cookies
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Episode, Collection, User 
from utils import ALLOWED_CATEGORIES, hash_password, check_password
import uuid
import os

ALLOWED_EXTENSIONS = {'mp3', 'wav', 'm4a', 'ogg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Create Blueprint
bp = Blueprint('api', __name__, url_prefix='')

@bp.route('/')
def index():
    return "Podcast API is running! Try /episodes"


"""
:::::::::::::::::'######:::'########:'########:::::::::::::::::
::::::::::::::::'##... ##:: ##.....::... ##..::::::::::::::::::
:::::::::::::::: ##:::..::: ##:::::::::: ##::::::::::::::::::::
:::::::::::::::: ##::'####: ######:::::: ##::::::::::::::::::::
:::::::::::::::: ##::: ##:: ##...::::::: ##::::::::::::::::::::
:::::::::::::::: ##::: ##:: ##:::::::::: ##::::::::::::::::::::
::::::::::::::::. ######::: ########:::: ##::::::::::::::::::::
:::::::::::::::::......::::........:::::..:::::::::::::::::::::
"""

# 1. List all shows
@bp.route('/collections', methods=['GET'])
def get_Collections():

    query = Collection.query

    # Filter by user/creator
    user_id = request.args.get('user_id', type=int)
    if user_id:
        query = query.filter_by(user_id=user_id)

    # Filter by category
    category = request.args.get('category')
    if category:
        query = query.filter(Collection.category.ilike(f"%{category}%"))

    # Sorting
    sort = request.args.get('sort', 'newest')
    if sort == 'newest':
        query = query.order_by(Collection.id.desc())
    elif sort == 'oldest':
        query = query.order_by(Collection.id.asc())
    elif sort == 'name':
        query = query.order_by(Collection.name.asc())
        
    # Optional: pagination if many collections
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    pagination = query.paginate(page=page, per_page=limit, error_out=False)

    return jsonify({
        "collections": [c.to_dict() for c in pagination.items],
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": pagination.page,
        "filters": {"user_id": user_id, "category": category}
    }), 200

# 2. Get one show + its episodes (very useful for frontend)
@bp.route('/collections/<int:collection_id>', methods=['GET'])
def get_Collection(collection_id):
    show = Collection.query.get_or_404(collection_id)
    episodes = Episode.query.filter_by(collection_id=collection_id).all()
    return jsonify({
        'show': show.to_dict(),
        'episodes': [e.to_dict() for e in episodes]
    })

@bp.route('/episodes/recent', methods=['GET'])
def get_recent_episodes():
    limit = min(request.args.get('limit', 10, type=int), 50)
    episodes = Episode.query.order_by(Episode.id.desc()).limit(limit).all()
    
    return jsonify({
        "episodes": [ep.to_dict() for ep in episodes],
        "total": len(episodes),
        "pages": 1,
        "current_page": 1,
        "applied_filters": {}
    }), 200
        
@bp.route('/episodes', methods=['GET'])
def get_episodes():
    """
    List episodes – now with filtering by collection_id
    Query params:
    - collection_id     (int)     Filter by specific show/podcast
    - page        (int)     default 1
    - limit       (int)     default 10
    - sort        (str)     'newest' (default), 'oldest', 'title'
    - search      (str)     Optional keyword in title or description
    """
    query = Episode.query

    # Filter by show
    collection_id = request.args.get('collection_id', type=int)
    if collection_id:
        query = query.filter_by(collection_id=collection_id)

    # Optional search in title or description
    search = request.args.get('search')
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Episode.title.ilike(search_term)) |
            (Episode.description.ilike(search_term))
        )

    # filter by category
    category = request.args.get('category')
    if category:
        query = query.filter(Episode.category.ilike(f"%{category}%"))

    # filter by user/creator
    user_id = request.args.get('user_id', type=int)
    if user_id:
        query = query.filter_by(user_id=user_id)


    # Sorting
    sort = request.args.get('sort', 'newest')
    if sort == 'newest':
        query = query.order_by(Episode.id.desc())  # assuming higher ID = newer
        # Alternative if you add publish_date:
        # query = query.order_by(Episode.publish_date.desc())
    elif sort == 'oldest':
        query = query.order_by(Episode.id.asc())
    elif sort == 'title':
        query = query.order_by(Episode.title.asc())

    # Pagination
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    pagination = query.paginate(page=page, per_page=limit, error_out=False)

    episodes = pagination.items

    return jsonify({
        "episodes": [ep.to_dict() for ep in episodes],
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": pagination.page,
        "per_page": limit,
        "applied_filters": {
            "collection_id": collection_id if collection_id else None,
            "search": search if search else None,
            "sort": sort,
            "category": category if category else None,
            "user_id": user_id
        }
    }), 200

# 2. Get single episode details
@bp.route('/episode/<int:episode_id>', methods=['GET'])
def get_episode(episode_id):
    """
    Get details for one episode.
    Response: JSON {id, title, description}
    """
    episode = Episode.query.get_or_404(episode_id)
    return jsonify(episode.to_dict())

# 3. Stream media (server-side playback)
@bp.route('/stream/<int:episode_id>', methods=['GET'])
def stream_episode(episode_id):
    """
    Stream audio file for episode.
    Supports range requests for seeking in HTML5 audio.
    Headers: Accept-Ranges: bytes, Content-Type: audio/mpeg
    No direct download; front-end uses <audio src="/stream/{id}"> to play.
    """
    episode = Episode.query.get_or_404(episode_id)
    file_path = os.path.join(current_app.config['MEDIA_FOLDER'], episode.file_path)
    
    if not os.path.exists(file_path):
        abort(404, description="Media file not found")
    
    range_header = request.headers.get('Range', None)

    return send_file(
        file_path,
        mimetype='audio/mpeg',
        conditional=True,  # Handles range requests
        as_attachment=False  # Streams instead of downloading
    )
                    
""" 
:::::::::::::::::'########:::'#######:::'######::'########::::::::::::::::::
::::::::::::::::: ##.... ##:'##.... ##:'##... ##:... ##..:::::::::::::::::::
::::::::::::::::: ##:::: ##: ##:::: ##: ##:::..::::: ##:::::::::::::::::::::
::::::::::::::::: ########:: ##:::: ##:. ######::::: ##:::::::::::::::::::::
::::::::::::::::: ##.....::: ##:::: ##::..... ##:::: ##:::::::::::::::::::::
::::::::::::::::: ##:::::::: ##:::: ##:'##::: ##:::: ##:::::::::::::::::::::
::::::::::::::::: ##::::::::. #######::. ######::::: ##:::::::::::::::::::::
:::::::::::::::::..::::::::::.......::::......::::::..::::::::::::::::::::::
"""

# 4. Create new collection (for creators)
@bp.route('/collection', methods=['POST'])
@jwt_required()
def add_collection():
    current_user_id = get_jwt_identity()
    data = request.json
    if not data or not data.get('name'):
        abort(400, "Missing name")
    
    show = Collection(
        name=data['name'],
        description=data.get('description'),
        creator_name=data.get('creator_name'),
        user_id=int(current_user_id) 
    )
    db.session.add(show)
    db.session.commit()
    return jsonify(show.to_dict()), 201


# 5. When creating episode → require collection_id
@bp.route('/episode', methods=['POST'])
@jwt_required()  # need login for create
def add_episode():

    current_user_id = get_jwt_identity()  # from JWT
    data = request.json
    required = ['title', 'file_path', 'collection_id']
    if not data or not all(k in data for k in required):
        abort(400, f"Missing one of: {required}")

    # Default logic
    collection_id = data.get('collection_id')
    if collection_id is None:
        default_show = Collection.query.filter_by(name="Default Podcast").first()
        if not default_show:
            abort(500, description="Default show not found – create it first")
        collection_id = default_show.id
    
    # Optional: validate show exists
    if not Collection.query.get(data['collection_id']):
        abort(404, "Show not found")
    

    category = data.get('category')
    if category and category not in ALLOWED_CATEGORIES:
        return jsonify({
            "error": f"Invalid category. Allowed: {', '.join(sorted(ALLOWED_CATEGORIES))}"
        }), 400

    episode = Episode(
        title=data['title'],
        description=data.get('description'),
        file_path=data['file_path'],
        collection_id=data['collection_id'],
        category=data.get('category'),          # optional
        user_id=current_user_id                 
    )
    db.session.add(episode)
    db.session.commit()
    return jsonify(episode.to_dict()), 201


@bp.route('/upload-audio', methods=['POST'])
def upload_audio():
    """
    Upload audio file.
    Returns: JSON with { "file_url": "/stream/<id>", "file_path": "generated_filename.mp3" }
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and allowed_file(file.filename):
        # Generate unique filename to avoid overwrites
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4()}.{ext}"
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Return the relative path (used later in metadata)
        return jsonify({
            "file_path": filename,  # e.g. "123e4567-e89b-12d3-a456-426614174000.mp3"
            "file_url": f"/stream/{filename}"  # Optional hint for frontend
        }), 201
    
    return jsonify({"error": "Invalid file type"}), 400

# ------------------- Editfields Endpoints -----------------------

# Add category to an existing episode (after upload)
@bp.route('/episode/<int:episode_id>/category', methods=['POST'])
@jwt_required()  # optional – if you want only logged-in users to set category
def set_episode_category(episode_id):
    episode = Episode.query.get_or_404(episode_id)
    data = request.json
    
    if not data or 'category' not in data:
        abort(400, description="Missing 'category' in JSON body")
    
    episode.category = data['category'].strip()[:25]  # max 25 char in name
    db.session.commit()
    
    return jsonify({
        "message": "Category updated",
        "episode_id": episode.id,
        "category": episode.category
    }), 200


"""
::::::::::::::::'########::'##::::'##:'########:::::::::::::::::
:::::::::::::::: ##.... ##: ##:::: ##:... ##..::::::::::::::::::
:::::::::::::::: ##:::: ##: ##:::: ##:::: ##::::::::::::::::::::
:::::::::::::::: ########:: ##:::: ##:::: ##::::::::::::::::::::
:::::::::::::::: ##.....::: ##:::: ##:::: ##::::::::::::::::::::
:::::::::::::::: ##:::::::: ##:::: ##:::: ##::::::::::::::::::::
:::::::::::::::: ##::::::::. #######::::: ##::::::::::::::::::::
::::::::::::::::..::::::::::.......::::::..:::::::::::::::::::::
"""

# Optional: Update multiple fields including category (full edit)
@bp.route('/episode/<int:episode_id>', methods=['PUT'])
@jwt_required()
def update_episode(episode_id):
    episode = Episode.query.get_or_404(episode_id)
    data = request.json
    
    if not data:
        abort(400, description="No data provided")
    
    if 'title' in data:
        episode.title = data['title']
    if 'description' in data:
        episode.description = data['description']
    if 'category' in data:
        episode.category = data['category'].strip()[:100]
    # add more fields if needed
    
    db.session.commit()
    
    return jsonify(episode.to_dict()), 200

@bp.route('/collections/<int:collection_id>', methods=['PUT'])
@jwt_required()
def update_collection(collection_id):
    collection = Collection.query.get_or_404(collection_id)
    current_user_id = get_jwt_identity()

    if collection.user_id != int(current_user_id):
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    if not data:
        abort(400, description="No data provided")

    if 'name' in data:
        collection.name = data['name']
    if 'description' in data:
        collection.description = data['description']
    if 'creator_name' in data:
        collection.creator_name = data['creator_name']

    db.session.commit()
    return jsonify(collection.to_dict()), 200


@bp.route('/collections/<int:collection_id>', methods=['DELETE'])
@jwt_required()
def delete_collection(collection_id):
    collection = Collection.query.get_or_404(collection_id)
    current_user_id = get_jwt_identity()
    requesting_user = User.query.get(int(current_user_id))

    if collection.user_id != int(current_user_id) and requesting_user.role != 'admin':
        return jsonify({"error": "Unauthorized"}), 403

    Episode.query.filter_by(collection_id=collection_id).delete()

    db.session.delete(collection)
    db.session.commit()
    return jsonify({"message": "Collection deleted"}), 200


""" 
:::'###::::'##::::'##:'########:'##::::'##:
::'## ##::: ##:::: ##:... ##..:: ##:::: ##:
:'##:. ##:: ##:::: ##:::: ##:::: ##:::: ##:
'##:::. ##: ##:::: ##:::: ##:::: #########:
 #########: ##:::: ##:::: ##:::: ##.... ##:
 ##.... ##: ##:::: ##:::: ##:::: ##:::: ##:
 ##:::: ##:. #######::::: ##:::: ##:::: ##:
..:::::..:::.......::::::..:::::..:::::..::
"""
# Register
@bp.route('/register', methods=['POST'])
def register():
    data = request.json
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({"error": "Missing username or password"}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"error": "Username already taken"}), 400
    
    user = User(
        username=data['username'],
        password_hash=hash_password(data['password'])
    )
    db.session.add(user)
    db.session.commit()
    
    return jsonify({"message": "User registered"}), 201

# Login
@bp.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data.get('username')).first()
    
    if not user or not check_password(user.password_hash, data.get('password')):
        return jsonify({"error": "Invalid credentials"}), 401
    
    # Create tokens
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    
    response = jsonify({"message": "Logged in"})
    
    # Set tokens in cookies
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)
    
    return response, 200

# Logout
@bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    response = jsonify({"message": "Logged out"})
    unset_jwt_cookies(response)
    return response, 200

# Refresh token endpoint
@bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    current_user_id = get_jwt_identity()
    access_token = create_access_token(identity=current_user_id)
    
    response = jsonify({"message": "Token refreshed"})
    set_access_cookies(response, access_token)
    return response, 200

@bp.route('/me', methods=['GET'])
@jwt_required(optional=True)
def me():
    user_id = get_jwt_identity()
    if user_id is None:
        return jsonify(None), 200 
        
    user = User.query.get(int(user_id))
    if not user:
        return jsonify(None), 200
        
    return jsonify({"id": user.id, "username": user.username, "role": user.role}), 200

# ------------------- Admin Endpoints ----------------------------

@bp.route('/users', methods=['GET'])
@jwt_required()
def get_all_users():
    current_user_id = get_jwt_identity()
    admin_user = User.query.get(int(current_user_id))

    if not admin_user or admin_user.role != 'admin':
        return jsonify({"error": "Admin privileges required"}), 403

    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    
    pagination = User.query.paginate(page=page, per_page=limit, error_out=False)
    users = pagination.items

    return jsonify({
        "users": [
            {
                "id": u.id, 
                "username": u.username, 
                "role": u.role,
            } for u in users
        ],
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": pagination.page
    }), 200

@bp.route('/users', methods=['POST'])
@jwt_required()
def admin_add_user():
    """
    Admin-only: Create a new user with a specific role.
    """
    current_user_id = get_jwt_identity()
    admin_user = User.query.get(int(current_user_id))

    if not admin_user or admin_user.role != 'admin':
        return jsonify({"error": "Admin privileges required"}), 403

    data = request.json
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({"error": "Username and password required"}), 400

    if User.query.filter_by(username=data['username']).first():
        return jsonify({"error": "Username already exists"}), 400

    new_user = User(
        username=data['username'],
        password_hash=hash_password(data['password']),
        role=data.get('role', 'user') 
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({"message": "User created successfully", "user": {"id": new_user.id, "username": new_user.username, "role": new_user.role}}), 201


@bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def admin_edit_user(user_id):
    current_user_id = get_jwt_identity()
    admin_user = User.query.get(int(current_user_id))

    if not admin_user or admin_user.role != 'admin':
        return jsonify({"error": "Admin privileges required"}), 403

    target_user = User.query.get_or_404(user_id)
    data = request.json

    if 'username' in data:
        existing = User.query.filter_by(username=data['username']).first()
        if existing and existing.id != target_user.id:
            return jsonify({"error": "Username already taken"}), 400
        target_user.username = data['username']

    if 'role' in data:
        target_user.role = data['role']

    if 'password' in data:
        target_user.password_hash = hash_password(data['password'])

    db.session.commit()
    
    return jsonify({
        "message": "User updated",
        "user": {"id": target_user.id, "username": target_user.username, "role": target_user.role}
    }), 200