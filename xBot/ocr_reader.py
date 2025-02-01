import easyocr
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

def extract_text_from_image(image_path, languages=['en']):
    """
    Extract text from an image using EasyOCR
    
    Args:
        image_path (str): Path to the image file
        languages (list): List of language codes (default: ['en'] for English)
    
    Returns:
        list: List of dictionaries containing text, confidence, and bounding box coordinates
    """
    try:
        # Initialize the reader
        reader = easyocr.Reader(languages)
        
        # Detect and recognize text
        results = reader.readtext(image_path)
        
        # Format results
        formatted_results = []
        for bbox, text, confidence in results:
            formatted_results.append({
                'text': text,
                'confidence': round(float(confidence), 3),
                'bbox': bbox
            })
            
        return formatted_results
    
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return []

def visualize_predictions(image_path, predictions):
    """
    Visualize the OCR predictions on the image
    
    Args:
        image_path (str): Path to the image file
        predictions (list): List of prediction dictionaries
    """
    try:
        # Read image using PIL
        image = Image.open(image_path)
        
        # Create figure
        plt.figure(figsize=(10, 10))
        plt.imshow(image)
        
        for pred in predictions:
            bbox = np.array(pred['bbox'])
            text = pred['text']
            
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
    image_path = "./images/test1.jpeg"
    
    # Extract text
    results = extract_text_from_image(image_path)
    
    # Print results
    print("\nExtracted Text:")
    for result in results:
        print(f"Text: {result['text']}")
        print(f"Confidence: {result['confidence']}")
        print("---")
    
    # Visualize results
    visualize_predictions(image_path, results)