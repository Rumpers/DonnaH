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
    return dashboard_common(active_tab='overview')

@app.route('/dashboard/services')
@require_login
def dashboard_services():
    """Dashboard view with connected services tab active"""
    return dashboard_common(active_tab='services')

@app.route('/dashboard/telegram')
@require_login
def dashboard_telegram():
    """Dashboard view with telegram tab active"""
    return dashboard_common(active_tab='telegram')

@app.route('/dashboard/memory')
@require_login
def dashboard_memory():
    """Dashboard view with memory entries tab active"""
    return dashboard_common(active_tab='memory')

@app.route('/dashboard/documents')
@require_login
def dashboard_documents():
    """Dashboard view with documents tab active"""
    return dashboard_common(active_tab='documents')

@app.route('/dashboard/status')
@require_login
def dashboard_status():
    """Dashboard view with system status tab active"""
    return dashboard_common(active_tab='system-status')

def dashboard_common(active_tab='overview'):
    """Common function to render dashboard with different active tabs"""
    # Get memory and document counts
    memory_count = MemoryEntry.query.filter_by(user_id=current_user.id).count()
    document_count = Document.query.filter_by(user_id=current_user.id).count()
    
    # Get the Replit domain for Google OAuth redirect URI
    replit_domain = os.environ.get("REPLIT_DEV_DOMAIN", "")
    
    # Determine which token is being used
    # Always check environment variable first to get the most current setting
    # This ensures we pick up changes made by other worker processes
    current_env = os.environ.get("MANUS_ENVIRONMENT", ENVIRONMENT)
    
    # Force a refresh of the token from config to match current environment
    # This ensures config is always up to date
    from config import set_token_for_environment
    set_token_for_environment()
    
    # Get fresh token info after the refresh
    from config import ACTIVE_BOT_TOKEN, BOT_TOKEN_PRODUCTION, BOT_TOKEN_DEVELOPMENT
    
    token_info = {
        'environment': current_env,
        'is_deployed': IS_DEPLOYED,
        'using_production_token': ACTIVE_BOT_TOKEN == BOT_TOKEN_PRODUCTION,
        'has_production_token': bool(BOT_TOKEN_PRODUCTION),
        'has_development_token': bool(BOT_TOKEN_DEVELOPMENT)
    }
    
    # Get telegram users (for admin view)
    telegram_users = User.query.filter(User.telegram_id.isnot(None)).all()
    
    # Generate a registration token (simple implementation)
    registration_token = "donnah_bot"  # In a real app, generate this securely
    
    # Bot username - use current environment from environment variable
    if current_env == 'production':
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
        (current_env == 'production' and ACTIVE_BOT_TOKEN == BOT_TOKEN_PRODUCTION) or
        (current_env == 'development' and ACTIVE_BOT_TOKEN == BOT_TOKEN_DEVELOPMENT)
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
        active_tab=active_tab,
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

@app.route('/check_services')
@require_login
def check_services():
    """Check the status of all services and redirect to status page"""
    try:
        # Check OpenAI API key
        openai_key_available = bool(os.environ.get("OPENAI_API_KEY"))
        if not openai_key_available:
            flash('OpenAI API key is not configured. OpenManus features will be limited.', 'warning')
        
        # Check Telegram token
        from config import ACTIVE_BOT_TOKEN, BOT_TOKEN_PRODUCTION, BOT_TOKEN_DEVELOPMENT, ENVIRONMENT
        
        # Force a refresh of the token from environment
        from config import set_token_for_environment
        set_token_for_environment()
        
        if not ACTIVE_BOT_TOKEN:
            if ENVIRONMENT == 'production':
                flash('Production Telegram bot token is not configured. Telegram bot functionality will not work.', 'warning')
            else:
                flash('Development Telegram bot token is not configured. Telegram bot functionality will not work.', 'warning')
        
        # Check webhook status
        import telegram_bot
        replit_domain = os.environ.get("REPLIT_DEV_DOMAIN", "")
        if replit_domain:
            try:
                # Re-initialize bot to ensure correct config
                telegram_bot.initialize_bot(ACTIVE_BOT_TOKEN, force_reinit=True)
                webhook_status = telegram_bot.get_webhook_info()
                if webhook_status and webhook_status.get('url', ''):
                    flash(f'Telegram webhook is active at {webhook_status.get("url")}', 'success')
                else:
                    webhook_url = f"https://{replit_domain}/telegram_webhook"
                    success = telegram_bot.setup_webhook(webhook_url)
                    if success:
                        flash(f'Telegram webhook was not set. Successfully set up at {webhook_url}', 'success')
                    else:
                        flash('Telegram webhook is not configured and automatic setup failed.', 'danger')
            except Exception as e:
                app.logger.error(f"Error checking webhook: {str(e)}")
                flash(f'Error checking Telegram webhook: {str(e)}', 'danger')
        else:
            flash('Replit domain not available. Cannot verify Telegram webhook status.', 'warning')
        
        # Check database
        try:
            # Simple database check - count users
            user_count = User.query.count()
            flash(f'Database connection successful. Found {user_count} users.', 'success')
        except Exception as e:
            app.logger.error(f"Database error: {str(e)}")
            flash(f'Database error: {str(e)}', 'danger')
        
        # Verify environment settings
        current_env = os.environ.get("MANUS_ENVIRONMENT", ENVIRONMENT)
        flash(f'Current environment: {current_env.upper()}', 'info')
        
        # Check for environment-token mismatch
        environment_token_match = (
            (current_env == 'production' and ACTIVE_BOT_TOKEN == BOT_TOKEN_PRODUCTION) or
            (current_env == 'development' and ACTIVE_BOT_TOKEN == BOT_TOKEN_DEVELOPMENT)
        )
        if not environment_token_match:
            flash('Warning: Environment and active token do not match. Consider switching the token.', 'warning')
            
    except Exception as e:
        app.logger.error(f"Error in service check: {str(e)}")
        flash(f'Error checking services: {str(e)}', 'danger')
    
    # Redirect to the status tab
    return redirect(url_for('dashboard_status'))

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