
import os, uuid
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from flask import current_app
def _db():
    return current_app.mongo.db
from models.db_utils import oid, str_id, str_ids, now
from bson import ObjectId

user_bp = Blueprint('users', __name__)

ALLOWED_IMG = {'png','jpg','jpeg','gif','webp'}

def save_img(file, folder):
    if not file or not file.filename: return None
    ext = file.filename.rsplit('.',1)[-1].lower()
    if ext not in ALLOWED_IMG: return None
    fname = f"{uuid.uuid4().hex}.{ext}"
    os.makedirs(folder, exist_ok=True)
    file.save(os.path.join(folder, fname))
    return fname

@user_bp.route('/profile/<user_id>')
@login_required
def profile(user_id):
    doc = _db().users.find_one({'_id': oid(user_id)})
    if not doc: return 'User not found', 404
    user = str_id(doc)
    is_matched = _db().matches.find_one({'$or':[
        {'user1_id': current_user.id, 'user2_id': user_id},
        {'user1_id': user_id, 'user2_id': current_user.id}
    ]})
    user_posts = str_ids(list(
        _db().posts.find({'user_id': user_id}).sort('timestamp',-1)
    ))
    return render_template('profile.html', user=user, is_matched=is_matched, user_posts=user_posts)

@user_bp.route('/profile/edit', methods=['GET','POST'])
@login_required
def edit_profile():
    from flask import current_app
    if request.method == 'POST':
        updates = {
            'bio':               request.form.get('bio','').strip(),
            'location':          request.form.get('location','').strip(),
            'gender':            request.form.get('gender',''),
            'relationship_goal': request.form.get('relationship_goal',''),
            'study_field':       request.form.get('study_field','').strip(),
            'website':           request.form.get('website','').strip(),
            'interests': [i.strip() for i in request.form.get('interests_text','').split(',') if i.strip()]
        }
        # Profile picture upload
        pf = request.files.get('profile_picture')
        if pf and pf.filename:
            fname = save_img(pf, current_app.config['UPLOAD_PROFILES'])
            if fname:
                if current_user.profile_picture:
                    try: os.remove(os.path.join(current_app.config['UPLOAD_PROFILES'], current_user.profile_picture))
                    except: pass
                updates['profile_picture'] = fname
                # Update user_pic on all their posts
                _db().posts.update_many({'user_id': current_user.id}, {'$set': {'user_pic': fname}})

        # Banner picture upload
        bf = request.files.get('banner_picture')
        if bf and bf.filename:
            fname = save_img(bf, current_app.config['UPLOAD_BANNERS'])
            if fname:
                if current_user.banner_picture:
                    try: os.remove(os.path.join(current_app.config['UPLOAD_BANNERS'], current_user.banner_picture))
                    except: pass
                updates['banner_picture'] = fname

        _db().users.update_one({'_id': oid(current_user.id)}, {'$set': updates})
        flash('Profile updated!', 'success')
        return redirect(url_for('users.profile', user_id=current_user.id))
    return render_template('edit_profile.html', user=current_user)

@user_bp.route('/explore')
@login_required
def explore():
    search = request.args.get('q','').strip()
    gender = request.args.get('gender','')
    goal   = request.args.get('goal','')
    query  = {'_id': {'$ne': oid(current_user.id)}}
    if search: query['username'] = {'$regex': search, '$options': 'i'}
    if gender: query['gender'] = gender
    if goal:   query['relationship_goal'] = goal
    users = str_ids(list(_db().users.find(query).limit(50)))
    return render_template('explore.html', users=users)

@user_bp.route('/match/<user_id>', methods=['POST'])
@login_required
def match_user(user_id):
    existing = _db().matches.find_one({'$or':[
        {'user1_id': current_user.id, 'user2_id': user_id},
        {'user1_id': user_id, 'user2_id': current_user.id}
    ]})
    if existing: return jsonify({'error':'Already matched'}), 400

    other = _db().users.find_one({'_id': oid(user_id)})
    if not other: return jsonify({'error':'User not found'}), 404

    # Compute match score
    my_ints    = set(current_user.interests)
    their_ints = set(other.get('interests',[]))
    shared = my_ints & their_ints
    score  = round((len(shared)/max(len(my_ints|their_ints),1))*100, 1) if (my_ints or their_ints) else 0

    _db().matches.insert_one({
        'user1_id': current_user.id, 'user2_id': user_id,
        'match_score': score, 'status': 'accepted',
        'ai_intro_sent': False, 'created_at': now()
    })
    _db().notifications.insert_one({
        'user_id': user_id, 'type': 'match',
        'content': f"{current_user.username} connected with you! Match score: {score}%",
        'related_id': current_user.id, 'is_read': False, 'timestamp': now()
    })
    return jsonify({'success': True, 'score': score})

@user_bp.route('/follow/<user_id>', methods=['POST'])
@login_required
def follow_user(user_id):
    is_following = user_id in current_user.following
    if is_following:
        _db().users.update_one({'_id': oid(current_user.id)}, {'$pull': {'following': user_id}})
        _db().users.update_one({'_id': oid(user_id)}, {'$pull': {'followers': current_user.id}})
        return jsonify({'following': False})
    else:
        _db().users.update_one({'_id': oid(current_user.id)}, {'$addToSet': {'following': user_id}})
        _db().users.update_one({'_id': oid(user_id)}, {'$addToSet': {'followers': current_user.id}})
        _db().notifications.insert_one({
            'user_id': user_id, 'type': 'follow',
            'content': f"{current_user.username} started following you",
            'related_id': current_user.id, 'is_read': False, 'timestamp': now()
        })
        return jsonify({'following': True})
