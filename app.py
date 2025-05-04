import os
import logging
import secrets
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy
db = SQLAlchemy(model_class=Base)

# Create Flask application
app = Flask(__name__)

# Use environment variable for secret key, or generate a secure random one for development
if os.environ.get("SESSION_SECRET"):
    app.secret_key = os.environ.get("SESSION_SECRET")
else:
    # If no secret key is set, generate a random one - warning: this will invalidate sessions on restart
    logger.warning("No SESSION_SECRET environment variable set. Using a random secret key.")
    app.secret_key = secrets.token_hex(32)

app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Initialize LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth'
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"
login_manager.session_protection = "strong"

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///manus_assistant.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the app with the SQLAlchemy extension
db.init_app(app)

# Import service functions after app is created to avoid circular imports
import json
import telegram_bot  # Import but don't initialize
from google_services import initialize_google_services
import config  # Import configuration
from manus_integration import initialize_manus
from memory_system import initialize_memory_system
from google_auth import google_auth  # Import the Google OAuth blueprint

# Register blueprints
app.register_blueprint(google_auth)

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/auth', methods=['GET'])
def auth():
    return render_template('auth.html')

@app.route('/login', methods=['POST'])
def login():
    from models import User
    
    email = request.form.get('email')
    password = request.form.get('password')
    
    user = User.query.filter_by(email=email).first()
    
    if user and check_password_hash(user.password_hash, password):
        login_user(user)
        session['user_id'] = user.id
        flash('Login successful!', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash('Invalid email or password. Please try again.', 'danger')
        return redirect(url_for('auth'))

@app.route('/register', methods=['POST'])
def register():
    from models import User
    
    logger.debug("Registration form submitted")
    
    # Log all form data to troubleshoot
    form_data = dict(request.form)
    # Remove password from logs for security
    if 'password' in form_data:
        form_data['password'] = '********'
    if 'confirm_password' in form_data:
        form_data['confirm_password'] = '********'
    logger.debug(f"All form data: {form_data}")
    
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    
    logger.debug(f"Form data: username={username}, email={email}")
    
    # Validate form data
    if not all([username, email, password, confirm_password]):
        logger.warning("Missing required fields in registration form")
        flash('All fields are required.', 'danger')
        return redirect(url_for('auth'))
    
    if password != confirm_password:
        logger.warning("Passwords do not match in registration form")
        flash('Passwords do not match.', 'danger')
        return redirect(url_for('auth'))
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        logger.info(f"Email {email} already registered")
        flash('Email already registered. Please login instead.', 'warning')
        return redirect(url_for('auth'))
    
    try:
        # Create new user
        new_user = User(
            username=username, 
            email=email, 
            password_hash=generate_password_hash(password)
        )
        
        logger.debug(f"Created new user object: {new_user}")
        
        db.session.add(new_user)
        db.session.commit()
        logger.debug(f"User committed to database with ID: {new_user.id}")
        
        # Log the user in
        login_successful = login_user(new_user)
        logger.debug(f"login_user result: {login_successful}")
        
        session['user_id'] = new_user.id
        logger.debug(f"Session user_id set to: {session.get('user_id')}")
        
        logger.info(f"User {username} (ID: {new_user.id}) registered successfully")
        flash('Registration successful! Welcome to OpenManus Assistant.', 'success')
        
        # Debug current_user after login
        logger.debug(f"current_user.is_authenticated: {current_user.is_authenticated}")
        logger.debug(f"current_user.id: {current_user.id if current_user.is_authenticated else 'Not authenticated'}")
        
        return redirect(url_for('dashboard'))
    except Exception as e:
        logger.error(f"Error during registration: {str(e)}")
        db.session.rollback()
        flash(f'An error occurred during registration: {str(e)}', 'danger')
        return redirect(url_for('auth'))

@app.route('/logout')
def logout():
    logout_user()
    if 'user_id' in session:
        session.pop('user_id')
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    from models import MemoryEntry, Document
    from config import ENVIRONMENT, BOT_TOKEN_PRODUCTION, BOT_TOKEN_DEVELOPMENT, ACTIVE_BOT_TOKEN, IS_DEPLOYED
    
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
    
    return render_template(
        'dashboard.html', 
        memory_count=memory_count, 
        document_count=document_count,
        replit_domain=replit_domain,
        token_info=token_info
    )

@app.route('/start_bot', methods=['POST'])
@login_required
def start_bot():
    try:
        telegram_token = os.environ.get("TELEGRAM_TOKEN")
        if not telegram_token:
            flash('Telegram token not configured. Using demo mode.', 'warning')
            # In demo mode, we will simulate the bot
            flash('Telegram bot initialized in demo mode. Some features may be limited.', 'info')
            return redirect(url_for('dashboard'))
        
        is_registered = telegram_bot.initialize_bot(telegram_token)
        if is_registered:
            flash('Telegram bot registered successfully. The bot is ready to handle commands but may not actively poll for updates in this environment.', 'success')
        else:
            flash('Failed to register Telegram bot. Check logs for details.', 'danger')
    except Exception as e:
        logger.error(f"Error registering Telegram bot: {e}")
        flash(f'Error registering Telegram bot: {str(e)}', 'danger')
    
    return redirect(url_for('dashboard'))

@app.route('/debug_users')
def debug_users():
    from models import User
    try:
        users = User.query.all()
        user_data = [
            {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'created_at': str(user.created_at) if hasattr(user, 'created_at') else None
            }
            for user in users
        ]
        return jsonify({"user_count": len(users), "users": user_data})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/try_login')
def try_login():
    """Helper route to automatically log in as the first user"""
    from models import User
    try:
        user = User.query.first()
        if not user:
            return jsonify({"error": "No users found in database"})
        
        # Log the user in
        login_successful = login_user(user)
        session['user_id'] = user.id
        logger.info(f"Auto-login successful for user {user.username} (ID: {user.id})")
        logger.debug(f"login_user result: {login_successful}")
        logger.debug(f"Session user_id: {session.get('user_id')}")
        logger.debug(f"current_user.is_authenticated: {current_user.is_authenticated}")
        
        flash(f'Auto-login successful! Welcome back, {user.username}.', 'success')
        return redirect(url_for('dashboard'))
    except Exception as e:
        logger.error(f"Error during auto-login: {str(e)}")
        return jsonify({"error": str(e)})
        
@app.route('/status')
def status():
    """Display system status and configuration information"""
    from models import User, MemoryEntry, Document
    from datetime import datetime
    from collections import deque
    import logging
    import re
    import sys
    
    # Custom log handler to capture recent logs
    class MemoryLogHandler(logging.Handler):
        def __init__(self, capacity=100):
            super().__init__()
            self.logs = deque(maxlen=capacity)
            
        def emit(self, record):
            self.logs.append({
                'timestamp': datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S'),
                'level': record.levelname,
                'message': record.getMessage()
            })
            
    # Get debug status from app
    debug_mode = app.debug
    
    # Get bot and deployment status
    bot_active = bool(config.ACTIVE_BOT_TOKEN)
    using_production_token = config.ACTIVE_BOT_TOKEN == config.BOT_TOKEN_PRODUCTION
    environment_token_match = (
        (config.ENVIRONMENT == 'production' and using_production_token) or
        (config.ENVIRONMENT == 'development' and not using_production_token)
    )
    
    # Test if webhook is set
    webhook_set = False
    replit_domain = os.environ.get("REPLIT_DEV_DOMAIN", "")
    if replit_domain and bot_active:
        webhook_url = f"https://{replit_domain}/telegram_webhook"
        webhook_set = True  # Assume it's set in this case
    
    # Check database connection
    db_connected = False
    db_type = "Unknown"
    user_count = 0
    memory_count = 0
    
    try:
        # Try to execute a simple query
        user_count = User.query.count()
        memory_count = MemoryEntry.query.count()
        db_connected = True
        
        # Determine database type
        db_url = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        if db_url.startswith("postgresql"):
            db_type = "PostgreSQL"
        elif db_url.startswith("sqlite"):
            db_type = "SQLite"
        else:
            db_type = db_url.split("://")[0] if "://" in db_url else "Unknown"
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
    
    # Check OpenManus status
    manus_active = True  # Assume it's active since we need it for the app
    manus_api_key = bool(config.MANUS_API_KEY)
    memory_system_initialized = True  # Assume it's initialized
    manus_impl = "OpenAI GPT-4"  # This could be determined based on config
    
    # Environment variables to check
    env_vars = [
        {
            'name': 'SESSION_SECRET',
            'exists': bool(os.environ.get("SESSION_SECRET")),
            'is_secret': True,
            'sample': None
        },
        {
            'name': 'TELEGRAM_BOT_TOKEN_DONNAH',
            'exists': bool(os.environ.get("TELEGRAM_BOT_TOKEN_DONNAH")),
            'is_secret': True,
            'sample': None
        },
        {
            'name': 'TELEGRAM_BOT_TOKEN_NOENA',
            'exists': bool(os.environ.get("TELEGRAM_BOT_TOKEN_NOENA")),
            'is_secret': True,
            'sample': None
        },
        {
            'name': 'DATABASE_URL',
            'exists': bool(os.environ.get("DATABASE_URL")),
            'is_secret': True,
            'sample': "postgresql://..."
        },
        {
            'name': 'OPENAI_API_KEY',
            'exists': bool(os.environ.get("OPENAI_API_KEY")),
            'is_secret': True,
            'sample': None
        },
        {
            'name': 'GOOGLE_CLIENT_ID',
            'exists': bool(os.environ.get("GOOGLE_CLIENT_ID")),
            'is_secret': False,
            'sample': os.environ.get("GOOGLE_CLIENT_ID", "")[0:12] + "..." if os.environ.get("GOOGLE_CLIENT_ID") else None
        },
        {
            'name': 'GOOGLE_CLIENT_SECRET',
            'exists': bool(os.environ.get("GOOGLE_CLIENT_SECRET")),
            'is_secret': True,
            'sample': None
        },
        {
            'name': 'REPLIT_DEV_DOMAIN',
            'exists': bool(os.environ.get("REPLIT_DEV_DOMAIN")),
            'is_secret': False,
            'sample': os.environ.get("REPLIT_DEV_DOMAIN")
        }
    ]
    
    # Get recent logs
    # Since we don't have a memory handler set up globally, we'll just provide some sample logs
    recent_logs = [
        {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'level': 'INFO',
            'message': 'System status page accessed'
        },
        {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'level': 'INFO',
            'message': f'Current environment: {config.ENVIRONMENT}'
        },
        {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'level': 'INFO',
            'message': f'Debug mode: {"Enabled" if debug_mode else "Disabled"}'
        },
        {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'level': 'INFO',
            'message': f'Database connection: {"Successful" if db_connected else "Failed"}'
        }
    ]
    
    # Render the status template
    return render_template(
        'status.html',
        environment=config.ENVIRONMENT,
        current_time=datetime.now(),
        debug_mode=debug_mode,
        is_deployed=config.IS_DEPLOYED,
        bot_active=bot_active,
        using_production_token=using_production_token,
        webhook_set=webhook_set,
        environment_token_match=environment_token_match,
        db_connected=db_connected,
        db_type=db_type,
        user_count=user_count,
        memory_count=memory_count,
        manus_active=manus_active,
        manus_api_key=manus_api_key,
        memory_system_initialized=memory_system_initialized,
        manus_impl=manus_impl,
        env_vars=env_vars,
        recent_logs=recent_logs
    )

@app.route('/api/logs')
def get_logs():
    """API endpoint to get recent system logs"""
    # In a real implementation, you'd retrieve logs from a persistent source
    # For now, we'll just return some sample logs
    from datetime import datetime, timedelta
    
    recent_logs = []
    now = datetime.now()
    
    log_levels = ['INFO', 'DEBUG', 'WARNING', 'INFO', 'ERROR', 'INFO']
    log_messages = [
        'Application started',
        'Processing request for user authentication',
        'Rate limit approaching for API calls',
        'User login successful',
        'Failed to connect to external service',
        'Database connection established'
    ]
    
    for i in range(len(log_messages)):
        log_time = now - timedelta(minutes=i*5)
        recent_logs.append({
            'timestamp': log_time.strftime('%Y-%m-%d %H:%M:%S'),
            'level': log_levels[i % len(log_levels)],
            'message': log_messages[i % len(log_messages)]
        })
    
    return jsonify({'logs': recent_logs})

@app.route('/dashboard_direct')
def dashboard_direct():
    """A version of the dashboard without the @login_required decorator for testing"""
    from models import MemoryEntry, Document, User
    from config import ENVIRONMENT, BOT_TOKEN_PRODUCTION, BOT_TOKEN_DEVELOPMENT, ACTIVE_BOT_TOKEN, IS_DEPLOYED
    
    try:
        # Get the first user for testing
        user = User.query.first()
        if not user:
            flash('No users found in database', 'danger')
            return redirect(url_for('auth'))
            
        # Get memory and document counts
        memory_count = MemoryEntry.query.filter_by(user_id=user.id).count()
        document_count = Document.query.filter_by(user_id=user.id).count()
        
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
        
        # Set a flag to indicate this is a direct access (bypass login check)
        is_direct_access = True
        
        return render_template(
            'dashboard.html', 
            memory_count=memory_count, 
            document_count=document_count,
            replit_domain=replit_domain,
            token_info=token_info,
            is_direct_access=is_direct_access,
            current_user=user  # Pass the user directly
        )
    except Exception as e:
        logger.error(f"Error accessing dashboard directly: {str(e)}")
        return jsonify({"error": str(e)})

# Initialize database
with app.app_context():
    # Import models
    import models
    
    # Create database tables
    db.create_all()
    
    # Initialize services
    try:
        # Initialize Google services
        initialize_google_services()
        
        # Initialize OpenManus framework
        initialize_manus()
        
        # Initialize memory system
        initialize_memory_system()
        
        # Check if Telegram token is available and register the bot
        # Import the active bot token from config
        from config import ACTIVE_BOT_TOKEN, BOT_TOKEN_PRODUCTION, BOT_TOKEN_DEVELOPMENT, ENVIRONMENT
        if ACTIVE_BOT_TOKEN:
            # Log which token and environment are being used
            logger.info(f"Using {'Production' if ENVIRONMENT == 'production' else 'Development'} bot for initialization")
                
            try:
                # Just register the bot without trying to start polling
                # This will allow commands to work but won't actively fetch updates
                is_registered = telegram_bot.initialize_bot(ACTIVE_BOT_TOKEN)
                if is_registered:
                    logger.info("Telegram bot registered successfully at startup")
                    
                    # Automatically set up the webhook for Telegram
                    replit_domain = os.environ.get("REPLIT_DEV_DOMAIN", "")
                    if replit_domain:
                        webhook_url = f"https://{replit_domain}/telegram_webhook"
                        success = telegram_bot.setup_webhook(webhook_url)
                        
                        if success:
                            logger.info(f"Telegram webhook set up automatically at {webhook_url}")
                        else:
                            logger.warning("Failed to set up Telegram webhook automatically")
                    else:
                        logger.warning("Replit domain not available. Webhook setup skipped.")
                else:
                    logger.error("Failed to register Telegram bot at startup")
            except Exception as e:
                logger.error(f"Error registering Telegram bot: {e}")
        
        logger.info("All services initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing services: {e}")

@app.route('/switch_token', methods=['POST'])
@login_required
def switch_token():
    """Switch between development and production tokens in development environment"""
    # This route should only be used in development
    if config.IS_DEPLOYED:
        flash('Token switching is disabled in production environment', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get the target token type
    target_token = request.form.get('target_token', 'development')
    
    # Validate input
    if target_token not in ['development', 'production']:
        flash('Invalid token type specified', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check if the target token is available
    if target_token == 'production' and not config.BOT_TOKEN_PRODUCTION:
        flash('Production token is not available', 'danger')
        return redirect(url_for('dashboard'))
    elif target_token == 'development' and not config.BOT_TOKEN_DEVELOPMENT:
        flash('Development token is not available', 'danger')
        return redirect(url_for('dashboard'))
    
    # Store the current active token for comparison
    old_token = config.ACTIVE_BOT_TOKEN
    
    # Update the active token in config
    if target_token == 'production':
        config.ACTIVE_BOT_TOKEN = config.BOT_TOKEN_PRODUCTION
        logger.info("Switched to PRODUCTION token")
    else:
        config.ACTIVE_BOT_TOKEN = config.BOT_TOKEN_DEVELOPMENT
        logger.info("Switched to DEVELOPMENT token")
    
    # Only rebuild the bot if the token has actually changed
    if old_token != config.ACTIVE_BOT_TOKEN:
        # Re-initialize the bot with the new token
        try:
            is_registered = telegram_bot.initialize_bot(config.ACTIVE_BOT_TOKEN)
            if is_registered:
                # Reset the webhook if using a different token
                webhook_url = None
                replit_domain = os.environ.get("REPLIT_DEV_DOMAIN", "")
                if replit_domain:
                    webhook_url = f"https://{replit_domain}/telegram_webhook"
                    success = telegram_bot.setup_webhook(webhook_url)
                    if success:
                        logger.info(f"Webhook updated to use the {target_token.upper()} token")
                        flash(f'Successfully switched to {target_token.upper()} token and updated webhook', 'success')
                    else:
                        logger.warning(f"Failed to update webhook for {target_token.upper()} token")
                        flash(f'Switched to {target_token.upper()} token but failed to update webhook', 'warning')
                else:
                    flash(f'Switched to {target_token.upper()} token but could not update webhook (domain not available)', 'warning')
            else:
                logger.error(f"Failed to initialize bot with {target_token.upper()} token")
                flash(f'Failed to initialize bot with {target_token.upper()} token', 'danger')
        except Exception as e:
            logger.error(f"Error switching tokens: {str(e)}")
            flash(f'Error switching tokens: {str(e)}', 'danger')
    else:
        flash(f'Already using the {target_token.upper()} token', 'info')
    
    return redirect(url_for('dashboard'))

@app.route('/inspect_users')
def inspect_users():
    from models import User
    users = User.query.all()
    for user in users:
        print(f'User ID: {user.id}, Username: {user.username}, Email: {user.email}')
    return "User information printed to console."

@app.route('/setup_telegram_webhook', methods=['POST'])
def setup_telegram_webhook():
    """Set up the Telegram webhook."""
    try:
        # Use the active bot token from config
        from config import ACTIVE_BOT_TOKEN, BOT_TOKEN_PRODUCTION, BOT_TOKEN_DEVELOPMENT, ENVIRONMENT
        replit_domain = os.environ.get("REPLIT_DEV_DOMAIN", "")
        
        if not ACTIVE_BOT_TOKEN:
            flash('Telegram bot token not configured. Cannot set up webhook.', 'danger')
            return redirect(url_for('dashboard'))
            
        # Log which token and environment are being used
        logger.info(f"Using {'Production' if ENVIRONMENT == 'production' else 'Development'} bot for webhook setup")
            
        if not replit_domain:
            flash('Replit domain not available. Cannot set up webhook.', 'danger')
            return redirect(url_for('dashboard'))
            
        # Initialize bot if not already initialized
        is_registered = telegram_bot.initialize_bot(ACTIVE_BOT_TOKEN)
        if not is_registered:
            flash('Failed to initialize Telegram bot. Check logs for details.', 'danger')
            return redirect(url_for('dashboard'))
            
        # Set up webhook
        webhook_url = f"https://{replit_domain}/telegram_webhook"
        success = telegram_bot.setup_webhook(webhook_url)
        
        if success:
            flash(f'Telegram webhook set up successfully at {webhook_url}', 'success')
        else:
            flash('Failed to set up webhook. Check logs for details.', 'danger')
            
    except Exception as e:
        logger.error(f"Error setting up webhook: {str(e)}")
        flash(f'Error setting up webhook: {str(e)}', 'danger')
        
    return redirect(url_for('dashboard'))
    
@app.route('/remove_telegram_webhook', methods=['POST'])
def remove_telegram_webhook():
    """Remove the Telegram webhook."""
    try:
        # Use the active bot token from config
        from config import ACTIVE_BOT_TOKEN, BOT_TOKEN_PRODUCTION, BOT_TOKEN_DEVELOPMENT, ENVIRONMENT
        
        if not ACTIVE_BOT_TOKEN:
            flash('Telegram bot token not configured. Cannot remove webhook.', 'danger')
            return redirect(url_for('dashboard'))
            
        # Log which token and environment are being used
        logger.info(f"Using {'Production' if ENVIRONMENT == 'production' else 'Development'} bot for webhook removal")
            
        # Initialize bot if not already initialized
        is_registered = telegram_bot.initialize_bot(ACTIVE_BOT_TOKEN)
        if not is_registered:
            flash('Failed to initialize Telegram bot. Check logs for details.', 'danger')
            return redirect(url_for('dashboard'))
            
        # Remove webhook
        success = telegram_bot.remove_webhook()
        
        if success:
            flash('Telegram webhook removed successfully', 'success')
        else:
            flash('Failed to remove webhook. Check logs for details.', 'danger')
            
    except Exception as e:
        logger.error(f"Error removing webhook: {str(e)}")
        flash(f'Error removing webhook: {str(e)}', 'danger')
        
    return redirect(url_for('dashboard'))
    
@app.route('/telegram_webhook', methods=['POST'])
def telegram_webhook():
    """
    Handle Telegram webhook requests.
    This route receives updates from Telegram when a user interacts with the bot.
    """
    try:
        # Get the update data from the request
        update_data = json.loads(request.data)
        logger.debug(f"Received update from Telegram: {update_data}")
        
        # Process the update - this is no longer async
        success = telegram_bot.process_update(update_data)
        
        if success:
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": "Failed to process update"}), 500
    except Exception as e:
        logger.error(f"Error processing Telegram update: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
        
@app.route('/chat')
@login_required
def chat():
    """
    Web interface for chatting with OpenManus (donnah).
    This provides a browser-based alternative to the Telegram bot.
    """
    return render_template('chat.html')

@app.route('/process_chat', methods=['POST'])
@login_required
def process_chat():
    """
    Process chat messages from the web interface.
    """
    try:
        message = request.json.get('message', '')
        if not message:
            return jsonify({"error": "No message provided"}), 400
            
        # Get current state from session or initialize new one
        current_state = session.get('chat_state', {})
        
        # Use the same OpenManus processing as Telegram bot
        from manus_integration import process_message
        
        # Process the message
        response = process_message(current_user, message, current_state)
        
        # Update session with new state
        session['chat_state'] = current_state
        
        # Return the response as JSON
        return jsonify({
            "response": response,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        return jsonify({"error": str(e)}), 500
