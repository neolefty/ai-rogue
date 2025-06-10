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

    def generate_image(self, prompt, size="256x256", quality="standard"):
        try:
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
        except requests.exceptions.RequestException as e:
            print(f"API Error: {str(e)}")
            print(f"Status Code: {response.status_code}")
            print(f"Response Text: {response.text}")
            raise

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
MONSTER_COUNT = 5

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
        # Request 1024x1024 but specify 16x16 pixel art style
        response = client.generate_image(
            prompt=f"{prompt}. Style: pixel art, 16x16 pixels, 8-bit colors",
            size="1024x1024",
            quality="standard"
        )
        image_url = response['data'][0]['url']
        
        # Download and save image
        img_response = requests.get(image_url)
        img = Image.open(BytesIO(img_response.content))
        
        # Resize to 32x32 while maintaining pixel art style
        img = img.resize((32, 32), Image.Resampling.NEAREST)
        
        # Convert to 8-bit palette to enhance pixel art style
        img = img.quantize(colors=256)
        
        img.save(cache_path)
        
        return pygame.image.load(cache_path)
    except Exception as e:
        print(f"Error generating sprite: {str(e)}")
        # Fallback to a default sprite if generation fails
        return pygame.Surface((32, 32))

def generate_monster(level):
    """Generate a monster with AI"""
    prompt = f"Create a fantasy monster sprite for level {level}"
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
    prompt = f"Create a {item_type} sprite"
    item_path = f"cache/items/item_{item_type}.png"
    return generate_sprite(prompt, item_path)

class Monster:
    def __init__(self, level, stats):
        self.level = level
        self.health = 100 * level  # Default health is 100 * level
        self.max_health = self.health  # Track max health for health bar
        self.damage = 10 * level
        self.stats = stats
        self.is_alive = True
        
        # Parse stats from AI-generated string
        self.parse_stats(stats)
    
    def parse_stats(self, stats):
        """Parse monster stats from AI-generated string"""
        try:
            # Split stats into lines and parse them
            lines = stats.split('\n')
            for line in lines:
                if 'Health' in line:
                    health = int(line.split(':')[1].strip())
                    # Ensure health is at least 100 * level
                    self.health = max(100 * self.level, health)
                    self.max_health = self.health  # Update max health
                elif 'Damage' in line:
                    self.damage = int(line.split(':')[1].strip())
        except:
            # Fallback values if parsing fails
            self.health = 100 * self.level
            self.max_health = self.health
            self.damage = 10 * self.level
    
    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.is_alive = False
    
    def get_health_ratio(self):
        """Get current health as a ratio of max health"""
        return self.health / self.max_health

class Player:
    def __init__(self):
        self.x = WINDOW_WIDTH // 2
        self.y = WINDOW_HEIGHT // 2
        self.health = 100
        self.level = 1
        self.inventory = []
        self.attack_power = 10
        self.attack_range = 32  # Same as TILE_SIZE
        
        # Generate player sprite
        self.sprite = generate_sprite(
            "Create a fantasy hero sprite",
            "cache/sprites/player.png"
        )

class Game:
    def __init__(self):
        self.player = Player()
        self.running = True
        self.level = 1
        self.monsters = []
        self.loot_items = []
        self.generate_level()

    def generate_level(self):
        """Generate a new level with AI-generated monsters"""
        self.monsters = []
        for _ in range(self.level * MONSTER_COUNT):
            monster_sprite, monster_stats = generate_monster(self.level)
            x = random.randint(0, WINDOW_WIDTH - TILE_SIZE)
            y = random.randint(0, WINDOW_HEIGHT - TILE_SIZE)
            monster = Monster(self.level, monster_stats)
            self.monsters.append({
                'monster': monster,
                'sprite': monster_sprite,
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

        # Handle combat
        self.handle_combat()
        
        # Handle loot pickup
        self.handle_loot_pickup()

    def handle_combat(self):
        """Handle player-monster interactions"""
        # Check for monsters in attack range
        for monster_data in self.monsters:
            monster = monster_data['monster']
            if not monster.is_alive:
                continue
                
            # Check if monster is within attack range
            dx = abs(self.player.x - monster_data['x'])
            dy = abs(self.player.y - monster_data['y'])
            if dx <= self.player.attack_range and dy <= self.player.attack_range:
                # Monster takes damage
                monster.take_damage(self.player.attack_power)
                print(f"Hit monster! Remaining health: {monster.health}")
                
                # If monster dies, remove it
                if not monster.is_alive:
                    self.monsters.remove(monster_data)
                    print("Monster defeated!")
                    
                    # Generate loot
                    self.generate_loot()

    def generate_loot(self):
        """Generate random loot after defeating a monster"""
        if random.random() < 0.3:  # 30% chance to drop loot
            item_sprite = generate_item()
            item_x = random.randint(0, WINDOW_WIDTH - TILE_SIZE)
            item_y = random.randint(0, WINDOW_HEIGHT - TILE_SIZE)
            self.loot_items.append({
                'sprite': item_sprite,
                'x': item_x,
                'y': item_y
            })

    def handle_loot_pickup(self):
        """Handle player picking up loot items"""
        for loot_item in self.loot_items[:]:  # Use slice copy to avoid modification during iteration
            # Check if player is close enough to pick up item
            dx = abs(self.player.x - loot_item['x'])
            dy = abs(self.player.y - loot_item['y'])
            if dx <= TILE_SIZE and dy <= TILE_SIZE:
                # Add to inventory and remove from ground
                self.player.inventory.append(loot_item)
                self.loot_items.remove(loot_item)
                print("Picked up item!")

    def draw(self):
        screen.fill((0, 0, 0))
        
        # Draw player
        screen.blit(self.player.sprite, (self.player.x, self.player.y))
        
        # Draw monsters
        for monster_data in self.monsters:
            screen.blit(monster_data['sprite'], (monster_data['x'], monster_data['y']))
            
            # Draw health bars for living monsters
            if not monster_data['monster'].is_alive:
                continue
                
            monster = monster_data['monster']
            health_bar_width = 32  # Same as sprite width
            health_bar_height = 4
            health_ratio = monster.health / (100 * monster.level)
            
            # Draw background (red)
            pygame.draw.rect(screen, (255, 0, 0), 
                           (monster_data['x'], monster_data['y'] - 10, 
                            health_bar_width, health_bar_height))
            # Draw health (green)
            pygame.draw.rect(screen, (0, 255, 0), 
                           (monster_data['x'], monster_data['y'] - 10, 
                            health_bar_width * monster.get_health_ratio(), health_bar_height))
        
        # Draw loot items
        for loot_item in self.loot_items:
            screen.blit(loot_item['sprite'], (loot_item['x'], loot_item['y']))
        
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
