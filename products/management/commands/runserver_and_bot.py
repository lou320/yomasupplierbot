import os
import sys
import threading
import logging
import aiohttp
import asyncio
import tempfile
from urllib.parse import quote
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from asgiref.sync import sync_to_async
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler
from telegram.constants import ParseMode
from products.sheets_service import sheets_service
from products.models import UserProfile

# Conversation states
ASK_NAME, ASK_PHONE, ASK_ADDRESS, CONFIRM_INFO = range(4)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run both Django development server and Telegram bot together'

    def add_arguments(self, parser):
        parser.add_argument(
            '--port',
            type=int,
            default=8000,
            help='Port for Django development server (default: 8000)',
        )

    def handle(self, *args, **options):
        """
        Main entry point for the management command.
        Runs Django server and Telegram bot in separate threads.
        """
        port = options['port']
        
        # Check for Telegram bot token
        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            self.stdout.write(
                self.style.ERROR('TELEGRAM_BOT_TOKEN is not set in environment variables!')
            )
            return
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Starting Django Server + Telegram Bot'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        # Start Django development server in a separate thread
        def run_django_server():
            self.stdout.write(self.style.SUCCESS(f'🌐 Django server starting on http://127.0.0.1:{port}/'))
            call_command('runserver', f'127.0.0.1:{port}', '--noreload')
        
        django_thread = threading.Thread(target=run_django_server, daemon=True)
        django_thread.start()
        
        self.stdout.write(self.style.SUCCESS('🤖 Telegram bot starting...'))
        
        # Run bot in main thread
        try:
            # Create the Application
            application = Application.builder().token(token).build()
            
            # Register handlers
            application.add_handler(CommandHandler("start", start))
            application.add_handler(CommandHandler("refresh", refresh_cache))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            application.add_handler(CallbackQueryHandler(handle_order_callback))
            application.add_handler(MessageHandler(filters.REPLY & filters.ChatType.PRIVATE, handle_admin_reply))
            
            # Start the bot
            self.stdout.write(self.style.SUCCESS('✅ Both services are running!'))
            self.stdout.write(self.style.SUCCESS(f'📱 Django Admin: http://127.0.0.1:{port}/admin'))
            self.stdout.write(self.style.SUCCESS('🤖 Telegram Bot: Active and polling'))
            self.stdout.write(self.style.WARNING('\nPress Ctrl+C to stop both services\n'))
            
            application.run_polling(allowed_updates=Update.ALL_TYPES)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n\nShutting down...'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            raise


