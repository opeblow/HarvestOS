import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["APP_ENV"] = "test"
os.environ["WHATSAPP_VERIFY_TOKEN"] = "change-me-random-string"
os.environ["SMS_WEBHOOK_AUTH_TOKEN"] = "change-me-random-string"
