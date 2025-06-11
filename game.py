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
pygame.display.set_caption("Dungeon Crawler")
clock = pygame.time.Clock()

# Cache directories
os.makedirs('cache/sprites', exist_ok=True)
os.makedirs('cache/monsters', exist_ok=True)
os.makedirs('cache/items', exist_ok=True)

def generate_sprite(prompt, cache_path, game=None):
    """Generate and cache a sprite using DALL-E"""
    if os.path.exists(cache_path):
        return pygame.image.load(cache_path)
    
    if game:
        game.loading = True
        game.loading_message = "Generating sprite..."
        game._draw_loading_screen()
        pygame.event.pump()  # Process events to keep window responsive
    
    try:
        # Generate image using DALL-E
        # Request 1024x1024 but specify very simple pixel art style
        response = client.generate_image(
            prompt=f"{prompt}. Style: simple 8-bit pixel art, very low detail, blocky shapes, retro game sprite, minimal colors",
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
        
        sprite = pygame.image.load(cache_path)
        if game:
            game.loading = False
        return sprite
    except Exception as e:
        print(f"Error generating sprite: {str(e)}")
        if game:
            game.loading = False
        # Fallback to a default sprite if generation fails
        return pygame.Surface((32, 32))

def generate_monster(level, game=None):
    """Generate a monster with AI"""
    prompt = f"Create a fantasy monster sprite for level {level}"
    monster_path = f"cache/monsters/monster_level_{level}.png"
    stats_path = f"cache/monsters/monster_level_{level}_stats.txt"
    
    # Check if both sprite and stats are cached
    if os.path.exists(monster_path) and os.path.exists(stats_path):
        monster_sprite = pygame.image.load(monster_path)
        with open(stats_path, 'r') as f:
            monster_stats = f.read()
        return monster_sprite, monster_stats
    
    # Generate sprite
    monster_sprite = generate_sprite(prompt, monster_path, game)
    
    # Generate or load monster stats
    if os.path.exists(stats_path):
        with open(stats_path, 'r') as f:
            monster_stats = f.read()
    else:
        # Generate monster stats using OpenAI
        try:
            response = client.generate_chat_completion([
                {"role": "system", "content": "You are a dungeon monster generator."},
                {"role": "user", "content": f"Generate stats for a level {level} monster."}
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
    
    return monster_sprite, monster_stats

def generate_item(game=None):
    """Generate a random item with AI"""
    item_type = random.choice(['weapon', 'armor', 'potion'])
    prompt = f"Create a {item_type} sprite"
    item_path = f"cache/items/item_{item_type}.png"
    sprite = generate_sprite(prompt, item_path, game)
    return sprite, item_type

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
        
        # Player sprite will be generated in Game.__init__ with loading screen
        self.sprite = None

class Game:
    def __init__(self):
        self.running = True
        self.level = 1
        self.monsters = []
        self.loot_items = []
        self.message = ""
        self.message_timer = 0
        self.loading = False
        self.loading_message = ""
        
        # Initialize player without sprite first
        self.player = Player()
        
        # Show initial loading screen
        self.loading = True
        self.loading_message = "Generating hero sprite..."
        self._draw_loading_screen()
        pygame.event.pump()  # Process events to keep window responsive
        
        # Generate player sprite
        self.player.sprite = generate_sprite(
            "Create a fantasy hero sprite",
            "cache/sprites/player.png",
            self
        )
        
        self.generate_level()

    def generate_level(self):
        """Generate a new level with AI-generated monsters"""
        self.monsters = []
        for i in range(self.level * MONSTER_COUNT):
            self.loading = True
            self.loading_message = f"Generating monsters... ({i+1}/{self.level * MONSTER_COUNT})"
            self._draw_loading_screen()
            pygame.event.pump()  # Process events to keep window responsive
            
            monster_sprite, monster_stats = generate_monster(self.level, self)
            x = random.randint(0, WINDOW_WIDTH - TILE_SIZE)
            y = random.randint(0, WINDOW_HEIGHT - TILE_SIZE)
            monster = Monster(self.level, monster_stats)
            monster_entity = MonsterEntity(monster, monster_sprite, x, y)
            self.monsters.append(monster_entity)
        
        self.loading = False

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

        # Update monsters
        self.update_monsters()
        
        # Handle combat
        self.handle_combat()
        
        # Handle loot pickup
        self.handle_loot_pickup()
        
        # Update message timer
        if self.message_timer > 0:
            self.message_timer -= 1

    def is_within_range(self, x1, y1, x2, y2, max_range):
        """Check if two positions are within a given range"""
        dx = abs(x1 - x2)
        dy = abs(y1 - y2)
        return dx <= max_range and dy <= max_range

    def update_monsters(self):
        """Update monster positions and behavior"""
        for monster_entity in self.monsters:
            if not monster_entity.monster.is_alive:
                continue
                
            # Move towards player
            dx = self.player.x - monster_entity.x
            dy = self.player.y - monster_entity.y
            
            # Normalize movement (simple approach)
            if dx != 0:
                monster_entity.x += 1 if dx > 0 else -1
            if dy != 0:
                monster_entity.y += 1 if dy > 0 else -1
                
            # Keep monsters within bounds
            monster_entity.x = max(0, min(WINDOW_WIDTH - TILE_SIZE, monster_entity.x))
            monster_entity.y = max(0, min(WINDOW_HEIGHT - TILE_SIZE, monster_entity.y))

    def handle_combat(self):
        """Handle player-monster interactions"""
        for monster_entity in self.monsters[:]:
            if not monster_entity.monster.is_alive:
                continue
                
            if self._is_monster_in_attack_range(monster_entity):
                self._attack_monster(monster_entity)
                
                if not monster_entity.monster.is_alive:
                    self._remove_defeated_monster(monster_entity)
            
            # Check if monster can attack player
            elif self._is_monster_in_attack_range(monster_entity):
                self._monster_attack_player(monster_entity)

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

    def _monster_attack_player(self, monster_entity):
        """Monster attacks the player"""
        damage = monster_entity.monster.damage
        self.player.health -= damage
        self.message = f"Monster hits for {damage} damage!"
        self.message_timer = 120
        print(f"Player takes {damage} damage! Health: {self.player.health}")
        
        if self.player.health <= 0:
            print("Game Over!")
            self.running = False

    def generate_loot(self):
        """Generate random loot after defeating a monster"""
        if random.random() < LOOT_DROP_CHANCE:
            item_sprite, item_type = generate_item(self)
            item_x = random.randint(0, WINDOW_WIDTH - TILE_SIZE)
            item_y = random.randint(0, WINDOW_HEIGHT - TILE_SIZE)
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
                
                # Show pickup message
                self.message = f"Picked up {loot_item.item_type}!"
                self.message_timer = 120  # 2 seconds at 60 FPS
                print(f"Picked up {loot_item.item_type}!")

    def draw(self):
        if self.loading:
            self._draw_loading_screen()
        else:
            screen.fill((32, 32, 48))  # Dark blue-gray background instead of pure black
            self._draw_player()
            self._draw_monsters()
            self._draw_loot()
            self._draw_ui()
            pygame.display.flip()

    def _draw_player(self):
        """Draw the player sprite and health bar"""
        if self.player.sprite:  # Only draw if sprite exists
            screen.blit(self.player.sprite, (self.player.x, self.player.y))
            self._draw_player_health_bar()

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

    def _draw_player_health_bar(self):
        """Draw health bar for the player"""
        if self.player.sprite:  # Only draw if sprite exists
            x, y = self.player.x, self.player.y
            health_ratio = self.player.health / PLAYER_BASE_HEALTH
            
            # Draw background (red)
            pygame.draw.rect(screen, (255, 0, 0), 
                           (x, y - 10, HEALTH_BAR_WIDTH, HEALTH_BAR_HEIGHT))
            # Draw health (green)
            pygame.draw.rect(screen, (0, 255, 0), 
                           (x, y - 10, 
                            HEALTH_BAR_WIDTH * health_ratio, 
                            HEALTH_BAR_HEIGHT))

    def _draw_loot(self):
        """Draw all loot items"""
        for loot_item in self.loot_items:
            screen.blit(loot_item.sprite, (loot_item.x, loot_item.y))

    def _draw_ui(self):
        """Draw user interface elements"""
        font = pygame.font.Font(None, 36)
        small_font = pygame.font.Font(None, 24)
        
        # Level display
        level_text = font.render(f"Level: {self.level}", True, (255, 255, 255))
        screen.blit(level_text, (10, 10))
        
        # Inventory count
        inventory_text = small_font.render(f"Inventory: {len(self.player.inventory)} items", True, (200, 200, 200))
        screen.blit(inventory_text, (10, 50))
        
        # Player stats
        health_text = small_font.render(f"Health: {self.player.health}", True, (255, 100, 100))
        screen.blit(health_text, (10, 75))
        
        attack_text = small_font.render(f"Attack: {self.player.attack_power}", True, (100, 255, 100))
        screen.blit(attack_text, (10, 100))
        
        # Message display
        if self.message_timer > 0:
            message_text = font.render(self.message, True, (255, 255, 100))
            screen.blit(message_text, (WINDOW_WIDTH // 2 - 100, WINDOW_HEIGHT // 2 - 50))

    def _draw_loading_screen(self):
        """Draw loading screen when generating sprites"""
        screen.fill((32, 32, 48))  # Same background color
        font = pygame.font.Font(None, 48)
        loading_text = font.render(self.loading_message, True, (255, 255, 255))
        text_rect = loading_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
        screen.blit(loading_text, text_rect)
        
        # Draw a simple animated indicator
        dots = "." * ((pygame.time.get_ticks() // 500) % 4)
        dots_text = font.render(dots, True, (255, 255, 255))
        dots_rect = dots_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 50))
        screen.blit(dots_text, dots_rect)
        
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
