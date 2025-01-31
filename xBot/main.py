# main.py
import logging
from bot import TwitterTranslationBot

def main():
    try:
        # List of potential usernames to translate
        usernames = [
            "haitienespanol",
            "DominiqueAyiti",
            "PresidenceHT",
            "metropoleHT",
            "RodneyHayti"
        ]
        
        # Choose a username (you can modify this logic as needed)
        target_username = "haitienespanol"
        
        # Initialize and run the bot
        bot = TwitterTranslationBot(target_username)
        bot.run()
    
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")

if __name__ == "__main__":
    main()
