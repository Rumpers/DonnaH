import os
import logging
import threading
import asyncio
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

# Define conversation states
MAIN_MENU, EMAIL, CALENDAR, DRIVE, MEMORY, DOCUMENT = range(6)

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
        ['📁 Drive', '🧠 Memory'],
        ['📄 Document', '❓ Help']
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
        "📁 *Drive*: Manage documents, create files, share content\n"
        "🧠 *Memory*: Remember information and recall it later\n"
        "📄 *Document*: Process, summarize, and file documents\n\n"
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
        ['📁 Drive', '🧠 Memory'],
        ['📄 Document', '❓ Help']
    ]
    
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    
    await update.message.reply_text(
        help_text,
        reply_markup=reply_markup
    )
    
    return MAIN_MENU

async def process_message(update: Update, context: CallbackContext) -> int:
    """Process user messages using OpenManus framework."""
    user_message = update.message.text
    user = update.effective_user
    telegram_id = str(user.id)
    
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
                    ['📁 Drive', '🧠 Memory'],
                    ['📄 Document', '❓ Help']
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
                    MessageHandler(filters.Regex('^📁 Drive$'), handle_drive),
                    MessageHandler(filters.Regex('^🧠 Memory$'), handle_memory),
                    MessageHandler(filters.Regex('^📄 Document$'), handle_document),
                    MessageHandler(filters.Regex('^❓ Help$'), handle_help),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, process_message),
                ],
                EMAIL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, process_message),
                ],
                CALENDAR: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, process_message),
                ],
                DRIVE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, process_message),
                ],
                MEMORY: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, process_message),
                ],
                DOCUMENT: [
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
        
async def process_update(update_data):
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
        
        # Process the update
        await bot_application.process_update(update)
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
        
        # Use async event loop to run the coroutine
        import asyncio
        
        async def async_set_webhook():
            try:
                # Set the webhook
                webhook_info = await bot.set_webhook(url=url)
                return webhook_info
            except Exception as e:
                logger.error(f"Error in async set_webhook: {e}")
                return False
        
        # Run the async function in the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        webhook_info = loop.run_until_complete(async_set_webhook())
        loop.close()
        
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
        
        # Use async event loop to run the coroutine
        import asyncio
        
        async def async_remove_webhook():
            try:
                # Remove the webhook
                success = await bot.delete_webhook()
                return success
            except Exception as e:
                logger.error(f"Error in async remove_webhook: {e}")
                return False
        
        # Run the async function in the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(async_remove_webhook())
        loop.close()
        
        if success:
            logger.info("Webhook removed successfully")
            return True
        else:
            logger.error("Failed to remove webhook")
            return False
    except Exception as e:
        logger.error(f"Error removing webhook: {e}")
        return False
