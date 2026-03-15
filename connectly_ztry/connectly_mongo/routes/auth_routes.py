
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from flask_bcrypt import generate_password_hash
from flask import current_app
def _db():
    return current_app.mongo.db
from datetime import datetime
from bson import ObjectId

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        doc = _db().users.find_one({'username': username})
        if doc:
            from flask import current_app
            u = current_app.MongoUser(doc)
            if u.check_password(password):
                login_user(u, remember=True)
                _db().users.update_one({'_id': doc['_id']}, {'$set': {'is_online': True}})
                return redirect(url_for('main.home'))
        flash('Invalid username or password', 'error')
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET','POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    if request.method == 'POST':
        username  = request.form.get('username','').strip()
        password  = request.form.get('password','')
        email     = request.form.get('email','').strip()
        gender    = request.form.get('gender','')
        bio       = request.form.get('bio','').strip()
        location  = request.form.get('location','').strip()
        goal      = request.form.get('relationship_goal','')
        study     = request.form.get('study_field','').strip()
        interests = [i.strip() for i in request.form.get('interests','').split(',') if i.strip()]

        if _db().users.find_one({'username': username}):
            flash('Username already taken', 'error')
            return render_template('register.html')

        doc = {
            'username': username,
            'email': email,
            'password_hash': generate_password_hash(password).decode('utf-8'),
            'gender': gender, 'bio': bio, 'location': location,
            'relationship_goal': goal, 'study_field': study,
            'interests': interests,
            'profile_picture': None, 'banner_picture': None,
            'followers': [], 'following': [],
            'is_online': True, 'last_seen': datetime.utcnow(),
            'created_at': datetime.utcnow()
        }
        result = _db().users.insert_one(doc)
        doc['_id'] = result.inserted_id
        from flask import current_app
        u = current_app.MongoUser(doc)
        login_user(u)
        flash('Welcome to Connectly! 🎉', 'success')
        return redirect(url_for('main.home'))
    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    _db().users.update_one(
        {'_id': ObjectId(current_user.id)},
        {'$set': {'is_online': False, 'last_seen': datetime.utcnow()}}
    )
    logout_user()
    return redirect(url_for('auth.login'))
