from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
from app import app, db, socketio
from models import Call, CallMessage
from datetime import datetime

@socketio.on('connect')
def on_connect():
    if current_user.is_authenticated:
        print(f'User {current_user.id} connected')
    else:
        print('Anonymous user connected')

@socketio.on('disconnect')
def on_disconnect():
    if current_user.is_authenticated:
        print(f'User {current_user.id} disconnected')

@socketio.on('join_call')
def on_join_call(data):
    if not current_user.is_authenticated:
        return
    
    call_id = data['call_id']
    room_name = f"call_{call_id}"
    
    # Verify user is authorized for this call
    call = Call.query.get(call_id)
    if not call or (call.caller_id != current_user.id and call.recipient_id != current_user.id):
        return
    
    join_room(room_name)
    emit('user_joined', {
        'user_id': current_user.id,
        'username': current_user.username or current_user.first_name or 'Anonymous'
    }, room=room_name, include_self=False)
    
    print(f'User {current_user.id} joined call {call_id}')

@socketio.on('leave_call')
def on_leave_call(data):
    if not current_user.is_authenticated:
        return
        
    call_id = data['call_id']
    room_name = f"call_{call_id}"
    
    leave_room(room_name)
    emit('user_left', {
        'user_id': current_user.id,
        'username': current_user.username or current_user.first_name or 'Anonymous'
    }, room=room_name, include_self=False)
    
    print(f'User {current_user.id} left call {call_id}')

@socketio.on('offer')
def on_offer(data):
    if not current_user.is_authenticated:
        return
        
    call_id = data['call_id']
    room_name = f"call_{call_id}"
    
    # Verify authorization
    call = Call.query.get(call_id)
    if not call or (call.caller_id != current_user.id and call.recipient_id != current_user.id):
        return
    
    emit('offer', {
        'call_id': call_id,
        'offer': data['offer'],
        'from_user': current_user.id
    }, room=room_name, include_self=False)
    
    print(f'WebRTC offer sent for call {call_id}')

@socketio.on('answer')
def on_answer(data):
    if not current_user.is_authenticated:
        return
        
    call_id = data['call_id']
    room_name = f"call_{call_id}"
    
    # Verify authorization
    call = Call.query.get(call_id)
    if not call or (call.caller_id != current_user.id and call.recipient_id != current_user.id):
        return
    
    emit('answer', {
        'call_id': call_id,
        'answer': data['answer'],
        'from_user': current_user.id
    }, room=room_name, include_self=False)
    
    print(f'WebRTC answer sent for call {call_id}')

@socketio.on('ice_candidate')
def on_ice_candidate(data):
    if not current_user.is_authenticated:
        return
        
    call_id = data['call_id']
    room_name = f"call_{call_id}"
    
    # Verify authorization
    call = Call.query.get(call_id)
    if not call or (call.caller_id != current_user.id and call.recipient_id != current_user.id):
        return
    
    emit('ice_candidate', {
        'call_id': call_id,
        'candidate': data['candidate'],
        'from_user': current_user.id
    }, room=room_name, include_self=False)

@socketio.on('call_message')
def on_call_message(data):
    if not current_user.is_authenticated:
        return
        
    call_id = data['call_id']
    message_content = data['message']
    
    # Verify authorization
    call = Call.query.get(call_id)
    if not call or (call.caller_id != current_user.id and call.recipient_id != current_user.id):
        return
    
    # Save message to database
    with app.app_context():
        call_message = CallMessage(
            call_id=call_id,
            user_id=current_user.id,
            content=message_content
        )
        db.session.add(call_message)
        db.session.commit()
    
    # Broadcast to call participants
    room_name = f"call_{call_id}"
    emit('call_message', {
        'call_id': call_id,
        'message': message_content,
        'username': current_user.username or current_user.first_name or 'Anonymous',
        'user_id': current_user.id,
        'timestamp': datetime.now().strftime('%H:%M')
    }, room=room_name)
    
    print(f'Call message sent in call {call_id}')

@socketio.on('end_call')
def on_end_call(data):
    if not current_user.is_authenticated:
        return
        
    call_id = data['call_id']
    room_name = f"call_{call_id}"
    
    # Verify authorization
    call = Call.query.get(call_id)
    if not call or (call.caller_id != current_user.id and call.recipient_id != current_user.id):
        return
    
    # Update call status in database
    with app.app_context():
        call.status = 'ended'
        call.ended_at = datetime.now()
        db.session.commit()
    
    # Notify all participants
    emit('call_ended', {
        'call_id': call_id,
        'ended_by': current_user.id
    }, room=room_name)
    
    print(f'Call {call_id} ended by user {current_user.id}')

# Server messaging events
@socketio.on('join_server')
def on_join_server(data):
    if not current_user.is_authenticated:
        return
        
    server_id = data['server_id']
    join_room(f"server_{server_id}")

@socketio.on('leave_server')
def on_leave_server(data):
    if not current_user.is_authenticated:
        return
        
    server_id = data['server_id']
    leave_room(f"server_{server_id}")

@socketio.on('server_message')
def on_server_message(data):
    if not current_user.is_authenticated:
        return
        
    server_id = data['server_id']
    emit('new_message', {
        'server_id': server_id,
        'message': data['message'],
        'user': current_user.username or current_user.first_name or 'Anonymous',
        'timestamp': datetime.now().strftime('%H:%M')
    }, room=f"server_{server_id}", include_self=False)