
from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from flask import current_app
def _db():
    return current_app.mongo.db
from models.db_utils import oid, str_id, str_ids, now
from bson import ObjectId

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/messages')
@login_required
def messages():
    # Get all unique users this user has chatted with
    sent     = _db().messages.distinct('receiver_id', {'sender_id': current_user.id})
    received = _db().messages.distinct('sender_id',   {'receiver_id': current_user.id})
    other_ids = list(set(sent + received) - {current_user.id})

    conversations = []
    for uid in other_ids:
        u = _db().users.find_one({'_id': oid(uid)})
        if not u: continue
        last = _db().messages.find_one(
            {'$or': [
                {'sender_id': current_user.id, 'receiver_id': uid},
                {'sender_id': uid, 'receiver_id': current_user.id}
            ]}, sort=[('timestamp', -1)]
        )
        unread = _db().messages.count_documents({
            'sender_id': uid, 'receiver_id': current_user.id, 'is_read': False
        })
        conversations.append({
            'user': str_id(u),
            'last_msg': str_id(last) if last else None,
            'unread': unread
        })
    conversations.sort(key=lambda x: x['last_msg']['timestamp'] if x['last_msg'] else '', reverse=True)

    # Matched users not yet messaged
    matches = list(_db().matches.find({'$or':[
        {'user1_id': current_user.id},{'user2_id': current_user.id}
    ], 'status':'accepted'}))
    matched_users = []
    for m in matches:
        uid = m['user2_id'] if m['user1_id']==current_user.id else m['user1_id']
        if uid not in other_ids:
            u = _db().users.find_one({'_id': oid(uid)})
            if u: matched_users.append(str_id(u))

    return render_template('messages.html', conversations=conversations, matched_users=matched_users)

@chat_bp.route('/chat/<user_id>')
@login_required
def chat(user_id):
    other_doc = _db().users.find_one({'_id': oid(user_id)})
    if not other_doc: return 'User not found', 404
    other_user = str_id(other_doc)

    msgs = str_ids(list(_db().messages.find({'$or':[
        {'sender_id': current_user.id, 'receiver_id': user_id},
        {'sender_id': user_id, 'receiver_id': current_user.id}
    ]}).sort('timestamp', 1)))

    # Mark as read
    _db().messages.update_many(
        {'sender_id': user_id, 'receiver_id': current_user.id, 'is_read': False},
        {'$set': {'is_read': True}}
    )

    # AI intro on first open of a match
    match = _db().matches.find_one({'$or':[
        {'user1_id': current_user.id, 'user2_id': user_id},
        {'user1_id': user_id, 'user2_id': current_user.id}
    ]})
    ai_intro = None
    if match and not match.get('ai_intro_sent') and len(msgs) == 0:
        try:
            from services.ai_host import get_intro_message
            my_ints    = current_user.interests
            their_ints = other_doc.get('interests', [])
            shared = list(set(my_ints) & set(their_ints))
            goals  = list({g for g in [current_user.relationship_goal, other_doc.get('relationship_goal')] if g})
            ai_intro = get_intro_message(current_user.username, other_user['username'], shared, goals)
            _db().matches.update_one({'_id': match['_id']}, {'$set': {'ai_intro_sent': True}})
        except Exception as e:
            print(f'[AI intro error] {e}')

    return render_template('chat.html', other_user=other_user, messages=msgs, ai_intro=ai_intro)

@chat_bp.route('/api/messages/<user_id>')
@login_required
def get_messages(user_id):
    msgs = str_ids(list(_db().messages.find({'$or':[
        {'sender_id': current_user.id, 'receiver_id': user_id},
        {'sender_id': user_id, 'receiver_id': current_user.id}
    ]}).sort('timestamp',1)))
    for m in msgs:
        if 'timestamp' in m and hasattr(m['timestamp'],'isoformat'):
            m['timestamp'] = m['timestamp'].isoformat()
    return jsonify(msgs)
