import pygame
import random
import os
from dotenv import load_dotenv
import openai
import requests
from io import BytesIO
from PIL import Image

# Game constants
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
TILE_SIZE = 32
INITIAL_MONSTER_COUNT = 3
MONSTER_INCREMENT = 2
MAX_MONSTER_COUNT = 50

# Game balance constants
PLAYER_BASE_HEALTH = 100
PLAYER_BASE_ATTACK = 10
PLAYER_SPEED = 5
MONSTER_HEALTH_MULTIPLIER = 100
MONSTER_DAMAGE_MULTIPLIER = 10
HEALTH_BAR_WIDTH = 32
HEALTH_BAR_HEIGHT = 4
LOOT_DROP_CHANCE = 0.3

# Combat timing constants
PLAYER_ATTACK_COOLDOWN = 90  # 1.5 seconds at 60 FPS
MONSTER_ATTACK_COOLDOWN = 180  # 3 seconds at 60 FPS

# Monster AI constants
MONSTER_FOLLOW_DISTANCE = 150  # Pixels - monsters closer than this follow player
MONSTER_WANDER_SPEED = 0.5  # Slower movement for wandering monsters
MONSTER_DIRECTION_CHANGE_CHANCE = 0.02  # 2% chance per frame to change direction
MONSTER_ATTACK_RANGE = TILE_SIZE  # Monsters need to be adjacent to attack (melee only)

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
            prompt=f"{prompt}. Style: extremely simple pixel art sprite, light solid colors only, no gradients, no details, no captions, no frame or added scenery; 16x16 retro game style, minimal shapes, black background",
            size="1024x1024", 
            quality="standard"
        )
        image_url = response['data'][0]['url']
        
        # Download and save image
        img_response = requests.get(image_url)
        img = Image.open(BytesIO(img_response.content))
        
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

def generate_stairway(game=None):
    """Generate a stairway sprite"""
    prompt = "Create a stone stairway going down sprite"
    stairway_path = "cache/sprites/stairway.png"
    sprite = generate_sprite(prompt, stairway_path, game)
    return sprite

class GameEntity:
    """Base class for game entities with position and sprite"""
    def __init__(self, sprite, x, y):
        self.sprite = sprite
        self.x = x
        self.y = y

class MonsterEntity(GameEntity):
    """Monster entity combining Monster logic with position/sprite"""
    def __init__(self, monster, sprite, x, y, is_miniboss=False):
        super().__init__(sprite, x, y)
        self.monster = monster
        self.is_miniboss = is_miniboss

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
        self.last_attack_time = 0  # Track when monster last attacked
        
        # AI behavior variables
        self.wander_direction_x = random.choice([-1, 0, 1])
        self.wander_direction_y = random.choice([-1, 0, 1])
        self.direction_change_timer = 0
        
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
        self.attack_range = TILE_SIZE * 2.5  # 2.5 tiles range for hit-and-run tactics
        self.last_attack_time = 0  # Track when player last attacked
        
        # Player sprite will be generated in Game.__init__ with loading screen
        self.sprite = None

    def get_max_health(self):
        """Calculate player's current max health based on armor"""
        armor_count = len([item for item in self.inventory if item.item_type == 'armor'])
        return PLAYER_BASE_HEALTH + (armor_count * 25)

