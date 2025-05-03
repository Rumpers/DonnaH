import os
import logging
import threading
import asyncio
import requests
import base64
import io

# Create a singleton event loop manager
class EventLoopManager:
    _instance = None
    _loop = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventLoopManager, cls).__new__(cls)
            cls._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(cls._loop)
        return cls._instance
    
    @property
    def loop(self):
        return self._loop
    
    def run_coroutine(self, coroutine):
        """Run a coroutine in the managed event loop"""
        return self._loop.run_until_complete(coroutine)
        
    def close(self):
        """Close the event loop (only do this at application shutdown)"""
        if self._loop and not self._loop.is_closed():
            self._loop.close()
            self._loop = None
from datetime import datetime
import google_services
import memory_system
import document_processor
import manus_integration
from models import User, Conversation, Message
from app import db

# Try to import Telegram packages, but provide fallbacks if not available
# This allows development and testing without the telegram package
try:
    from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        ConversationHandler,
        CallbackContext,
        filters
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    # Create mock classes for development
    class Update:
        pass

    class CallbackContext:
        pass

    class ConversationHandler:
        END = -1

    TELEGRAM_AVAILABLE = False
    logging.warning("Telegram package not available. Bot functionality will be limited.")

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Import ACTIVE_BOT_TOKEN from config
from config import ACTIVE_BOT_TOKEN

# Define conversation states
MAIN_MENU = 0
EMAIL = 1
CALENDAR = 2
DRIVE = 3
MEMORY = 4
DOCUMENT = 5

# Bot instance
bot_application = None

