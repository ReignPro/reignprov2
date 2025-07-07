
import datetime
import os

LOG_FILE = os.path.join(os.path.dirname(__file__), '..', 'bot.log')

def log_event(message):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"[{timestamp}] {message}"
    print(log_message)

    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_message + '\n')
