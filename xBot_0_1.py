import tweepy
from deep_translator import GoogleTranslator
import time
import os
from dotenv import load_dotenv
# Load environment variables
load_dotenv()
# Twitter API credentials
client = tweepy.Client(
    bearer_token=os.getenv('BEARER_TOKEN'),
    consumer_key=os.getenv('CONSUMER_KEY'),
    consumer_secret=os.getenv('CONSUMER_SECRET'),
    access_token=os.getenv('ACCESS_TOKEN'),
    access_token_secret=os.getenv('ACCESS_TOKEN_SECRET'),
    wait_on_rate_limit=True
)
# Initialize translator (Spanish to English by default)
translator = GoogleTranslator(source='es', target='en')
def get_latest_tweet(username):
    """Get the latest tweet from a specified user"""
    try:
        # Get user ID from username
        user = client.get_user(username=username, user_fields=['id'])
        if not user.data:
            raise Exception(f"User {username} not found")
        
        # Get latest tweets from user
        tweets = client.get_users_tweets(
            id=user.data.id,
            max_results=5,
            tweet_fields=['text', 'created_at'],
            exclude=['retweets', 'replies']
        )
        
        if not tweets.data:
            raise Exception(f"No tweets found for {username}")
        
        return tweets.data[0]
        
    except Exception as e:
        print(f"Error getting latest tweet: {str(e)}")
        return None
def translate_and_repost(username, check_interval=300):
    """
    Continuously check for new tweets, translate and repost them
    check_interval: time between checks in seconds (default 5 minutes)
    """
    last_processed_id = None
    
    while True:
        try:
            print(f"Checking for new tweets from {username}...")
            
            tweet = get_latest_tweet(username)
            
            if tweet and str(tweet.id) != str(last_processed_id):
                print(f"Found new tweet: {tweet.text}")
                
                # Translate the tweet
                translated_text = translator.translate(tweet.text)
                print(f"Translated text: {translated_text}")
                
                # Create the repost text
                # repost_text = f"Translated from @{username}:\n\n{translated_text}"
                repost_text = f"{translated_text}"
                
                # Post the translation
                response = client.create_tweet(text=repost_text)
                
                if response.data:
                    print(f"Successfully posted tweet with ID: {response.data['id']}")
                    last_processed_id = tweet.id
                
            else:
                print("No new tweets found")
            # Wait before checking again
            print(f"Waiting {check_interval} seconds before next check...")
            time.sleep(check_interval)
            
        except Exception as e:
            print(f"Error: {str(e)}")
            print("Waiting 60 seconds before retrying...")
            time.sleep(60)
def main():
    TARGET_USERNAME = "haitienespanol"  # Username we want to monitor
    
    try:
        print(f"Starting to monitor tweets from @{TARGET_USERNAME}")
        translate_and_repost(TARGET_USERNAME)
        
    except KeyboardInterrupt:
        print("\nStopping the bot...")
if __name__ == "__main__":
    main()