async def start(update: Update, context: CallbackContext) -> int:
    """Start conversation with the user."""
    user = update.effective_user
    telegram_id = str(user.id)

    # Check if user exists in the database
    db_user = User.query.filter_by(telegram_id=telegram_id).first()

    if not db_user:
        # User is not registered yet - set state to wait for user ID
        context.user_data['awaiting_user_id'] = True

        await update.message.reply_text(
            f"Hi {user.first_name}! I don't recognize your Telegram account.\n\n"
            "To link this Telegram account with your registered web account, "
            "please enter your user ID number.\n"
            "You can find your user ID on the dashboard in the Telegram Bot section."
        )
        return MAIN_MENU  # Use MAIN_MENU state but with a flag to handle the user ID entry

    # Create new conversation
    conversation = Conversation(user_id=db_user.id)
    db.session.add(conversation)
    db.session.commit()

    # Store conversation ID in user context
    context.user_data['conversation_id'] = conversation.id

    keyboard = [
        ['📧 Email', '📅 Calendar'],
        ['🧠 Memory', '❓ Help']
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    await update.message.reply_text(
        f"Hello {user.first_name}! I'm your executive assistant. How can I help you today?",
        reply_markup=reply_markup
    )

    # Save this message to the database
    message = Message(
        conversation_id=conversation.id,
        content=f"Hello {user.first_name}! I'm your executive assistant. How can I help you today?",
        is_user=False
    )
    db.session.add(message)
    db.session.commit()

    return MAIN_MENU

async def handle_email(update: Update, context: CallbackContext) -> int:
    """Handle email-related requests."""
    user = update.effective_user
    telegram_id = str(user.id)
    db_user = User.query.filter_by(telegram_id=telegram_id).first()

    # Save user message to database
    if 'conversation_id' in context.user_data:
        message = Message(
            conversation_id=context.user_data['conversation_id'],
            content=update.message.text,
            is_user=True
        )
        db.session.add(message)
        db.session.commit()

    await update.message.reply_text("What would you like to do with your emails?\n\n"
                                   "You can say things like:\n"
                                   "- Check my inbox\n"
                                   "- Show unread emails\n"
                                   "- Send an email to [recipient]\n"
                                   "- Search emails about [topic]")

    return EMAIL

async def handle_calendar(update: Update, context: CallbackContext) -> int:
    """Handle calendar-related requests."""
    user = update.effective_user
    telegram_id = str(user.id)
    db_user = User.query.filter_by(telegram_id=telegram_id).first()

    # Save user message to database
    if 'conversation_id' in context.user_data:
        message = Message(
            conversation_id=context.user_data['conversation_id'],
            content=update.message.text,
            is_user=True
        )
        db.session.add(message)
        db.session.commit()

    await update.message.reply_text("What would you like to do with your calendar?\n\n"
                                   "You can say things like:\n"
                                   "- Show my schedule for today\n"
                                   "- What meetings do I have tomorrow?\n"
                                   "- Schedule a meeting with [person] about [topic]\n"
                                   "- Find a free slot next week")

    return CALENDAR

async def handle_drive(update: Update, context: CallbackContext) -> int:
    """Handle Google Drive-related requests."""
    user = update.effective_user
    telegram_id = str(user.id)
    db_user = User.query.filter_by(telegram_id=telegram_id).first()

    # Save user message to database
    if 'conversation_id' in context.user_data:
        message = Message(
            conversation_id=context.user_data['conversation_id'],
            content=update.message.text,
            is_user=True
        )
        db.session.add(message)
        db.session.commit()

    await update.message.reply_text("What would you like to do with Google Drive?\n\n"
                                   "You can say things like:\n"
                                   "- List recent documents\n"
                                   "- Find files about [topic]\n"
                                   "- Create a new document named [name]\n"
                                   "- Share [document] with [email]")

    return DRIVE

async def handle_memory(update: Update, context: CallbackContext) -> int:
    """Handle memory-related requests."""
    user = update.effective_user
    telegram_id = str(user.id)
    db_user = User.query.filter_by(telegram_id=telegram_id).first()

    # Save user message to database
    if 'conversation_id' in context.user_data:
        message = Message(
            conversation_id=context.user_data['conversation_id'],
            content=update.message.text,
            is_user=True
        )
        db.session.add(message)
        db.session.commit()

    await update.message.reply_text("What would you like to remember or recall?\n\n"
                                   "You can say things like:\n"
                                   "- Remember that [information]\n"
                                   "- What do you know about [topic]?\n"
                                   "- Tell me about [person/project]\n"
                                   "- When did we last discuss [topic]?")

    return MEMORY

async def handle_document(update: Update, context: CallbackContext) -> int:
    """Handle document-related requests."""
    user = update.effective_user
    telegram_id = str(user.id)
    db_user = User.query.filter_by(telegram_id=telegram_id).first()

    # Save user message to database
    if 'conversation_id' in context.user_data:
        message = Message(
            conversation_id=context.user_data['conversation_id'],
            content=update.message.text,
            is_user=True
        )
        db.session.add(message)
        db.session.commit()

    await update.message.reply_text("What would you like to do with documents?\n\n"
                                   "You can say things like:\n"
                                   "- Create a summary of [document]\n"
                                   "- File this document under [category]\n"
                                   "- Extract information from [document]\n"
                                   "- Find documents related to [topic]")

    return DOCUMENT

async def handle_help(update: Update, context: CallbackContext) -> int:
    """Handle help requests."""
    # Save user message to database
    if 'conversation_id' in context.user_data:
        message = Message(
            conversation_id=context.user_data['conversation_id'],
            content=update.message.text,
            is_user=True
        )
        db.session.add(message)
        db.session.commit()

    help_text = (
        "I'm your executive assistant powered by OpenManus. Here's what I can help you with:\n\n"
        "📧 *Email*: Check inbox, send emails, search for messages\n"
        "📅 *Calendar*: View schedule, create events, find free time\n"
        "🧠 *Memory*: Remember information and recall it later\n\n"
        "You can navigate using the keyboard menu or simply tell me what you need help with!"
    )

    # Save bot response to database
    if 'conversation_id' in context.user_data:
        bot_message = Message(
            conversation_id=context.user_data['conversation_id'],
            content=help_text,
            is_user=False
        )
        db.session.add(bot_message)
        db.session.commit()

    keyboard = [
        ['📧 Email', '📅 Calendar'],
        ['🧠 Memory', '❓ Help']
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    await update.message.reply_text(
        help_text,
        reply_markup=reply_markup
    )

    return MAIN_MENU

async def process_message(update: Update, context: CallbackContext) -> int:
    """Process user messages using OpenManus framework."""
    user = update.effective_user
    telegram_id = str(user.id)
    
    # Check if this is a photo message
    if hasattr(update.message, 'photo') and update.message.photo:
        logger.info("Processing photo message from conversation handler")
        chat_id = update.message.chat_id
        
        # Check if user exists in database
        from models import User
        db_user = User.query.filter_by(telegram_id=telegram_id).first()
        
        if not db_user:
            await update.message.reply_text(
                "I don't recognize your Telegram account. Please register through the web interface or link your account by using the /start command."
            )
            return MAIN_MENU
        
        try:
            # Get the largest photo (best quality)
            photo = update.message.photo[-1]
            file_id = photo.file_id
            
            # Get file from Telegram
            file = await context.bot.get_file(file_id)
            file_path = file.file_path
            
            # Process photo
            await process_photo(context.bot, db_user, file_path, chat_id)
            return MAIN_MENU
        except Exception as e:
            logger.error(f"Error processing photo in conversation handler: {e}")
            await update.message.reply_text(f"I encountered an error processing your photo: {str(e)}")
            return MAIN_MENU
    
    # For text messages, proceed as usual
    user_message = update.message.text
    
    # Check if we're waiting for a user ID for account linking
    if 'awaiting_user_id' in context.user_data and context.user_data['awaiting_user_id']:
        try:
            user_id_text = user_message.strip()
            user_id = int(user_id_text)

            # Check if user exists
            from models import User

            user = User.query.get(user_id)
            if user:
                # Link Telegram ID to user
                user.telegram_id = telegram_id
                db.session.commit()

                # Clear the awaiting flag
                context.user_data.pop('awaiting_user_id', None)

                # Create a new conversation
                conversation = Conversation(user_id=user.id)
                db.session.add(conversation)
                db.session.commit()

                # Store conversation ID in user context
                context.user_data['conversation_id'] = conversation.id

                keyboard = [
                    ['📧 Email', '📅 Calendar'],
                    ['🧠 Memory', '❓ Help']
                ]

                reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

                await update.message.reply_text(
                    f"Account linked successfully! Welcome, {user.username}!\n\n"
                    "You can now use your assistant through Telegram. How can I help you today?",
                    reply_markup=reply_markup
                )

                # Save this message to the database
                message = Message(
                    conversation_id=conversation.id,
                    content=f"Account linked successfully! Welcome, {user.username}! How can I help you today?",
                    is_user=False
                )
                db.session.add(message)
                db.session.commit()

                return MAIN_MENU
            else:
                await update.message.reply_text(
                    "User ID not found. Please check the ID and try again, or register through the web interface."
                )
                return MAIN_MENU

        except ValueError:
            await update.message.reply_text(
                "Invalid user ID format. Please enter a numeric ID."
            )
            return MAIN_MENU

    # Normal message processing
    db_user = User.query.filter_by(telegram_id=telegram_id).first()

    # If user not found in database, prompt to register
    if not db_user:
        await update.message.reply_text(
            "I don't recognize your Telegram account. Please register through the web interface or link your account by using the /start command."
        )
        return ConversationHandler.END

    # Save user message to database
    if 'conversation_id' in context.user_data:
        message = Message(
            conversation_id=context.user_data['conversation_id'],
            content=user_message,
            is_user=True
        )
        db.session.add(message)
        db.session.commit()

    try:
        # Process message with OpenManus framework
        response = manus_integration.process_message(db_user, user_message, context.user_data.get('current_state', MAIN_MENU))

        # Save bot response to database
        if 'conversation_id' in context.user_data:
            bot_message = Message(
                conversation_id=context.user_data['conversation_id'],
                content=response,
                is_user=False
            )
            db.session.add(bot_message)
            db.session.commit()

        await update.message.reply_text(response)

        # Return to main menu for simplicity
        # In a more complex implementation, we would determine the next state based on the message content
        return context.user_data.get('current_state', MAIN_MENU)
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await update.message.reply_text(f"I encountered an error processing your request: {str(e)}")
        return MAIN_MENU

async def process_photo(bot, user, file_path, chat_id):
    """
    Process a photo message and extract information if it's a business card.
    
    Args:
        bot: The Telegram bot instance
        user: The database user
        file_path: Path to the Telegram file
        chat_id: The chat ID for sending responses
    
    Returns:
        True if processing was successful, False otherwise
    """
    global ACTIVE_BOT_TOKEN
    logger.info(f"Starting to process photo from {file_path} for chat {chat_id}")
    try:
        logger.info(f"Processing photo at {file_path}")
        
        # Grab the image from Telegram's servers
        # Always use the clean path approach without relying on the path format
        # This ensures we don't have URL duplication issues
        
        # Check if file_path already contains the bot token (which means it's a full URL)
        if ACTIVE_BOT_TOKEN in file_path:
            logger.info("File path already contains bot token, extracting clean path")
            # Extract just the path portion from the full URL
            token_parts = file_path.split(ACTIVE_BOT_TOKEN)
            if len(token_parts) > 1 and "/" in token_parts[1]:
                # Get everything after the first slash following the token
                clean_path = token_parts[1].split("/", 1)[1]
                logger.info(f"Extracted clean path: {clean_path}")
                file_path = clean_path
        
        # According to Telegram Bot API docs, the correct file URL format is:
        # https://api.telegram.org/file/bot<token>/<file_path>
        # Let's make sure we're using that exact format
        
        # First, clean any tokens or API references from file_path if present
        if "api.telegram.org" in file_path or "bot" in file_path:
            logger.info("Cleaning file_path of API references")
            # Extract just the path portion (likely photos/file_X.jpg)
            parts = file_path.split("/")
            # Look for the 'photos' directory in the path
            for i, part in enumerate(parts):
                if part == "photos" and i < len(parts) - 1:
                    # Found the photos directory, use it and everything after
                    file_path = "/".join(parts[i:])
                    logger.info(f"Cleaned file_path to: {file_path}")
                    break
        
        # Now construct the URL using the standard Telegram API format
        image_url = f"https://api.telegram.org/file/bot{ACTIVE_BOT_TOKEN}/{file_path}"
        logger.info(f"Final download URL: {image_url}")
        
        # Add detailed logging - don't expose full token for security
        if ACTIVE_BOT_TOKEN:
            logger.info(f"ACTIVE_BOT_TOKEN (partial): {ACTIVE_BOT_TOKEN[:5]}...{ACTIVE_BOT_TOKEN[-5:]}")
        else:
            logger.error("ACTIVE_BOT_TOKEN is None or empty!")
            
        logger.info(f"file_path: {file_path}")
        
        try:
            response = requests.get(image_url)
            logger.info(f"Download response status code: {response.status_code}")
            logger.info(f"Response headers: {response.headers}")
            
            if response.status_code != 200:
                logger.error(f"Failed to download image: HTTP {response.status_code}")
                logger.error(f"Response content: {response.content[:1000]}")
                
                # Try without the bot token as a fallback
                fallback_url = f"https://api.telegram.org/file/{file_path}"
                logger.info(f"Trying fallback URL: {fallback_url}")
                fallback_response = requests.get(fallback_url)
                
                if fallback_response.status_code == 200:
                    logger.info("Fallback URL worked!")
                    response = fallback_response
                else:
                    await bot.send_message(
                        chat_id=chat_id,
                        text="I couldn't download the image. Please try again later."
                    )
                    return False
            
        except Exception as e:
            logger.error(f"Exception during image download: {str(e)}")
            await bot.send_message(
                chat_id=chat_id,
                text=f"Error downloading image: {str(e)}"
            )
            return False
            
        logger.info("Successfully downloaded image from Telegram servers")
        
        # Convert to base64
        image_bytes = response.content
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        # Use OpenAI's vision capabilities to analyze the image
        from openai import OpenAI
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        # Create conversation with image
        logger.info("Sending image to OpenAI for analysis")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system", 
                    "content": "You are an AI assistant that specializes in analyzing images of business cards. " 
                              "When you see a business card, extract all the information from it including: " 
                              "name, title, company, phone number, email, website, address, and any other " 
                              "relevant details. Format the response as JSON with these fields. " 
                              "If the image is not a business card, reply with a JSON object with a single field " 
                              "'is_business_card': false and 'description' field explaining what the image shows."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyze this image and tell me if it's a business card. If it is, extract all the information from it."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ],
                }
            ],
            max_tokens=1000,
            response_format={"type": "json_object"},
        )
        
        analysis_result = response.choices[0].message.content
        logger.info(f"Image analysis complete: {analysis_result}")
        
        # Parse the JSON response
        import json
        card_data = json.loads(analysis_result)
        
        # Create a new conversation if one doesn't exist
        if not hasattr(user, 'conversation_id'):
            conversation = Conversation(user_id=user.id)
            db.session.add(conversation)
            db.session.commit()
            conversation_id = conversation.id
        else:
            conversation_id = user.conversation_id
        
        # Save the image message to the database
        image_message = Message(
            conversation_id=conversation_id,
            content="[User sent an image]",
            is_user=True
        )
        db.session.add(image_message)
        db.session.commit()
        
        # Check if it's a business card
        if card_data.get('is_business_card', True):
            # Format a nice response with the extracted information
            card_info = []
            if 'name' in card_data:
                card_info.append(f"👤 *Name*: {card_data['name']}")
            if 'title' in card_data:
                card_info.append(f"📋 *Title*: {card_data['title']}")
            if 'company' in card_data:
                card_info.append(f"🏢 *Company*: {card_data['company']}")
            if 'phone' in card_data:
                card_info.append(f"📱 *Phone*: {card_data['phone']}")
            if 'email' in card_data:
                card_info.append(f"📧 *Email*: {card_data['email']}")
            if 'website' in card_data:
                card_info.append(f"🌐 *Website*: {card_data['website']}")
            if 'address' in card_data:
                card_info.append(f"📍 *Address*: {card_data['address']}")
            
            # Extra fields that might be present
            for key, value in card_data.items():
                if key not in ['name', 'title', 'company', 'phone', 'email', 'website', 'address', 'is_business_card'] and value:
                    card_info.append(f"ℹ️ *{key.capitalize()}*: {value}")
            
            # Create the full response message
            if card_info:
                response_text = "I've identified this as a business card and extracted the following information:\n\n" + "\n".join(card_info) + "\n\nHow do you know this person? Would you like me to save this contact to your memory?"
            else:
                response_text = "This appears to be a business card, but I couldn't extract specific details. Could you please provide more information about this contact?"
            
            # Save to memory system if clearly a business card
            memory_title = card_data.get('name', 'Unknown Contact')
            memory_content = json.dumps(card_data)
            memory_entry = memory_system.add_memory(user, 'contact', memory_title, memory_content)
            
            # Send response
            await bot.send_message(
                chat_id=chat_id,
                text=response_text,
                parse_mode="Markdown"
            )
            
            # Save bot response to the database
            bot_message = Message(
                conversation_id=conversation_id,
                content=response_text,
                is_user=False
            )
            db.session.add(bot_message)
            db.session.commit()
            
            return True
        else:
            # Not a business card
            description = card_data.get('description', 'an image that is not a business card')
            response_text = f"This doesn't appear to be a business card. It looks like {description}. How can I help you with this image?"
            
            await bot.send_message(
                chat_id=chat_id,
                text=response_text
            )
            
            # Save bot response to the database
            bot_message = Message(
                conversation_id=conversation_id,
                content=response_text,
                is_user=False
            )
            db.session.add(bot_message)
            db.session.commit()
            
            return True
    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=f"I encountered an error processing your image: {str(e)}"
            )
        except Exception as send_error:
            logger.error(f"Error sending error message: {send_error}")
        return False

