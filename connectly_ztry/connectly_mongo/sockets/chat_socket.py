
from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
from flask import current_app
def _db():
    return current_app.mongo.db
from models.db_utils import oid, str_id, now
from services.ai_host import get_ai_host_response
from datetime import datetime
import re

_conv_context = {}

# Match ALL names users might type: @ztry @zyra @spark @ai @bot @host @zai
_AI_PATTERN = re.compile(r'@(ztry|zyra|spark|zai|ai|bot|host)\b', re.IGNORECASE)

def register_socket_events(socketio):

    @socketio.on('connect')
    def on_connect():
        if current_user.is_authenticated:
            _db().users.update_one({'_id': oid(current_user.id)},{'$set':{'is_online':True}})
            join_room(f'user_{current_user.id}')
            emit('user_online',{'user_id':current_user.id}, broadcast=True, include_self=False)

    @socketio.on('disconnect')
    def on_disconnect():
        if current_user.is_authenticated:
            _db().users.update_one({'_id': oid(current_user.id)},{'$set':{'is_online':False,'last_seen':datetime.utcnow()}})
            emit('user_offline',{'user_id':current_user.id}, broadcast=True, include_self=False)

    @socketio.on('join_personal')
    def on_join_personal():
        if current_user.is_authenticated:
            join_room(f'user_{current_user.id}')

    @socketio.on('join_chat')
    def on_join(data):
        if not current_user.is_authenticated: return
        other_id = str(data.get('other_user_id',''))
        join_room(_room(current_user.id, other_id))

    @socketio.on('leave_chat')
    def on_leave(data):
        if not current_user.is_authenticated: return
        other_id = str(data.get('other_user_id',''))
        leave_room(_room(current_user.id, other_id))

    @socketio.on('send_message')
    def handle_message(data):
        if not current_user.is_authenticated: return
        receiver_id = str(data.get('receiver_id',''))
        content     = data.get('content','').strip()
        if not content or not receiver_id: return

        room     = _room(current_user.id, receiver_id)
        # Fix: catch ALL AI trigger words including @ztry, @zyra
        is_spark = bool(_AI_PATTERN.search(content))

        if is_spark:
            # Save to DB
            result = _db().messages.insert_one({
                'sender_id': current_user.id, 'receiver_id': receiver_id,
                'content': content, 'is_read': False, 'is_ai_intro': False,
                'timestamp': datetime.utcnow()
            })
            _push_context(room, current_user.username, content)
            # Confirm to sender only (shows as spark_trigger bubble)
            emit('receive_message', {
                'id': str(result.inserted_id),
                'sender_id': current_user.id,
                'content': content,
                'timestamp': datetime.utcnow().strftime('%H:%M'),
                'type': 'spark_trigger'
            })
            # Fire AI in background thread so socket doesn't block
            _fire_spark_async(socketio, content, room, current_user.id, receiver_id)
        else:
            # Normal message
            result = _db().messages.insert_one({
                'sender_id': current_user.id, 'receiver_id': receiver_id,
                'content': content, 'is_read': False, 'is_ai_intro': False,
                'timestamp': datetime.utcnow()
            })
            _db().notifications.insert_one({
                'user_id': receiver_id, 'type': 'message',
                'content': f"{current_user.username}: {content[:50]}",
                'related_id': current_user.id, 'is_read': False, 'timestamp': datetime.utcnow()
            })
            _push_context(room, current_user.username, content)
            emit('receive_message', {
                'id': str(result.inserted_id),
                'sender_id': current_user.id,
                'receiver_id': receiver_id,
                'sender_username': current_user.username,
                'content': content,
                'timestamp': datetime.utcnow().strftime('%H:%M'),
                'type': 'user', 'is_read': False
            }, room=room)
            emit('new_message_notification', {
                'from_user': current_user.username,
                'from_user_id': current_user.id,
                'content': content[:50]
            }, room=f'user_{receiver_id}')

    @socketio.on('ask_spark')
    def ask_spark(data):
        if not current_user.is_authenticated: return
        receiver_id = str(data.get('receiver_id',''))
        question    = data.get('question','Break the ice for us!').strip()
        label       = data.get('label','Quick question')
        room        = _room(current_user.id, receiver_id)
        emit('spark_button_used', {'by': current_user.username, 'label': label}, room=room)
        # Also fire in background thread
        _fire_spark_async(socketio, question, room, current_user.id, receiver_id)

    @socketio.on('typing')
    def handle_typing(data):
        if not current_user.is_authenticated: return
        receiver_id = str(data.get('receiver_id',''))
        room = _room(current_user.id, receiver_id)
        emit('user_typing',{'user_id':current_user.id,'username':current_user.username}, room=room, include_self=False)

    @socketio.on('stop_typing')
    def handle_stop(data):
        if not current_user.is_authenticated: return
        receiver_id = str(data.get('receiver_id',''))
        room = _room(current_user.id, receiver_id)
        emit('user_stop_typing',{'user_id':current_user.id}, room=room, include_self=False)

    @socketio.on('mark_read')
    def mark_read(data):
        if not current_user.is_authenticated: return
        sender_id = str(data.get('sender_id',''))
        _db().messages.update_many(
            {'sender_id': sender_id, 'receiver_id': current_user.id, 'is_read': False},
            {'$set': {'is_read': True}}
        )
        room = _room(current_user.id, sender_id)
        emit('messages_read', {'reader_id': current_user.id}, room=room)


