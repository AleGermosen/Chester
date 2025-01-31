# config.py
import os
from dotenv import load_dotenv

class Config:
    def __init__(self):
        # Load environment variables
        load_dotenv()

    def get_twitter_credentials(self):
        """Retrieve and validate Twitter API credentials"""
        required_env_vars = [
            'BEARER_TOKEN', 'CONSUMER_KEY', 'CONSUMER_SECRET',
            'ACCESS_TOKEN', 'ACCESS_TOKEN_SECRET'
        ]
        
        # Verify all required environment variables are present
        credentials = {}
        for var in required_env_vars:
            value = os.getenv(var)
            if not value:
                raise ValueError(f"Missing required environment variable: {var}")
            credentials[var] = value
        
        return credentials

    def get_translation_api_key(self):
        """Retrieve translation API key"""
        return os.getenv('DETECT_API_KEY')