async def cancel(update: Update, context: CallbackContext) -> int:
    """Cancel the conversation."""
    user = update.effective_user

    # Close the conversation in the database if it exists
    if 'conversation_id' in context.user_data:
        conversation = Conversation.query.get(context.user_data['conversation_id'])
        if conversation:
            from datetime import datetime
            conversation.end_time = datetime.utcnow()
            db.session.commit()

    await update.message.reply_text(
        "Conversation ended. Type /start to begin a new conversation.",
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END

# Global variable to track the bot thread
bot_thread = None

def initialize_bot(token, webhook_url=None):
    """
    Initialize the Telegram bot with the given token.

    Args:
        token (str): The Telegram bot token
        webhook_url (str, optional): The webhook URL for the bot. If provided,
                                   the bot will be set up to use webhooks.
    """
    global bot_application, bot_thread

    # Check if bot is already initialized
    if bot_application is not None:
        logger.info("Telegram bot is already initialized")
        return True

    try:
        # Create the Application
        bot_application = Application.builder().token(token).build()

        # Create conversation handler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                MAIN_MENU: [
                    MessageHandler(filters.Regex('^📧 Email$'), handle_email),
                    MessageHandler(filters.Regex('^📅 Calendar$'), handle_calendar),
                    MessageHandler(filters.Regex('^🧠 Memory$'), handle_memory),
                    MessageHandler(filters.Regex('^❓ Help$'), handle_help),
                    MessageHandler(filters.PHOTO, process_message),  # Added to handle photos
                    MessageHandler(filters.TEXT & ~filters.COMMAND, process_message),
                ],
                EMAIL: [
                    MessageHandler(filters.PHOTO, process_message),  # Added to handle photos
                    MessageHandler(filters.TEXT & ~filters.COMMAND, process_message),
                ],
                CALENDAR: [
                    MessageHandler(filters.PHOTO, process_message),  # Added to handle photos
                    MessageHandler(filters.TEXT & ~filters.COMMAND, process_message),
                ],
                MEMORY: [
                    MessageHandler(filters.PHOTO, process_message),  # Added to handle photos
                    MessageHandler(filters.TEXT & ~filters.COMMAND, process_message),
                ],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )

        bot_application.add_handler(conv_handler)

        # Bot is now ready to be used with webhooks
        logger.info("Telegram bot initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing Telegram bot: {e}")
        return False

