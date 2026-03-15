import os, uuid
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from models.db_utils import oid, str_id, str_ids, now
from bson import ObjectId
from datetime import datetime, timedelta

main_bp = Blueprint('main', __name__)

ALLOWED_IMG = {'png','jpg','jpeg','gif','webp'}
ALLOWED_VID = {'mp4','mov','webm','ogg','avi'}

def _db():
    return current_app.mongo.db

def save_media(file, folder):
    """Save image or video, return (filename, media_type) or (None, None)."""
    if not file or not file.filename:
        return None, None
    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext in ALLOWED_IMG:
        mtype = 'image'
    elif ext in ALLOWED_VID:
        mtype = 'video'
    else:
        return None, None
    fname = f"{uuid.uuid4().hex}.{ext}"
    os.makedirs(folder, exist_ok=True)
    file.save(os.path.join(folder, fname))
    return fname, mtype

def save_img(file, folder):
    """Save image only, return filename or None."""
    if not file or not file.filename:
        return None
    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED_IMG:
        return None
    fname = f"{uuid.uuid4().hex}.{ext}"
    os.makedirs(folder, exist_ok=True)
    file.save(os.path.join(folder, fname))
    return fname

# ── HOME ─────────────────────────────────────────────────────────────────────
@main_bp.route('/')
@main_bp.route('/home')
@login_required
def home():
    page  = request.args.get('page', 1, type=int)
    limit = 10
    skip  = (page - 1) * limit
    total = _db().posts.count_documents({})
    posts = str_ids(list(_db().posts.find({}).sort('timestamp', -1).skip(skip).limit(limit)))
    has_next = (skip + limit) < total
    has_prev = page > 1
    # Active stories (not expired)
    active_stories = str_ids(list(
        _db().stories.find({'expires_at': {'$gt': datetime.utcnow()}})
        .sort('created_at', -1).limit(30)
    ))
    return render_template('home.html', posts=posts,
        page=page, has_next=has_next, has_prev=has_prev,
        next_num=page+1, prev_num=page-1,
        active_stories=active_stories)

