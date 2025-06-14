"""Game state management for tracking all game data."""

import random
import pygame
from constants import *
from entities import Monster, Player, LootItem, Stairway


class GameState:
    """Manages all game state data and provides clean interfaces for systems."""
    
    def __init__(self, sprite_generator):
        self.sprite_generator = sprite_generator
        
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
        
        # UI state
        self.message = ""
        self.message_timer = 0
        self.loading = False
        self.loading_message = ""
        
        # Initialize player
        self._initialize_player()
    
    def _initialize_player(self):
        """Initialize the player with generated sprite."""
        self.show_loading("Generating hero sprite...")
        player_sprite = self.sprite_generator.generate_player_sprite(self)
        self.player = Player(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2, player_sprite)
        self.hide_loading()
    
    def generate_level(self):
        """Generate a new level with monsters."""
        self.monsters = []
        # Keep loot_items - they persist between levels
        self.stairway = None
        
        total_monsters = min(
            INITIAL_MONSTER_COUNT + (self.level - 1) * MONSTER_INCREMENT,
            MAX_MONSTER_COUNT
        )
        
        # Create a mix of monster levels for variety
        monster_levels = self._generate_monster_level_mix(total_monsters)
        
        for i, monster_level in enumerate(monster_levels):
            self.show_loading(f"Generating monsters... ({i+1}/{total_monsters})")
            
            monster_sprite, monster_stats = self.sprite_generator.generate_monster_sprite_and_stats(
                monster_level, self
            )
            x, y = self._find_safe_monster_spawn_position()
            
            is_miniboss = monster_level >= self.level + 2
            monster = Monster(monster_level, monster_stats, x, y, monster_sprite, is_miniboss)
            self.monsters.append(monster)
        
        self.hide_loading()
    
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
                item_sprite, item_type = self.sprite_generator.generate_item_sprite(self)
                
                # If monster position provided, scatter loot nearby
                if monster_x is not None and monster_y is not None:
                    # Scatter within 2-3 tiles of monster position
                    scatter_radius = TILE_SIZE * 3
                    item_x = monster_x + random.randint(-scatter_radius, scatter_radius)
                    item_y = monster_y + random.randint(-scatter_radius, scatter_radius)
                    
                    # Keep within screen bounds
                    item_x = max(0, min(WINDOW_WIDTH - TILE_SIZE, item_x))
                    item_y = max(0, min(WINDOW_HEIGHT - TILE_SIZE, item_y))
                else:
                    # Fallback to random position (for edge cases)
                    item_x = random.randint(0, WINDOW_WIDTH - TILE_SIZE)
                    item_y = random.randint(0, WINDOW_HEIGHT - TILE_SIZE)
                
                loot_item = LootItem(item_type, item_x, item_y, item_sprite)
                self.loot_items.append(loot_item)
            remaining -= 1
    
    def spawn_stairway(self):
        """Spawn the stairway to the next level."""
        if self.stairway is not None:
            return
            
        self.show_loading("Generating stairway...")
        stairway_sprite = self.sprite_generator.generate_stairway_sprite(self)
        
        # Find a safe position for the stairway
        stairway_x, stairway_y = self._find_safe_stairway_position()
        self.stairway = Stairway(stairway_x, stairway_y, stairway_sprite)
        
        self.set_message("Level cleared! Collect loot, then find the stairway!", 240)
        self.hide_loading()
    
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
        """Remove a monster from the game."""
        if monster in self.monsters:
            self.monsters.remove(monster)
            self.monsters_defeated += 1
    
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
    
    def show_loading(self, message):
        """Show loading screen with message."""
        self.loading = True
        self.loading_message = message
    
    def hide_loading(self):
        """Hide loading screen."""
        self.loading = False
    
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
        
        # Reset UI state
        self.message = ""
        self.message_timer = 0
        
        # Reinitialize player
        self._initialize_player()
        
        # Generate first level
        self.generate_level()