# tweet_processor.py
import logging

class TweetProcessor:
    @staticmethod
    def clean_tweet_text(tweet_text):
        """
        Clean and preprocess tweet text
        
        :param tweet_text: Original tweet text
        :return: Cleaned tweet text
        """
        try:
            # Remove URLs
            import re
            tweet_text = re.sub(r'http\S+', '', tweet_text)
            
            # Remove extra whitespace
            tweet_text = ' '.join(tweet_text.split())
            
            return tweet_text
        except Exception as e:
            logging.error(f"Error cleaning tweet text: {e}")
            return tweet_text

    @staticmethod
    def is_retweet(tweet):
        """
        Check if the tweet is a retweet
        
        :param tweet: Tweet object
        :return: Boolean indicating if it's a retweet
        """
        try:
            return (tweet.referenced_tweets and 
                    any(ref.type == 'retweeted' for ref in tweet.referenced_tweets))
        except Exception as e:
            logging.error(f"Error checking if tweet is a retweet: {e}")
            return False

    @staticmethod
    def extract_original_tweet_text(tweet, twitter_client):
        """
        Extract original tweet text for retweets
        
        :param tweet: Tweet object
        :param twitter_client: TwitterClient instance
        :return: Original tweet text
        """
        try:
            if TweetProcessor.is_retweet(tweet):
                for ref in tweet.referenced_tweets:
                    if ref.type == 'retweeted':
                        original_tweet = twitter_client.get_tweet(ref.id, tweet_fields=['text'])
                        return original_tweet.data.text if original_tweet.data else tweet.text
            return tweet.text
        except Exception as e:
            logging.error(f"Error extracting original tweet text: {e}")
            return tweet.text

    @staticmethod
    def truncate_tweet(text, max_length=280):
        """
        Truncate tweet text to fit Twitter's character limit
        
        :param text: Original text
        :param max_length: Maximum tweet length
        :return: Truncated text
        """
        if len(text) <= max_length:
            return text
        
        # Truncate and add ellipsis
        return text[:max_length-3] + "..."
