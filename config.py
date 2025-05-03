import os
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Bot configuration
# Support different environments with separate bot tokens
BOT_TOKEN_PRODUCTION = os.environ.get("TELEGRAM_BOT_TOKEN_DONNAH")  # Production bot token
BOT_TOKEN_DEVELOPMENT = os.environ.get("TELEGRAM_BOT_TOKEN_NOENA")  # Development bot token

# Check if this is a deployed environment (not the Replit development server)
IS_DEPLOYED = not os.environ.get("REPLIT_DEV_DOMAIN", "").endswith("janeway.replit.dev")

# Set environment and token based on deployment status
if IS_DEPLOYED:
    # When deployed, ONLY use the production token
    ACTIVE_BOT_TOKEN = BOT_TOKEN_PRODUCTION
    ENVIRONMENT = "production"
else:
    # In development (Replit), use development token, production token is not allowed
    ACTIVE_BOT_TOKEN = BOT_TOKEN_DEVELOPMENT
    ENVIRONMENT = "development"

# Log deployment status
logger.info(f"Deployment status: {'DEPLOYED' if IS_DEPLOYED else 'DEVELOPMENT'}")

# Google API configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

# OpenManus configuration
MANUS_API_KEY = os.environ.get("MANUS_API_KEY")
MANUS_API_URL = os.environ.get("MANUS_API_URL", "https://api.openmanus.ai")

# Database configuration
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///manus_assistant.db")

# Vector database configuration
VECTOR_DB_PATH = os.environ.get("VECTOR_DB_PATH", "./vector_db")

# Flask configuration
SESSION_SECRET = os.environ.get("SESSION_SECRET", "dev_secret_key")
FLASK_ENV = os.environ.get("FLASK_ENV", "development")
FLASK_PORT = int(os.environ.get("FLASK_PORT", 5000))
FLASK_HOST = os.environ.get("FLASK_HOST", "0.0.0.0")

# Check required environment variables
def check_env_vars():
    """Check if all required environment variables are set."""
    # Check if at least one of the Telegram tokens is available
    has_telegram_token = bool(ACTIVE_BOT_TOKEN)
    
    required_vars = {
        "Bot Token (either TELEGRAM_BOT_TOKEN_DonnaH or TELEGRAM_BOT_TOKEN_Noena)": has_telegram_token,
        "GOOGLE_CLIENT_ID": GOOGLE_CLIENT_ID,
        "GOOGLE_CLIENT_SECRET": GOOGLE_CLIENT_SECRET,
        "MANUS_API_KEY": MANUS_API_KEY
    }
    
    missing_vars = [var for var, value in required_vars.items() if not value]
    
    if missing_vars:
        logger.warning(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    # Log which token and environment are being used
    if IS_DEPLOYED and not BOT_TOKEN_PRODUCTION:
        logger.error("DEPLOYED ENVIRONMENT MISSING PRODUCTION TOKEN! TELEGRAM_BOT_TOKEN_DONNAH must be configured")
        # We still return True to allow app to start, but log a serious error
    
    if BOT_TOKEN_PRODUCTION:
        logger.info(f"Using Production token (TELEGRAM_BOT_TOKEN_DonnaH) in {ENVIRONMENT} mode")
    elif BOT_TOKEN_DEVELOPMENT:
        logger.info(f"Using Development token (TELEGRAM_BOT_TOKEN_Noena) in {ENVIRONMENT} mode")
    else:
        logger.warning("No Telegram bot token configured")
    
    return True
