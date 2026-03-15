import os
from dotenv import load_dotenv
load_dotenv()

BASE = os.path.dirname(__file__)

# On Render, uploaded files go to a mounted disk
# The disk is mounted at /opt/render/project/src/.../static/uploads
UPLOAD_BASE = os.environ.get('UPLOAD_DIR', os.path.join(BASE, 'static', 'uploads'))

class Config:
    SECRET_KEY         = os.environ.get('SECRET_KEY', 'ztry-change-in-production-please')
    MONGO_URI          = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/ztry')
    UPLOAD_FOLDER      = UPLOAD_BASE
    UPLOAD_POSTS       = os.path.join(UPLOAD_BASE, 'posts')
    UPLOAD_PROFILES    = os.path.join(UPLOAD_BASE, 'profiles')
    UPLOAD_BANNERS     = os.path.join(UPLOAD_BASE, 'banners')
    UPLOAD_STORIES     = os.path.join(UPLOAD_BASE, 'stories')
    MAX_CONTENT_LENGTH = 128 * 1024 * 1024   # 128 MB
    GROQ_API_KEY       = os.environ.get('GROQ_API_KEY', '')
    GEMINI_API_KEY     = os.environ.get('GEMINI_API_KEY', '')
    OPENAI_API_KEY     = os.environ.get('OPENAI_API_KEY', '')
    DEBUG              = False

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG                            = False
    SESSION_COOKIE_SECURE            = True
    SESSION_COOKIE_HTTPONLY          = True
    SESSION_COOKIE_SAMESITE          = 'Lax'
    PREFERRED_URL_SCHEME             = 'https'

config = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'default':     DevelopmentConfig
}
