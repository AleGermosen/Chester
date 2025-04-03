# translation_service.py
from deep_translator import GoogleTranslator, single_detection
import logging
from tweet_processor import TweetProcessor

class TranslationService:
    def __init__(self, detect_api_key=None):
        """
        Initialize translation service
        
        :param detect_api_key: API key for language detection
        """
        self.logger = logging.getLogger(__name__)
        self.translator = GoogleTranslator(target='en')
        
        # Log initial API key state
        self.logger.info(f"TranslationService initialization - API key provided: {detect_api_key is not None}")
        if detect_api_key:
            self.logger.info(f"Initial API key length: {len(detect_api_key)}")
        
        # Validate and store API key
        if detect_api_key:
            # Clean the API key
            detect_api_key = detect_api_key.strip()
            if not detect_api_key:
                self.logger.warning("Empty API key provided after stripping")
                self.detect_api_key = None
            else:
                self.detect_api_key = detect_api_key
                self.logger.info(f"TranslationService initialized with valid API key (length: {len(detect_api_key)})")
        else:
            self.logger.warning("No API key provided for language detection")
            self.detect_api_key = None
            
        # Log final API key state
        self.logger.info(f"Final API key state - Present: {self.detect_api_key is not None}, Length: {len(self.detect_api_key) if self.detect_api_key else 0}")

    def detect_language(self, text):
        """
        Detect the language of the given text
        
        :param text: Text to detect language for
        :return: Detected language code
        """
        try:
            # Log API key state at start of detection
            self.logger.info(f"Starting language detection - API key present: {self.detect_api_key is not None}, Length: {len(self.detect_api_key) if self.detect_api_key else 0}")
            
            # Clean the text before language detection
            cleaned_text = TweetProcessor.clean_tweet_text(text)
            
            # Skip first 10 words to avoid common English words at the start
            words = cleaned_text.split()
            if len(words) > 10:
                cleaned_text = ' '.join(words[10:])
            
            # Log API key details
            self.logger.info(f"Attempting language detection with API key length: {len(self.detect_api_key) if self.detect_api_key else 0}")
            self.logger.info(f"Text to detect: {cleaned_text[:100]}...")  # Log first 100 chars
            
            # Ensure API key is not empty or None
            if not self.detect_api_key:
                self.logger.error("No API key provided for language detection")
                return None
                
            # Make the API call
            detected_lang = single_detection(cleaned_text, api_key=self.detect_api_key)
            self.logger.info(f"Successfully detected language: {detected_lang}")
            return detected_lang
            
        except Exception as e:
            self.logger.error(f"Language detection error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                self.logger.error(f"Response status code: {e.response.status_code}")
                self.logger.error(f"Response text: {e.response.text}")
            return None

    def translate_text(self, text, source_language):
        """
        Translate text to English
        
        :param text: Text to translate
        :param source_language: Source language code
        :return: Translated text
        """
        try:
            return self.translator.translate(
                text,
                source=source_language,
                target='en'
            )
        except Exception as e:
            logging.error(f"Translation error: {e}")
            return None

    def prepare_tweet(self, original_text, detected_language):
        """
        Prepare tweet text with language indicator
        
        :param original_text: Original tweet text
        :param detected_language: Detected language code
        :return: Formatted tweet text
        """
        # Clean the text
        cleaned_text = TweetProcessor.clean_tweet_text(original_text)
        
        # Translate the text
        translated_text = self.translate_text(cleaned_text, detected_language)
        
        if not translated_text:
            return None
        
        # Create repost text with language indicator
        repost_text = f"({detected_language} → en):\n\n{translated_text}"
        
        # Truncate if necessary
        return TweetProcessor.truncate_tweet(repost_text)