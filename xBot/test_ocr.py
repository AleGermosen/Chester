# test_ocr.py
import os
import logging
import tempfile
import requests
from dotenv import load_dotenv
from ocr_reader import OCRReader
from translation_service import TranslationService
from PIL import Image, ImageDraw, ImageFont

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_test_image(text="Bonjour le monde!", language="fr"):
    """Create a test image with text in the specified language"""
    # Create a blank image
    img = Image.new('RGB', (400, 200), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    
    # Try to use a default font
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        # If font not found, use default
        font = ImageFont.load_default()
    
    # Add text to the image
    d.text((10, 10), text, fill=(0, 0, 0), font=font)
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
        img.save(temp_file, format='PNG')
        temp_path = temp_file.name
        
    return temp_path

def test_ocr_without_translation():
    """Test OCR extraction without auto-translation"""
    # Load environment variables
    load_dotenv()
    
    # Get API key
    detect_api_key = os.getenv('DETECT_API_KEY')
    if not detect_api_key:
        logger.error("Missing API key for language detection")
        return False
    
    # Initialize translator and OCR reader
    translator = TranslationService(detect_api_key)
    ocr = OCRReader(translator=translator)
    
    # Create a test image with French text
    test_text = "Bonjour le monde! C'est un test pour OCR."
    test_image_path = create_test_image(test_text, "fr")
    logger.info(f"Created test image at: {test_image_path}")
    
    try:
        # Test the OCR reader with the local image path directly
        results = ocr.reader.readtext(test_image_path)
        
        # Combine all text
        extracted_text = " ".join([result[1] for result in results])
        logger.info(f"Extracted text: {extracted_text}")
        
        # Detect language
        detected_lang = translator.detect_language(extracted_text)
        logger.info(f"Detected language: {detected_lang}")
        
        # Now manually translate
        if detected_lang and detected_lang != 'en':
            translated_text = translator.translate_text(extracted_text, source_language=detected_lang)
            logger.info(f"Translated text: {translated_text}")
            
            # These should be different if we're not auto-translating
            if extracted_text != translated_text:
                logger.info("SUCCESS: Extracted text is different from translated text")
                return True
            else:
                logger.error("FAIL: Extracted text matches translated text - this suggests auto-translation is still happening")
                return False
        else:
            logger.info("No translation needed - text is already in English")
            return True
            
    except Exception as e:
        logger.error(f"Error in OCR test: {str(e)}")
        return False
    finally:
        # Clean up test image
        try:
            os.unlink(test_image_path)
            logger.info(f"Deleted test image: {test_image_path}")
        except:
            pass

if __name__ == "__main__":
    test_result = test_ocr_without_translation()
    print(f"Test result: {'SUCCESS' if test_result else 'FAILED'}") 