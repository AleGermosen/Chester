from internetarchive import upload, get_item
import logging
import os
from datetime import datetime

class ArchiveUploader:
    def __init__(self, access_key=None, secret_key=None):
        """
        Initialize Archive.org uploader
        
        :param access_key: S3 access key for archive.org
        :param secret_key: S3 secret key for archive.org
        """
        self.logger = logging.getLogger(__name__)
        self.access_key = access_key
        self.secret_key = secret_key
        
        if not access_key or not secret_key:
            self.logger.warning("Missing Archive.org credentials")
        else:
            self.logger.info("Archive.org uploader initialized with credentials")
            
    def upload_translation(self, file_path, language_from, original_text, translated_text, tweet_id=None):
        """
        Upload a translation to Archive.org
        
        :param file_path: Path to save the translation file
        :param language_from: Source language code
        :param original_text: Original text content
        :param translated_text: Translated text content
        :param tweet_id: Twitter ID associated with the content (optional)
        :return: URL of the uploaded content or None if upload failed
        """
        try:
            # Create directory for translations if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Create content file with original and translation
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"Original ({language_from}):\n\n{original_text}\n\n")
                f.write(f"Translation (en):\n\n{translated_text}\n\n")
                f.write(f"Translated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                if tweet_id:
                    f.write(f"Source Tweet ID: {tweet_id}\n")
            
            # Generate unique identifier
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            identifier = f"xbot_translation_{timestamp}"
            if tweet_id:
                identifier = f"xbot_tweet_{tweet_id}_{timestamp}"
            
            # Metadata for the upload
            metadata = {
                "title": f"Translation from {language_from} to English",
                "mediatype": "texts",
                "description": f"Translation from {language_from} to English by xBot",
                "collection": "opensource",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "language": f"{language_from}, en",
                "creator": "xBot Twitter Translation Bot"
            }
            
            if tweet_id:
                metadata["source"] = f"https://twitter.com/i/web/status/{tweet_id}"
            
            # Configure S3 credentials
            config = {
                's3': {
                    'access': self.access_key,
                    'secret': self.secret_key
                }
            }
            
            # Upload the file
            self.logger.info(f"Uploading translation to Archive.org with identifier: {identifier}")
            response = upload(identifier, files=file_path, metadata=metadata, config=config)
            
            # Check if upload was successful
            if response[0].status_code == 200:
                item_url = f"https://archive.org/details/{identifier}"
                self.logger.info(f"Upload successful! Item URL: {item_url}")
                return item_url
            else:
                self.logger.error(f"Upload failed. Status code: {response[0].status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error uploading translation to Archive.org: {str(e)}")
            return None

# Example usage (only runs when script is executed directly)
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example translation data
    sample_text = "Este es un documento generado por Python."
    translated = "This is a Python-generated document."
    
    # Load credentials from environment variables
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    access_key = os.getenv('S3_ACCESS_KEY')
    secret_key = os.getenv('S3_SECRET_KEY')
    
    # Create uploader
    uploader = ArchiveUploader(access_key, secret_key)
    
    # Test upload
    file_path = "extracted_texts/sample_translation.txt"
    result = uploader.upload_translation(
        file_path=file_path,
        language_from="es",
        original_text=sample_text,
        translated_text=translated
    )
    
    if result:
        print(f"Upload successful! Access the file at: {result}")
    else:
        print("Upload failed. Check logs for details.")