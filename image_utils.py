"""Utility functions for image processing shared across sprite generation."""

from io import BytesIO
from PIL import Image
import pygame


def process_generated_image(image_bytes, target_size=(32, 32)):
    """
    Process raw image bytes from AI generation into a pygame-ready sprite.
    
    Args:
        image_bytes: Raw image data from DALL-E API
        target_size: Tuple of (width, height) to resize to
        
    Returns:
        PIL Image object ready for saving/conversion
        
    Processing steps:
    1. Open image from bytes
    2. Convert to RGBA for transparency support
    3. Resize to target size using nearest neighbor (pixel art style)
    4. Convert dark background pixels to transparent
    """
    # Load and convert image
    img = Image.open(BytesIO(image_bytes))
    img = img.convert("RGBA")
    
    # Resize to target size while maintaining pixel art style
    img = img.resize(target_size, Image.Resampling.NEAREST)
    
    # Convert dark background pixels to transparent
    data = img.getdata()
    new_data = []
    for item in data:
        # If pixel is very dark (RGB sum < 30), make it transparent
        if item[0] + item[1] + item[2] < 30:
            new_data.append((255, 255, 255, 0))  # Transparent
        else:
            new_data.append(item)
    
    img.putdata(new_data)
    return img


def save_and_load_sprite(img, cache_path):
    """
    Save processed image to cache and load it as a pygame sprite.
    
    Args:
        img: PIL Image object
        cache_path: Path to save the image
        
    Returns:
        pygame.Surface sprite object
    """
    img.save(cache_path, "PNG")
    return pygame.image.load(cache_path)