def _fire_spark_async(socketio, trigger_msg, room, sender_id, receiver_id):
    """
    Run AI call in a background task compatible with eventlet/gevent/threading.
    socketio.start_background_task is the correct way with Flask-SocketIO.
    """
    app = current_app._get_current_object()

    def _run():
        with app.app_context():
            _fire_spark(socketio, trigger_msg, room, sender_id, receiver_id)

    socketio.start_background_task(_run)


def _fire_spark(socketio, trigger_msg, room, sender_id, receiver_id):
    try:
        db           = current_app.mongo.db
        sender_doc   = db.users.find_one({'_id': oid(sender_id)})
        receiver_doc = db.users.find_one({'_id': oid(receiver_id)})
        if not sender_doc or not receiver_doc:
            print(f'[AI] Could not find users: sender={sender_id} receiver={receiver_id}')
            return

        context = _conv_context.get(room, [])
        s_int   = sender_doc.get('interests', [])
        r_int   = receiver_doc.get('interests', [])
        goals   = list({g for g in [sender_doc.get('relationship_goal'), receiver_doc.get('relationship_goal')] if g})

        print(f'[AI] Firing for room={room} trigger="{trigger_msg[:40]}"')
        socketio.emit('spark_typing', {}, room=room)

        response = get_ai_host_response(
            trigger_message=trigger_msg,
            conversation_history=context,
            user1_name=sender_doc['username'],
            user2_name=receiver_doc['username'],
            user1_interests=s_int,
            user2_interests=r_int,
            goals=goals
        )

        print(f'[AI] Response: "{response[:80]}"')
        socketio.emit('spark_stop_typing', {}, room=room)
        socketio.emit('receive_message', {
            'sender_id': 0,
            'sender_username': 'ZTRY AI',
            'content': response,
            'timestamp': datetime.utcnow().strftime('%H:%M'),
            'type': 'spark',
            'is_read': True
        }, room=room)
        _push_context(room, 'ZTRY AI', response)

    except Exception as e:
        import traceback
        print(f'[AI] ERROR: {e}')
        traceback.print_exc()
        try:
            socketio.emit('spark_stop_typing', {}, room=room)
            socketio.emit('receive_message', {
                'sender_id': 0, 'type': 'spark',
                'content': "Sorry, I had a hiccup — try @ztry again!",
                'timestamp': datetime.utcnow().strftime('%H:%M'),
                'is_read': True
            }, room=room)
        except Exception:
            pass


def _push_context(room, sender, content):
    if room not in _conv_context: _conv_context[room] = []
    _conv_context[room].append({'sender': sender, 'content': content})
    _conv_context[room] = _conv_context[room][-20:]


def _room(uid1, uid2):
    ids = sorted([str(uid1), str(uid2)])
    return f'chat_{ids[0]}_{ids[1]}'
