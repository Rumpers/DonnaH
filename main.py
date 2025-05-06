import os
import logging
import config

# Ensure environment variable is set at startup
if not os.environ.get("MANUS_ENVIRONMENT"):
    os.environ["MANUS_ENVIRONMENT"] = config.ENVIRONMENT

# Configure logging first
logging.basicConfig(
    level=logging.INFO if config.IS_DEPLOYED else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s' if config.IS_DEPLOYED else '%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)

# Import app after logging is configured
from app import app
# Import routes after app to register blueprints
import routes

# Log startup information
logger.info(f"Starting application in {config.ENVIRONMENT.upper()} mode")
logger.info(f"Deployment status: {'DEPLOYED' if config.IS_DEPLOYED else 'DEVELOPMENT'}")

# Get the domain for webhook setup
replit_domain = os.environ.get("REPLIT_DEV_DOMAIN", "")
if replit_domain:
    logger.info(f"REPLIT_DEV_DOMAIN: {replit_domain}")
    logger.info(f"Replit Redirect URI: https://{replit_domain}/google_login/callback")

if __name__ == "__main__":
    # Only use debug mode in development, not in production
    debug_mode = not config.IS_DEPLOYED
    
    # Get port from environment or use default 5000
    port = int(os.environ.get("PORT", 5000))
    
    logger.info(f"Starting server on port {port} with debug={debug_mode}")
    
    # Run the application
    app.run(
        host="0.0.0.0",  # Listen on all network interfaces
        port=port,
        debug=debug_mode
    )