def process_update(update_data):
    """
    Process an update from Telegram webhook.

    Args:
        update_data (dict): The update data from Telegram
    """
    if bot_application is None:
        logger.error("Bot application not initialized")
        return False

    try:
        # Convert the update data to a Telegram Update object
        update = Update.de_json(data=update_data, bot=bot_application.bot)

        # Check if this is a message update (could be other types like callback_query, etc.)
        if not hasattr(update, 'message') or update.message is None:
            logger.info("Received a non-message update, ignoring")
            return True

        # Check if message has text or photo
        if not hasattr(update.message, 'text') or update.message.text is None:
            # Check if message has photo
            if hasattr(update.message, 'photo') and update.message.photo:
                # Handle photo message
                chat_id = update.message.chat_id
                user_id = update.message.from_user.id
                telegram_id = str(user_id)
                
                # Check if user exists in database
                from models import User
                db_user = User.query.filter_by(telegram_id=telegram_id).first()
                
                if not db_user:
                    try:
                        import asyncio
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(bot_application.bot.send_message(
                            chat_id=chat_id,
                            text="I don't recognize your Telegram account. Please register through the web interface or link your account by using the /start command."
                        ))
                        loop.close()
                    except Exception as e:
                        logger.error(f"Error sending message: {e}")
                    return True
                
                # Process the photo message
                try:
                    logger.info("Processing photo message")
                    # Get the largest photo (best quality)
                    photo = update.message.photo[-1]
                    file_id = photo.file_id
                    
                    # Use the event loop manager for async operations
                    loop_manager = EventLoopManager()
                    
                    try:
                        # Get file from Telegram
                        file = loop_manager.run_coroutine(bot_application.bot.get_file(file_id))
                        file_path = file.file_path
                        
                        # Log the raw file path for debugging
                        logger.info(f"Original file_path from Telegram: {file_path}")
                        
                        # Ensure we're only using the relative path part, not a full URL
                        if "https://api.telegram.org/file/bot" in file_path:
                            # Extract just the path portion after the token
                            parts = file_path.split("/file/bot")
                            if len(parts) > 1:
                                token_and_path = parts[1]
                                # Extract just the path after the token
                                path_parts = token_and_path.split("/", 1)
                                if len(path_parts) > 1:
                                    file_path = path_parts[1]
                                    logger.info(f"Extracted file_path: {file_path}")
                        
                        # Process photo using the same loop
                        response = loop_manager.run_coroutine(
                            process_photo(bot_application.bot, db_user, file_path, chat_id)
                        )
                    except Exception as e:
                        logger.error(f"Error in event loop manager: {e}")
                        # Send an error message
                        loop_manager.run_coroutine(
                            bot_application.bot.send_message(
                                chat_id=chat_id, 
                                text=f"Error processing image: {str(e)}"
                            )
                        )
                    
                    return True
                except Exception as e:
                    logger.error(f"Error processing photo: {e}")
                    try:
                        # Use event loop manager for error sending
                        loop_manager = EventLoopManager()
                        loop_manager.run_coroutine(
                            bot_application.bot.send_message(
                                chat_id=chat_id,
                                text=f"I encountered an error processing your photo: {str(e)}"
                            )
                        )
                    except Exception as send_error:
                        logger.error(f"Error sending error message: {send_error}")
                    return True
            else:
                logger.info("Received a message without text or photo, ignoring")
                return True

        # Handle the update manually instead of using process_update
        # This avoids the "Application not initialized" error
        chat_id = update.message.chat_id
        user_id = update.message.from_user.id
        text = update.message.text

        logger.info(f"Received message from user {user_id} in chat {chat_id}: {text}")

        # Check if this is a command
        if text.startswith('/'):
            if text.startswith('/start'):
                # Check if user exists in the database
                from models import User
                telegram_id = str(user_id)
                db_user = User.query.filter_by(telegram_id=telegram_id).first()

                if db_user:
                    # User already registered
                    try:
                        bot_application.bot.send_message(
                            chat_id=chat_id,
                            text=f"Welcome back, {db_user.username}! How can I help you today?\n\n"
                                 "You can ask me about your emails, calendar events, documents, or anything else you need help with."
                        )
                    except Exception as e:
                        logger.error(f"Error sending welcome message: {e}")
                        # Fallback to a direct HTTP request
                        try:
                            import requests
                            telegram_token = os.environ.get("TELEGRAM_TOKEN")
                            requests.post(
                                f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                                json={"chat_id": chat_id, "text": f"Welcome back, {db_user.username}! How can I help you today?\n\nYou can ask me about your emails, calendar events, documents, or anything else you need help with."}
                            )
                        except Exception as http_error:
                            logger.error(f"Failed fallback request: {http_error}")
                else:
                    # User not registered - prompt for linking with user ID
                    try:
                        bot_application.bot.send_message(
                            chat_id=chat_id,
                            text="Welcome to OpenManus Executive Assistant! I'm your AI-powered assistant.\n\n"
                                 "To link this Telegram account with your registered web account, please enter your user ID number.\n"
                                 "You can find your user ID on the dashboard in the Telegram Bot section."
                        )
                    except Exception as e:
                        logger.error(f"Error sending welcome message: {e}")
                        # Fallback to a direct HTTP request
                        try:
                            import requests
                            telegram_token = os.environ.get("TELEGRAM_TOKEN")
                            requests.post(
                                f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                                json={"chat_id": chat_id, "text": "Welcome to OpenManus Executive Assistant! I'm your AI-powered assistant.\n\nTo link this Telegram account with your registered web account, please enter your user ID number.\nYou can find your user ID on the dashboard in the Telegram Bot section."}
                            )
                        except Exception as http_error:
                            logger.error(f"Failed fallback request: {http_error}")
            elif text.startswith('/help'):
                # Send help message
                try:
                    bot_application.bot.send_message(
                        chat_id=chat_id,
                        text="I'm your executive assistant powered by OpenManus. Here's what I can help you with:\n\n"
                             "📧 *Email*: Check inbox, send emails, search for messages\n"
                             "📅 *Calendar*: View schedule, create events, find free time\n"
                             "🧠 *Memory*: Remember information and recall it later\n\n"
                             "You can navigate using the keyboard menu or simply tell me what you need help with!"
                    )
                except Exception as e:
                    logger.error(f"Error sending help message: {e}")
                    # Fallback to a direct HTTP request
                    try:
                        import requests
                        telegram_token = os.environ.get("TELEGRAM_TOKEN")
                        requests.post(
                            f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                            json={"chat_id": chat_id, "text": "I'm your executive assistant powered by OpenManus. Here's what I can help you with:\n\n📧 Email: Check inbox, send emails, search for messages\n📅 Calendar: View schedule, create events, find free time\n🧠 Memory: Remember information and recall it later\n\nYou can navigate using the keyboard menu or simply tell me what you need help with!"}
                        )
                    except Exception as http_error:
                        logger.error(f"Failed fallback request: {http_error}")
        else:
            # Check if this could be a user ID for account linking
            from models import User
            telegram_id = str(user_id)
            db_user = User.query.filter_by(telegram_id=telegram_id).first()

            if not db_user:
                # No linked account yet, this might be a user ID
                try:
                    input_user_id = int(text.strip())

                    # Look up the user by ID
                    user = User.query.get(input_user_id)
                    if user:
                        # Link Telegram ID to user
                        user.telegram_id = telegram_id
                        from app import db
                        db.session.commit()

                        try:
                            bot_application.bot.send_message(
                                chat_id=chat_id,
                                text=f"Account linked successfully! Welcome, {user.username}!\n\n"
                                     "You can now use your assistant through Telegram. How can I help you today?"
                            )
                        except Exception as e:
                            logger.error(f"Error sending account linked message: {e}")
                            # Fallback to a direct HTTP request
                            try:
                                import requests
                                telegram_token = os.environ.get("TELEGRAM_TOKEN")
                                requests.post(
                                    f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                                    json={"chat_id": chat_id, "text": f"Account linked successfully! Welcome, {user.username}!\n\nYou can now use your assistant through Telegram. How can I help you today?"}
                                )
                            except Exception as http_error:
                                logger.error(f"Failed fallback request: {http_error}")
                        return True
                except ValueError:
                    # Not a user ID, just a regular message
                    pass

            # Regular message processing with OpenManus
            if db_user:
                from manus_integration import process_message as manus_process

                # Process with OpenManus
                response = manus_process(db_user, text, None)

                # Use our event loop manager to send messages
                try:
                    loop_manager = EventLoopManager()
                    loop_manager.run_coroutine(
                        bot_application.bot.send_message(
                            chat_id=chat_id,
                            text=response
                        )
                    )
                except Exception as send_error:
                    logger.error(f"Error sending message: {send_error}")
                    # Fallback to a direct HTTP request if needed
                    try:
                        import requests
                        telegram_token = ACTIVE_BOT_TOKEN
                        requests.post(
                            f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                            json={"chat_id": chat_id, "text": response}
                        )
                    except Exception as http_error:
                        logger.error(f"Failed fallback request: {http_error}")
            else:
                try:
                    bot_application.bot.send_message(
                        chat_id=chat_id,
                        text="I don't recognize your Telegram account. Please register through the web interface or link your account by using the /start command."
                    )
                except Exception as send_error:
                    logger.error(f"Error sending message: {send_error}")
                    # Fallback to a direct HTTP request if needed
                    try:
                        import requests
                        telegram_token = os.environ.get("TELEGRAM_TOKEN")
                        requests.post(
                            f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                            json={"chat_id": chat_id, "text": "I don't recognize your Telegram account. Please register through the web interface or link your account by using the /start command."}
                        )
                    except Exception as http_error:
                        logger.error(f"Failed fallback request: {http_error}")

        return True
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        return False

