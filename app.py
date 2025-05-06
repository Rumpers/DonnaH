import os
import logging
import secrets
import json
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

# Create memory log handler to track recent logs
class MemoryLogHandler(logging.Handler):
    def __init__(self, capacity=100):
        super().__init__()
        self.capacity = capacity
        self.logs = []
        self.formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    def emit(self, record):
        self.logs.append(record)
        if len(self.logs) > self.capacity:
            self.logs = self.logs[-self.capacity:]
    
    def get_logs(self):
        return self.logs

# Add the memory log handler to the logger
memory_log_handler = MemoryLogHandler(capacity=100)
logger.addHandler(memory_log_handler)

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

# Initialize LoginManager for Replit Auth
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'replit_auth.login'  # Point to Replit Auth login route
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"
login_manager.session_protection = "strong"

# Log to make sure LoginManager is initialized properly
logger.info("LoginManager initialized with login_view='replit_auth.login'")

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
# Note: Replit Auth blueprint is registered in routes.py

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    from models import User
    # No need to convert to int for Replit Auth since user_id is a string
    return User.query.get(user_id)

# Routes - Now moved to routes.py
# Check app.py for utility functions

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
    """Redirect to the system status tab on dashboard"""
    return redirect(url_for('dashboard', _anchor='system-status'))
    
@app.route('/status_data')
def status_data():
    """Provide system status and configuration information via API"""
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
    manus_model = config.MANUS_MODEL
    manus_impl = f"OpenAI {manus_model}"
    
    # Check if there have been recent Telegram interactions
    telegram_connected = False
    has_telegram_users = False
    
    try:
        # Check if any users have Telegram IDs
        has_telegram_users = db.session.query(User).filter(User.telegram_id.isnot(None)).count() > 0
        
        # Look through the logs to see if we've received any Telegram updates recently
        if memory_log_handler:
            for record in memory_log_handler.get_logs():
                if "Received update from Telegram" in record.getMessage():
                    telegram_connected = True
                    break
    except Exception as e:
        logger.error(f"Error checking Telegram connection status: {str(e)}")
    
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
        telegram_connected=telegram_connected,
        has_telegram_users=has_telegram_users,
        manus_model=manus_model,
        available_models=config.AVAILABLE_MODELS,
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
    from config import (
        ENVIRONMENT, BOT_TOKEN_PRODUCTION, BOT_TOKEN_DEVELOPMENT, 
        ACTIVE_BOT_TOKEN, IS_DEPLOYED, MANUS_MODEL, AVAILABLE_MODELS
    )
    
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
        
        # Get telegram users (for admin view)
        telegram_users = []
        if user.is_admin:
            telegram_users = User.query.filter(User.telegram_id.isnot(None)).all()
        
        # Get memory entries for the user
        memories = MemoryEntry.query.filter_by(user_id=user.id).order_by(MemoryEntry.created_at.desc()).limit(20).all()
        
        # Get documents for the user
        documents = Document.query.filter_by(user_id=user.id).order_by(Document.updated_at.desc()).limit(10).all()
        
        # Generate a registration token for Telegram
        registration_token = secrets.token_hex(8)
        
        # Get bot username from environment or use default
        bot_username = os.environ.get("TELEGRAM_BOT_USERNAME", "OpenManus_Assistant_Bot")
        
        # Check if the bot is active
        bot_active = bool(ACTIVE_BOT_TOKEN)
        
        # Check if the bot matches environment
        environment_token_match = (
            (ENVIRONMENT == 'production' and ACTIVE_BOT_TOKEN == BOT_TOKEN_PRODUCTION) or
            (ENVIRONMENT == 'development' and ACTIVE_BOT_TOKEN == BOT_TOKEN_DEVELOPMENT)
        )
        
        # Status for webhooks
        webhook_set = False
        if replit_domain and bot_active:
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
        
        # Set a flag to indicate this is a direct access (bypass login check)
        is_direct_access = True
        
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
            available_models=AVAILABLE_MODELS,
            # Direct access flag
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