async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin replies to forward them to customers"""
    admin_chat_id = settings.TELEGRAM_ADMIN_CHAT_ID
    
    # Only process if this is from the admin
    if str(update.effective_chat.id) != str(admin_chat_id):
        return
    
    # Check if this is a reply to a customer order message
    if not update.message.reply_to_message:
        return
    
    replied_message_id = update.message.reply_to_message.message_id
    
    # Get customer ID from mapping
    customer_id = context.bot_data.get('admin_customer_mapping', {}).get(replied_message_id)
    
    if not customer_id:
        await update.message.reply_text("❌ Could not find the customer for this order.")
        return
    
    try:
        # Forward admin's message to customer
        await context.bot.send_message(
            chat_id=customer_id,
            text=f"📩 Message from {settings.TELEGRAM_ADMIN_USERNAME}:\n\n{update.message.text}"
        )
        
        await update.message.reply_text("✅ Message sent to customer!")
    except Exception as e:
        logger.error(f"Error forwarding message to customer: {e}")
        await update.message.reply_text(f"❌ Failed to send message: {str(e)}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /start command.
    Send welcome message and display the main menu keyboard.
    """
    user = update.effective_user
    
    # Create custom keyboard with two buttons
    keyboard = [
        [KeyboardButton("📦 In-Stock ပစ္စည်းများ")],
        [KeyboardButton("🚚 Pre-Order မှာယူနိုင်သောပစ္စည်းများ")]
    ]
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )
    
    welcome_message = (
        f"👋 မင်္ဂလာပါ {user.first_name},\n Yoma Supplier မှကြိုဆိုပါတယ်!\n\n"
        # f"လက်ရှိမှာယူနိုင်သော ပစ္စည်းများကိုကြည့်ရန် '📦 <b>In-Stock ပစ္စည်းများ</b>' ကိုနှိပ်ပါ\n\n"
        # f"မကြာခင်ရောက်လာတော့မည့် ပစ္စည်းများကိုကြည့်ရန် '🚚 <b>Pre-Order မှာယူနိုင်သောပစ္စည်းများ</b>' ကိုနှိပ်ပါ"
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
    
    # Check if collecting user info
    if context.user_data.get('collecting_info'):
        step = context.user_data.get('info_step')
        
        if step == 'name':
            context.user_data['user_name'] = text
            context.user_data['info_step'] = 'phone'
            # Add cancel button
            keyboard = [[InlineKeyboardButton("❌ မလုပ်တော့ပါ (Cancel)", callback_data="cancel_info")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "📞 ပစ္စည်းလက်ခံမည့်သူ၏ ဖုန်းနာမ်ပတ် ပေးပို့ပါ။",
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            return
        elif step == 'phone':
            context.user_data['user_phone'] = text
            context.user_data['info_step'] = 'address'
            # Add cancel button
            keyboard = [[InlineKeyboardButton("❌ မလုပ်တော့ပါ (Cancel)", callback_data="cancel_info")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "📍 ပစ္စည်းလက်ခံမည့်သူ၏ လိပ်စာ ပေးပို့ပါ။",
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            return
        elif step == 'address':
            context.user_data['user_address'] = text
            context.user_data['info_step'] = None
            context.user_data['collecting_info'] = False
            
            # Save user profile
            user_profile = await sync_to_async(UserProfile.objects.update_or_create)(
                telegram_id=user.id,
                defaults={
                    'telegram_username': user.username or '',
                    'first_name': user.first_name or '',
                    'name': context.user_data['user_name'],
                    'phone': context.user_data['user_phone'],
                    'address': context.user_data['user_address'],
                }
            )
            
            # Send order to admin
            await send_order_to_admin(update, context, user_profile[0], update.effective_chat.id)
            
            await update.message.reply_text(
                "✅ Order တင်ပြီးပါပြီ။\n\n"
                "📱 Yoma Supplier မှ ငွေကောက်ခံရန် အမြန်ဆုံးဆက်သွယ်ပေးပါမည်။\n\n"
                "Admin အားဆက်သွယ်ရန် နှိပ်ပါ 👇"
                "@yomasupplier",
                parse_mode=ParseMode.HTML
            )
            return
    
    logger.info(f"User {user.id} pressed: {text}")
    
    if text == "📦 In-Stock ပစ္စည်းများ":
        await send_products(update, context, "In-Stock")
    elif text == "🚚 Pre-Order မှာယူနိုင်သောပစ္စည်းများ":
        await send_products(update, context, "On The Way")
    else:
        await update.message.reply_text(
            "ကျေးဇူးပြု၍ အောက်ပါ ခလုတ်များကို အသုံးပြု၍ ပစ္စည်းများကို ကြည့်ရှုပါ။",
            parse_mode=ParseMode.HTML
        )


async def handle_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle order button callbacks.
    Check if user has profile, if not start registration, if yes show options.
    """
    query = update.callback_query
    
    # Handle different callback types
    if query.data == "use_saved_info":
        await query.answer()
        user = query.from_user
        user_profile = await sync_to_async(UserProfile.objects.filter(telegram_id=user.id).first)()
        await send_order_to_admin(update, context, user_profile, query.message.chat_id)
        await query.edit_message_text("✅ Order တင်ပြီးပါပြီ။ Yoma Supplier မှ ငွေကောက်ခံရန် အမြန်ဆုံးဆက်သွယ်ပေးပါမည်။")
        return
    elif query.data == "update_info":
        await query.answer()
        # Add cancel button
        keyboard = [[InlineKeyboardButton("❌ မလုပ်တော့ပါ (Cancel)", callback_data="cancel_info")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📝 အချက်အလက်များကို ပြင်ဆင်ရန်:\n\n👤 နာမည်ပေးပို့ပါ။",
            reply_markup=reply_markup
        )
        context.user_data['collecting_info'] = True
        context.user_data['info_step'] = 'name'
        return
    elif query.data == "cancel_info":
        await query.answer()
        context.user_data['collecting_info'] = False
        context.user_data['info_step'] = None
        context.user_data.pop('order_product_message_id', None)
        context.user_data.pop('order_product_chat_id', None)
        await query.edit_message_text(
            "❌ Order မတင်တော့ပါ။\n\n"
            "ပစ္စည်းများကို ကြည့်ရှုရန် အောက်ပါခလုတ်များကို အသုံးပြုပါ။"
        )
        return
    
    await query.answer()
    user = query.from_user
    
    # Check if user has a profile
    user_profile = await sync_to_async(UserProfile.objects.filter(telegram_id=user.id).first)()
    
    # Store product message details for later
    context.user_data['order_product_message_id'] = query.message.message_id
    context.user_data['order_product_chat_id'] = query.message.chat_id
    
    if user_profile:
        # User has profile, show options
        keyboard = [
            [InlineKeyboardButton("✅ အချက်အလက်များကိုပြန်လည်အသုံးပြုပါ", callback_data="use_saved_info")],
            [InlineKeyboardButton("📝 အချက်အလက်များကို ပြင်ဆင်ပါ", callback_data="update_info")],
            [InlineKeyboardButton("❌ မလုပ်တော့ပါ (Cancel)", callback_data="cancel_info")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        profile_text = (
            f"📋 သင်၏ သိမ်းဆည်းထားသော အချက်အလက်များ:\n\n"
            f"👤 နာမည်: {user_profile.name}\n"
            f"📞 ဖုန်းနံပါတ်: {user_profile.phone}\n"
            f"📍 လိပ်စာ: {user_profile.address}\n\n"
            f"✅ အချက်အလက်များကို အသုံးပြုရန် သို့မဟုတ် ပြင်ဆင်ရန် ရွေးချယ်ပါ။")
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=profile_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    else:
        # No profile, start registration
        await query.edit_message_reply_markup(reply_markup=None)
        # Add cancel button
        keyboard = [[InlineKeyboardButton("❌ မလုပ်တော့ပါ (Cancel)", callback_data="cancel_info")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="📝 Order တင်ရန် သင်၏အချက်အလက်များကိုဖြည့်ပါ။ \n\n👤 နာမည်ပေးပို့ပါ။",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        context.user_data['collecting_info'] = True
        context.user_data['info_step'] = 'name'


async def send_order_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, user_profile: UserProfile, chat_id: int) -> None:
    """Forward product and send user info to admin."""
    admin_chat_id = settings.TELEGRAM_ADMIN_CHAT_ID
    admin_username = settings.TELEGRAM_ADMIN_USERNAME
    
    if not admin_chat_id:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Order တင်ရန် @{admin_username} ဆက်သွယ်ပါ။",
            parse_mode=ParseMode.HTML
        )
        return
    
    try:
        # Forward the product message
        product_msg_id = context.user_data.get('order_product_message_id')
        product_chat_id = context.user_data.get('order_product_chat_id')
        
        if product_msg_id and product_chat_id:
            await context.bot.forward_message(
                chat_id=admin_chat_id,
                from_chat_id=product_chat_id,
                message_id=product_msg_id
            )
        
        # Send customer info
        telegram_contact = f"@{user_profile.telegram_username}" if user_profile.telegram_username else f"{user_profile.first_name}"
        user_link = f"<a href='tg://user?id={user_profile.telegram_id}'>{telegram_contact}</a>"
        
        customer_info = (
            f"📦 NEW ORDER REQUEST\n\n"
            f"👤 Name: {user_profile.name}\n"
            f"📞 Phone: {user_profile.phone}\n"
            f"📍 Address: {user_profile.address}\n\n"
            f"💬 Contact Customer: {user_link}\n"
            # f"🆔 User ID: {user_profile.telegram_id}\n\n"
            # f"ℹ️ Reply to this message to contact the customer via bot."
        )
        
        sent_message = await context.bot.send_message(
            chat_id=admin_chat_id,
            text=customer_info,
            parse_mode=ParseMode.HTML
        )
        
        # Store customer ID mapping for admin replies
        if 'admin_customer_mapping' not in context.bot_data:
            context.bot_data['admin_customer_mapping'] = {}
        context.bot_data['admin_customer_mapping'][sent_message.message_id] = user_profile.telegram_id
        
        # Clear temporary data
        context.user_data.pop('order_product_message_id', None)
        context.user_data.pop('order_product_chat_id', None)
        
        logger.info(f"Order sent to admin from user {user_profile.telegram_id}")
    except Exception as e:
        logger.error(f"Error sending order to admin: {str(e)}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"There was an error. Please contact @{admin_username} directly.",
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
    # Fetch products from Google Sheets (using sync_to_async)
    products = await sync_to_async(sheets_service.get_products_by_status)(status)
    
    if not products:
        status_name = "In Stock" if status == "In-Stock" else "On The Way"
        await update.message.reply_text(
            f"No {status_name} products found at the moment.",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Send a loading message
    status_emoji = "📦" if status == "In-Stock" else "🚚"
    status_name = "In Stock" if status == "In-Stock" else "On The Way"
    
    await update.message.reply_text(
        f"{status_emoji} Loading {status_name} products...",
        parse_mode=ParseMode.HTML
    )
    
    # Send each product with image and caption
    for product in products:
        await send_product_details(update, product)
    
    # Send completion message
    await update.message.reply_text(
        f"✅ Sent {len(products)} {status_name} product(s).",
        parse_mode=ParseMode.HTML
    )


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
        unit_text = f"{product.get('unit', '')}" if product.get('unit') else ""
        
        # Create the caption with HTML formatting
        caption = (
            f"<b>{product['name']}</b>\n\n"
            f"💰 စျေးနှုန်း: တစ်{unit_text} {product['price']} Kyat \n"
            f"📊 ပစ္စည်းလက်ကျန်: {product['stock_count']} {unit_text}"
        )
        
        # Add expiry date if available
        if product.get('expiry_date'):
            caption += f"\n🗓 သက်တမ်းကုန်ဆုံးရက်: {product['expiry_date']}"
        
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