# ── CREATE POST ───────────────────────────────────────────────────────────────
@main_bp.route('/post/create', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        file    = request.files.get('media')
        fname, mtype = save_media(file, current_app.config['UPLOAD_POSTS'])
        if not content and not fname:
            flash('Post needs text or a photo/video', 'error')
            return redirect(url_for('main.create_post'))
        _db().posts.insert_one({
            'user_id':    current_user.id,
            'username':   current_user.username,
            'user_pic':   current_user.profile_picture,  # filename stored permanently
            'content':    content,
            'media_url':  fname,
            'media_type': mtype,
            'post_type':  mtype or 'text',
            'likes':      [],
            'comments':   [],
            'timestamp':  now()
        })
        flash('Post shared! ✨', 'success')
        return redirect(url_for('main.home'))
    return render_template('post_create.html')

# ── LIKE ──────────────────────────────────────────────────────────────────────
@main_bp.route('/post/<post_id>/like', methods=['POST'])
@login_required
def like_post(post_id):
    post = _db().posts.find_one({'_id': oid(post_id)})
    if not post:
        return jsonify({'error': 'not found'}), 404
    uid = current_user.id
    if uid in post.get('likes', []):
        _db().posts.update_one({'_id': oid(post_id)}, {'$pull': {'likes': uid}})
        liked = False
    else:
        _db().posts.update_one({'_id': oid(post_id)}, {'$addToSet': {'likes': uid}})
        liked = True
        if post['user_id'] != uid:
            _db().notifications.insert_one({
                'user_id':    post['user_id'],
                'type':       'like',
                'content':    f"{current_user.username} liked your post",
                'related_id': post_id,
                'is_read':    False,
                'timestamp':  now()
            })
    updated = _db().posts.find_one({'_id': oid(post_id)})
    return jsonify({'liked': liked, 'count': len(updated.get('likes', []))})

# ── COMMENT ───────────────────────────────────────────────────────────────────
@main_bp.route('/post/<post_id>/comment', methods=['POST'])
@login_required
def comment_post(post_id):
    content = request.form.get('content', '').strip()
    if not content:
        return redirect(url_for('main.home'))
    comment = {
        '_id':       str(ObjectId()),
        'user_id':   current_user.id,
        'username':  current_user.username,
        'user_pic':  current_user.profile_picture,
        'content':   content,
        'timestamp': now()
    }
    _db().posts.update_one({'_id': oid(post_id)}, {'$push': {'comments': comment}})
    post = _db().posts.find_one({'_id': oid(post_id)})
    if post and post['user_id'] != current_user.id:
        _db().notifications.insert_one({
            'user_id':    post['user_id'],
            'type':       'comment',
            'content':    f"{current_user.username} commented on your post",
            'related_id': post_id,
            'is_read':    False,
            'timestamp':  now()
        })
    return redirect(url_for('main.home'))

# ── DELETE POST ───────────────────────────────────────────────────────────────
@main_bp.route('/post/<post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = _db().posts.find_one({'_id': oid(post_id)})
    if not post:
        return jsonify({'error': 'not found'}), 404
    if post['user_id'] != current_user.id:
        return jsonify({'error': 'forbidden'}), 403
    # Delete media file from disk
    if post.get('media_url'):
        try:
            os.remove(os.path.join(current_app.config['UPLOAD_POSTS'], post['media_url']))
        except Exception:
            pass
    _db().posts.delete_one({'_id': oid(post_id)})
    return jsonify({'success': True})

# ── STORIES ───────────────────────────────────────────────────────────────────
@main_bp.route('/story/create', methods=['POST'])
@login_required
def create_story():
    file    = request.files.get('story_media')
    caption = request.form.get('caption', '').strip()
    fname, mtype = save_media(file, current_app.config['UPLOAD_STORIES'])
    if not fname:
        flash('Please select an image or video for your story', 'error')
        return redirect(url_for('main.home'))
    _db().stories.insert_one({
        'user_id':    current_user.id,
        'username':   current_user.username,
        'user_pic':   current_user.profile_picture,
        'media_url':  fname,
        'media_type': mtype,
        'caption':    caption,
        'viewers':    [],
        'expires_at': datetime.utcnow() + timedelta(hours=24),
        'created_at': now()
    })
    flash('Story posted! Disappears in 24 hours ✨', 'success')
    return redirect(url_for('main.home'))

@main_bp.route('/story/<story_id>/view', methods=['POST'])
@login_required
def view_story(story_id):
    _db().stories.update_one(
        {'_id': oid(story_id)},
        {'$addToSet': {'viewers': current_user.id}}
    )
    return jsonify({'success': True})

# ── NOTIFICATIONS ─────────────────────────────────────────────────────────────
@main_bp.route('/notifications')
@login_required
def notifications():
    notifs = str_ids(list(
        _db().notifications.find({'user_id': current_user.id})
        .sort('timestamp', -1).limit(50)
    ))
    _db().notifications.update_many(
        {'user_id': current_user.id, 'is_read': False},
        {'$set': {'is_read': True}}
    )
    return render_template('notifications.html', notifications=notifs)

@main_bp.route('/api/notifications/count')
@login_required
def notif_count():
    count = _db().notifications.count_documents({'user_id': current_user.id, 'is_read': False})
    return jsonify({'count': count})

@main_bp.route('/api/unread')
@login_required
def unread_count():
    count = _db().messages.count_documents({'receiver_id': current_user.id, 'is_read': False})
    return jsonify({'count': count})

# ── CLEANUP ORPHAN MEDIA POSTS ────────────────────────────────────────────────
@main_bp.route('/api/cleanup-orphans', methods=['POST'])
@login_required
def cleanup_orphans():
    """Remove posts/stories where media file no longer exists on disk."""
    if not current_user.is_online:  # basic auth check
        return jsonify({'error': 'unauthorized'}), 403
    
    POSTS_DIR   = current_app.config['UPLOAD_POSTS']
    STORIES_DIR = current_app.config['UPLOAD_STORIES']
    
    removed_posts   = 0
    removed_stories = 0
    
    # Check posts
    for post in _db().posts.find({'media_url': {'$ne': None}}):
        fpath = os.path.join(POSTS_DIR, post['media_url'])
        if not os.path.exists(fpath):
            # File missing — clear media from this post (keep text content)
            _db().posts.update_one(
                {'_id': post['_id']},
                {'$set': {'media_url': None, 'media_type': None}}
            )
            removed_posts += 1
    
    # Check stories
    for story in _db().stories.find({}):
        fpath = os.path.join(STORIES_DIR, story.get('media_url', ''))
        if not os.path.exists(fpath):
            _db().stories.delete_one({'_id': story['_id']})
            removed_stories += 1
    
    return jsonify({
        'success': True,
        'posts_cleaned': removed_posts,
        'stories_cleaned': removed_stories,
        'message': f"Cleaned {removed_posts} posts and {removed_stories} stories"
    })