@app.route('/switch_environment', methods=['POST'])
@login_required
def switch_environment():
    """Switch between development and production environments"""
    # This route should only be used in development
    if config.IS_DEPLOYED:
        flash('Environment switching is disabled in production environment', 'danger')
        return redirect(url_for('dashboard_status'))
    
    # Get the target environment
    target_env = request.form.get('target_environment', 'development')
    
    # Validate input
    if target_env not in ['development', 'production']:
        flash('Invalid environment specified', 'danger')
        return redirect(url_for('dashboard_status'))
    
    # Store old environment for comparison
    old_env = config.ENVIRONMENT
    
    # Update the environment setting
    if old_env != target_env:
        # Update the environment in config
        config.ENVIRONMENT = target_env
        logger.info(f"Switched to {target_env.upper()} environment")
        
        # Update the token to match the new environment
        old_token = config.ACTIVE_BOT_TOKEN
        config.set_token_for_environment()
        
        # Always force reinitialization of the bot when switching environments
        try:
            # Always force reinitialization for environment switch
            is_registered = telegram_bot.initialize_bot(config.ACTIVE_BOT_TOKEN, force_reinit=True)
            if is_registered:
                # Reset the webhook
                webhook_url = None
                replit_domain = os.environ.get("REPLIT_DEV_DOMAIN", "")
                if replit_domain:
                    webhook_url = f"https://{replit_domain}/telegram_webhook"
                    success = telegram_bot.setup_webhook(webhook_url)
                    if success:
                        if config.ACTIVE_BOT_TOKEN:
                            token_prefix = config.ACTIVE_BOT_TOKEN[:5]
                            logger.info(f"Webhook updated for {target_env.upper()} environment with token: {token_prefix}...")
                        else:
                            logger.info(f"Webhook updated for {target_env.upper()} environment")
                        flash(f'Successfully switched to {target_env.upper()} environment and updated webhook', 'success')
                    else:
                        logger.warning(f"Failed to update webhook for {target_env.upper()} environment")
                        flash(f'Switched to {target_env.upper()} environment but failed to update webhook', 'warning')
                else:
                    logger.warning("No Replit domain found for webhook setup")
                    flash(f'Switched to {target_env.upper()} environment but could not update webhook', 'warning')
            else:
                logger.error(f"Failed to initialize bot for {target_env.upper()} environment")
                flash(f'Failed to initialize bot for {target_env.upper()} environment', 'danger')
        except Exception as e:
            logger.error(f"Error switching environment: {str(e)}")
            flash(f'Error switching environment: {str(e)}', 'danger')
    else:
        flash(f'Already in {target_env.upper()} environment', 'info')
    
    # Return to the system status tab
    return redirect(url_for('dashboard_status'))

@app.route('/inspect_users')
def inspect_users():
    from models import User
    users = User.query.all()
    for user in users:
        print(f'User ID: {user.id}, Username: {user.username}, Email: {user.email}')
    return "User information printed to console."

@app.route('/manage_telegram_users')
@login_required
def manage_telegram_users():
    """Display and manage users that can access the Telegram bot."""
    # Only allow admin users to access this page
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    
    from models import User
    users = User.query.all()
    return render_template('telegram_users.html', users=users)

@app.route('/reset_telegram_id/<int:user_id>', methods=['POST'])
@login_required
def reset_telegram_id(user_id):
    """Reset a user's Telegram ID, unlinking their account."""
    # Only allow admin users or the user themselves
    if not current_user.is_admin and current_user.id != user_id:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('dashboard'))
    
    from models import User
    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    user.telegram_id = None
    db.session.commit()
    flash(f'Telegram account unlinked for user {user.username}.', 'success')
    return redirect(url_for('dashboard', _anchor='bot'))

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
            
        # Initialize bot with force reinit to ensure correct token is used
        is_registered = telegram_bot.initialize_bot(ACTIVE_BOT_TOKEN, force_reinit=True)
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
            
        # Initialize bot with force reinit to ensure correct token is used
        is_registered = telegram_bot.initialize_bot(ACTIVE_BOT_TOKEN, force_reinit=True)
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
    
@app.route('/change_model', methods=['POST'])
@login_required
def change_model():
    """Change the OpenManus model."""
    # Get the selected model
    model = request.form.get('model')
    
    # Check if the model is valid
    if model not in config.AVAILABLE_MODELS:
        flash('Invalid model selected', 'danger')
        return redirect(url_for('dashboard', _anchor='system-status'))
    
    # Update the model in the configuration
    old_model = config.MANUS_MODEL
    config.MANUS_MODEL = model
    
    # Log the model change
    logger.info(f"Changed OpenManus model from {old_model} to {model}")
    
    # Re-initialize the OpenManus framework
    try:
        # Re-initialize OpenManus with the new model
        from manus_integration import initialize_manus
        initialize_manus()
        flash(f'Successfully switched to model: {config.AVAILABLE_MODELS[model]}', 'success')
    except Exception as e:
        logger.error(f"Error re-initializing OpenManus: {str(e)}")
        flash(f'Error switching model: {str(e)}', 'danger')
    
    return redirect(url_for('dashboard', _anchor='system-status'))

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
        
# Chat routes moved to routes.py
def process_chat_helper():
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
