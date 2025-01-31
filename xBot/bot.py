# bot.py
import os
import time
import logging
import tweepy
from config import Config
from twitter_client import TwitterClient
from translation_service import TranslationService

class TwitterTranslationBot:
    def __init__(self, target_username, check_interval=300):
        """
        Initialize Twitter Translation Bot
        
        :param target_username: Username to monitor
        :param check_interval: Time between checks in seconds
        """
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('twitter_bot.log'),
                logging.StreamHandler()
            ]
        )
        
        # Load configuration
        self.config = Config()
        
        # Initialize services
        twitter_credentials = self.config.get_twitter_credentials()
        self.twitter_client = TwitterClient(twitter_credentials)
        
        translation_api_key = self.config.get_translation_api_key()
        self.translation_service = TranslationService(translation_api_key)
        
        # Bot configuration
        self.target_username = target_username
        self.check_interval = check_interval
        self.last_processed_id_file = 'last_processed_id.txt'
        
    def _save_last_processed_id(self, tweet_id):
        """
        Save the last processed tweet ID to file
        
        :param tweet_id: ID of the last processed tweet
        """
        try:
            with open(self.last_processed_id_file, 'w') as file:
                file.write(str(tweet_id))
        except IOError as e:
            logging.error(f"Failed to save last processed ID: {e}")

    def _read_last_processed_id(self):
        """
        Read the last processed tweet ID from file
        
        :return: Last processed tweet ID or None
        """
        try:
            if os.path.exists(self.last_processed_id_file):
                with open(self.last_processed_id_file, 'r') as file:
                    return file.read().strip()
        except IOError as e:
            logging.error(f"Failed to read last processed ID: {e}")
        return None

    def run(self):
        """
        Main bot loop to check for new tweets, translate and repost
        """
        last_processed_id = self._read_last_processed_id()
        
        while True:
            try:
                logging.info(f"Checking for new tweets from {self.target_username}...")
                
                # Get user ID
                user_id = self.twitter_client.get_user_id(self.target_username)
                if not user_id:
                    logging.error(f"Could not find user ID for {self.target_username}")
                    time.sleep(self.check_interval)
                    continue
                
                # Get latest tweet
                tweet = self.twitter_client.get_latest_non_reply_tweet(user_id)
                
                if tweet and str(tweet.id) != str(last_processed_id):
                    logging.info(f"Found new tweet: {tweet.text}")
                    
                    try:
                        # Detect language
                        detected_language = self.translation_service.detect_language(tweet.text)
                        if not detected_language:
                            logging.error("Failed to detect language")
                            time.sleep(self.check_interval)
                            continue
                        
                        # Skip if already in English
                        if detected_language == 'en':
                            logging.info("Tweet is already in English, skipping translation")
                            self._save_last_processed_id(tweet.id)
                            last_processed_id = tweet.id
                            time.sleep(self.check_interval)
                            continue
                        
                        # Prepare translated tweet
                        repost_text = self.translation_service.prepare_tweet(tweet.text, detected_language)
                        if not repost_text:
                            logging.error("Failed to prepare tweet for reposting")
                            time.sleep(self.check_interval)
                            continue
                        
                        # Create and post translation
                        response_data = self.twitter_client.create_tweet(repost_text)
                        if response_data:
                            logging.info(f"Successfully posted tweet: {response_data['id']}")
                            self._save_last_processed_id(tweet.id)
                            last_processed_id = tweet.id
                        else:
                            logging.error("Failed to post tweet, will retry on next iteration")
                            
                    except Exception as e:
                        logging.error(f"Error processing tweet: {str(e)}")
                else:
                    logging.info("No new tweets found")
                
                time.sleep(self.check_interval)
                
            except tweepy.errors.TooManyRequests as e:
                reset_time = int(e.response.headers.get('x-rate-limit-reset', 0))
                wait_time = max(reset_time - int(time.time()), 60)  # At least 60 seconds
                logging.warning(f"Rate limit exceeded. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                
            except Exception as e:
                logging.error(f"Unexpected error in main loop: {str(e)}")
                time.sleep(60)
