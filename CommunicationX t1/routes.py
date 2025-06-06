from flask import session, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import current_user
from app import app, db
from replit_auth import require_login, make_replit_blueprint
from models import User, Server, Channel, Message, DirectMessage, ServerMembership, Call, CallMessage, Voicemail, SharedFile
from datetime import datetime
from werkzeug.utils import secure_filename
from sqlalchemy import or_
from io import BytesIO

app.register_blueprint(make_replit_blueprint(), url_prefix="/auth")

# Make session permanent
@app.before_request
def make_session_permanent():
    session.permanent = True

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    return redirect(url_for('landing'))

@app.route('/landing')
def landing():
    return render_template('landing.html')

@app.route('/home')
@require_login
def home():
    # Get user's servers with auto-add functionality
    auto_add_user_to_servers(current_user)
    
    servers = db.session.query(Server).join(
        ServerMembership, Server.id == ServerMembership.server_id
    ).filter(
        ServerMembership.user_id == current_user.id
    ).all()
    
    return render_template('home.html', servers=servers)

@app.route('/server/<int:server_id>')
@require_login
def server_view(server_id):
    server = Server.query.get_or_404(server_id)
    
    # Check if user is member
    membership = ServerMembership.query.filter_by(
        user_id=current_user.id,
        server_id=server_id
    ).first()
    
    if not membership:
        flash('You are not a member of this server.', 'error')
        return redirect(url_for('home'))
    
    # Get channels and recent messages
    channels = Channel.query.filter_by(server_id=server_id).all()
    default_channel = channels[0] if channels else None
    
    messages = []
    if default_channel:
        messages = Message.query.filter_by(
            channel_id=default_channel.id
        ).order_by(Message.created_at.desc()).limit(50).all()
        messages.reverse()
    
    return render_template('server.html', 
                         server=server, 
                         channels=channels, 
                         current_channel=default_channel,
                         messages=messages)

@app.route('/server/<int:server_id>/send_message', methods=['POST'])
@require_login
def send_message(server_id):
    content = request.form.get('message', '').strip()
    channel_id = request.form.get('channel_id', type=int)
    
    if not content:
        flash('Message cannot be empty.', 'error')
        return redirect(url_for('server_view', server_id=server_id))
    
    # Verify user is member of server
    membership = ServerMembership.query.filter_by(
        user_id=current_user.id,
        server_id=server_id
    ).first()
    
    if not membership:
        flash('You are not a member of this server.', 'error')
        return redirect(url_for('home'))
    
    message = Message(
        content=content,
        author_id=current_user.id,
        channel_id=channel_id
    )
    db.session.add(message)
    db.session.commit()
    
    return redirect(url_for('server_view', server_id=server_id))

@app.route('/create_server', methods=['GET', 'POST'])
@require_login
def create_server():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        logo_url = request.form.get('logo_url', '').strip()
        is_public = request.form.get('is_public') == 'on'
        
        if not name:
            flash('Server name is required.', 'error')
            return render_template('create_server.html')
        
        # Create server
        server = Server(
            name=name,
            description=description,
            logo_url=logo_url if logo_url else None,
            owner_id=current_user.id,
            is_public=is_public
        )
        db.session.add(server)
        db.session.commit()
        
        # Create default general channel
        channel = Channel(name='general', server_id=server.id)
        db.session.add(channel)
        db.session.commit()
        
        # Add owner as member
        membership = ServerMembership(user_id=current_user.id, server_id=server.id)
        db.session.add(membership)
        
        # If public server, add all existing users
        if is_public:
            all_users = User.query.all()
            for user in all_users:
                if user.id != current_user.id:
                    existing = ServerMembership.query.filter_by(
                        user_id=user.id, server_id=server.id
                    ).first()
                    if not existing:
                        membership = ServerMembership(user_id=user.id, server_id=server.id)
                        db.session.add(membership)
        
        db.session.commit()
        flash(f'Server "{name}" created successfully!', 'success')
        return redirect(url_for('server_view', server_id=server.id))
    
    return render_template('create_server.html')

