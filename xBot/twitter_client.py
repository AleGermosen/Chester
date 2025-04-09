# twitter_client.py
import os
import tweepy
import logging
from tweet_processor import TweetProcessor
from dotenv import load_dotenv
from config import Config

# Load environment variables from .env file
load_dotenv()

class TwitterClient:
    def __init__(self):
        self.config = Config()
        self.credentials = self.config.get_twitter_credentials()
        self.logger = logging.getLogger(__name__)
        
        # Initialize Client v2 (primary client)
        try:
            self.client = tweepy.Client(
                bearer_token=self.credentials['BEARER_TOKEN'],
                consumer_key=self.credentials['CONSUMER_KEY'],
                consumer_secret=self.credentials['CONSUMER_SECRET'],
                access_token=self.credentials['ACCESS_TOKEN'],
                access_token_secret=self.credentials['ACCESS_TOKEN_SECRET'],
                wait_on_rate_limit=True
            )
            self.media_url_cache = {}  # Cache to store tweet_id -> media_url mappings
            self.logger.info("Successfully initialized Client v2")
            
            # Get and store our own user ID
            me = self.client.get_me()
            self.user_id = me.data.id
            self.username = me.data.username
            self.logger.info(f"Authenticated as @{self.username}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Client v2: {str(e)}")
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
    
    def get_tweet(self, tweet_id):
        """Get tweet using v2 API"""
        try:
            tweet = self.client.get_tweet(
                tweet_id,
                tweet_fields=['text', 'entities', 'attachments', 'author_id']
            )
            self.logger.info(f"Successfully retrieved tweet {tweet_id}")
            return tweet.data
            
        except tweepy.errors.TweepyException as e:
            self.logger.error(f"Error getting tweet {tweet_id}: {str(e)}")
            if hasattr(e, 'response'):
                self.logger.error(f"Response status: {e.response.status_code}")
                self.logger.error(f"Response text: {e.response.text}")
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

    def post_reply(self, tweet_id, reply_text):
        """Post a reply to a tweet"""
        try:
            response = self.client.create_tweet(
                text=reply_text,
                in_reply_to_tweet_id=tweet_id
            )
            self.logger.info(f"Successfully posted reply to tweet {tweet_id}")
            return response
            
        except Exception as e:
            self.logger.error(f"Error posting reply to tweet {tweet_id}: {str(e)}")
            return None

    def get_user_tweets(self, count=10):
        """Get tweets from our own account"""
        try:
            tweets = self.client.get_users_tweets(
                self.user_id,
                max_results=count,
                tweet_fields=['text', 'entities', 'attachments']
            )
            self.logger.info(f"Successfully retrieved {count} tweets from our account")
            return tweets.data if tweets.data else []
            
        except Exception as e:
            self.logger.error(f"Error getting tweets from our account: {str(e)}")
            return []

    def get_mentions(self, count=10):
        """Get mentions of our account"""
        try:
            self.logger.info(f"Attempting to get mentions for user ID: {self.user_id}")
            self.logger.info(f"Requesting {count} mentions")
            
            mentions = self.client.get_users_mentions(
                self.user_id,
                max_results=count,
                tweet_fields=['text', 'entities', 'attachments', 'referenced_tweets']
            )
            
            # Log the raw response
            self.logger.info(f"Raw mentions response: {mentions}")
            
            # Log if we got any data
            if mentions.data:
                mentions_count = len(mentions.data)
                self.logger.info(f"Successfully retrieved {mentions_count} mention(s)")
                # Log details of each mention
                for i, mention in enumerate(mentions.data, 1):
                    self.logger.info(f"Mention {i}: ID={mention.id}, Text={mention.text[:100]}...")
                    if hasattr(mention, 'referenced_tweets'):
                        self.logger.info(f"Mention {i} references: {mention.referenced_tweets}")
            else:
                self.logger.info("No mentions data received from API")
            
            return mentions.data if mentions.data else []
            
        except Exception as e:
            self.logger.error(f"Error getting mentions: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                self.logger.error(f"Response status code: {e.response.status_code}")
                self.logger.error(f"Response text: {e.response.text}")
            return []

    def get_media_url(self, tweet_id):
        """Get media URL for a tweet"""
        try:
            # Check cache first
            if tweet_id in self.media_url_cache:
                self.logger.info(f"Using cached media URL for tweet {tweet_id}")
                return self.media_url_cache[tweet_id]

            # Get the tweet with all necessary fields
            tweet = self.client.get_tweet(
                tweet_id, 
                tweet_fields=['attachments', 'entities', 'author_id'],
                expansions=['attachments.media_keys'],
                media_fields=['url', 'type', 'variants', 'preview_image_url']
            )
            
            if not tweet:
                self.logger.warning(f"Could not get tweet {tweet_id}")
                return None

            # Log the full tweet data for debugging
            self.logger.debug(f"Tweet data for {tweet_id}: {tweet}")

            # Check for media in includes (v2 API format)
            if hasattr(tweet, 'includes') and 'media' in tweet.includes:
                for media in tweet.includes['media']:
                    if media.type == 'photo':
                        url = media.url
                        self.media_url_cache[tweet_id] = url
                        self.logger.info(f"Found photo media URL for tweet {tweet_id}")
                        return url
                    elif media.type == 'video':
                        # For videos, get the highest quality variant
                        variants = getattr(media, 'variants', [])
                        video_variants = [v for v in variants if v.get('content_type') == 'video/mp4']
                        if video_variants:
                            # Sort by bitrate and get the highest quality
                            video_variants.sort(key=lambda x: x.get('bitrate', 0), reverse=True)
                            url = video_variants[0]['url']
                            self.media_url_cache[tweet_id] = url
                            self.logger.info(f"Found video media URL for tweet {tweet_id}")
                            return url

            # Check for media in entities (legacy format)
            if hasattr(tweet, 'entities') and 'media' in tweet.entities:
                for media in tweet.entities['media']:
                    if media['type'] == 'photo':
                        url = media['media_url_https']
                        self.media_url_cache[tweet_id] = url
                        self.logger.info(f"Found photo media URL in entities for tweet {tweet_id}")
                        return url
                    elif media['type'] == 'video':
                        variants = media.get('video_info', {}).get('variants', [])
                        video_variants = [v for v in variants if v['content_type'] == 'video/mp4']
                        if video_variants:
                            video_variants.sort(key=lambda x: x.get('bitrate', 0), reverse=True)
                            url = video_variants[0]['url']
                            self.media_url_cache[tweet_id] = url
                            self.logger.info(f"Found video media URL in entities for tweet {tweet_id}")
                            return url

            # Check for media in attachments
            if hasattr(tweet, 'attachments') and tweet.attachments:
                for attachment in tweet.attachments:
                    if attachment.type == 'photo':
                        url = attachment.url
                        self.media_url_cache[tweet_id] = url
                        self.logger.info(f"Found photo media URL in attachments for tweet {tweet_id}")
                        return url
                    elif attachment.type == 'video':
                        url = attachment.url
                        self.media_url_cache[tweet_id] = url
                        self.logger.info(f"Found video media URL in attachments for tweet {tweet_id}")
                        return url

            self.logger.warning(f"No media found in tweet {tweet_id}")
            return None

        except Exception as e:
            self.logger.error(f"Error getting media URL for tweet {tweet_id}: {str(e)}")
            return None

    def get_cached_media_url(self, tweet_id):
        """Get media URL for a tweet using cached data"""
        # Simply use the cache from get_media_url
        return self.get_media_url(tweet_id)