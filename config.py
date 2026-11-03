import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DEFAULT_CHANNEL_ID = int(os.getenv("DEFAULT_CHANNEL_ID", "0"))
STAFF_ROLE_ID = int(os.getenv("STAFF_ROLE_ID", "0"))
DISPATCHER_ROLE_ID = int(os.getenv("DISPATCHER_ROLE_ID", "0"))
THUMBNAIL_URL = os.getenv("THUMBNAIL_URL", "")

# Роли
DRIVER_ROLE_ID = int(os.getenv("DRIVER_ROLE_ID", "0"))
CONDUCTOR_ROLE_ID = int(os.getenv("CONDUCTOR_ROLE_ID", "0"))
SECURITY_ROLE_ID = int(os.getenv("SECURITY_ROLE_ID", "0"))

# Каналы
CHANNEL_TRIPS_ID = int(os.getenv("CHANNEL_TRIPS_ID", "0"))
CHANNEL_VACATIONS_ID = int(os.getenv("CHANNEL_VACATIONS_ID", "0"))
CHANNEL_LOGS_ID = int(os.getenv("CHANNEL_LOGS_ID", "0"))

# Новые каналы (которые мы добавили для формы и неявок)
CHANNEL_REGISTRATION_ID = int(os.getenv("CHANNEL_REGISTRATION_ID", "0"))
CHANNEL_NO_SHOW_ID = int(os.getenv("CHANNEL_NO_SHOW_ID", "0"))