@app.route('/server/<int:server_id>/add_member', methods=['POST'])
@require_login
def add_member(server_id):
    server = Server.query.get_or_404(server_id)
    
    if server.owner_id != current_user.id:
        flash('Only the server owner can add members.', 'error')
        return redirect(url_for('server_view', server_id=server_id))
    
    username = request.form.get('username', '').strip()
    if not username:
        flash('Username is required.', 'error')
        return redirect(url_for('server_view', server_id=server_id))
    
    user = User.query.filter_by(username=username).first()
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('server_view', server_id=server_id))
    
    # Check if already a member
    existing_membership = ServerMembership.query.filter_by(
        user_id=user.id,
        server_id=server_id
    ).first()
    
    if existing_membership:
        flash('User is already a member of this server.', 'warning')
        return redirect(url_for('server_view', server_id=server_id))
    
    membership = ServerMembership(
        user_id=user.id,
        server_id=server_id
    )
    db.session.add(membership)
    db.session.commit()
    
    flash(f'User {username} added to server successfully!', 'success')
    return redirect(url_for('server_view', server_id=server_id))

@app.route('/direct_messages')
@require_login
def direct_messages():
    # Get all users who have had conversations with current user
    conversations = db.session.query(User).join(
        DirectMessage,
        (DirectMessage.sender_id == User.id) | (DirectMessage.recipient_id == User.id)
    ).filter(
        (DirectMessage.sender_id == current_user.id) | (DirectMessage.recipient_id == current_user.id),
        User.id != current_user.id
    ).distinct().all()
    
    # Get all users for potential new conversations
    all_users = User.query.filter(User.id != current_user.id).all()
    
    return render_template('direct_messages.html', 
                         conversations=conversations, 
                         all_users=all_users)

@app.route('/dm/<user_id>')
@require_login
def dm_conversation(user_id):
    other_user = User.query.get_or_404(user_id)
    
    # Get messages between current user and other user
    messages = DirectMessage.query.filter(
        ((DirectMessage.sender_id == current_user.id) & (DirectMessage.recipient_id == user_id)) |
        ((DirectMessage.sender_id == user_id) & (DirectMessage.recipient_id == current_user.id))
    ).order_by(DirectMessage.created_at.desc()).limit(50).all()
    
    messages.reverse()
    
    # Mark messages as read
    DirectMessage.query.filter(
        DirectMessage.sender_id == user_id,
        DirectMessage.recipient_id == current_user.id,
        DirectMessage.read_at == None
    ).update({DirectMessage.read_at: datetime.now()})
    db.session.commit()
    
    return render_template('direct_messages.html', 
                         other_user=other_user, 
                         messages=messages,
                         all_users=User.query.filter(User.id != current_user.id).all())

@app.route('/send_dm/<user_id>', methods=['POST'])
@require_login
def send_dm(user_id):
    other_user = User.query.get_or_404(user_id)
    content = request.form.get('message', '').strip()
    
    if not content:
        flash('Message cannot be empty.', 'error')
        return redirect(url_for('dm_conversation', user_id=user_id))
    
    dm = DirectMessage(
        content=content,
        sender_id=current_user.id,
        recipient_id=user_id
    )
    db.session.add(dm)
    db.session.commit()
    
    return redirect(url_for('dm_conversation', user_id=user_id))

@app.route('/call/<user_id>/<call_type>')
@require_login
def initiate_call(user_id, call_type):
    other_user = User.query.get_or_404(user_id)
    
    # Check for existing pending call
    existing_call = Call.query.filter_by(
        caller_id=current_user.id,
        recipient_id=user_id,
        status='pending'
    ).first()
    
    if existing_call:
        flash('You already have a pending call with this user.', 'warning')
        return redirect(url_for('dm_conversation', user_id=user_id))
    
    call = Call(
        caller_id=current_user.id,
        recipient_id=user_id,
        call_type=call_type
    )
    db.session.add(call)
    db.session.commit()
    
    return render_template('call.html', 
                         call=call, 
                         other_user=other_user, 
                         is_caller=True)

@app.route('/join_call/<int:call_id>')
@require_login
def join_call(call_id):
    call = Call.query.get_or_404(call_id)
    
    if call.recipient_id != current_user.id:
        flash('You are not authorized to join this call.', 'error')
        return redirect(url_for('home'))
    
    if call.status != 'pending':
        flash('This call is no longer available.', 'error')
        return redirect(url_for('home'))
    
    call.status = 'active'
    db.session.commit()
    
    other_user = User.query.get(call.caller_id)
    return render_template('call.html', 
                         call=call, 
                         other_user=other_user, 
                         is_caller=False)

@app.route('/end_call/<int:call_id>', methods=['POST'])
@require_login
def end_call(call_id):
    call = Call.query.get_or_404(call_id)
    
    if call.caller_id != current_user.id and call.recipient_id != current_user.id:
        flash('You are not authorized to end this call.', 'error')
        return redirect(url_for('home'))
    
    call.status = 'ended'
    call.ended_at = datetime.now()
    db.session.commit()
    
    return jsonify({'status': 'success'})

