# test_twitter_client.py
import logging
from dotenv import load_dotenv
from twitter_client import TwitterClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_post_reply():
    """Test posting a reply to a tweet"""
    # Load environment variables
    load_dotenv()
    
    # Initialize Twitter client
    client = TwitterClient()
    
    # Get the latest mentions (minimum 5 as required by API)
    mentions = client.get_mentions(count=5)
    
    if not mentions:
        logger.error("No mentions found to reply to")
        return False
    
    # Get the first mention
    mention = mentions[0]
    logger.info(f"Found mention: ID={mention.id}, Text={mention.text[:50]}...")
    
    # Post a test reply
    test_reply = "This is a test reply to verify the fix. Please ignore."
    result = client.post_reply(mention.id, test_reply)
    
    if result:
        logger.info("Successfully posted test reply")
        return True
    else:
        logger.error("Failed to post test reply")
        return False

if __name__ == "__main__":
    print("Starting Twitter client test...")
    test_result = test_post_reply()
    print(f"Test result: {'SUCCESS' if test_result else 'FAILED'}") 