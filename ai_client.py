"""OpenAI integration for sprite and stats generation."""

import base64
import os
import random
import pygame
import requests
from io import BytesIO
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv

from constants import *
from prompts import (
    PLAYER_SPRITE_PROMPT,
    MONSTER_SPRITE_PROMPT,
    ITEM_SPRITE_PROMPT,
    STAIRWAY_SPRITE_PROMPT,
    SPRITE_STYLE,
    MONSTER_STATS_SYSTEM_PROMPT,
    MONSTER_STATS_USER_PROMPT,
)

# Load environment variables
load_dotenv()


class OpenAIClient:
    """Client for OpenAI API interactions."""
    
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.base_url = "https://api.openai.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.client = OpenAI()

    def generate_image(self, prompt):
        """Generate an image using DALL-E."""
        try:
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                response_format="b64_json"
            )
            image_base64 = response.data[0].b64_json
            image_bytes = base64.b64decode(image_base64)
            return image_bytes

        except requests.exceptions.RequestException as e:
            print(f"API Error: {str(e)}")
            raise

    def generate_chat_completion(self, messages):
        """Generate a chat completion using GPT."""
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self.headers,
            json={
                "model": "gpt-3.5-turbo",
                "messages": messages
            }
        )
        response.raise_for_status()
        return response.json()


class SpriteGenerator:
    """Handles sprite generation and caching."""
    
    def __init__(self):
        self.client = OpenAIClient()
        # Ensure cache directories exist
        os.makedirs(CACHE_SPRITES_DIR, exist_ok=True)
        os.makedirs(CACHE_MONSTERS_DIR, exist_ok=True)
        os.makedirs(CACHE_ITEMS_DIR, exist_ok=True)
    
    def generate_sprite(self, prompt, cache_path, game=None):
        """Generate and cache a sprite using DALL-E."""
        if os.path.exists(cache_path):
            return pygame.image.load(cache_path)
        
        # Loading screens removed - generation now uses placeholders
        
        try:
            # Generate image using DALL-E
            image_bytes = self.client.generate_image(f"{prompt}. {SPRITE_STYLE}")
            img = Image.open(BytesIO(image_bytes))

            # Convert to RGBA to preserve transparency
            img = img.convert("RGBA")
            
            # Resize to 32x32 while maintaining pixel art style
            img = img.resize((32, 32), Image.Resampling.NEAREST)
            
            # Convert dark background pixels to transparent
            data = img.getdata()
            new_data = []
            for item in data:
                # If pixel is very dark (close to black), make it transparent
                if item[0] + item[1] + item[2] < 30:
                    new_data.append((255, 255, 255, 0))  # Transparent
                else:
                    new_data.append(item)
            
            img.putdata(new_data)
            img.save(cache_path, "PNG")
            
            sprite = pygame.image.load(cache_path)
            return sprite
            
        except Exception as e:
            print(f"Error generating sprite: {str(e)}")
            # Fallback to a default sprite if generation fails
            return pygame.Surface((32, 32))
    
    def generate_player_sprite(self, game=None):
        """Generate the player sprite."""
        return self.generate_sprite(
            PLAYER_SPRITE_PROMPT,
            f"{CACHE_SPRITES_DIR}/player.png",
            game
        )
    
    def generate_monster_sprite_and_stats(self, level, game=None):
        """Generate a monster sprite and stats."""
        prompt = MONSTER_SPRITE_PROMPT.format(level=level)
        monster_path = f"{CACHE_MONSTERS_DIR}/monster_level_{level}.png"
        stats_path = f"{CACHE_MONSTERS_DIR}/monster_level_{level}_stats.txt"
        
        # Check if both sprite and stats are cached
        if os.path.exists(monster_path) and os.path.exists(stats_path):
            monster_sprite = pygame.image.load(monster_path)
            with open(stats_path, 'r') as f:
                monster_stats = f.read()
            return monster_sprite, monster_stats
        
        # Generate sprite
        monster_sprite = self.generate_sprite(prompt, monster_path, game)
        
        # Generate or load monster stats
        if os.path.exists(stats_path):
            with open(stats_path, 'r') as f:
                monster_stats = f.read()
        else:
            monster_stats = self._generate_monster_stats(level, stats_path)
        
        return monster_sprite, monster_stats
    
    def generate_item_sprite(self, game=None):
        """Generate a random item sprite."""
        item_type = random.choice(['weapon', 'armor', 'potion'])
        prompt = ITEM_SPRITE_PROMPT.format(item_type=item_type)
        item_path = f"{CACHE_ITEMS_DIR}/item_{item_type}.png"
        sprite = self.generate_sprite(prompt, item_path, game)
        return sprite, item_type
    
    def generate_stairway_sprite(self, game=None):
        """Generate the stairway sprite."""
        return self.generate_sprite(
            STAIRWAY_SPRITE_PROMPT,
            f"{CACHE_SPRITES_DIR}/stairway.png",
            game
        )
    
    def _generate_monster_stats(self, level, stats_path):
        """Generate monster stats using OpenAI."""
        try:
            response = self.client.generate_chat_completion([
                {"role": "system", "content": MONSTER_STATS_SYSTEM_PROMPT},
                {"role": "user", "content": MONSTER_STATS_USER_PROMPT.format(level=level)}
            ])
            monster_stats = response['choices'][0]['message']['content']
            
            # Cache the stats
            with open(stats_path, 'w') as f:
                f.write(monster_stats)
                
        except Exception as e:
            print(f"Error generating monster stats: {str(e)}")
            monster_stats = f"Level {level} monster"
            
            # Cache the fallback stats
            with open(stats_path, 'w') as f:
                f.write(monster_stats)
        
        return monster_stats