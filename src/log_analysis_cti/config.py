import os
from dotenv import load_dotenv

try:
    load_dotenv()
except Exception as e:
    print(f"Warning: Could not load .env file: {e}")
    pass

VIRUSTOTAL_API_KEY = os.getenv('VIRUSTOTAL_API_KEY')
ABUSEIPDB_API_KEY = os.getenv('ABUSEIPDB_API_KEY')

RATE_LIMIT_DELAY = float(os.getenv('RATE_LIMIT_DELAY', '0'))

VIRUSTOTAL_BASE_URL = "https://www.virustotal.com/api/v3"
ABUSEIPDB_BASE_URL = "https://api.abuseipdb.com/api/v2"
TALOS_BASE_URL = "https://talosintelligence.com/reputation_center/lookup"

OUTPUT_DIR = "reports"
LOG_LEVEL = "INFO"

ABUSEIPDB_MAX_AGE = int(os.getenv('ABUSEIPDB_MAX_AGE', '365'))