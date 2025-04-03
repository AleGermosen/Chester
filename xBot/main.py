# main.py
import os
import logging
from bot import TwitterBot
from config import Config

def setup_logging():
    """Configure logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('twitter_bot.log'),
            logging.StreamHandler()
        ]
    )

def main():
    """Main entry point"""
    try:
        # Setup logging
        setup_logging()
        logger = logging.getLogger(__name__)
        
        # Initialize bot
        logger.info("Initializing Twitter bot...")
        bot = TwitterBot()
        
        # Run the bot
        logger.info("Starting Twitter bot...")
        bot.run()
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise

if __name__ == "__main__":
    main()
