import os
import logging
import aiohttp
import asyncio
import tempfile
from urllib.parse import quote
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from asgiref.sync import sync_to_async
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode
from products.sheets_service import sheets_service

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run the Telegram bot'

    def handle(self, *args, **options):
        """
        Main entry point for the management command.
        """
        token = settings.TELEGRAM_BOT_TOKEN
        
        if not token:
            self.stdout.write(
                self.style.ERROR('TELEGRAM_BOT_TOKEN is not set in environment variables!')
            )
            return
        
        self.stdout.write(self.style.SUCCESS('Starting Telegram bot...'))
        
        # Create the Application
        application = Application.builder().token(token).build()
        
        # Register handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("refresh", refresh_cache))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CallbackQueryHandler(handle_order_callback))
        
        # Start the bot
        self.stdout.write(self.style.SUCCESS('Bot is running! Press Ctrl+C to stop.'))
        application.run_polling(allowed_updates=Update.ALL_TYPES)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /start command.
    Send welcome message and display the main menu keyboard.
    """
    user = update.effective_user
    
    # Create custom keyboard with two buttons
    keyboard = [
        [KeyboardButton("📦 In Stock Products")],
        [KeyboardButton("🚚 On The Way Products")]
    ]
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )
    
    welcome_message = (
        f"👋 Welcome, {user.first_name}!\n\n"
        f"I'm your Supplier Bot. Use the buttons below to browse products:\n\n"
        f"📦 <b>In Stock Products</b> - View available items\n"
        f"🚚 <b>On The Way Products</b> - View incoming items"
    )
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    
    logger.info(f"User {user.id} started the bot")


async def refresh_cache(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /refresh command to manually refresh the Google Sheets cache.
    """
    user = update.effective_user
    admin_chat_id = settings.TELEGRAM_ADMIN_CHAT_ID
    
    # Only allow admin to refresh cache
    if admin_chat_id and str(user.id) != str(admin_chat_id):
        await update.message.reply_text(
            "⛔ Only admin can refresh the cache.",
            parse_mode=ParseMode.HTML
        )
        return
    
    await update.message.reply_text(
        "🔄 Refreshing data from Google Sheets...",
        parse_mode=ParseMode.HTML
    )
    
    # Refresh the cache
    await sync_to_async(sheets_service.refresh_cache)()
    
    await update.message.reply_text(
        "✅ Cache refreshed successfully!",
        parse_mode=ParseMode.HTML
    )
    
    logger.info(f"Cache refreshed by admin user {user.id}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle text messages from users.
    Process button clicks and send product information.
    """
    text = update.message.text
    user = update.effective_user
    
    logger.info(f"User {user.id} pressed: {text}")
    
    # Delete previous product messages if they exist (both bot and user messages)
    if 'product_messages' in context.user_data and context.user_data['product_messages']:
        for msg_id in context.user_data['product_messages']:
            try:
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
            except Exception as e:
                logger.debug(f"Could not delete message {msg_id}: {e}")
        context.user_data['product_messages'] = []
    
    # Delete the user's button click message
    try:
        await update.message.delete()
    except Exception as e:
        logger.debug(f"Could not delete user message: {e}")
    
    if text == "📦 In Stock Products":
        await send_products(update, context, "In-Stock")
    elif text == "🚚 On The Way Products":
        await send_products(update, context, "On The Way")
    else:
        await update.message.reply_text(
            "Please use the buttons below to browse products.",
            parse_mode=ParseMode.HTML
        )


async def handle_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle order button callbacks.
    Forwards the product message to admin and notifies user.
    """
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    admin_username = settings.TELEGRAM_ADMIN_USERNAME
    admin_chat_id = settings.TELEGRAM_ADMIN_CHAT_ID
    
    # Forward the product message to admin if admin chat ID is set
    if admin_chat_id:
        try:
            # Forward the message with the product
            await context.bot.forward_message(
                chat_id=admin_chat_id,
                from_chat_id=query.message.chat_id,
                message_id=query.message.message_id
            )
            
            # Send user info to admin
            user_info = (
                f"📦 New Order Request:\n"
                f"From: {user.first_name}"
                + (f" {user.last_name}" if user.last_name else "")
                + (f" (@{user.username})" if user.username else "")
                + f"\nUser ID: {user.id}"
            )
            await context.bot.send_message(
                chat_id=admin_chat_id,
                text=user_info
            )
            
            # Notify user
            await query.edit_message_reply_markup(reply_markup=None)
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"✅ Order request sent to admin!\n\nContact: @{admin_username}",
                parse_mode=ParseMode.HTML
            )
            logger.info(f"Order forwarded from user {user.id} to admin {admin_chat_id}")
            
        except Exception as e:
            logger.error(f"Error forwarding to admin: {str(e)}")
            await query.edit_message_reply_markup(reply_markup=None)
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"Please contact @{admin_username} directly to place your order.",
                parse_mode=ParseMode.HTML
            )
    else:
        # No admin chat ID configured, just provide contact link
        await query.edit_message_reply_markup(reply_markup=None)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"Please contact @{admin_username} to place your order.",
            parse_mode=ParseMode.HTML
        )


