# test_credentials.py
import os
import tweepy
from dotenv import load_dotenv
import logging
from deep_translator import single_detection
from config import Config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_twitter_credentials():
    """Test Twitter API credentials"""
    try:
        # Load environment variables
        load_dotenv()
        
        # Get credentials
        bearer_token = os.getenv('BEARER_TOKEN')
        consumer_key = os.getenv('CONSUMER_KEY')
        consumer_secret = os.getenv('CONSUMER_SECRET')
        access_token = os.getenv('ACCESS_TOKEN')
        access_token_secret = os.getenv('ACCESS_TOKEN_SECRET')
        
        # Print credential details (masked)
        logger.info("Checking Twitter credentials:")
        logger.info(f"Bearer Token: {'*' * len(bearer_token) if bearer_token else 'Not found'}")
        logger.info(f"Consumer Key: {'*' * len(consumer_key) if consumer_key else 'Not found'}")
        logger.info(f"Consumer Secret: {'*' * len(consumer_secret) if consumer_secret else 'Not found'}")
        logger.info(f"Access Token: {'*' * len(access_token) if access_token else 'Not found'}")
        logger.info(f"Access Token Secret: {'*' * len(access_token_secret) if access_token_secret else 'Not found'}")
        
        # Check if all required credentials are present
        if not all([bearer_token, consumer_key, consumer_secret, access_token, access_token_secret]):
            logger.error("Missing required Twitter credentials")
            return False
            
        # Test API v1.1
        try:
            auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
            auth.set_access_token(access_token, access_token_secret)
            api = tweepy.API(auth)
            
            # Test API v1.1
            try:
                user = api.verify_credentials()
                logger.info(f"Successfully authenticated with API v1.1 as @{user.screen_name}")
            except Exception as e:
                logger.error(f"API v1.1 authentication failed: {str(e)}")
                if hasattr(e, 'response') and e.response is not None:
                    logger.error(f"Response status code: {e.response.status_code}")
                    logger.error(f"Response text: {e.response.text}")
            
            # Test API v2
            try:
                client = tweepy.Client(
                    bearer_token=bearer_token,
                    consumer_key=consumer_key,
                    consumer_secret=consumer_secret,
                    access_token=access_token,
                    access_token_secret=access_token_secret
                )
                user = client.get_me()
                logger.info(f"Successfully authenticated with API v2 as @{user.data.username}")
            except Exception as e:
                logger.error(f"API v2 authentication failed: {str(e)}")
                if hasattr(e, 'response') and e.response is not None:
                    logger.error(f"Response status code: {e.response.status_code}")
                    logger.error(f"Response text: {e.response.text}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error testing Twitter credentials: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"Error in test_twitter_credentials: {str(e)}")
        return False

def test_detect_api_key():
    """Test detectlanguage.com API key"""
    try:
        # Load environment variables
        load_dotenv()
        
        # Get API key
        detect_api_key = os.getenv('DETECT_API_KEY')
        
        # Print API key details (masked)
        logger.info("Checking detect API key:")
        logger.info(f"Detect API Key: {'*' * len(detect_api_key) if detect_api_key else 'Not found'}")
        logger.info(f"API Key length: {len(detect_api_key) if detect_api_key else 0}")
        
        # Check if API key is present
        if not detect_api_key:
            logger.error("Missing detect API key")
            return False
            
        # Test language detection
        try:
            # Test with a simple English text
            test_text = "This is a test sentence in English."
            logger.info(f"Testing with text: {test_text}")
            detected_lang = single_detection(test_text, api_key=detect_api_key)
            logger.info(f"Successfully detected language: {detected_lang}")
            
            # Test with a simple French text
            test_text = "Ceci est une phrase de test en français."
            logger.info(f"Testing with text: {test_text}")
            detected_lang = single_detection(test_text, api_key=detect_api_key)
            logger.info(f"Successfully detected language: {detected_lang}")
            
            # Test with a longer text to verify API key format
            test_text = "This is a longer test sentence in English that should help us verify the API key format and functionality."
            logger.info(f"Testing with longer text: {test_text}")
            detected_lang = single_detection(test_text, api_key=detect_api_key)
            logger.info(f"Successfully detected language: {detected_lang}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error testing detect API key: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status code: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error in test_detect_api_key: {str(e)}")
        return False

def main():
    """Main test function"""
    logger.info("Starting credential tests...")
    
    # Test Twitter credentials
    twitter_success = test_twitter_credentials()
    logger.info(f"Twitter credentials test: {'Success' if twitter_success else 'Failed'}")
    
    # Test detect API key
    detect_success = test_detect_api_key()
    logger.info(f"Detect API key test: {'Success' if detect_success else 'Failed'}")
    
    # Overall result
    if twitter_success and detect_success:
        logger.info("All credential tests passed!")
    else:
        logger.error("Some credential tests failed. Please check the logs above for details.")

if __name__ == "__main__":
    main() 