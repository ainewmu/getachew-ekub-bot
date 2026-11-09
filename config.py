import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "9107287321:AAEjQQrdZTdzlertDB9LmqC3TMZshuf7CIc")
ADMIN_PASSWORD = "bobmarley#123"
DATABASE_URL = os.getenv("DATABASE_URL", "")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "8565823278"))
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-domain.com")  # Will be updated after hosting

# Default bank accounts (can be edited in admin)
DEFAULT_BANKS = [
    {"name": "Commercial Bank of Ethiopia", "account": "1000805030082", "holder": "Getachew Fikadu Jirata"},
    {"name": "Awash Bank", "account": "013201829228400", "holder": "Getachew Fikadu Jirata"},
    {"name": "Dashen Bank", "account": "2944411549211", "holder": "Getachew Fikadu Jirata"},
]

# Default vehicles (can be edited in admin)
DEFAULT_VEHICLES = [
    {
        "id": 1,
        "name": "BYD YUAN UP",
        "name_am": "BYD ዩዋን አፕ",
        "name_or": "BYD YUAN UP",
        "subtitle": "white",
        "price": 3500,
        "total_tickets": 3500,
        "image": "https://via.placeholder.com/400x250?text=BYD+YUAN+UP",
        "is_active": True
    },
    {
        "id": 2,
        "name": "SINO CASONI",
        "name_am": "ሲኖ ካሶኒ",
        "name_or": "SINO CASONI",
        "subtitle": "10 Gech Mekina Ekub",
        "price": 9000,
        "total_tickets": 4000,
        "image": "https://via.placeholder.com/400x250?text=SINO+CASONI",
        "is_active": True
    },
    {
        "id": 3,
        "name": "OBAMA",
        "name_am": "ኦባማ",
        "name_or": "OBAMA",
        "subtitle": "10 Gech Yemekina Ekub",
        "price": 5000,
        "total_tickets": 4000,
        "image": "https://via.placeholder.com/400x250?text=OBAMA+BUS",
        "is_active": True
    },
    {
        "id": 4,
        "name": "REVO INVINCIBLE 2022",
        "name_am": "ሬቮ ኢንቪንሲብል 2022",
        "name_or": "REVO INVINCIBLE 2022",
        "subtitle": "2.8 HC",
        "price": 8000,
        "total_tickets": 3500,
        "image": "https://via.placeholder.com/400x250?text=REVO+INVINCIBLE",
        "is_active": True
    },
]
