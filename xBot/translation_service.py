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
        self.translator = GoogleTranslator(target='en')
        self.detect_api_key = detect_api_key

    def detect_language(self, text):
        """
        Detect the language of the given text
        
        :param text: Text to detect language for
        :return: Detected language code
        """
        try:
            # Clean the text before language detection
            cleaned_text = TweetProcessor.clean_tweet_text(text)
            return single_detection(cleaned_text, api_key=self.detect_api_key)
        except Exception as e:
            logging.error(f"Language detection error: {e}")
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