"""Game state management for tracking all game data."""

import random
import pygame
from constants import *
from entities import Monster, Player, LootItem, Stairway, DeathSprite
from sprite_manager import SpriteManager


class GameState:
    """Manages all game state data and provides clean interfaces for systems."""
    
    def __init__(self, sprite_generator, render_callback=None):
        self.sprite_generator = sprite_generator
        self.sprite_manager = SpriteManager(sprite_generator)
        self.render_callback = render_callback
        
        # Core game state
        self.running = True
        self.paused = False
        self.game_over = False
        self.level = 1
        
        # Game statistics
        self.monsters_defeated = 0
        self.items_collected = 0
        self.levels_completed = 0
        
        # Entities
        self.player = None
        self.monsters = []
        self.loot_items = []
        self.stairway = None
        self.death_sprites = []
        
        # UI state
        self.message = ""
        self.message_timer = 0
        # Loading screens removed - using placeholders now
        
        # Initialize player
        self._initialize_player()
    
    def _initialize_player(self):
        """Initialize the player with sprite manager."""
        # Get sprite (placeholder initially, real sprite loads in background)
        player_sprite = self.sprite_manager.get_sprite('player', 'player', priority=1)
        self.player = Player(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2, player_sprite)
    
    def generate_level(self):
        """Generate a new level with monsters."""
        self.monsters = []
        # Keep loot_items - they persist between levels
        self.stairway = None
        self.death_sprites = []  # Clear death sprites for new level
        
        # Update sprite manager with current level for mini-boss scaling
        self.sprite_manager._current_level = self.level
        
        total_monsters = min(
            INITIAL_MONSTER_COUNT + (self.level - 1) * MONSTER_INCREMENT,
            MAX_MONSTER_COUNT
        )
        
        # Create a mix of monster levels for variety
        monster_levels = self._generate_monster_level_mix(total_monsters)
        
        for i, monster_level in enumerate(monster_levels):
            # Generate monster using sprite manager (instant with placeholders)
            monster_key = f"monster_level_{monster_level}"
            monster_sprite, monster_stats = self.sprite_manager.get_monster_data(monster_key)
            
            x, y = self._find_safe_monster_spawn_position()
            
            is_miniboss = monster_level >= self.level + 2
            monster = Monster(monster_level, monster_stats, x, y, monster_sprite, is_miniboss)
            monster.sprite_key = monster_key  # Store key for sprite updates
            self.monsters.append(monster)
    
    def _generate_monster_level_mix(self, total_monsters):
        """Generate a mix of monster levels for the current dungeon level."""
        monster_levels = []
        
        # Calculate monster distribution
        higher_level_count = max(1, int(total_monsters * 0.05))
        current_level_count = max(1, int(total_monsters * 0.35))
        previous_level_count = max(0, int(total_monsters * 0.15))
        older_levels_count = total_monsters - current_level_count - previous_level_count - higher_level_count

        # Add higher level monsters (minibosses)
        for _ in range(higher_level_count):
            higher_level = random.randint(
                self.level + 2, 
                self.level + 2 + int(self.level * self.level * 0.1)
            )
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
    
    def _find_safe_monster_spawn_position(self):
        """Find a position for monster that's not too close to player."""
        attempts = 0
        max_attempts = 20
        min_distance = TILE_SIZE * 5  # At least 5 tiles away from player
        
        while attempts < max_attempts:
            x = random.randint(TILE_SIZE, WINDOW_WIDTH - TILE_SIZE * 2)
            y = random.randint(TILE_SIZE, WINDOW_HEIGHT - TILE_SIZE * 2)
            
            # Check distance from player
            dx = abs(self.player.x - x)
            dy = abs(self.player.y - y)
            if dx > min_distance or dy > min_distance:
                return x, y
            
            attempts += 1
        
        # Fallback: corner far from player
        if self.player.x < WINDOW_WIDTH // 2:
            return WINDOW_WIDTH - TILE_SIZE * 2, TILE_SIZE * 2
        else:
            return TILE_SIZE * 2, TILE_SIZE * 2
    
    def generate_loot(self, count=LOOT_DROP_CHANCE, monster_x=None, monster_y=None):
        """Generate random loot items near a monster's death location."""
        remaining = count
        while remaining > 0:
            if random.random() < count:
                # Generate item type immediately (don't wait for sprite)
                item_type = random.choice(['weapon', 'armor', 'potion'])
                
                # Generate unique key for this loot item
                import time
                item_key = f"item_{item_type}_{int(time.time() * 1000000) % 1000000}"
                
                # Get placeholder sprite, real sprite loads in background
                item_sprite = self.sprite_manager.get_sprite(item_key, 'item', {'item_type': item_type})
                
                # If monster position provided, create sliding animation
                if monster_x is not None and monster_y is not None:
                    # Start at monster center
                    start_x = monster_x + TILE_SIZE // 2
                    start_y = monster_y + TILE_SIZE // 2
                    
                    # Calculate target position near monster (2-3 tiles away)
                    scatter_radius = TILE_SIZE * 3
                    target_x = monster_x + random.randint(-scatter_radius, scatter_radius)
                    target_y = monster_y + random.randint(-scatter_radius, scatter_radius)
                    
                    # Keep target within screen bounds
                    target_x = max(0, min(WINDOW_WIDTH - TILE_SIZE, target_x))
                    target_y = max(0, min(WINDOW_HEIGHT - TILE_SIZE, target_y))
                    
                    # Create loot item with sliding animation
                    loot_item = LootItem(item_type, start_x, start_y, item_sprite, target_x, target_y)
                else:
                    # Fallback to random position (for edge cases) - no animation
                    item_x = random.randint(0, WINDOW_WIDTH - TILE_SIZE)
                    item_y = random.randint(0, WINDOW_HEIGHT - TILE_SIZE)
                    loot_item = LootItem(item_type, item_x, item_y, item_sprite)
                loot_item.sprite_key = item_key  # Store key for sprite updates
                self.loot_items.append(loot_item)
            remaining -= 1
    
    def spawn_stairway(self):
        """Spawn the stairway to the next level."""
        if self.stairway is not None:
            return
            
        # Get stairway sprite (placeholder initially)
        stairway_sprite = self.sprite_manager.get_sprite('stairway', 'stairway', priority=2)
        
        # Find a safe position for the stairway
        stairway_x, stairway_y = self._find_safe_stairway_position()
        self.stairway = Stairway(stairway_x, stairway_y, stairway_sprite)
        self.stairway.sprite_key = 'stairway'  # Store key for sprite updates
        
        self.set_message("Level cleared! Collect loot, then find the stairway!", 240)
    
    def _find_safe_stairway_position(self):
        """Find a position for stairway that doesn't conflict with player or loot."""
        attempts = 0
        max_attempts = 20
        
        while attempts < max_attempts:
            # Try random positions
            x = random.randint(TILE_SIZE * 2, WINDOW_WIDTH - TILE_SIZE * 3)
            y = random.randint(TILE_SIZE * 2, WINDOW_HEIGHT - TILE_SIZE * 3)
            
            # Check distance from player (at least 3 tiles away)
            dx = abs(self.player.x - x)
            dy = abs(self.player.y - y)
            if dx <= TILE_SIZE * 3 and dy <= TILE_SIZE * 3:
                attempts += 1
                continue
                
            # Check distance from any loot items (at least 2 tiles away)
            too_close_to_loot = False
            for loot_item in self.loot_items:
                dx = abs(loot_item.x - x)
                dy = abs(loot_item.y - y)
                if dx <= TILE_SIZE * 2 and dy <= TILE_SIZE * 2:
                    too_close_to_loot = True
                    break
            
            if not too_close_to_loot:
                return x, y
            
            attempts += 1
        
        # Fallback: top-right corner if no good position found
        return WINDOW_WIDTH - TILE_SIZE * 2, TILE_SIZE * 2
    
    def advance_level(self):
        """Advance to the next level."""
        self.levels_completed += 1
        self.level += 1
        self.stairway = None
        self.set_message(f"Entering Level {self.level}!", 120)
        print(f"Advanced to Level {self.level}!")
        self.generate_level()
    
    def remove_monster(self, monster):
        """Remove a monster from the game and create death sprite."""
        if monster in self.monsters:
            self.monsters.remove(monster)
            self.monsters_defeated += 1
            
            # Create death sprite at monster's position
            self.create_death_sprite(monster.x, monster.y)
    
    def create_death_sprite(self, x, y):
        """Create a death sprite at the given position."""
        # Get death sprite (placeholder initially, real sprite loads in background)
        death_sprite = self.sprite_manager.get_sprite('death', 'death')
        death_entity = DeathSprite(x, y, death_sprite)
        death_entity.sprite_key = 'death'
        self.death_sprites.append(death_entity)
    
    def remove_loot_item(self, loot_item):
        """Remove a loot item from the game."""
        if loot_item in self.loot_items:
            self.loot_items.remove(loot_item)
            self.items_collected += 1
    
    def set_message(self, message, duration):
        """Set a temporary message to display."""
        self.message = message
        self.message_timer = duration
    
    def update_timers(self):
        """Update all game timers."""
        if self.message_timer > 0:
            self.message_timer -= 1
        
        # Update entity flash timers
        if self.player:
            if self.player.damage_flash_timer > 0:
                self.player.damage_flash_timer -= 1
            if self.player.attack_flash_timer > 0:
                self.player.attack_flash_timer -= 1
        
        for monster in self.monsters:
            if monster.damage_flash_timer > 0:
                monster.damage_flash_timer -= 1
            if monster.attack_flash_timer > 0:
                monster.attack_flash_timer -= 1
        
        # Update death sprites and remove expired ones
        self.death_sprites = [death_sprite for death_sprite in self.death_sprites 
                             if not death_sprite.update()]
        
        # Update loot item animations
        for loot_item in self.loot_items:
            loot_item.update()
    
    def update_sprites(self):
        """Update sprites that have finished generating."""
        # Update player sprite
        if hasattr(self.player, 'sprite_key') or 'player' in self.sprite_manager.sprites:
            new_sprite = self.sprite_manager.sprites.get('player')
            if new_sprite and new_sprite != self.player.sprite:
                self.player.sprite = new_sprite
        
        # Update monster sprites
        for monster in self.monsters:
            if hasattr(monster, 'sprite_key'):
                new_sprite = self.sprite_manager.sprites.get(monster.sprite_key)
                if new_sprite and new_sprite != monster.sprite:
                    # Handle mini-boss scaling
                    if monster.is_miniboss:
                        scaled_size = int(TILE_SIZE * 1.5)
                        monster.sprite = pygame.transform.scale(new_sprite, (scaled_size, scaled_size))
                    else:
                        monster.sprite = new_sprite
        
        # Update loot item sprites
        for loot_item in self.loot_items:
            if hasattr(loot_item, 'sprite_key'):
                # For items, check type-based key since sprites are shared by type
                type_based_key = f"item_{loot_item.item_type}"
                new_sprite = self.sprite_manager.sprites.get(type_based_key)
                if new_sprite and new_sprite != loot_item.sprite:
                    loot_item.sprite = new_sprite
        
        # Update stairway sprite
        if self.stairway and hasattr(self.stairway, 'sprite_key'):
            new_sprite = self.sprite_manager.sprites.get(self.stairway.sprite_key)
            if new_sprite and new_sprite != self.stairway.sprite:
                self.stairway.sprite = new_sprite
        
        # Update death sprites
        for death_sprite in self.death_sprites:
            if hasattr(death_sprite, 'sprite_key'):
                new_sprite = self.sprite_manager.sprites.get(death_sprite.sprite_key)
                if new_sprite and new_sprite != death_sprite.sprite:
                    death_sprite.sprite = new_sprite
    
    # Loading screen methods removed - using background generation with placeholders
    
    def restart_game(self):
        """Restart the game with a fresh state."""
        # Reset core game state
        self.game_over = False
        self.paused = False
        self.level = 1
        
        # Reset statistics
        self.monsters_defeated = 0
        self.items_collected = 0
        self.levels_completed = 0
        
        # Clear entities (but keep loot_items for "ghost of runs past" effect)
        self.monsters = []
        # Keep loot_items - they persist through restarts!
        self.stairway = None
        self.death_sprites = []
        
        # Reset UI state
        self.message = ""
        self.message_timer = 0
        
        # Reinitialize player
        self._initialize_player()
        
        # Generate first level
        self.generate_level()