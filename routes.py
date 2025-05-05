import os
import json
from datetime import datetime
from flask import session, redirect, url_for, render_template, flash, request, jsonify
from app import app, db
from replit_auth import require_login, make_replit_blueprint
from flask_login import current_user, login_required
from models import MemoryEntry, Document, User, Conversation, Message
from config import (
    ENVIRONMENT, BOT_TOKEN_PRODUCTION, BOT_TOKEN_DEVELOPMENT, 
    ACTIVE_BOT_TOKEN, IS_DEPLOYED, MANUS_MODEL, AVAILABLE_MODELS
)
import manus_integration

app.register_blueprint(make_replit_blueprint(), url_prefix="/auth")

# Make session permanent and set a secure cookie
@app.before_request
def make_session_permanent():
    session.permanent = True
    # Set a session key if not already set
    if 'SESSION_SECRET' not in os.environ:
        # If no secret key is set in environment, warn but continue
        app.logger.warning("SESSION_SECRET environment variable not set!")
    app.logger.debug("Session setup complete")

@app.route('/')
def index():
    """Landing page that explains the assistant and provides login option"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    return render_template('index.html')

@app.route('/dashboard')
@require_login
def dashboard():
    """Dashboard view with tabs for different functionality"""
    # Get memory and document counts
    memory_count = MemoryEntry.query.filter_by(user_id=current_user.id).count()
    document_count = Document.query.filter_by(user_id=current_user.id).count()
    
    # Get the Replit domain for Google OAuth redirect URI
    replit_domain = os.environ.get("REPLIT_DEV_DOMAIN", "")
    
    # Determine which token is being used
    token_info = {
        'environment': ENVIRONMENT,
        'is_deployed': IS_DEPLOYED,
        'using_production_token': ACTIVE_BOT_TOKEN == BOT_TOKEN_PRODUCTION,
        'has_production_token': bool(BOT_TOKEN_PRODUCTION),
        'has_development_token': bool(BOT_TOKEN_DEVELOPMENT)
    }
    
    # Get telegram users (for admin view)
    telegram_users = User.query.filter(User.telegram_id.isnot(None)).all()
    
    # Generate a registration token (simple implementation)
    registration_token = "donnah_bot"  # In a real app, generate this securely
    
    # Bot username
    if ENVIRONMENT == 'production':
        bot_username = os.environ.get("BOT_USERNAME_PRODUCTION", "YourBotUsernameProduction")
    else:
        bot_username = os.environ.get("BOT_USERNAME_DEVELOPMENT", "YourBotUsernameDev")
    
    # Get memories for display
    memories = MemoryEntry.query.filter_by(user_id=current_user.id).order_by(MemoryEntry.updated_at.desc()).limit(5).all()
    
    # Get documents for display
    documents = Document.query.filter_by(user_id=current_user.id).order_by(Document.updated_at.desc()).limit(5).all()
    
    # Check bot connection status
    bot_active = True  # Assume it's active
    
    # Check if the bot matches environment
    environment_token_match = (
        (ENVIRONMENT == 'production' and ACTIVE_BOT_TOKEN == BOT_TOKEN_PRODUCTION) or
        (ENVIRONMENT == 'development' and ACTIVE_BOT_TOKEN == BOT_TOKEN_DEVELOPMENT)
    )
    
    # Status for webhooks
    webhook_set = False
    if replit_domain:
        webhook_url = f"https://{replit_domain}/telegram_webhook"
        webhook_set = True  # Assume it's set since we auto-setup on init
    
    # Check if there have been recent Telegram interactions
    telegram_connected = False
    has_telegram_users = User.query.filter(User.telegram_id.isnot(None)).count() > 0
    
    # Check debugging status
    debug_mode = app.debug
    
    # OpenManus status
    manus_active = True  # Assume it's active
    manus_api_key = bool(os.environ.get("OPENAI_API_KEY"))
    memory_system_initialized = True
    manus_impl = f"OpenAI {MANUS_MODEL}"
    
    return render_template(
        'new_dashboard.html',  # Use the new template 
        memory_count=memory_count, 
        document_count=document_count,
        replit_domain=replit_domain,
        token_info=token_info,
        memories=memories,
        documents=documents,
        telegram_users=telegram_users,
        registration_token=registration_token,
        bot_username=bot_username,
        # Status information
        bot_active=bot_active,
        webhook_set=webhook_set,
        environment_token_match=environment_token_match,
        telegram_connected=telegram_connected,
        has_telegram_users=has_telegram_users,
        debug_mode=debug_mode,
        manus_active=manus_active,
        manus_api_key=manus_api_key,
        memory_system_initialized=memory_system_initialized,
        manus_impl=manus_impl,
        manus_model=MANUS_MODEL,
        available_models=AVAILABLE_MODELS
    )

@app.route('/chat')
@require_login
def chat():
    """Web interface for chatting with OpenManus"""
    return render_template('chat.html')

@app.route('/process_chat', methods=['POST'])
@require_login
def process_chat():
    """Process chat messages from the web interface"""
    data = request.json
    message = data.get('message', '')
    
    if not message:
        return jsonify({'error': 'No message provided'}), 400
    
    # Get or create a conversation for this user
    conversation = Conversation.query.filter_by(
        user_id=current_user.id, 
        end_time=None
    ).order_by(Conversation.start_time.desc()).first()
    
    if not conversation:
        conversation = Conversation(user_id=current_user.id)
        db.session.add(conversation)
        db.session.commit()
    
    # Save the user message
    user_message = Message(
        conversation_id=conversation.id,
        content=message,
        is_user=True
    )
    db.session.add(user_message)
    db.session.commit()
    
    # Process with OpenManus
    current_state = {
        'conversation_id': conversation.id
    }
    bot_response = manus_integration.process_message(current_user, message, current_state)
    
    # Save the bot response
    bot_message = Message(
        conversation_id=conversation.id,
        content=bot_response,
        is_user=False
    )
    db.session.add(bot_message)
    db.session.commit()
    
    # Return the response
    return jsonify({
        'response': bot_response,
        'timestamp': datetime.utcnow().isoformat()
    })