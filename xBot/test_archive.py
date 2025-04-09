# test_archive.py
import logging
import os
from dotenv import load_dotenv
from upload_doc import ArchiveUploader

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_archive_upload():
    """Test Archive.org upload functionality"""
    # Load environment variables
    load_dotenv()
    
    # Get credentials
    access_key = os.getenv('S3_ACCESS_KEY')
    secret_key = os.getenv('S3_SECRET_KEY')
    
    if not access_key or not secret_key:
        logger.error("Missing S3 credentials in environment variables")
        return False
    
    logger.info(f"Found S3 credentials - Access key: {access_key[:4]}..., Secret key: {secret_key[:4]}...")
    
    # Create uploader
    uploader = ArchiveUploader(access_key, secret_key)
    
    # Test upload
    sample_text = "This is sample text to upload to Archive.org."
    translated = "Esta es una muestra de texto para subir a Archive.org."
    
    file_path = "extracted_texts/test_upload.txt"
    result = uploader.upload_translation(
        file_path=file_path,
        language_from="en",
        original_text=sample_text,
        translated_text=translated,
        tweet_id="test123456"
    )
    
    if result:
        logger.info(f"Upload successful! Access the file at: {result}")
        return True
    else:
        logger.error("Upload failed")
        return False

if __name__ == "__main__":
    test_result = test_archive_upload()
    print(f"Test result: {'SUCCESS' if test_result else 'FAILED'}") 