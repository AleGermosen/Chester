# twitter_client.py
import os
import tweepy
import logging
from tweet_processor import TweetProcessor
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get Twitter API credentials from environment variables
consumer_key = os.getenv("CONSUMER_KEY")
consumer_secret = os.getenv("CONSUMER_SECRET")
access_token = os.getenv("ACCESS_TOKEN")
access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")

# Authenticate to Twitter
auth = tweepy.OAuth1UserHandler(consumer_key, consumer_secret, access_token, access_token_secret)
api = tweepy.API(auth)
class TwitterClient:
    def __init__(self, credentials):
        """
        Initialize Twitter API client
        
        :param credentials: Dictionary of Twitter API credentials
        """
        try:
            self.client = tweepy.Client(
                bearer_token=credentials['BEARER_TOKEN'],
                consumer_key=credentials['CONSUMER_KEY'],
                consumer_secret=credentials['CONSUMER_SECRET'],
                access_token=credentials['ACCESS_TOKEN'],
                access_token_secret=credentials['ACCESS_TOKEN_SECRET'],
                wait_on_rate_limit=True
            )
        except Exception as e:
            logging.error(f"Failed to initialize Twitter client: {e}")
            raise

    def get_user_id(self, username):
        """
        Retrieve user ID for a given username
        
        :param username: Twitter username
        :return: User ID or None
        """
        try:
            user = self.client.get_user(username=username, user_fields=['id'])
            return user.data.id if user.data else None
        except Exception as e:
            logging.error(f"Error getting user ID for {username}: {e}")
            return None

    def get_latest_non_reply_tweet(self, user_id):
        """
        Get the latest non-reply tweet for a user
        
        :param user_id: Twitter user ID
        :return: Latest tweet or None
        """
        try:
            tweets = self.client.get_users_tweets(
                id=user_id,
                max_results=10,
                tweet_fields=['text', 'created_at', 'referenced_tweets', 'in_reply_to_user_id'],
                exclude=['replies']
            )
            
            if not tweets.data:
                return None
            
            # Filter out any remaining replies
            non_reply_tweets = [
                tweet for tweet in tweets.data 
                if tweet.in_reply_to_user_id is None
            ]
            
            if not non_reply_tweets:
                return None
                
            latest_post = non_reply_tweets[0]
            
            # Handle retweets using the TweetProcessor
            if TweetProcessor.is_retweet(latest_post):
                latest_post.text = TweetProcessor.extract_original_tweet_text(latest_post, self.client)
            
            return latest_post
        except Exception as e:
            logging.error(f"Error getting latest non-reply tweet: {e}")
            return None
    
    def get_tweet(tweet_id):
        try:
            tweet = api.get_status(tweet_id, tweet_mode='extended')
            return tweet
        except tweepy.errors.TweepyException as e:
            print(f"Error: {e}")
            return None

    def create_tweet(self, text):
        """
        Create a new tweet
        
        :param text: Text of the tweet
        :return: Tweet response or None
        """
        try:
            # Ensure tweet is within character limit
            tweet_text = TweetProcessor.truncate_tweet(text)
            
            response = self.client.create_tweet(text=tweet_text)
            return response.data
        except tweepy.errors.Forbidden as e:
            logging.error(f"403 Forbidden error when posting tweet: {e}")
            return None
        except tweepy.errors.TooManyRequests as e:
            logging.error(f"Rate limit exceeded when posting tweet: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error when posting tweet: {e}")
            return None