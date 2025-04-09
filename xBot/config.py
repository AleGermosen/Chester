# config.py
import os
import re
from dotenv import load_dotenv
import logging

class Config:
    def __init__(self):
        # Load environment variables
        load_dotenv()

    def _clean_credential(self, value):
        """Clean credential by removing spaces, newlines, and quotes"""
        if not value:
            return value
        # Remove quotes, spaces, and newlines
        cleaned = value.strip().replace(' ', '').replace('\n', '').strip('"\'')
        return cleaned

    def _validate_credential_length(self, key, value):
        """Validate credential length"""
        max_lengths = {
            'BEARER_TOKEN': 150,
            'CONSUMER_KEY': 50,
            'CONSUMER_SECRET': 100,
            'ACCESS_TOKEN': 100,
            'ACCESS_TOKEN_SECRET': 100
        }
        
        if key in max_lengths and len(value) > max_lengths[key]:
            raise ValueError(f"{key} is too long. Expected max {max_lengths[key]} characters, got {len(value)}")

    def _validate_credential_format(self, key, value):
        """Validate credential format"""
        if not value:
            return
        
        # Check for common issues
        if ' ' in value:
            raise ValueError(f"{key} contains spaces")
        if '\n' in value:
            raise ValueError(f"{key} contains newlines")
        if '"' in value or "'" in value:
            raise ValueError(f"{key} contains quotes")
        
        # Basic format validation
        if key == 'BEARER_TOKEN' and not value.startswith('AAAA'):
            raise ValueError(f"{key} should start with 'AAAA'")
        if key == 'CONSUMER_KEY' and not re.match(r'^[a-zA-Z0-9]+$', value):
            raise ValueError(f"{key} should contain only alphanumeric characters")
        if key in ['CONSUMER_SECRET', 'ACCESS_TOKEN', 'ACCESS_TOKEN_SECRET'] and not re.match(r'^[a-zA-Z0-9_\-]+$', value):
            raise ValueError(f"{key} should contain only alphanumeric characters, underscores, and hyphens")

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
            
            # Clean and validate the credential
            cleaned_value = self._clean_credential(value)
            self._validate_credential_length(var, cleaned_value)
            self._validate_credential_format(var, cleaned_value)
            
            credentials[var] = cleaned_value
        
        return credentials

    def get_translation_api_key(self):
        """Retrieve translation API key"""
        return os.getenv('TRANSLATION_API_KEY')

    def get_detect_api_key(self):
        """Retrieve language detection API key"""
        api_key = os.getenv('DETECT_API_KEY')
        if api_key:
            api_key = api_key.strip()
            if not api_key:
                logging.warning("DETECT_API_KEY is empty after stripping")
                return None
            logging.info(f"Retrieved DETECT_API_KEY with length: {len(api_key)}")
            return api_key
        else:
            logging.warning("DETECT_API_KEY not found in environment variables")
            return None
            
    def get_s3_credentials(self):
        """Retrieve S3/Archive.org credentials"""
        access_key = os.getenv('S3_ACCESS_KEY')
        secret_key = os.getenv('S3_SECRET_KEY')
        
        if not access_key or not secret_key:
            logging.warning("Missing S3 credentials in environment variables")
            return None, None
            
        access_key = self._clean_credential(access_key)
        secret_key = self._clean_credential(secret_key)
        
        logging.info(f"Retrieved S3 credentials - Access key length: {len(access_key)}")
        
        return access_key, secret_key
