import pygame
import random
import os
from dotenv import load_dotenv
import openai
import requests
from io import BytesIO
from PIL import Image

# Load environment variables
load_dotenv()

# Initialize OpenAI
class OpenAIClient:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.base_url = "https://api.openai.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def generate_image(self, prompt, size="1024x1024", quality="standard"):
        response = requests.post(
            f"{self.base_url}/images/generations",
            headers=self.headers,
            json={
                "model": "dall-e-3",
                "prompt": prompt,
                "n": 1,
                "size": size,
                "quality": quality,
                "response_format": "url"
            }
        )
        response.raise_for_status()
        return response.json()

    def generate_chat_completion(self, messages):
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

client = OpenAIClient()

# Game constants
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
TILE_SIZE = 32
LEVELS = 5

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
clock = pygame.time.Clock()

# Cache directories
os.makedirs('cache/sprites', exist_ok=True)
os.makedirs('cache/monsters', exist_ok=True)
os.makedirs('cache/items', exist_ok=True)

def generate_sprite(prompt, cache_path):
    """Generate and cache a sprite using DALL-E"""
    if os.path.exists(cache_path):
        return pygame.image.load(cache_path)
    
    try:
        # Generate image using DALL-E
        response = client.generate_image(prompt)
        image_url = response['data'][0]['url']
        
        # Download and save image
        img_response = requests.get(image_url)
        img = Image.open(BytesIO(img_response.content))
        img = img.resize((32, 32), Image.Resampling.LANCZOS)
        img.save(cache_path)
        
        return pygame.image.load(cache_path)
    except Exception as e:
        print(f"Error generating sprite: {str(e)}")
        # Fallback to a default sprite if generation fails
        return pygame.Surface((32, 32))

def generate_monster(level):
    """Generate a monster with AI"""
    prompt = f"Create a fantasy monster sprite for level {level}. Style: pixel art, 32x32 pixels"
    monster_path = f"cache/monsters/monster_level_{level}.png"
    monster_sprite = generate_sprite(prompt, monster_path)
    
    # Generate monster stats using OpenAI
    try:
        response = client.generate_chat_completion([
            {"role": "system", "content": "You are a dungeon monster generator."},
            {"role": "user", "content": f"Generate stats for a level {level} monster."}
        ])
        monster_stats = response['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error generating monster stats: {str(e)}")
        monster_stats = f"Level {level} monster"
    
    return monster_sprite, monster_stats

def generate_item():
    """Generate a random item with AI"""
    item_type = random.choice(['weapon', 'armor', 'potion'])
    prompt = f"Create a {item_type} sprite. Style: pixel art, 32x32 pixels"
    item_path = f"cache/items/item_{item_type}.png"
    return generate_sprite(prompt, item_path)

class Player:
    def __init__(self):
        self.x = WINDOW_WIDTH // 2
        self.y = WINDOW_HEIGHT // 2
        self.health = 100
        self.level = 1
        self.inventory = []
        
        # Generate player sprite
        self.sprite = generate_sprite(
            "Create a fantasy hero sprite. Style: pixel art, 32x32 pixels",
            "cache/sprites/player.png"
        )

class Game:
    def __init__(self):
        self.player = Player()
        self.running = True
        self.level = 1
        self.monsters = []
        self.generate_level()

    def generate_level(self):
        """Generate a new level with AI-generated monsters"""
        self.monsters = []
        for _ in range(self.level * 2):
            monster_sprite, monster_stats = generate_monster(self.level)
            x = random.randint(0, WINDOW_WIDTH - TILE_SIZE)
            y = random.randint(0, WINDOW_HEIGHT - TILE_SIZE)
            self.monsters.append({
                'sprite': monster_sprite,
                'stats': monster_stats,
                'x': x,
                'y': y
            })

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

    def update(self):
        keys = pygame.key.get_pressed()
        speed = 5
        
        if keys[pygame.K_LEFT]:
            self.player.x -= speed
        if keys[pygame.K_RIGHT]:
            self.player.x += speed
        if keys[pygame.K_UP]:
            self.player.y -= speed
        if keys[pygame.K_DOWN]:
            self.player.y += speed

        # Keep player within bounds
        self.player.x = max(0, min(WINDOW_WIDTH - TILE_SIZE, self.player.x))
        self.player.y = max(0, min(WINDOW_HEIGHT - TILE_SIZE, self.player.y))

    def draw(self):
        screen.fill((0, 0, 0))
        
        # Draw player
        screen.blit(self.player.sprite, (self.player.x, self.player.y))
        
        # Draw monsters
        for monster in self.monsters:
            screen.blit(monster['sprite'], (monster['x'], monster['y']))
        
        # Draw UI
        font = pygame.font.Font(None, 36)
        level_text = font.render(f"Level: {self.level}", True, (255, 255, 255))
        screen.blit(level_text, (10, 10))
        
        pygame.display.flip()

def main():
    game = Game()
    
    while game.running:
        game.handle_events()
        game.update()
        game.draw()
        clock.tick(60)
    
    pygame.quit()

if __name__ == "__main__":
    main()
