import easyocr
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from datetime import datetime
import os
from translation_service import TranslationService
import logging
from langdetect import detect
from dotenv import load_dotenv

def extract_and_translate_text(image_path, languages=['en']):
    """
    Extract text from an image using EasyOCR and translate it
    
    Args:
        image_path (str): Path to the image file
        languages (list): List of language codes for OCR
    
    Returns:
        list: List of dictionaries containing original and translated text
    """
    try:
        # Initialize the readers
        reader = easyocr.Reader(languages)
        translator = TranslationService()

        # Load environment variables from .env file
        load_dotenv()

        # Get the API key from the environment variable
        api_key = os.getenv("DETECT_API_KEY")

        # Initialize the translator with the API key
        translator = TranslationService(api_key)
        
        # Detect and recognize text
        results = reader.readtext(image_path)
        
        # Detect language of the text
        text = " ".join([result[1] for result in results])
        # detected_lang = detect(text)
        detected_lang = translator.detect_language(text)
        print(f"Detected language: {detected_lang}")

        # Format results with translation
        formatted_results = []
        for bbox, text, confidence in results:
            # Detect language of extracted text
            # detected_lang = 'fr' # translator.detect_language(text)
            # detected_lang = detect(text)
            
            # Only translate if language is detected and it's not English
            translated_text = None
            if detected_lang and detected_lang != 'en':
                translated_text = translator.translate_text(text, detected_lang)
            
            formatted_results.append({
                'original_text': text,
                'translated_text': translated_text,
                'source_language': detected_lang,
                'confidence': round(float(confidence), 3),
                'bbox': bbox
            })
            
        return formatted_results
    
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return []

def save_to_documents(results, image_path, output_dir="extracted_texts"):
    """
    Save extracted and translated text to files
    
    Args:
        results (list): List of dictionaries containing OCR and translation results
        image_path (str): Original image path (used for naming)
        output_dir (str): Directory to save output files
    """
    try:
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Generate base filename using timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        
        # Save original text
        original_path = os.path.join(output_dir, f"{base_name}_{timestamp}_original.txt")
        with open(original_path, 'w', encoding='utf-8') as txt_file:
            txt_file.write(f"OCR Results for: {image_path}\n")
            txt_file.write(f"Extraction Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            txt_file.write("-" * 50 + "\n\n")
            
            for i, result in enumerate(results, 1):
                txt_file.write(f"{i}. Original Text: {result['original_text']}\n")
                txt_file.write(f"   Language: {result['source_language']}\n")
                txt_file.write(f"   Confidence: {result['confidence']:.3f}\n\n")
        
        # Save translated text
        translated_path = os.path.join(output_dir, f"{base_name}_{timestamp}_translated.txt")
        with open(translated_path, 'w', encoding='utf-8') as txt_file:
            txt_file.write(f"Translation Results for: {image_path}\n")
            txt_file.write(f"Translation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            txt_file.write("-" * 50 + "\n\n")
            
            for i, result in enumerate(results, 1):
                txt_file.write(f"{i}. Original ({result['source_language']}): {result['original_text']}\n")
                if result['translated_text']:
                    txt_file.write(f"   English: {result['translated_text']}\n")
                else:
                    txt_file.write(f"   English: [No translation needed or available]\n")
                txt_file.write(f"   Confidence: {result['confidence']:.3f}\n\n")
        
        print(f"\nFiles saved successfully:")
        print(f"Original text: {original_path}")
        print(f"Translated text: {translated_path}")
        
        return original_path, translated_path
        
    except Exception as e:
        print(f"Error saving documents: {str(e)}")
        return None, None

def visualize_predictions(image_path, predictions):
    """
    Visualize the OCR predictions on the image
    """
    try:
        # Read image using PIL
        image = Image.open(image_path)
        
        # Create figure
        plt.figure(figsize=(10, 10))
        plt.imshow(image)
        
        for pred in predictions:
            bbox = np.array(pred['bbox'])
            text = pred['original_text']
            
            # Plot the bounding box
            plt.plot([bbox[0][0], bbox[1][0], bbox[2][0], bbox[3][0], bbox[0][0]],
                    [bbox[0][1], bbox[1][1], bbox[2][1], bbox[3][1], bbox[0][1]],
                    'r-', linewidth=2)
            
            # Add text annotation
            plt.text(bbox[0][0], bbox[0][1], 
                    f"{text} ({pred['confidence']:.2f})",
                    color='white', backgroundcolor='red',
                    fontsize=8)
        
        plt.axis('off')
        plt.show()
        
    except Exception as e:
        print(f"Error visualizing predictions: {str(e)}")

# Example usage
if __name__ == "__main__":
    # Replace with your image path
    image_path = "./images/test3.jpeg"
    
    # Extract and translate text
    results = extract_and_translate_text(image_path, languages=['en', 'fr', 'es']) # , 'ht'])  # Added common languages
    
    # Print results
    print("\nExtracted and Translated Text:")
    for result in results:
        print(f"Original Text: {result['original_text']}")
        print(f"Language: {result['source_language']}")
        if result['translated_text']:
            print(f"English Translation: {result['translated_text']}")
        print(f"Confidence: {result['confidence']}")
        print("---")
    
    # Save results to documents
    original_path, translated_path = save_to_documents(results, image_path)
    
    # Visualize results
    visualize_predictions(image_path, results)