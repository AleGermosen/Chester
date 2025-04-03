import os
import logging
from dotenv import load_dotenv
from translation_service import TranslationService
from config import Config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_translation():
    """Test translation service with a sample text"""
    try:
        # Load environment variables
        load_dotenv()
        
        # Get API key
        config = Config()
        detect_api_key = config.get_detect_api_key()
        logger.info(f"Retrieved DETECT_API_KEY with length: {len(detect_api_key) if detect_api_key else 0}")
        
        # Create translation service
        translator = TranslationService(detect_api_key)
        
        # Test text (French)
        test_text = "Transition appelle à la reprise du dialogue entre Haïti et la République dominicaine Port-au-Prince;"
        logger.info(f"Testing with text: {test_text}")
        
        # Detect language
        detected_lang = translator.detect_language(test_text)
        logger.info(f"Detected language: {detected_lang}")
        
        if detected_lang and detected_lang != 'en':
            # Translate text
            translated_text = translator.translate_text(test_text, source_language=detected_lang)
            logger.info(f"Translated text: {translated_text}")
            
            # Format reply
            reply_text = f"({detected_lang} → en):\n\n{translated_text}"
            logger.info(f"Formatted reply:\n{reply_text}")
        else:
            logger.info("No translation needed (English or no language detected)")
            
    except Exception as e:
        logger.error(f"Error in test_translation: {str(e)}")

if __name__ == "__main__":
    test_translation() 