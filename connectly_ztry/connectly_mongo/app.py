import os, logging
from flask import Flask
from flask_socketio import SocketIO
from flask_login import LoginManager
from flask_bcrypt import Bcrypt

socketio  = SocketIO()
login_mgr = LoginManager()
bcrypt    = Bcrypt()

def create_app(cfg='development'):
    app = Flask(__name__)

    # ── Load config ───────────────────────────────────────────────────────────
    from config import config
    app.config.from_object(config[cfg])

    # ── Print which MongoDB URI we're using ───────────────────────────────────
    uri = app.config.get('MONGO_URI', '')
    if not uri:
        print('\n❌  MONGO_URI is empty in your .env file!')
        print('Add this line to your .env:\n  MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/connectly\n')
        raise SystemExit(1)
    masked = uri[:30] + '...' if len(uri) > 30 else uri
    print(f'[MongoDB] Connecting to: {masked}')

    # ── Create upload dirs ────────────────────────────────────────────────────
    for d in ['UPLOAD_POSTS','UPLOAD_PROFILES','UPLOAD_BANNERS','UPLOAD_STORIES']:
        os.makedirs(app.config[d], exist_ok=True)

    # ── Init extensions ───────────────────────────────────────────────────────
    from flask_pymongo import PyMongo
    mongo = PyMongo()
    mongo.init_app(app)
    app.mongo = mongo

    bcrypt.init_app(app)
    login_mgr.init_app(app)

    socketio.init_app(
        app,
        cors_allowed_origins='*',
        async_mode='gevent',
        ping_timeout=60,
        ping_interval=25,
        max_http_buffer_size=10_000_000,
        logger=False,
        engineio_logger=False,
    )
    login_mgr.login_view = 'auth.login'
    login_mgr.login_message_category = 'info'

    # ── Test connection ───────────────────────────────────────────────────────
    with app.app_context():
        try:
            mongo.db.client.admin.command('ping')
            print('[MongoDB] ✅ Connected successfully!')
        except Exception as e:
            print(f'\n❌  Cannot reach MongoDB: {e}')
            print('Check your MONGO_URI in .env and make sure Atlas cluster is RESUMED\n')
            raise SystemExit(1)

    # ── MongoUser class ───────────────────────────────────────────────────────
    from bson import ObjectId
    from flask_login import UserMixin

    class MongoUser(UserMixin):
        def __init__(self, doc):
            self.id               = str(doc['_id'])
            self.username         = doc.get('username', '')
            self.email            = doc.get('email', '')
            self.password_hash    = doc.get('password_hash', '')
            self.gender           = doc.get('gender', '')
            self.bio              = doc.get('bio', '')
            self.profile_picture  = doc.get('profile_picture')
            self.banner_picture   = doc.get('banner_picture')
            self.location         = doc.get('location', '')
            self.relationship_goal= doc.get('relationship_goal', '')
            self.study_field      = doc.get('study_field', '')
            self.website          = doc.get('website', '')
            self.interests        = doc.get('interests', [])
            self.followers        = doc.get('followers', [])
            self.following        = doc.get('following', [])
            self.is_online        = doc.get('is_online', False)
            self.last_seen        = doc.get('last_seen')
            self.created_at       = doc.get('created_at')

        def check_password(self, password):
            return bcrypt.check_password_hash(self.password_hash, password)

        def avatar_url(self):
            return f'/static/uploads/profiles/{self.profile_picture}' if self.profile_picture else None

        def banner_url(self):
            return f'/static/uploads/banners/{self.banner_picture}' if self.banner_picture else None

        def to_dict(self):
            return {
                'id': self.id, 'username': self.username,
                'bio': self.bio, 'location': self.location,
                'profile_picture': self.avatar_url(),
                'relationship_goal': self.relationship_goal,
                'is_online': self.is_online,
                'interests': self.interests
            }

    app.MongoUser = MongoUser

    @login_mgr.user_loader
    def load_user(user_id):
        try:
            doc = app.mongo.db.users.find_one({'_id': ObjectId(user_id)})
            return MongoUser(doc) if doc else None
        except Exception:
            return None

    # ── Register blueprints ───────────────────────────────────────────────────
    from routes.auth_routes import auth_bp
    from routes.post_routes import main_bp
    from routes.user_routes import user_bp
    from routes.chat_routes import chat_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(chat_bp)

    # ── Socket events ─────────────────────────────────────────────────────────
    from sockets.chat_socket import register_socket_events
    register_socket_events(socketio)

    # ── Indexes + seed ────────────────────────────────────────────────────────
    with app.app_context():
        _setup_indexes(mongo)
        _seed_data(mongo)

    # Auto-cleanup orphan media records on startup
    with app.app_context():
        _cleanup_orphans(mongo)
    
    logging.basicConfig(level=logging.WARNING)
    return app


