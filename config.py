import os
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Bot configuration
# Support multiple bot tokens for different environments
BOT_TOKEN_DONNAH = os.environ.get("TELEGRAM_BOT_TOKEN_DonnaH")
BOT_TOKEN_NOENA = os.environ.get("TELEGRAM_BOT_TOKEN_Noena")
# For backward compatibility
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# Determine which token to use
ACTIVE_BOT_TOKEN = BOT_TOKEN_DONNAH or BOT_TOKEN_NOENA or BOT_TOKEN

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
        "Bot Token (at least one of TELEGRAM_TOKEN, TELEGRAM_BOT_TOKEN_DonnaH, or TELEGRAM_BOT_TOKEN_Noena)": has_telegram_token,
        "GOOGLE_CLIENT_ID": GOOGLE_CLIENT_ID,
        "GOOGLE_CLIENT_SECRET": GOOGLE_CLIENT_SECRET,
        "MANUS_API_KEY": MANUS_API_KEY
    }
    
    missing_vars = [var for var, value in required_vars.items() if not value]
    
    if missing_vars:
        logger.warning(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    # Log which bot token is being used
    if BOT_TOKEN_DONNAH:
        logger.info("Using TELEGRAM_BOT_TOKEN_DonnaH")
    elif BOT_TOKEN_NOENA:
        logger.info("Using TELEGRAM_BOT_TOKEN_Noena")
    elif BOT_TOKEN:
        logger.info("Using TELEGRAM_TOKEN")
    else:
        logger.warning("No Telegram bot token configured")
    
    return True
