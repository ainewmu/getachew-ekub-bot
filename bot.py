import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton, MenuButtonWebApp
from config import BOT_TOKEN, WEBAPP_URL

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    # Language selection first
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇪🇹 አማርኛ", callback_data="lang_am"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
        ],
        [
            InlineKeyboardButton(text="🇪🇹 Afaan Oromoo", callback_data="lang_or"),
        ]
    ])
    await message.answer(
        "👋 እንኳን በደህና መጡ!\nWelcome!\nBaga gara bootii keenyaa dhuftan!\n\n"
        "እባክዎ ቋንቋ ይምረጡ / Please choose language / Afaan filadhaa:",
        reply_markup=keyboard
    )


@dp.callback_query(F.data.startswith("lang_"))
async def process_language(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    
    texts = {
        "am": {
            "welcome": "🚗 እንኳን ወደ ጌታቸው ፍቃዱ እቁብ በደህና መጡ!\n\nከታች ያለውን ቁልፍ በመጫን መተግበሪያውን ይክፈቱ።",
            "button": "🚀 መተግበሪያውን ክፈት"
        },
        "en": {
            "welcome": "🚗 Welcome to Getachew Fikadu Ekub!\n\nClick the button below to open the app.",
            "button": "🚀 Open App"
        },
        "or": {
            "welcome": "🚗 Baga gara Getachew Fikadu Ekub dhuftan!\n\nAppii banuuf button armaan gadii tuqi.",
            "button": "🚀 Appii Bani"
        }
    }
    
    t = texts.get(lang, texts["en"])
    
    # Important: Replace WEBAPP_URL with your real hosted URL later
    webapp_url = f"{WEBAPP_URL}?lang={lang}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=t["button"],
            web_app=WebAppInfo(url=webapp_url)
        )]
    ])
    
    await callback.message.edit_text(t["welcome"], reply_markup=keyboard)
    await callback.answer()


async def main():
    # Set menu button
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Open App",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        )
    except Exception as e:
        logging.warning(f"Could not set menu button: {e}")
    
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())