async def send_products(update: Update, context: ContextTypes.DEFAULT_TYPE, status: str) -> None:
    """
    Query and send products based on status from Google Sheets.
    
    Args:
        update: Telegram update object
        context: Context for storing message IDs
        status: Product status ("In-Stock" or "On The Way")
    """
    # Initialize message tracking list
    if 'product_messages' not in context.user_data:
        context.user_data['product_messages'] = []
    
    # Fetch products from Google Sheets (using sync_to_async)
    products = await sync_to_async(sheets_service.get_products_by_status)(status)
    
    if not products:
        status_name = "In Stock" if status == "In-Stock" else "On The Way"
        msg = await update.message.reply_text(
            f"No {status_name} products found at the moment.",
            parse_mode=ParseMode.HTML
        )
        context.user_data['product_messages'].append(msg.message_id)
        return
    
    # Send a loading message
    status_emoji = "📦" if status == "In-Stock" else "🚚"
    status_name = "In Stock" if status == "In-Stock" else "On The Way"
    
    loading_msg = await update.message.reply_text(
        f"{status_emoji} Loading {status_name} products...",
        parse_mode=ParseMode.HTML
    )
    context.user_data['product_messages'].append(loading_msg.message_id)
    
    # Send each product with image and caption
    for product in products:
        msg = await send_product_details(update, product)
        if msg:
            context.user_data['product_messages'].append(msg.message_id)
    
    # Send completion message
    completion_msg = await update.message.reply_text(
        f"✅ Sent {len(products)} {status_name} product(s).",
        parse_mode=ParseMode.HTML
    )
    context.user_data['product_messages'].append(completion_msg.message_id)


async def send_product_details(update: Update, product: dict):
    """
    Send a single product with image and formatted caption.
    
    Args:
        update: Telegram update object
        product: Product dictionary from Google Sheets
        
    Returns:
        Message object or None
    """
    try:
        # Build unit text (တစ် + unit from column)
        unit_text = f"တစ်{product.get('unit', '')}" if product.get('unit') else ""
        
        # Create the caption with HTML formatting
        caption = (
            f"<b>{product['name']}</b>\n\n"
            f"💰 Price: {product['price']} Kyat {unit_text}\n"
            f"📊 Stock: {product['stock_count']} units"
        )
        
        # Add expiry date if available
        if product.get('expiry_date'):
            caption += f"\n🗓 Expiry: {product['expiry_date']}"
        
        # Create inline keyboard with Order button (callback data stores product name)
        product_data = f"order_{product['name'][:50]}"  # Limit to 50 chars for callback data
        keyboard = [
            [InlineKeyboardButton("🛒 Order တင်ရန်", callback_data=product_data)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Get the image URL from Google Sheets
        image_url = product.get('image_link', '')
        
        # Send photo with caption
        if image_url:
            try:
                # Download image asynchronously with aiohttp
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(image_url) as response:
                        if response.status == 200:
                            image_data = await response.read()
                            
                            # Create a temporary file to store the image
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                                temp_file.write(image_data)
                                temp_path = temp_file.name
                            
                            # Send the photo
                            with open(temp_path, 'rb') as photo:
                                msg = await update.message.reply_photo(
                                    photo=photo,
                                    caption=caption,
                                    parse_mode=ParseMode.HTML,
                                    reply_markup=reply_markup
                                )
                            
                            # Clean up temp file
                            os.unlink(temp_path)
                            return msg
                        else:
                            # If image download fails, send text only
                            msg = await update.message.reply_text(
                                f"{caption}\n\n⚠️ Image not available",
                                parse_mode=ParseMode.HTML,
                                reply_markup=reply_markup
                            )
                            return msg
            except Exception as img_error:
                logger.warning(f"Error downloading image: {str(img_error)}")
                msg = await update.message.reply_text(
                    f"{caption}\n\n⚠️ Image not available",
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
                return msg
        else:
            # No image URL provided
            msg = await update.message.reply_text(
                caption,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            return msg
            
    except Exception as e:
        logger.error(f"Error sending product {product.get('name', 'Unknown')}: {str(e)}")
        msg = await update.message.reply_text(
            f"❌ Error loading product: {product.get('name', 'Unknown')}",
            parse_mode=ParseMode.HTML
        )
        return msg