class Game:
    def __init__(self):
        self.running = True
        self.level = 1
        self.monsters = []
        self.loot_items = []
        self.stairway = None
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
        """Generate a new level with AI-generated monsters of mixed levels"""
        self.monsters = []
        total_monsters = min(
            INITIAL_MONSTER_COUNT + (self.level - 1) * MONSTER_INCREMENT,
            MAX_MONSTER_COUNT
        )
        
        # Create a mix of monster levels for variety and manageable difficulty
        monster_levels = self._generate_monster_level_mix(total_monsters)
        
        for i, monster_level in enumerate(monster_levels):
            self.loading = True
            self.loading_message = f"Generating monsters... ({i+1}/{total_monsters})"
            self._draw_loading_screen()
            pygame.event.pump()  # Process events to keep window responsive
            
            monster_sprite, monster_stats = generate_monster(monster_level, self)
            x, y = self._find_safe_monster_spawn_position()
            monster = Monster(monster_level, monster_stats)

            is_miniboss = monster_level >= self.level + 2
            if is_miniboss:
                scaled_size = int(TILE_SIZE * 1.5)
                monster_sprite = pygame.transform.scale(monster_sprite, (scaled_size, scaled_size))

            monster_entity = MonsterEntity(monster, monster_sprite, x, y, is_miniboss=is_miniboss)
            self.monsters.append(monster_entity)
        
        self.loading = False

    def _generate_monster_level_mix(self, total_monsters):
        """Generate a mix of monster levels for the current dungeon level"""
        monster_levels = []
        
        # Higher levels: Mix of current level and previous levels
        # 5% higher level, 35% current level, 15% previous level, 45% older levels
        higher_level_count = max(1, int(total_monsters * 0.05))
        current_level_count = max(1, int(total_monsters * 0.35))
        previous_level_count = max(0, int(total_monsters * 0.15))
        older_levels_count = total_monsters - current_level_count - previous_level_count - higher_level_count

        # Add higher level monsters (minibosses)
        for _ in range(higher_level_count):
            # level 1: miniboss is level 3
            # level 10: miniboss is level 12-22
            # level 20: miniboss is level 22-62
            # level 30: miniboss is level 32-122
            higher_level = random.randint(self.level + 2, self.level + 2 + int(self.level * self.level * 0.1))
            monster_levels.append(higher_level)

        # Add current level monsters
        monster_levels.extend([self.level] * current_level_count)

        # Add previous level monsters
        if self.level > 1:
            monster_levels.extend([self.level - 1] * previous_level_count)

        # Add mix of older level monsters
        for _ in range(older_levels_count):
            older_level = random.randint(1, max(1, self.level - 1))
            monster_levels.append(older_level)

        # Shuffle the list so monsters aren't grouped by level
        random.shuffle(monster_levels)
        return monster_levels

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
        
        # Handle stairway interaction
        self.handle_stairway_interaction()
        
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
            
            # Calculate distance to player
            dx_to_player = self.player.x - monster_entity.x
            dy_to_player = self.player.y - monster_entity.y
            distance_to_player = (dx_to_player ** 2 + dy_to_player ** 2) ** 0.5
            
            if distance_to_player <= MONSTER_FOLLOW_DISTANCE:
                # Close monsters follow the player directly
                self._move_monster_toward_player(monster_entity, dx_to_player, dy_to_player)
            else:
                # Distant monsters wander randomly
                self._wander_monster(monster_entity)
                
            # Keep monsters within bounds
            sprite_w = monster_entity.sprite.get_width()
            sprite_h = monster_entity.sprite.get_height()
            monster_entity.x = max(0, min(WINDOW_WIDTH - sprite_w, monster_entity.x))
            monster_entity.y = max(0, min(WINDOW_HEIGHT - sprite_h, monster_entity.y))

    def _move_monster_toward_player(self, monster_entity, dx, dy):
        """Move monster directly toward player"""
        # Normalize movement
        if dx != 0:
            monster_entity.x += 1 if dx > 0 else -1
        if dy != 0:
            monster_entity.y += 1 if dy > 0 else -1

    def _wander_monster(self, monster_entity):
        """Make monster wander randomly, avoiding walls and other monsters"""
        monster = monster_entity.monster
        
        # Occasionally change direction
        if random.random() < MONSTER_DIRECTION_CHANGE_CHANCE:
            monster.wander_direction_x = random.choice([-1, 0, 1])
            monster.wander_direction_y = random.choice([-1, 0, 1])
        
        # Calculate new position
        new_x = monster_entity.x + (monster.wander_direction_x * MONSTER_WANDER_SPEED)
        new_y = monster_entity.y + (monster.wander_direction_y * MONSTER_WANDER_SPEED)
        
        # Check for wall collisions and change direction if needed
        sprite_w = monster_entity.sprite.get_width()
        sprite_h = monster_entity.sprite.get_height()

        if new_x <= 0 or new_x >= WINDOW_WIDTH - sprite_w:
            monster.wander_direction_x *= -1
            new_x = monster_entity.x + (monster.wander_direction_x * MONSTER_WANDER_SPEED)

        if new_y <= 0 or new_y >= WINDOW_HEIGHT - sprite_h:
            monster.wander_direction_y *= -1
            new_y = monster_entity.y + (monster.wander_direction_y * MONSTER_WANDER_SPEED)
        
        # Check for collisions with other monsters
        if self._check_monster_collision(monster_entity, new_x, new_y):
            # Change direction if collision detected
            monster.wander_direction_x = random.choice([-1, 0, 1])
            monster.wander_direction_y = random.choice([-1, 0, 1])
        else:
            # Move to new position
            monster_entity.x = new_x
            monster_entity.y = new_y

    def _check_monster_collision(self, current_monster, new_x, new_y):
        """Check if monster would collide with another monster at new position"""
        for other_monster in self.monsters:
            if other_monster == current_monster or not other_monster.monster.is_alive:
                continue
                
            # Check if too close to other monster
            dx = abs(new_x - other_monster.x)
            dy = abs(new_y - other_monster.y)
            max_w = max(current_monster.sprite.get_width(), other_monster.sprite.get_width())
            max_h = max(current_monster.sprite.get_height(), other_monster.sprite.get_height())
            if dx < max_w and dy < max_h:
                return True
        return False

    def handle_combat(self):
        """Handle player-monster interactions"""
        attacked = False  # Track if player attacked this frame
        current_time = pygame.time.get_ticks()

        # Deal with combat for all monsters in range
        for monster_entity in self.monsters[:]:
            if not monster_entity.monster.is_alive:
                continue
                
            if self._is_monster_in_attack_range(monster_entity):
                # Check if player can attack (cooldown check)
                if current_time - self.player.last_attack_time >= PLAYER_ATTACK_COOLDOWN:
                    self._attack_monster(monster_entity)
                    attacked = True

                    if not monster_entity.monster.is_alive:
                        self._remove_defeated_monster(monster_entity)
                        
                        # Check if level is complete
                        self._check_level_completion()
                        continue  # Skip to next monster since this one is dead
                
            # Check if monster can attack back (cooldown check and range check)
            if (current_time - monster_entity.monster.last_attack_time >= MONSTER_ATTACK_COOLDOWN and
                self._is_monster_in_melee_range(monster_entity)):
                self._monster_attack_player(monster_entity)
                monster_entity.monster.last_attack_time = current_time

        if attacked:
            self.player.last_attack_time = current_time


    def _is_monster_in_attack_range(self, monster_entity):
        """Check if monster is within player's attack range"""
        return self.is_within_range(self.player.x, self.player.y, 
                                  monster_entity.x, monster_entity.y,
                                  self.player.attack_range)

    def _is_monster_in_melee_range(self, monster_entity):
        """Check if monster is close enough to attack player (melee range only)"""
        return self.is_within_range(self.player.x, self.player.y,
                                  monster_entity.x, monster_entity.y,
                                  MONSTER_ATTACK_RANGE)

    def _attack_monster(self, monster_entity):
        """Attack a monster and deal damage"""
        monster_entity.monster.take_damage(self.player.attack_power)
        # print(f"Hit monster! Remaining health: {monster_entity.monster.health}")

    def _remove_defeated_monster(self, monster_entity):
        """Remove defeated monster and generate loot"""
        higher_level = monster_entity.monster.level > self.level
        lower_level = monster_entity.monster.level < self.level - 1
        # higher level monsters drop 3; current level drops fractionally; lower levels drop less
        count = 3 if higher_level else LOOT_DROP_CHANCE * 0.5 if lower_level else LOOT_DROP_CHANCE
        self.monsters.remove(monster_entity)
        # print("Monster defeated!")
        self.generate_loot(count)

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

    def _check_level_completion(self):
        """Check if all monsters are defeated and spawn stairway"""
        if len(self.monsters) == 0 and self.stairway is None:
            # All monsters defeated, spawn stairway
            self.loading = True
            self.loading_message = "Generating stairway..."
            self._draw_loading_screen()
            pygame.event.pump()
            
            stairway_sprite = generate_stairway(self)
            
            # Find a position away from player and loot
            stairway_x, stairway_y = self._find_safe_stairway_position()
            self.stairway = GameEntity(stairway_sprite, stairway_x, stairway_y)
            
            self.message = "Level cleared! Collect loot, then find the stairway!"
            self.message_timer = 240  # 4 seconds
            self.loading = False

    def _find_safe_stairway_position(self):
        """Find a position for stairway that doesn't conflict with player or loot"""
        attempts = 0
        max_attempts = 20
        
        while attempts < max_attempts:
            # Try random positions
            x = random.randint(TILE_SIZE * 2, WINDOW_WIDTH - TILE_SIZE * 3)
            y = random.randint(TILE_SIZE * 2, WINDOW_HEIGHT - TILE_SIZE * 3)
            
            # Check distance from player (at least 3 tiles away)
            if self.is_within_range(self.player.x, self.player.y, x, y, TILE_SIZE * 3):
                attempts += 1
                continue
                
            # Check distance from any loot items (at least 2 tiles away)
            too_close_to_loot = False
            for loot_item in self.loot_items:
                if self.is_within_range(loot_item.x, loot_item.y, x, y, TILE_SIZE * 2):
                    too_close_to_loot = True
                    break
            
            if not too_close_to_loot:
                return x, y
            
            attempts += 1
        
        # Fallback: top-right corner if no good position found
        return WINDOW_WIDTH - TILE_SIZE * 2, TILE_SIZE * 2

    def _find_safe_monster_spawn_position(self):
        """Find a position for monster that's not too close to player"""
        attempts = 0
        max_attempts = 20
        min_distance = TILE_SIZE * 5  # At least 5 tiles away from player
        
        while attempts < max_attempts:
            x = random.randint(TILE_SIZE, WINDOW_WIDTH - TILE_SIZE * 2)
            y = random.randint(TILE_SIZE, WINDOW_HEIGHT - TILE_SIZE * 2)
            
            # Check distance from player
            if not self.is_within_range(self.player.x, self.player.y, x, y, min_distance):
                return x, y
            
            attempts += 1
        
        # Fallback: corner far from player
        if self.player.x < WINDOW_WIDTH // 2:
            return WINDOW_WIDTH - TILE_SIZE * 2, TILE_SIZE * 2
        else:
            return TILE_SIZE * 2, TILE_SIZE * 2

    def generate_loot(self, count = LOOT_DROP_CHANCE):
        """Generate random loot after defeating a monster"""
        remaining = count
        while remaining > 0:
            if random.random() < count:
                item_sprite, item_type = generate_item(self)
                item_x = random.randint(0, WINDOW_WIDTH - TILE_SIZE)
                item_y = random.randint(0, WINDOW_HEIGHT - TILE_SIZE)
                loot_item = LootItem(item_type, item_sprite, item_x, item_y)
                self.loot_items.append(loot_item)
            remaining -= 1

    def handle_loot_pickup(self):
        """Handle player picking up loot items"""
        for loot_item in self.loot_items[:]:  # Use slice copy to avoid modification during iteration
            # Check if player is close enough to pick up item
            if self.is_within_range(self.player.x, self.player.y,
                                  loot_item.x, loot_item.y, TILE_SIZE):
                # Apply loot effects and add to inventory
                self._apply_loot_effects(loot_item)
                self.player.inventory.append(loot_item)
                self.loot_items.remove(loot_item)
                
                # Show pickup message with effect
                effect_msg = self._get_loot_effect_message(loot_item)
                self.message = f"Picked up {loot_item.item_type}! {effect_msg}"
                self.message_timer = 180  # 3 seconds at 60 FPS
                print(f"Picked up {loot_item.item_type}! {effect_msg}")

    def handle_stairway_interaction(self):
        """Handle player interacting with stairway to advance level"""
        if self.stairway and self.is_within_range(
            self.player.x, self.player.y, 
            self.stairway.x, self.stairway.y, TILE_SIZE):
            
            # Advance to next level
            self.level += 1
            self.stairway = None  # Remove stairway
            
            self.message = f"Entering Level {self.level}!"
            self.message_timer = 120
            print(f"Advanced to Level {self.level}!")
            
            # Generate new level
            self.generate_level()

    def _apply_loot_effects(self, loot_item):
        """Apply the effects of picked up loot to the player"""
        if loot_item.item_type == 'weapon':
            # Weapons increase attack power
            self.player.attack_power += 5
        elif loot_item.item_type == 'armor':
            # Armor increases max health and heals
            # Add temporary armor to calculate new max health (this item will be added to inventory after)
            self.player.inventory.append(loot_item)  # Temporarily add to get correct count
            new_max_health = self.player.get_max_health()
            self.player.inventory.pop()  # Remove it since it gets added again after this function
            
            heal_amount = 20
            self.player.health = max(
                min(new_max_health, self.player.health + heal_amount),
                self.player.health,  # don't take away temp health if already above max
            )
        elif loot_item.item_type == 'potion':
            # Potions heal the player
            heal_amount = 50
            temp_heal_amount = 5
            max_health = self.player.get_max_health()
            self.player.health = max(
                min(max_health, self.player.health + heal_amount),
                self.player.health + temp_heal_amount,
            )

    def _get_loot_effect_message(self, loot_item):
        """Get the message describing what the loot item does"""
        if loot_item.item_type == 'weapon':
            return "Attack +5"
        elif loot_item.item_type == 'armor':
            return "Max Health +25, Healed +20"
        elif loot_item.item_type == 'potion':
            if self.player.health > self.player.get_max_health():
                return "+5 Temporary Health"
            else:
                return "Healed +50"
        return ""

    def draw(self):
        if self.loading:
            self._draw_loading_screen()
        else:
            screen.fill((32, 32, 48))  # Dark blue-gray background instead of pure black
            self._draw_player()
            self._draw_monsters()
            self._draw_loot()
            self._draw_stairway()
            self._draw_ui()
            pygame.display.flip()

    def _draw_player(self):
        """Draw the player sprite and health bar"""
        if self.player.sprite:  # Only draw if sprite exists
            screen.blit(self.player.sprite, (self.player.x, self.player.y))
            self._draw_player_health_bar()
            self._draw_player_attack_indicator()
            self._draw_attack_range_indicator()

    def _draw_monsters(self):
        """Draw all monsters and their health bars"""
        for monster_entity in self.monsters:
            screen.blit(monster_entity.sprite, (monster_entity.x, monster_entity.y))
            
            # Draw health bars, attack indicators, and level indicators for living monsters
            if monster_entity.monster.is_alive:
                self._draw_health_bar(monster_entity)
                self._draw_monster_attack_indicator(monster_entity)
                self._draw_monster_level_indicator(monster_entity)

    def _draw_health_bar(self, monster_entity):
        """Draw health bar for a monster"""
        monster = monster_entity.monster
        x, y = monster_entity.x, monster_entity.y
        bar_width = monster_entity.sprite.get_width()

        # Draw background (red)
        pygame.draw.rect(screen, (255, 0, 0),
                       (x, y - 10, bar_width, HEALTH_BAR_HEIGHT))
        # Draw health (green)
        pygame.draw.rect(screen, (0, 255, 0),
                       (x, y - 10,
                        bar_width * monster.get_health_ratio(),
                        HEALTH_BAR_HEIGHT))

    def _draw_player_health_bar(self):
        """Draw health bar for the player"""
        if self.player.sprite:  # Only draw if sprite exists
            x, y = self.player.x, self.player.y
            health_ratio = self.player.health / self.player.get_max_health()
            
            # Draw background (red)
            pygame.draw.rect(screen, (255, 0, 0), 
                           (x, y - 10, HEALTH_BAR_WIDTH, HEALTH_BAR_HEIGHT))
            # Draw health (green)
            pygame.draw.rect(screen, (0, 255, 0), 
                           (x, y - 10, 
                            HEALTH_BAR_WIDTH * health_ratio, 
                            HEALTH_BAR_HEIGHT))

    def _draw_player_attack_indicator(self):
        """Draw attack readiness indicator for player"""
        if self.player.sprite:
            current_time = pygame.time.get_ticks()
            time_since_attack = current_time - self.player.last_attack_time
            can_attack = time_since_attack >= PLAYER_ATTACK_COOLDOWN
            
            x, y = self.player.x, self.player.y
            indicator_size = 6
            
            if can_attack:
                # Green circle = ready to attack
                pygame.draw.circle(screen, (0, 255, 0), 
                                 (x + TILE_SIZE + 5, y + TILE_SIZE // 2), indicator_size)
            else:
                # Red circle = on cooldown
                pygame.draw.circle(screen, (255, 0, 0), 
                                 (x + TILE_SIZE + 5, y + TILE_SIZE // 2), indicator_size)

    def _draw_monster_attack_indicator(self, monster_entity):
        """Draw attack readiness indicator for monster"""
        current_time = pygame.time.get_ticks()
        time_since_attack = current_time - monster_entity.monster.last_attack_time
        can_attack = time_since_attack >= MONSTER_ATTACK_COOLDOWN

        x, y = monster_entity.x, monster_entity.y
        sprite_h = monster_entity.sprite.get_height()
        indicator_size = 4

        if can_attack:
            # Orange triangle = ready to attack (danger!)
            points = [(x - 8, y + sprite_h // 2 - 4),
                     (x - 8, y + sprite_h // 2 + 4),
                     (x - 2, y + sprite_h // 2)]
            pygame.draw.polygon(screen, (255, 165, 0), points)
        else:
            # Gray circle = on cooldown (safe)
            pygame.draw.circle(screen, (128, 128, 128),
                             (x - 5, y + sprite_h // 2), indicator_size)

    def _draw_monster_level_indicator(self, monster_entity):
        """Draw level number on monster to show difficulty"""
        color = (255, 215, 0) if getattr(monster_entity, "is_miniboss", False) else (255, 255, 255)
        font_size = 24 if getattr(monster_entity, "is_miniboss", False) else 20
        font = pygame.font.Font(None, font_size)
        level_text = font.render(str(monster_entity.monster.level), True, color)

        # Position in top-right corner of monster
        sprite_w = monster_entity.sprite.get_width()
        text_x = monster_entity.x + sprite_w - 15
        text_y = monster_entity.y - 5

        # Draw small dark background circle for readability
        bg_color_outer = (100, 80, 0) if getattr(monster_entity, "is_miniboss", False) else (0, 0, 0)
        bg_color_inner = (150, 120, 0) if getattr(monster_entity, "is_miniboss", False) else (64, 64, 64)
        pygame.draw.circle(screen, bg_color_outer, (text_x + 8, text_y + 8), 10)
        pygame.draw.circle(screen, bg_color_inner, (text_x + 8, text_y + 8), 9)

        screen.blit(level_text, (text_x, text_y))

    def _draw_attack_range_indicator(self):
        """Draw a subtle circle showing player's attack range"""
        if self.player.sprite:
            current_time = pygame.time.get_ticks()
            time_since_attack = current_time - self.player.last_attack_time
            can_attack = time_since_attack >= PLAYER_ATTACK_COOLDOWN
            
            # Only show range when player can attack
            if can_attack:
                center_x = self.player.x + TILE_SIZE // 2
                center_y = self.player.y + TILE_SIZE // 2
                
                # Draw a subtle transparent circle showing attack range
                range_surface = pygame.Surface((int(self.player.attack_range * 2), int(self.player.attack_range * 2)))
                range_surface.set_alpha(30)  # Very transparent
                range_surface.fill((0, 255, 0))  # Green tint
                
                # Draw circle outline
                pygame.draw.circle(range_surface, (0, 255, 0, 60), 
                                 (int(self.player.attack_range), int(self.player.attack_range)), 
                                 int(self.player.attack_range), 2)
                
                range_rect = range_surface.get_rect(center=(center_x, center_y))
                screen.blit(range_surface, range_rect)

    def _draw_loot(self):
        """Draw all loot items"""
        for loot_item in self.loot_items:
            screen.blit(loot_item.sprite, (loot_item.x, loot_item.y))

    def _draw_stairway(self):
        """Draw the stairway if it exists"""
        if self.stairway:
            screen.blit(self.stairway.sprite, (self.stairway.x, self.stairway.y))

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
        health_text = small_font.render(f"Health: {self.player.health}/{self.player.get_max_health()}", True, (255, 100, 100))
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
