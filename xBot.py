from deep_translator import GoogleTranslator, single_detection
from dotenv import load_dotenv
import os
import time
import tweepy
import logging
from typing import Optional, Dict
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('twitter_bot.log'),
        logging.StreamHandler()
    ]
)

class TwitterTranslationBot:
    def __init__(self, target_username: str, check_interval: int = 300):
        # Load environment variables
        load_dotenv()
        
        # Configuration
        self.target_username = target_username
        self.check_interval = check_interval
        self.last_processed_id_file = 'last_processed_id.txt'
        
        # Initialize API clients
        self.client = self._init_twitter_client()
        self.translator = GoogleTranslator(target='en')
        
    def _init_twitter_client(self) -> tweepy.Client:
        """Initialize and return Twitter API client with error handling"""
        required_env_vars = [
            'BEARER_TOKEN', 'CONSUMER_KEY', 'CONSUMER_SECRET',
            'ACCESS_TOKEN', 'ACCESS_TOKEN_SECRET'
        ]
        
        # Verify all required environment variables are present
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
            
        return tweepy.Client(
            bearer_token=os.getenv('BEARER_TOKEN'),
            consumer_key=os.getenv('CONSUMER_KEY'),
            consumer_secret=os.getenv('CONSUMER_SECRET'),
            access_token=os.getenv('ACCESS_TOKEN'),
            access_token_secret=os.getenv('ACCESS_TOKEN_SECRET'),
            wait_on_rate_limit=True
        )
    
    def _save_last_processed_id(self, tweet_id: str) -> None:
        """Save the last processed tweet ID to file"""
        try:
            with open(self.last_processed_id_file, 'w') as file:
                file.write(str(tweet_id))
        except IOError as e:
            logging.error(f"Failed to save last processed ID: {e}")

    def _read_last_processed_id(self) -> Optional[str]:
        """Read the last processed tweet ID from file"""
        try:
            if os.path.exists(self.last_processed_id_file):
                with open(self.last_processed_id_file, 'r') as file:
                    return file.read().strip()
        except IOError as e:
            logging.error(f"Failed to read last processed ID: {e}")
        return None

    def get_latest_tweet(self) -> Optional[Dict]:
        """Get the latest non-reply post (tweet or retweet) from the target user"""
        try:
            user = self.client.get_user(username=self.target_username, user_fields=['id'])
            if not user.data:
                raise ValueError(f"User {self.target_username} not found")
            
            # Get recent posts including retweets, excluding all replies
            tweets = self.client.get_users_tweets(
                id=user.data.id,
                max_results=10,  # Increased to ensure we find non-reply posts
                tweet_fields=['text', 'created_at', 'referenced_tweets', 'in_reply_to_user_id'],
                exclude=['replies']
            )
            
            if not tweets.data:
                logging.info(f"No posts found for user {self.target_username}")
                return None
            
            # Filter out any remaining replies (tweets with in_reply_to_user_id)
            non_reply_tweets = [
                tweet for tweet in tweets.data 
                if tweet.in_reply_to_user_id is None
            ]
            
            if not non_reply_tweets:
                logging.info(f"No non-reply posts found for user {self.target_username}")
                return None
                
            latest_post = non_reply_tweets[0]
            
            # If it's a retweet, get the original tweet's text
            if latest_post.referenced_tweets and any(ref.type == 'retweeted' for ref in latest_post.referenced_tweets):
                for ref in latest_post.referenced_tweets:
                    if ref.type == 'retweeted':
                        original_tweet = self.client.get_tweet(ref.id, tweet_fields=['text'])
                        if original_tweet.data:
                            latest_post.text = original_tweet.data.text
            
            return latest_post
            
        except Exception as e:
            logging.error(f"Error getting latest post: {str(e)}")
            return None

    def create_tweet(self, text: str) -> Optional[Dict]:
        """
        Attempt to create a tweet with proper error handling
        """
        try:
            response = self.client.create_tweet(text=text)
            return response.data
        except tweepy.errors.Forbidden as e:
            logging.error(f"403 Forbidden error when posting tweet: {str(e)}")
            logging.error("This usually means the app doesn't have write permissions or the tweet is a duplicate")
            return None
        except tweepy.errors.TooManyRequests as e:
            logging.error(f"Rate limit exceeded when posting tweet: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error when posting tweet: {str(e)}")
            return None

    def run(self) -> None:
        """Main loop to check for new tweets, translate and repost them"""
        last_processed_id = self._read_last_processed_id()
        
        while True:
            try:
                logging.info(f"Checking for new tweets from {self.target_username}...")
                tweet = self.get_latest_tweet()
                
                if tweet and str(tweet.id) != str(last_processed_id):
                    logging.info(f"Found new tweet: {tweet.text}")
                    
                    try:
                        # Detect language and translate
                        detected_language = single_detection(tweet.text, api_key=os.getenv('DETECT_API_KEY'))
                        if detected_language == 'en':
                            logging.info("Tweet is already in English, skipping translation")
                            self._save_last_processed_id(tweet.id)
                            last_processed_id = tweet.id
                            continue
                            
                        translated_text = self.translator.translate(
                            tweet.text,
                            source=detected_language,
                            target='en'
                        )
                        
                        # Create and post translation
                        repost_text = (
                            f"Translated from @{self.target_username} "
                            f"({detected_language} → en):\n\n{translated_text}"
                        )
                        
                        # Check tweet length and truncate if necessary
                        if len(repost_text) > 280:
                            repost_text = repost_text[:277] + "..."
                        
                        response_data = self.create_tweet(repost_text)
                        if response_data:
                            logging.info(f"Successfully posted tweet: {response_data['id']}")
                            self._save_last_processed_id(tweet.id)
                            last_processed_id = tweet.id
                        else:
                            logging.error("Failed to post tweet, will retry on next iteration")
                            
                    except Exception as e:
                        logging.error(f"Error processing tweet: {str(e)}")
                        # Don't update last_processed_id so we can retry this tweet
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

def main():
    try:
        # bot = TwitterTranslationBot("haitienespanol")
        # bot = TwitterTranslationBot("DominiqueAyiti")
        # bot = TwitterTranslationBot("PresidenceHT")
        bot = TwitterTranslationBot("metropoleHT")
        bot.run()
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")

if __name__ == "__main__":
    main()