def _setup_indexes(mongo):
    try:
        mongo.db.users.create_index('username', unique=True)
        mongo.db.users.create_index('email')
        mongo.db.posts.create_index([('timestamp', -1)])
        mongo.db.posts.create_index('user_id')
        mongo.db.messages.create_index([('sender_id',1),('receiver_id',1)])
        mongo.db.messages.create_index([('timestamp', 1)])
        mongo.db.matches.create_index([('user1_id',1),('user2_id',1)])
        mongo.db.notifications.create_index([('user_id',1),('is_read',1)])
        mongo.db.stories.create_index('expires_at', expireAfterSeconds=0)
        print('[MongoDB] ✅ Indexes ready')
    except Exception as e:
        print(f'[MongoDB] Index note: {e}')


def _seed_data(mongo):
    try:
        if mongo.db.users.count_documents({}) > 0:
            count = mongo.db.users.count_documents({})
            print(f'[MongoDB] ✅ Database ready ({count} users)')
            return
        from datetime import datetime
        from flask_bcrypt import generate_password_hash
        demo_users = [
            {'username':'alex_dev',    'gender':'Male',   'location':'San Francisco',
             'bio':'Full-stack dev passionate about AI',
             'relationship_goal':'Networking','study_field':'Computer Science',
             'interests':['Python','AI','Startups']},
            {'username':'priya_math',  'gender':'Female', 'location':'New York',
             'bio':'Math enthusiast and ML researcher',
             'relationship_goal':'Study partner','study_field':'Mathematics',
             'interests':['Mathematics','AI','Machine Learning']},
            {'username':'jake_startup','gender':'Male',   'location':'Austin',
             'bio':'Building the next unicorn startup',
             'relationship_goal':'Networking','study_field':'Business',
             'interests':['Startups','Business','Technology']},
            {'username':'sofia_art',   'gender':'Female', 'location':'Paris',
             'bio':'Artist meets coder — bringing creativity to tech',
             'relationship_goal':'Friendship','study_field':'Design',
             'interests':['Art','Technology','Python']},
            {'username':'raj_data',    'gender':'Male',   'location':'Bangalore',
             'bio':'Data scientist by day, gamer by night',
             'relationship_goal':'Networking','study_field':'Data Science',
             'interests':['Python','Machine Learning','Gaming']},
        ]
        for ud in demo_users:
            ud.update({
                'password_hash':   generate_password_hash('demo123').decode('utf-8'),
                'email':           f"{ud['username']}@demo.com",
                'profile_picture': None,
                'banner_picture':  None,
                'followers':       [],
                'following':       [],
                'is_online':       False,
                'last_seen':       datetime.utcnow(),
                'created_at':      datetime.utcnow()
            })
            mongo.db.users.insert_one(ud)
        print('[MongoDB] ✅ 5 demo users seeded (password: demo123)')
    except Exception as e:
        print(f'[MongoDB] Seed note: {e}')



def _cleanup_orphans(mongo):
    """Remove posts/stories where media file is missing from disk."""
    import os
    from flask import current_app
    try:
        posts_dir   = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'posts')
        stories_dir = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'stories')
        
        cleaned_posts = 0
        for post in mongo.db.posts.find({'media_url': {'$nin': [None, '']}}):
            fpath = os.path.join(posts_dir, post['media_url'])
            if not os.path.exists(fpath):
                # File missing — clear media fields, keep text
                mongo.db.posts.update_one(
                    {'_id': post['_id']},
                    {'$set': {'media_url': None, 'media_type': None, 'post_type': 'text'}}
                )
                cleaned_posts += 1
        
        cleaned_stories = 0
        for story in mongo.db.stories.find({}):
            fpath = os.path.join(stories_dir, story.get('media_url', ''))
            if not os.path.exists(fpath):
                mongo.db.stories.delete_one({'_id': story['_id']})
                cleaned_stories += 1
        
        if cleaned_posts or cleaned_stories:
            print(f'[MongoDB] ✅ Cleaned {cleaned_posts} orphan posts, {cleaned_stories} orphan stories')
        else:
            print('[MongoDB] ✅ No orphan media found')
    except Exception as e:
        print(f'[MongoDB] Cleanup note: {e}')
# Create global app instance for Gunicorn
app = create_app(os.getenv("FLASK_ENV", "development"))

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
