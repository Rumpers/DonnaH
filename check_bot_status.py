#!/usr/bin/env python3
"""
Bot Status Checker

This script helps troubleshoot Telegram bot configuration issues by checking:
1. The active bot token
2. The current environment setting
3. Webhook status
4. Bot connection status

Run this before deployment to ensure proper configuration.
"""

import os
import sys
import logging
import requests
import json
from config import (
    ACTIVE_BOT_TOKEN, 
    BOT_TOKEN_PRODUCTION, 
    BOT_TOKEN_DEVELOPMENT, 
    ENVIRONMENT, 
    IS_DEPLOYED
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_token_status():
    """Check the status of the bot token."""
    print("=== Bot Token Status ===")
    print(f"Current Environment: {ENVIRONMENT.upper()}")
    print(f"Is Deployed: {IS_DEPLOYED}")
    
    # Check which token is active
    if ACTIVE_BOT_TOKEN == BOT_TOKEN_PRODUCTION:
        print("Active Token: PRODUCTION (TELEGRAM_BOT_TOKEN_DONNAH)")
    elif ACTIVE_BOT_TOKEN == BOT_TOKEN_DEVELOPMENT:
        print("Active Token: DEVELOPMENT (TELEGRAM_BOT_TOKEN_NOENA)")
    else:
        print("Active Token: UNKNOWN")
    
    # Check if tokens are available
    if not BOT_TOKEN_PRODUCTION:
        print("WARNING: Production token (TELEGRAM_BOT_TOKEN_DONNAH) is not set")
    if not BOT_TOKEN_DEVELOPMENT:
        print("WARNING: Development token (TELEGRAM_BOT_TOKEN_NOENA) is not set")
    
    if not ACTIVE_BOT_TOKEN:
        print("ERROR: No active token available")
        return False
    
    return True

def check_bot_connection():
    """Check if we can connect to the Telegram Bot API with the active token."""
    print("\n=== Bot Connection Test ===")
    if not ACTIVE_BOT_TOKEN:
        print("ERROR: No active token available")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{ACTIVE_BOT_TOKEN}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            bot_info = response.json()
            if bot_info.get("ok"):
                print(f"SUCCESS: Connected to bot @{bot_info['result']['username']}")
                print(f"Bot ID: {bot_info['result']['id']}")
                return True
            else:
                print(f"ERROR: Bot API responded with error: {bot_info.get('description')}")
        else:
            print(f"ERROR: Failed to connect to Bot API. Status code: {response.status_code}")
    except Exception as e:
        print(f"ERROR: Exception while connecting to Bot API: {str(e)}")
    
    return False

def check_webhook_status():
    """Check the current webhook status."""
    print("\n=== Webhook Status ===")
    if not ACTIVE_BOT_TOKEN:
        print("ERROR: No active token available")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{ACTIVE_BOT_TOKEN}/getWebhookInfo"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            webhook_info = response.json()
            if webhook_info.get("ok"):
                result = webhook_info['result']
                
                if result.get('url'):
                    print(f"Current Webhook URL: {result['url']}")
                    
                    if result.get('has_custom_certificate'):
                        print("Custom Certificate: Yes")
                    else:
                        print("Custom Certificate: No")
                    
                    if result.get('pending_update_count'):
                        print(f"Pending Updates: {result['pending_update_count']}")
                    else:
                        print("Pending Updates: 0")
                    
                    if result.get('last_error_date'):
                        from datetime import datetime
                        error_time = datetime.fromtimestamp(result['last_error_date'])
                        print(f"Last Error: {error_time} - {result.get('last_error_message', 'Unknown')}")
                    
                    return True
                else:
                    print("No webhook URL set")
            else:
                print(f"ERROR: Bot API responded with error: {webhook_info.get('description')}")
        else:
            print(f"ERROR: Failed to get webhook info. Status code: {response.status_code}")
    except Exception as e:
        print(f"ERROR: Exception while getting webhook info: {str(e)}")
    
    return False

def set_webhook(url=None):
    """Set a webhook URL."""
    print(f"\n=== Setting Webhook to {url} ===")
    if not ACTIVE_BOT_TOKEN:
        print("ERROR: No active token available")
        return False
    
    if not url:
        # Get Replit domain
        replit_domain = os.environ.get("REPLIT_DEV_DOMAIN")
        if not replit_domain:
            print("ERROR: No REPLIT_DEV_DOMAIN environment variable found")
            return False
        
        url = f"https://{replit_domain}/telegram_webhook"
        print(f"Using detected URL: {url}")
    
    try:
        api_url = f"https://api.telegram.org/bot{ACTIVE_BOT_TOKEN}/setWebhook"
        data = {"url": url}
        response = requests.post(api_url, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("ok"):
                print(f"SUCCESS: Webhook set to {url}")
                return True
            else:
                print(f"ERROR: Bot API responded with error: {result.get('description')}")
        else:
            print(f"ERROR: Failed to set webhook. Status code: {response.status_code}")
    except Exception as e:
        print(f"ERROR: Exception while setting webhook: {str(e)}")
    
    return False

def remove_webhook():
    """Remove the webhook."""
    print("\n=== Removing Webhook ===")
    if not ACTIVE_BOT_TOKEN:
        print("ERROR: No active token available")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{ACTIVE_BOT_TOKEN}/deleteWebhook"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("ok"):
                print("SUCCESS: Webhook removed")
                return True
            else:
                print(f"ERROR: Bot API responded with error: {result.get('description')}")
        else:
            print(f"ERROR: Failed to remove webhook. Status code: {response.status_code}")
    except Exception as e:
        print(f"ERROR: Exception while removing webhook: {str(e)}")
    
    return False

def main():
    """Main function."""
    # Banner
    print("=" * 60)
    print(" TELEGRAM BOT CONFIGURATION CHECKER ")
    print("=" * 60)
    
    # Check token status
    token_ok = check_token_status()
    if not token_ok:
        print("\nERROR: No valid token available. Please check environment variables.")
        sys.exit(1)
    
    # Check bot connection
    bot_ok = check_bot_connection()
    if not bot_ok:
        print("\nERROR: Could not connect to Telegram Bot API. Please check token.")
        sys.exit(1)
    
    # Check webhook status
    webhook_ok = check_webhook_status()
    
    # Menu
    while True:
        print("\n" + "=" * 60)
        print(" ACTIONS ")
        print("=" * 60)
        print("1. Recheck current status")
        print("2. Set webhook to Replit URL")
        print("3. Set webhook to custom URL")
        print("4. Remove webhook")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ")
        
        if choice == "1":
            check_token_status()
            check_bot_connection()
            check_webhook_status()
        elif choice == "2":
            set_webhook()
            check_webhook_status()
        elif choice == "3":
            custom_url = input("Enter custom webhook URL: ")
            set_webhook(custom_url)
            check_webhook_status()
        elif choice == "4":
            remove_webhook()
            check_webhook_status()
        elif choice == "5":
            print("\nExiting...")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()