def setup_webhook(url):
    """
    Set up a webhook for the Telegram bot.

    Args:
        url (str): The webhook URL

    Returns:
        bool: True if successful, False otherwise
    """
    if bot_application is None:
        logger.error("Bot application not initialized")
        return False

    try:
        # Get the bot instance
        bot = bot_application.bot

        # Use EventLoopManager to run the coroutine
        async def async_set_webhook():
            try:
                # Set the webhook
                webhook_info = await bot.set_webhook(url=url)
                return webhook_info
            except Exception as e:
                logger.error(f"Error in async set_webhook: {e}")
                return False

        # Run the async function using our event loop manager
        loop_manager = EventLoopManager()
        webhook_info = loop_manager.run_coroutine(async_set_webhook())

        if webhook_info:
            logger.info(f"Webhook set up successfully at {url}")
            return True
        else:
            logger.error("Failed to set up webhook")
            return False
    except Exception as e:
        logger.error(f"Error setting up webhook: {e}")
        return False

def remove_webhook():
    """Remove the webhook for the Telegram bot."""
    if bot_application is None:
        logger.error("Bot application not initialized")
        return False

    try:
        # Get the bot instance
        bot = bot_application.bot

        # Use EventLoopManager to run the coroutine
        async def async_remove_webhook():
            try:
                # Remove the webhook
                success = await bot.delete_webhook()
                return success
            except Exception as e:
                logger.error(f"Error in async remove_webhook: {e}")
                return False

        # Run the async function using our event loop manager
        loop_manager = EventLoopManager()
        success = loop_manager.run_coroutine(async_remove_webhook())

        if success:
            logger.info("Webhook removed successfully")
            return True
        else:
            logger.error("Failed to remove webhook")
            return False
    except Exception as e:
        logger.error(f"Error removing webhook: {e}")
        return False