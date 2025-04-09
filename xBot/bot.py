# bot.py
import os
import time
import logging
import tweepy
from config import Config
from twitter_client import TwitterClient
from translation_service import TranslationService
from ocr_reader import extract_and_translate_text, save_to_documents, OCRReader
from upload_doc import ArchiveUploader
import tempfile
import requests
from datetime import datetime

class TwitterBot:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = Config()
        self.client = TwitterClient()
        
        # Get detect API key first
        detect_api_key = self.config.get_detect_api_key()
        if detect_api_key:
            detect_api_key = detect_api_key.strip()
            if not detect_api_key:
                self.logger.warning("Empty detect API key found in config")
                detect_api_key = None
            else:
                self.logger.info(f"Found detect API key (length: {len(detect_api_key)})")
        else:
            self.logger.warning("No detect API key found in config")
            detect_api_key = None
            
        # Create translation service with API key
        self.translator = TranslationService(detect_api_key)
        
        # Pass the translator to OCRReader
        self.ocr = OCRReader(translator=self.translator)
        
        # Initialize Archive.org uploader
        s3_access_key, s3_secret_key = self.config.get_s3_credentials()
        if s3_access_key and s3_secret_key:
            self.logger.info("Archive.org integration enabled with valid credentials")
            self.archive_uploader = ArchiveUploader(s3_access_key, s3_secret_key)
            self.archive_enabled = True
        else:
            self.logger.warning("Archive.org integration disabled - missing credentials")
            self.archive_uploader = None
            self.archive_enabled = False
        
        self.last_processed_id = self._load_last_processed_id()
        self.processed_mentions_file = "processed_mentions.txt"
        self.downloaded_tweets_file = "downloaded_tweets.txt"
        self.pending_tweets_file = "pending_tweets.txt"
        self.processed_accounts_file = "processed_accounts.txt"  # New file for tracking accounts
        self.processed_mentions = self.load_processed_mentions()
        self.downloaded_tweets = self.load_downloaded_tweets()
        self.pending_tweets = self.load_pending_tweets()
        self.processed_accounts = self.load_processed_accounts()  # Load processed accounts

    def _load_last_processed_id(self):
        """Load the last processed tweet ID from file"""
        try:
            with open('last_processed_id.txt', 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            return None

    def _save_last_processed_id(self, tweet_id):
        """Save the last processed tweet ID to file"""
        with open('last_processed_id.txt', 'w') as f:
            f.write(str(tweet_id))

    def _extract_original_tweet_id(self, mention):
        """Extract the original tweet ID from a mention"""
        try:
            # Get the referenced tweets from the mention
            if hasattr(mention, 'referenced_tweets'):
                for ref in mention.referenced_tweets:
                    if ref.type == 'replied_to':
                        return ref.id
            return None
        except Exception as e:
            self.logger.error(f"Error extracting original tweet ID: {str(e)}")
            return None

    def _process_tweet(self, mention):
        """Process a mention and translate the original tweet"""
        try:
            # Skip if we've already processed this mention
            if self.last_processed_id and str(mention.id) <= self.last_processed_id:
                return

            # Get the original tweet ID
            original_tweet_id = self._extract_original_tweet_id(mention)
            if not original_tweet_id:
                self.logger.warning(f"Could not find original tweet ID in mention {mention.id}")
                return

            # Get the original tweet
            original_tweet = self.client.get_tweet(original_tweet_id)
            if not original_tweet:
                self.logger.warning(f"Could not get original tweet {original_tweet_id}")
                return

            # Get tweet text
            text = original_tweet.text
            
            # Check if tweet has media
            if hasattr(original_tweet, 'attachments') and original_tweet.attachments:
                # Download and process image
                image_url = self.client.get_media_url(original_tweet_id)
                if image_url:
                    text = self.ocr.extract_text(image_url)
            
            # Detect language and translate
            detected_lang = self.translator.detect_language(text)
            if detected_lang and detected_lang != 'en':
                translated_text = self.translator.translate_text(text, detected_lang)
                if translated_text:
                    # Save translation to Archive.org
                    self._upload_to_archive(text, translated_text, detected_lang, original_tweet_id)
            else:
                self.logger.info(f"No translation needed for tweet {original_tweet_id} (language: {detected_lang})")
            
            # Update last processed ID
            self._save_last_processed_id(mention.id)
            
        except Exception as e:
            self.logger.error(f"Error processing mention {mention.id}: {str(e)}")

    def _upload_to_archive(self, original_text, translated_text, detected_lang, tweet_id):
        """Upload translation to Archive.org"""
        # Skip if Archive.org integration is disabled
        if not self.archive_enabled or not self.archive_uploader:
            self.logger.info(f"Skipping Archive.org upload for tweet {tweet_id} - integration disabled")
            return False
            
        try:
            # Create a filename with timestamp and tweet ID
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"extracted_texts/tweet_{tweet_id}_{timestamp}.txt"
            
            # Upload to Archive.org
            archive_url = self.archive_uploader.upload_translation(
                file_path=filename,
                language_from=detected_lang,
                original_text=original_text,
                translated_text=translated_text,
                tweet_id=tweet_id
            )
            
            if archive_url:
                self.logger.info(f"Translation for tweet {tweet_id} archived at: {archive_url}")
                
                # Post only the archive link as a reply to the original tweet
                reply_text = f"Translation ({detected_lang} → en) available at: {archive_url}. No downloading required."
                
                # Post the reply with just the archive link
                self.client.post_reply(tweet_id, reply_text)
                self.logger.info(f"Posted archive link as reply to tweet {tweet_id}")
                return True
            else:
                self.logger.warning(f"Failed to archive translation for tweet {tweet_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error uploading to Archive.org: {str(e)}")
            return False

    def save_processed_mention(self, mention_id):
        """Save a processed mention ID to the file"""
        try:
            # First check if it's already in our in-memory set
            if str(mention_id) in self.processed_mentions:
                self.logger.info(f"Skipping already processed mention {mention_id}")
                return

            # Then check the file directly to be extra safe
            if os.path.exists(self.processed_mentions_file):
                with open(self.processed_mentions_file, 'r') as f:
                    if str(mention_id) in [line.strip() for line in f]:
                        self.logger.info(f"Found mention {mention_id} in file, skipping")
                        return

            # If we get here, it's a new mention
            self.processed_mentions.add(str(mention_id))
            
            # Use a temporary file for atomic write
            temp_file = f"{self.processed_mentions_file}.tmp"
            with open(temp_file, 'w') as f:
                # Write all existing mentions
                if os.path.exists(self.processed_mentions_file):
                    with open(self.processed_mentions_file, 'r') as old_f:
                        for line in old_f:
                            f.write(line)
                # Write the new mention
                f.write(f"{mention_id}\n")
            
            # Atomic rename
            os.replace(temp_file, self.processed_mentions_file)
            
            # Reload processed mentions to ensure we have the latest data
            self.processed_mentions = self.load_processed_mentions()
            
        except Exception as e:
            self.logger.error(f"Error saving processed mention: {e}")
            # Clean up temp file if it exists
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def load_processed_mentions(self):
        """Load the list of already processed mention IDs"""
        try:
            if os.path.exists(self.processed_mentions_file):
                with open(self.processed_mentions_file, 'r') as f:
                    # Use a set to ensure uniqueness
                    return set(line.strip() for line in f)
            return set()
        except Exception as e:
            self.logger.error(f"Error loading processed mentions: {e}")
            return set()

    def load_downloaded_tweets(self):
        """Load the list of downloaded tweet IDs"""
        try:
            if os.path.exists(self.downloaded_tweets_file):
                with open(self.downloaded_tweets_file, 'r') as f:
                    return set(line.strip() for line in f)
            return set()
        except Exception as e:
            self.logger.error(f"Error loading downloaded tweets: {e}")
            return set()

    def save_downloaded_tweet(self, tweet_id):
        """Save a downloaded tweet ID to the file"""
        try:
            with open(self.downloaded_tweets_file, 'a') as f:
                f.write(f"{tweet_id}\n")
            self.downloaded_tweets.add(tweet_id)
        except Exception as e:
            self.logger.error(f"Error saving downloaded tweet: {e}")

    def load_pending_tweets(self):
        """Load the list of tweets waiting for image download"""
        try:
            if os.path.exists(self.pending_tweets_file):
                with open(self.pending_tweets_file, 'r') as f:
                    return set(line.strip() for line in f)
            return set()
        except Exception as e:
            self.logger.error(f"Error loading pending tweets: {e}")
            return set()

    def save_pending_tweet(self, tweet_id):
        """Save a tweet ID that needs image download"""
        try:
            with open(self.pending_tweets_file, 'a') as f:
                f.write(f"{tweet_id}\n")
            self.pending_tweets.add(tweet_id)
        except Exception as e:
            self.logger.error(f"Error saving pending tweet: {e}")

    def remove_pending_tweet(self, tweet_id):
        """Remove a tweet from the pending list"""
        try:
            self.pending_tweets.remove(tweet_id)
            with open(self.pending_tweets_file, 'w') as f:
                for tweet in self.pending_tweets:
                    f.write(f"{tweet}\n")
        except Exception as e:
            self.logger.error(f"Error removing pending tweet: {e}")

    def load_processed_accounts(self):
        """Load the list of account IDs we've already processed"""
        try:
            if os.path.exists(self.processed_accounts_file):
                with open(self.processed_accounts_file, 'r') as f:
                    return set(line.strip() for line in f)
            return set()
        except Exception as e:
            self.logger.error(f"Error loading processed accounts: {e}")
            return set()

    def save_processed_account(self, account_id):
        """Save an account ID to the processed accounts file"""
        try:
            with open(self.processed_accounts_file, 'a') as f:
                f.write(f"{account_id}\n")
            self.processed_accounts.add(account_id)
            self.logger.info(f"Saved processed account ID: {account_id}")
        except Exception as e:
            self.logger.error(f"Error saving processed account: {e}")

    def process_mention(self, mention):
        """Process a single mention"""
        try:
            self.logger.info(f"Starting to process mention {mention.id}")
            
            # Skip if we've already processed this mention
            if str(mention.id) in self.processed_mentions:
                self.logger.info(f"Skipping already processed mention {mention.id}")
                return

            # Get the original tweet if this is a reply
            original_tweet_id = None
            if mention.referenced_tweets:
                for ref in mention.referenced_tweets:
                    if ref.type == 'replied_to':
                        original_tweet_id = ref.id
                        break

            if original_tweet_id:
                self.logger.info(f"Found original tweet ID: {original_tweet_id}")
                
                # Skip if we've already processed this original tweet
                if str(original_tweet_id) in self.processed_mentions:
                    self.logger.info(f"Skipping already processed original tweet {original_tweet_id}")
                    return

                # Get the original tweet
                original_tweet = self.client.get_tweet(original_tweet_id)
                if not original_tweet:
                    self.logger.warning(f"Could not get original tweet {original_tweet_id}")
                    return

                # Get tweet text
                text = original_tweet.text
                
                # Check if tweet has media
                if hasattr(original_tweet, 'attachments') and original_tweet.attachments:
                    # Check if we've already processed this account
                    author_id = str(original_tweet.author_id)
                    if author_id in self.processed_accounts:
                        self.logger.info(f"Already processed account {author_id}, using cached media URL")
                        # For processed accounts, we can use the cached media URL directly
                        image_url = self.client.get_cached_media_url(original_tweet_id)
                    else:
                        # For new accounts, get the media URL normally
                        image_url = self.client.get_media_url(original_tweet_id)
                        # Save the account ID after processing
                        self.save_processed_account(author_id)

                    if image_url:
                        try:
                            # Extract text from image
                            extracted_text = self.ocr.extract_text(image_url)
                            if extracted_text:
                                text = extracted_text
                                self.logger.info(f"Successfully extracted text from image for tweet {original_tweet_id}")
                                
                                # Save the extracted text
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                extracted_text_filename = f"tweet_{original_tweet_id}_{timestamp}_extracted.txt"
                                with open(os.path.join("extracted_texts", extracted_text_filename), 'w', encoding='utf-8') as f:
                                    f.write(text)
                                self.logger.info(f"Saved extracted text to {extracted_text_filename}")
                            else:
                                self.logger.warning(f"No text extracted from image for tweet {original_tweet_id}")
                        except Exception as e:
                            self.logger.error(f"Error processing image for tweet {original_tweet_id}: {str(e)}")
                            # Continue with original text if image processing fails
                
                # Detect language and translate
                detected_lang = self.translator.detect_language(text)
                if detected_lang and detected_lang != 'en':
                    translated_text = self.translator.translate_text(text, source_language=detected_lang)
                    if translated_text:
                        # Save the translated text locally
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        translated_text_filename = f"tweet_{original_tweet_id}_{timestamp}_translated.txt"
                        with open(os.path.join("extracted_texts", translated_text_filename), 'w', encoding='utf-8') as f:
                            f.write(translated_text)
                        self.logger.info(f"Saved translated text to {translated_text_filename}")
                        
                        # Upload translation to Archive.org (this will post the archive link as a reply)
                        self._upload_to_archive(text, translated_text, detected_lang, original_tweet_id)
                        
                        # Save both the mention ID and original tweet ID to processed mentions
                        self.save_processed_mention(mention.id)
                        self.save_processed_mention(original_tweet_id)
                else:
                    self.logger.info(f"No translation needed for tweet {original_tweet_id} (language: {detected_lang})")
                    # Still save both IDs to prevent reprocessing
                    self.save_processed_mention(mention.id)
                    self.save_processed_mention(original_tweet_id)
                
        except Exception as e:
            self.logger.error(f"Error processing mention {mention.id}: {str(e)}")

    def process_pending_tweets(self):
        """Process tweets that are waiting for image download"""
        self.logger.info(f"Starting to process {len(self.pending_tweets)} pending tweets")
        for tweet_id in list(self.pending_tweets):  # Create a copy to iterate
            try:
                self.logger.info(f"Processing pending tweet {tweet_id}")
                # Get the media URL
                self.logger.info(f"Getting media URL for pending tweet {tweet_id}")
                media_url = self.client.get_media_url(tweet_id)
                if media_url:
                    self.logger.info(f"Found media URL for pending tweet {tweet_id}")
                    # Download the image
                    self.logger.info(f"Downloading image for pending tweet {tweet_id}")
                    image_path = self.ocr.download_image(media_url)
                    if image_path:
                        self.logger.info(f"Successfully downloaded image for tweet {tweet_id}")
                        # Save as downloaded
                        self.save_downloaded_tweet(tweet_id)
                        # Remove from pending
                        self.remove_pending_tweet(tweet_id)
                        self.logger.info(f"Removed tweet {tweet_id} from pending list")
                        
                        # Process the image
                        try:
                            self.logger.info(f"Extracting text from downloaded image for tweet {tweet_id}")
                            extracted_text = self.ocr.extract_text(image_path)
                            if extracted_text:
                                self.logger.info(f"Successfully extracted text from tweet {tweet_id}")
                                detected_lang = self.translator.detect_language(extracted_text)
                                if detected_lang and detected_lang != 'en':
                                    self.logger.info(f"Detected non-English language ({detected_lang}) for tweet {tweet_id}")
                                    translated_text = self.translator.translate_text(extracted_text)
                                    if translated_text:
                                        self.logger.info(f"Successfully translated text from tweet {tweet_id}")
                                        self.save_processed_mention(tweet_id)
                                        
                                        # Upload translation to Archive.org
                                        self._upload_to_archive(extracted_text, translated_text, detected_lang, tweet_id)
                            else:
                                self.logger.warning(f"No text extracted from downloaded image for tweet {tweet_id}")
                        finally:
                            self.logger.info(f"Cleaning up downloaded image for tweet {tweet_id}")
                            self.ocr.cleanup_image(image_path)
                else:
                    self.logger.warning(f"No media URL found for pending tweet {tweet_id}")
            except Exception as e:
                if "Rate limit exceeded" in str(e):
                    self.logger.warning(f"Rate limit hit while processing pending tweet {tweet_id}")
                else:
                    self.logger.error(f"Error processing pending tweet {tweet_id}: {e}")

    def run(self):
        """Main bot loop"""
        self.logger.info("Starting Twitter bot...")
        last_check_time = 0  # Initialize to 0 to check immediately
        
        while True:
            try:
                current_time = time.time()
                self.logger.info("Starting main loop iteration")
                
                # Process any pending tweets first
                if self.pending_tweets:
                    self.logger.info(f"Processing {len(self.pending_tweets)} pending tweets")
                    self.process_pending_tweets()
                else:
                    self.logger.info("No pending tweets to process")
                
                # Check for new mentions
                self.logger.info("Checking for new mentions")
                mentions = self.client.get_mentions(count=10)
                
                # Filter out already processed mentions
                new_mentions = []
                for mention in mentions:
                    if str(mention.id) not in self.processed_mentions:
                        new_mentions.append(mention)
                    else:
                        self.logger.info(f"Skipping already processed mention {mention.id}")
                
                self.logger.info(f"Found {len(mentions)} mentions, {len(new_mentions)} are new")
                
                # Process each new mention
                for mention in new_mentions:
                    self.process_mention(mention)
                
                # Update last check time
                last_check_time = current_time
                
                # Wait before next check
                self.logger.info("Waiting 60 seconds before next check")
                time.sleep(60)
                
            except Exception as e:
                self.logger.error(f"Error in main loop: {str(e)}")
                time.sleep(60)  # Wait a minute before retrying