@app.route('/profile')
@require_login
def profile():
    return render_template('profile.html', user=current_user)

@app.route('/edit_profile', methods=['GET', 'POST'])
@require_login
def edit_profile():
    if request.method == 'POST':
        current_user.username = request.form.get('username') or current_user.username
        current_user.bio = request.form.get('bio')
        current_user.location = request.form.get('location')
        current_user.status = request.form.get('status') or 'online'
        
        # Handle custom profile image URL
        profile_image_url = request.form.get('profile_image_url')
        if profile_image_url:
            current_user.profile_image_url = profile_image_url
            
        current_user.updated_at = datetime.now()
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    return render_template('edit_profile.html', user=current_user)

@app.route('/voicemails')
@require_login
def voicemails():
    received_voicemails = Voicemail.query.filter_by(recipient_id=current_user.id).order_by(Voicemail.created_at.desc()).all()
    sent_voicemails = Voicemail.query.filter_by(sender_id=current_user.id).order_by(Voicemail.created_at.desc()).all()
    return render_template('voicemails.html', received=received_voicemails, sent=sent_voicemails)

@app.route('/send_voicemail/<user_id>', methods=['POST'])
@require_login
def send_voicemail(user_id):
    audio_url = request.form.get('audio_url')
    duration = request.form.get('duration', type=int)
    
    if not audio_url:
        flash('Audio recording required', 'error')
        return redirect(url_for('dm_conversation', user_id=user_id))
    
    voicemail = Voicemail(
        sender_id=current_user.id,
        recipient_id=user_id,
        audio_url=audio_url,
        duration=duration
    )
    db.session.add(voicemail)
    db.session.commit()
    
    flash('Voicemail sent!', 'success')
    return redirect(url_for('dm_conversation', user_id=user_id))

@app.route('/mark_voicemail_read/<int:voicemail_id>', methods=['POST'])
@require_login
def mark_voicemail_read(voicemail_id):
    voicemail = Voicemail.query.get_or_404(voicemail_id)
    if voicemail.recipient_id != current_user.id:
        flash('Unauthorized', 'error')
        return redirect(url_for('voicemails'))
    
    voicemail.is_read = True
    db.session.commit()
    return jsonify({'status': 'success'})

def auto_add_user_to_servers(user):
    """Automatically add new users to all public servers"""
    public_servers = Server.query.filter_by(is_public=True).all()
    for server in public_servers:
        existing_membership = ServerMembership.query.filter_by(
            user_id=user.id, 
            server_id=server.id
        ).first()
        
        if not existing_membership:
            membership = ServerMembership(user_id=user.id, server_id=server.id)
            db.session.add(membership)
    
    db.session.commit()

@app.route('/server_call/<int:server_id>')
@require_login
def server_call(server_id):
    server = Server.query.get_or_404(server_id)
    
    # Check if user is member of server
    membership = ServerMembership.query.filter_by(
        user_id=current_user.id,
        server_id=server_id
    ).first()
    
    if not membership:
        flash('You are not a member of this server', 'error')
        return redirect(url_for('home'))
    
    # Get active server calls
    active_calls = Call.query.filter_by(
        server_id=server_id,
        status='active'
    ).all()
    
    return render_template('server_call.html', server=server, active_calls=active_calls)

@app.route('/initiate_server_call/<int:server_id>', methods=['POST'])
@require_login
def initiate_server_call(server_id):
    call_type = request.form.get('call_type', 'audio')
    
    # Create server call
    call = Call(
        caller_id=current_user.id,
        recipient_id=current_user.id,  # For server calls, we'll use same ID
        server_id=server_id,
        call_type=call_type,
        status='active'
    )
    db.session.add(call)
    db.session.commit()
    
    return redirect(url_for('server_call', server_id=server_id))

@app.route('/send_call_message/<int:call_id>', methods=['POST'])
@require_login
def send_call_message(call_id):
    content = request.form.get('content')
    if not content:
        return jsonify({'error': 'Message content required'}), 400
    
    call = Call.query.get_or_404(call_id)
    
    message = CallMessage(
        call_id=call_id,
        user_id=current_user.id,
        content=content
    )
    db.session.add(message)
    db.session.commit()
    
    return jsonify({
        'id': message.id,
        'content': message.content,
        'user': current_user.username or current_user.first_name or 'Anonymous',
        'timestamp': message.created_at.strftime('%H:%M')
    })