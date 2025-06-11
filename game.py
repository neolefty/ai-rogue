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

# Game balance constants
PLAYER_BASE_HEALTH = 100
PLAYER_BASE_ATTACK = 10
PLAYER_SPEED = 5
MONSTER_HEALTH_MULTIPLIER = 100
MONSTER_DAMAGE_MULTIPLIER = 10
HEALTH_BAR_WIDTH = 32
HEALTH_BAR_HEIGHT = 4
LOOT_DROP_CHANCE = 0.3

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

class GameEntity:
    """Base class for game entities with position and sprite"""
    def __init__(self, sprite, x, y):
        self.sprite = sprite
        self.x = x
        self.y = y

class MonsterEntity(GameEntity):
    """Monster entity combining Monster logic with position/sprite"""
    def __init__(self, monster, sprite, x, y):
        super().__init__(sprite, x, y)
        self.monster = monster

class LootItem(GameEntity):
    """Loot item entity"""
    def __init__(self, item_type, sprite, x, y):
        super().__init__(sprite, x, y)
        self.item_type = item_type

class Monster:
    def __init__(self, level, stats):
        self.level = level
        self.health = MONSTER_HEALTH_MULTIPLIER * level
        self.max_health = self.health  # Track max health for health bar
        self.damage = MONSTER_DAMAGE_MULTIPLIER * level
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
                    # Ensure health is at least base * level
                    self.health = max(MONSTER_HEALTH_MULTIPLIER * self.level, health)
                    self.max_health = self.health  # Update max health
                elif 'Damage' in line:
                    self.damage = int(line.split(':')[1].strip())
        except:
            # Fallback values if parsing fails
            self.health = MONSTER_HEALTH_MULTIPLIER * self.level
            self.max_health = self.health
            self.damage = MONSTER_DAMAGE_MULTIPLIER * self.level
    
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
        self.health = PLAYER_BASE_HEALTH
        self.level = 1
        self.inventory = []
        self.attack_power = PLAYER_BASE_ATTACK
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
            monster_entity = MonsterEntity(monster, monster_sprite, x, y)
            self.monsters.append(monster_entity)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

    def update(self):
        keys = pygame.key.get_pressed()
        speed = PLAYER_SPEED
        
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

    def is_within_range(self, x1, y1, x2, y2, max_range):
        """Check if two positions are within a given range"""
        dx = abs(x1 - x2)
        dy = abs(y1 - y2)
        return dx <= max_range and dy <= max_range

    def handle_combat(self):
        """Handle player-monster interactions"""
        for monster_entity in self.monsters[:]:
            if not monster_entity.monster.is_alive:
                continue
                
            if self._is_monster_in_attack_range(monster_entity):
                self._attack_monster(monster_entity)
                
                if not monster_entity.monster.is_alive:
                    self._remove_defeated_monster(monster_entity)

    def _is_monster_in_attack_range(self, monster_entity):
        """Check if monster is within player's attack range"""
        return self.is_within_range(self.player.x, self.player.y, 
                                  monster_entity.x, monster_entity.y,
                                  self.player.attack_range)

    def _attack_monster(self, monster_entity):
        """Attack a monster and deal damage"""
        monster_entity.monster.take_damage(self.player.attack_power)
        print(f"Hit monster! Remaining health: {monster_entity.monster.health}")

    def _remove_defeated_monster(self, monster_entity):
        """Remove defeated monster and generate loot"""
        self.monsters.remove(monster_entity)
        print("Monster defeated!")
        self.generate_loot()

    def generate_loot(self):
        """Generate random loot after defeating a monster"""
        if random.random() < LOOT_DROP_CHANCE:
            item_sprite = generate_item()
            item_x = random.randint(0, WINDOW_WIDTH - TILE_SIZE)
            item_y = random.randint(0, WINDOW_HEIGHT - TILE_SIZE)
            item_type = random.choice(['weapon', 'armor', 'potion'])
            loot_item = LootItem(item_type, item_sprite, item_x, item_y)
            self.loot_items.append(loot_item)

    def handle_loot_pickup(self):
        """Handle player picking up loot items"""
        for loot_item in self.loot_items[:]:  # Use slice copy to avoid modification during iteration
            # Check if player is close enough to pick up item
            if self.is_within_range(self.player.x, self.player.y,
                                  loot_item.x, loot_item.y, TILE_SIZE):
                # Add to inventory and remove from ground
                self.player.inventory.append(loot_item)
                self.loot_items.remove(loot_item)
                print("Picked up item!")

    def draw(self):
        screen.fill((0, 0, 0))
        self._draw_player()
        self._draw_monsters()
        self._draw_loot()
        self._draw_ui()
        pygame.display.flip()

    def _draw_player(self):
        """Draw the player sprite"""
        screen.blit(self.player.sprite, (self.player.x, self.player.y))

    def _draw_monsters(self):
        """Draw all monsters and their health bars"""
        for monster_entity in self.monsters:
            screen.blit(monster_entity.sprite, (monster_entity.x, monster_entity.y))
            
            # Draw health bars for living monsters
            if monster_entity.monster.is_alive:
                self._draw_health_bar(monster_entity)

    def _draw_health_bar(self, monster_entity):
        """Draw health bar for a monster"""
        monster = monster_entity.monster
        x, y = monster_entity.x, monster_entity.y
        
        # Draw background (red)
        pygame.draw.rect(screen, (255, 0, 0), 
                       (x, y - 10, HEALTH_BAR_WIDTH, HEALTH_BAR_HEIGHT))
        # Draw health (green)
        pygame.draw.rect(screen, (0, 255, 0), 
                       (x, y - 10, 
                        HEALTH_BAR_WIDTH * monster.get_health_ratio(), 
                        HEALTH_BAR_HEIGHT))

    def _draw_loot(self):
        """Draw all loot items"""
        for loot_item in self.loot_items:
            screen.blit(loot_item.sprite, (loot_item.x, loot_item.y))

    def _draw_ui(self):
        """Draw user interface elements"""
        font = pygame.font.Font(None, 36)
        level_text = font.render(f"Level: {self.level}", True, (255, 255, 255))
        screen.blit(level_text, (10, 10))

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
