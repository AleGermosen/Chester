import os
from dotenv import load_dotenv
from tweepy import Client, TweepyException
import json

# Load environment variables
load_dotenv()

# Twitter API credentials
bearer_token = os.getenv('BEARER_TOKEN')
consumer_key = os.getenv('CONSUMER_KEY')
consumer_secret = os.getenv('CONSUMER_SECRET')
access_token = os.getenv('ACCESS_TOKEN')
access_token_secret = os.getenv('ACCESS_TOKEN_SECRET')

def check_api_keys():
    try:
        # Initialize client with all keys
        client = Client(
            bearer_token=bearer_token,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        # Try to fetch something from the API to check authentication
        user = client.get_user(username="haitienespanol")
        
        if user.data:
            print("Authentication successful!")
            print("Keys are valid and can access the Twitter API.")
        else:
            print("Authentication was successful, but no data returned for user 'haitienespanol'.")
        
    except TweepyException as e:
        error_json = json.loads(str(e))
        if 'errors' in error_json:
            for error in error_json['errors']:
                print(f"Error {error['code']}: {error['message']}")
        else:
            print(f"An error occurred: {str(e)}")
        
        if 'invalid' in str(e).lower() or 'unauthorized' in str(e).lower():
            print("One or more of your API keys might be invalid or unauthorized.")
        elif 'rate limit' in str(e).lower():
            print("You've hit a rate limit. Try again later.")
        else:
            print("An unexpected error occurred while checking the keys.")
    
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    print("Checking Twitter API keys...")
    check_api_keys()