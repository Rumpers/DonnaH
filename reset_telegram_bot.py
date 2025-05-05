#!/usr/bin/env python3
"""
Telegram Bot Reset Utility

This script forcefully reinitializes the Telegram bot and configures the webhook,
which can help resolve issues with the bot not responding after deployment.

Usage:
    python reset_telegram_bot.py [--environment production|development] [--webhook URL]
"""

import os
import sys
import argparse
import logging
from flask import Flask
import config
import telegram_bot
from app import db

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Reset and reinitialize the Telegram bot.')
    parser.add_argument('--environment', choices=['production', 'development'], 
                        help='Set the environment to use (production or development)')
    parser.add_argument('--webhook', help='Set a custom webhook URL')
    return parser.parse_args()

def reset_bot(environment=None, webhook_url=None):
    """Reset and reinitialize the Telegram bot."""
    # Create a minimal Flask app context
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///manus_assistant.db")
    db.init_app(app)
    
    with app.app_context():
        # Set environment if specified
        if environment:
            old_env = config.ENVIRONMENT
            config.ENVIRONMENT = environment
            logger.info(f"Changed environment from {old_env} to {environment}")
            
            # Update the token to match the new environment
            old_token = config.ACTIVE_BOT_TOKEN
            config.set_token_for_environment()
            if old_token != config.ACTIVE_BOT_TOKEN:
                logger.info(f"Token updated for {environment} environment")
        
        # Get the active token
        token = config.ACTIVE_BOT_TOKEN
        if not token:
            logger.error(f"No token available for {config.ENVIRONMENT} environment")
            return False
        
        # Print environment and token info
        logger.info(f"Current environment: {config.ENVIRONMENT.upper()}")
        token_type = "Production" if token == config.BOT_TOKEN_PRODUCTION else "Development"
        token_prefix = token[:5] if token else "N/A"
        logger.info(f"Using {token_type} token: {token_prefix}...")
        
        # Force reinitialize the bot
        logger.info("Forcefully reinitializing the bot...")
        is_registered = telegram_bot.initialize_bot(token, force_reinit=True)
        if not is_registered:
            logger.error("Failed to initialize bot")
            return False
        
        logger.info("Bot successfully initialized")
        
        # Set up webhook if needed
        if webhook_url:
            logger.info(f"Setting webhook to: {webhook_url}")
        else:
            # Get the Replit domain
            replit_domain = os.environ.get("REPLIT_DEV_DOMAIN")
            if not replit_domain:
                logger.error("No REPLIT_DEV_DOMAIN environment variable found")
                return False
            
            webhook_url = f"https://{replit_domain}/telegram_webhook"
            logger.info(f"Using detected webhook URL: {webhook_url}")
        
        # Set the webhook
        success = telegram_bot.setup_webhook(webhook_url)
        if success:
            logger.info(f"Webhook successfully set to {webhook_url}")
        else:
            logger.error("Failed to set webhook")
            return False
        
        return True

def main():
    """Main function."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Print banner
    print("=" * 60)
    print(" TELEGRAM BOT RESET UTILITY ")
    print("=" * 60)
    
    # Reset the bot
    success = reset_bot(args.environment, args.webhook)
    
    if success:
        print("\nBot successfully reset and initialized!")
        print("The Telegram bot should now be operational.")
    else:
        print("\nFailed to reset and initialize the bot.")
        print("Check the logs above for error messages.")
        sys.exit(1)

if __name__ == "__main__":
    main()