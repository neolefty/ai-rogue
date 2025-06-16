"""Game state management for tracking all game data."""

import random
import pygame
from constants import *
from entities import Monster, Player, LootItem, Stairway, DeathSprite
from sprite_manager import SpriteManager
from preferences import PreferencesManager


class GameState:
    """Manages all game state data and provides clean interfaces for systems."""
    
    def __init__(self, sprite_generator, render_callback=None):
        self.sprite_generator = sprite_generator
        self.sprite_manager = SpriteManager(sprite_generator)
        self.render_callback = render_callback
        self.preferences = PreferencesManager()
        
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
        
        # Regeneration dialog state
        self.regeneration_dialog = None
        self.regeneration_entity = None
        self.regeneration_type = None
        
        # Initialize player
        self._initialize_player()
        
        # Set up sprite completion callback for variant availability
        self.sprite_manager.add_completion_callback(self._on_sprite_completion)
        
        # Sync available variants with existing cached sprites
        self.preferences.sync_available_with_existing_sprites(self.sprite_manager)
        
        # Queue generation for all unlocked variants on game start
        self.preferences.queue_initial_variants(self.sprite_manager)
    
    def _initialize_player(self):
        """Initialize the player with sprite manager."""
        # Get sprite (placeholder initially, real sprite loads in background)
        player_sprite = self.sprite_manager.get_sprite('player', 'player', priority=1)
        self.player = Player(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2, player_sprite)
    
    def _on_sprite_completion(self, key, sprite_type, params):
        """Handle sprite generation completion."""
        if sprite_type == 'item' and params and 'item_type' in params and 'item_variant' in params:
            item_type = params['item_type']
            item_variant = params['item_variant']
            
            # Mark variant as available if it was newly completed
            newly_available = self.preferences.mark_variant_available(item_type, item_variant)
            if newly_available:
                variant_name = f"{item_variant.title()}"
                self.set_message(f"New {item_type} ready: {variant_name}!", 150)
    
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
                # Generate item type and variant based on unlocked options
                item_type = random.choice(['weapon', 'armor', 'potion'])
                item_variant = self.preferences.get_random_variant(item_type)
                
                # Generate unique key for this loot item
                import time
                item_key = f"item_{item_type}_{item_variant}_{int(time.time() * 1000000) % 1000000}"
                
                # Get placeholder sprite, real sprite loads in background
                item_sprite = self.sprite_manager.get_sprite(item_key, 'item', {'item_type': item_type, 'item_variant': item_variant})
                
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
                loot_item.item_variant = item_variant  # Store variant for identification
                self.loot_items.append(loot_item)
            remaining -= 1
    
    def generate_specific_loot(self, item_type, x, y):
        """Generate a specific type of loot item at the given position."""
        # Generate variant based on unlocked options
        item_variant = self.preferences.get_random_variant(item_type)
        
        # Generate unique key for this loot item
        import time
        item_key = f"item_{item_type}_{item_variant}_{int(time.time() * 1000000) % 1000000}"
        
        # Get placeholder sprite, real sprite loads in background
        item_sprite = self.sprite_manager.get_sprite(item_key, 'item', {'item_type': item_type, 'item_variant': item_variant})
        
        # Calculate scatter position from center point
        scatter_radius = TILE_SIZE * 2
        target_x = x + random.randint(-scatter_radius, scatter_radius)
        target_y = y + random.randint(-scatter_radius, scatter_radius)
        
        # Keep target within screen bounds
        target_x = max(0, min(WINDOW_WIDTH - TILE_SIZE, target_x))
        target_y = max(0, min(WINDOW_HEIGHT - TILE_SIZE, target_y))
        
        # Create loot item with sliding animation from center
        start_x = x + TILE_SIZE // 2
        start_y = y + TILE_SIZE // 2
        loot_item = LootItem(item_type, start_x, start_y, item_sprite, target_x, target_y)
        
        loot_item.sprite_key = item_key  # Store key for sprite updates
        loot_item.item_variant = item_variant  # Store variant for identification
        self.loot_items.append(loot_item)
    
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
        
        # Update preferences and check for new unlocks
        newly_unlocked = self.preferences.update_game_stats(levels_completed=1, sprite_manager=self.sprite_manager)
        if newly_unlocked:
            unlock_names = [name.replace('_', ' ').title() for name in newly_unlocked]
            self.set_message(f"Level {self.level}! Unlocked: {', '.join(unlock_names)}!", 180)
        else:
            self.set_message(f"Entering Level {self.level}!", 120)
        
        print(f"Advanced to Level {self.level}!")
        self.generate_level()
    
    def remove_monster(self, monster):
        """Remove a monster from the game and create death sprite."""
        if monster in self.monsters:
            self.monsters.remove(monster)
            self.monsters_defeated += 1
            
            # Create death sprite at monster's position
            self.create_death_sprite(monster.x, monster.y, monster.is_miniboss)
            
            # Update preferences and check for new unlocks
            newly_unlocked = self.preferences.update_game_stats(monsters_killed=1, sprite_manager=self.sprite_manager)
            if newly_unlocked:
                unlock_names = [name.replace('_', ' ').title() for name in newly_unlocked]
                self.set_message(f"Unlocked: {', '.join(unlock_names)}!", 180)
    
    def create_death_sprite(self, x, y, is_miniboss=False):
        """Create a death sprite at the given position."""
        # Get death sprite (placeholder initially, real sprite loads in background)
        death_sprite = self.sprite_manager.get_sprite('death', 'death')
        death_entity = DeathSprite(x, y, death_sprite, is_miniboss)
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
            if hasattr(loot_item, 'item_variant') and hasattr(loot_item, 'item_type'):
                # Check for variant-specific sprite using shared key
                variant_key = f"item_{loot_item.item_type}_{loot_item.item_variant}"
                new_sprite = self.sprite_manager.sprites.get(variant_key)
                if new_sprite and new_sprite != loot_item.sprite:
                    loot_item.sprite = new_sprite
        
        # Update stairway sprite
        if self.stairway and hasattr(self.stairway, 'sprite_key'):
            new_sprite = self.sprite_manager.sprites.get(self.stairway.sprite_key)
            if new_sprite and new_sprite != self.stairway.sprite:
                # Scale stairway sprite to be more prominent
                scaled_size = int(TILE_SIZE * STAIRWAY_SCALE)
                self.stairway.sprite = pygame.transform.scale(new_sprite, (scaled_size, scaled_size))
        
        # Update death sprites
        for death_sprite in self.death_sprites:
            if hasattr(death_sprite, 'sprite_key'):
                new_sprite = self.sprite_manager.sprites.get(death_sprite.sprite_key)
                if new_sprite and new_sprite != death_sprite.sprite:
                    # Scale for mini-bosses if needed
                    if death_sprite.is_miniboss:
                        scaled_size = int(TILE_SIZE * DEATH_SPRITE_MINIBOSS_SCALE)
                        death_sprite.sprite = pygame.transform.scale(new_sprite, (scaled_size, scaled_size))
                    else:
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
    
    def save_game(self, filename="savegame.json"):
        """Save complete game state to file."""
        import json
        import time
        
        save_data = {
            "version": "1.0",
            "timestamp": time.time(),
            "game_state": {
                "level": self.level,
                "monsters_defeated": self.monsters_defeated,
                "items_collected": self.items_collected,
                "levels_completed": self.levels_completed,
                "game_over": self.game_over,
                "paused": self.paused,
                "message": self.message,
                "message_timer": self.message_timer
            },
            "player": {
                "x": self.player.x,
                "y": self.player.y,
                "health": self.player.health,
                "attack_power": self.player.attack_power,
                "inventory": [{"item_type": item.item_type} for item in self.player.inventory]
            },
            "monsters": [],
            "loot_items": [],
            "stairway": None,
            "death_sprites": []
        }
        
        # Save monsters
        for monster in self.monsters:
            monster_data = {
                "x": monster.x,
                "y": monster.y,
                "level": monster.level,
                "health": monster.health,
                "max_health": monster.max_health,
                "damage": monster.damage,
                "stats": monster.stats,
                "is_miniboss": monster.is_miniboss,
                "sprite_key": getattr(monster, 'sprite_key', f"monster_level_{monster.level}")
            }
            save_data["monsters"].append(monster_data)
        
        # Save loot items
        for loot_item in self.loot_items:
            loot_data = {
                "x": loot_item.x,
                "y": loot_item.y,
                "item_type": loot_item.item_type,
                "item_variant": getattr(loot_item, 'item_variant', loot_item.item_type),
                "sprite_key": getattr(loot_item, 'sprite_key', f"item_{loot_item.item_type}"),
                "is_sliding": getattr(loot_item, 'is_sliding', False),
                "target_x": getattr(loot_item, 'target_x', loot_item.x),
                "target_y": getattr(loot_item, 'target_y', loot_item.y)
            }
            save_data["loot_items"].append(loot_data)
        
        # Save stairway
        if self.stairway:
            save_data["stairway"] = {
                "x": self.stairway.x,
                "y": self.stairway.y,
                "sprite_key": getattr(self.stairway, 'sprite_key', 'stairway')
            }
        
        # Save death sprites
        for death_sprite in self.death_sprites:
            death_data = {
                "x": death_sprite.x,
                "y": death_sprite.y,
                "is_miniboss": death_sprite.is_miniboss,
                "fade_timer": death_sprite.fade_timer,
                "lifetime": death_sprite.lifetime,
                "alpha": death_sprite.alpha
            }
            save_data["death_sprites"].append(death_data)
        
        # Write to file
        try:
            with open(filename, 'w') as f:
                json.dump(save_data, f, indent=2)
            print(f"Game saved to {filename}")
            return True
        except Exception as e:
            print(f"Failed to save game: {e}")
            return False
    
    def load_game(self, filename="savegame.json"):
        """Load complete game state from file."""
        import json
        import os
        
        if not os.path.exists(filename):
            return False
        
        try:
            with open(filename, 'r') as f:
                save_data = json.load(f)
            
            print(f"Loading game from {filename}")
            
            # Restore game state
            game_state = save_data["game_state"]
            self.level = game_state["level"]
            self.monsters_defeated = game_state["monsters_defeated"]
            self.items_collected = game_state["items_collected"]
            self.levels_completed = game_state["levels_completed"]
            self.game_over = game_state["game_over"]
            self.paused = game_state["paused"]
            self.message = game_state["message"]
            self.message_timer = game_state["message_timer"]
            
            # Restore player
            player_data = save_data["player"]
            self.player.x = player_data["x"]
            self.player.y = player_data["y"]
            self.player.health = player_data["health"]
            self.player.attack_power = player_data["attack_power"]
            
            # Restore player inventory
            self.player.inventory = []
            for item_data in player_data["inventory"]:
                # Create dummy loot item for inventory
                dummy_item = type('Item', (), item_data)()
                self.player.inventory.append(dummy_item)
            
            # Clear existing entities
            self.monsters = []
            self.loot_items = []
            self.stairway = None
            self.death_sprites = []
            
            # Restore monsters
            for monster_data in save_data["monsters"]:
                sprite = self.sprite_manager.get_sprite(
                    monster_data["sprite_key"], 'monster', 
                    {'level': monster_data["level"]}
                )
                monster = Monster(
                    monster_data["level"], monster_data["stats"],
                    monster_data["x"], monster_data["y"], sprite,
                    monster_data["is_miniboss"]
                )
                monster.health = monster_data["health"]
                monster.max_health = monster_data["max_health"]
                monster.damage = monster_data["damage"]
                monster.sprite_key = monster_data["sprite_key"]
                self.monsters.append(monster)
            
            # Restore loot items
            for loot_data in save_data["loot_items"]:
                sprite = self.sprite_manager.get_sprite(
                    loot_data["sprite_key"], 'item',
                    {'item_type': loot_data["item_type"], 'item_variant': loot_data["item_variant"]}
                )
                loot_item = LootItem(
                    loot_data["item_type"], loot_data["x"], loot_data["y"], sprite,
                    loot_data["target_x"], loot_data["target_y"]
                )
                loot_item.sprite_key = loot_data["sprite_key"]
                loot_item.item_variant = loot_data["item_variant"]
                loot_item.is_sliding = loot_data["is_sliding"]
                self.loot_items.append(loot_item)
            
            # Restore stairway
            if save_data["stairway"]:
                stairway_data = save_data["stairway"]
                sprite = self.sprite_manager.get_sprite('stairway', 'stairway')
                self.stairway = Stairway(stairway_data["x"], stairway_data["y"], sprite)
                self.stairway.sprite_key = stairway_data["sprite_key"]
            
            # Restore death sprites
            for death_data in save_data["death_sprites"]:
                sprite = self.sprite_manager.get_sprite('death', 'death')
                death_sprite = DeathSprite(
                    death_data["x"], death_data["y"], sprite,
                    death_data["is_miniboss"]
                )
                death_sprite.fade_timer = death_data["fade_timer"]
                death_sprite.lifetime = death_data["lifetime"]
                death_sprite.alpha = death_data["alpha"]
                death_sprite.sprite_key = 'death'
                self.death_sprites.append(death_sprite)
            
            print(f"Game loaded: Level {self.level}, {len(self.monsters)} monsters, {len(self.loot_items)} loot items")
            return True
            
        except Exception as e:
            print(f"Failed to load game: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def show_regeneration_dialog(self, entity, entity_type):
        """Show regeneration dialog for an entity."""
        self.regeneration_dialog = True
        self.regeneration_entity = entity
        self.regeneration_type = entity_type
        self.paused = True
        print(f"Showing regeneration dialog for {entity_type}")
    
    def hide_regeneration_dialog(self):
        """Hide regeneration dialog and resume game."""
        self.regeneration_dialog = None
        self.regeneration_entity = None
        self.regeneration_type = None
        self.paused = False
    
    def regenerate_sprite(self):
        """Regenerate the sprite for the selected entity."""
        if not self.regeneration_entity or not self.regeneration_type:
            return
        
        entity = self.regeneration_entity
        entity_type = self.regeneration_type
        
        if entity_type == 'player':
            self._regenerate_player_sprite()
        elif entity_type == 'monster':
            self._regenerate_monster_sprite(entity)
        elif entity_type == 'loot':
            self._regenerate_loot_sprite(entity)
        elif entity_type == 'stairway':
            self._regenerate_stairway_sprite()
        elif entity_type == 'death':
            self._regenerate_death_sprite()
        
        self.hide_regeneration_dialog()
    
    def _regenerate_player_sprite(self):
        """Regenerate player sprite."""
        import os
        
        # Archive old sprite
        cache_path = "cache/sprites/player.png"
        if os.path.exists(cache_path):
            import time
            archived_path = f"cache/sprites/player_archived_{int(time.time())}.png"
            os.rename(cache_path, archived_path)
            print(f"Archived player sprite to {archived_path}")
        
        # Remove from sprite manager (both sprites and placeholders)
        if 'player' in self.sprite_manager.sprites:
            del self.sprite_manager.sprites['player']
        if 'player' in self.sprite_manager.placeholders:
            del self.sprite_manager.placeholders['player']
        
        # Queue regeneration and set placeholder
        new_sprite = self.sprite_manager.get_sprite('player', 'player', priority=1)
        self.player.sprite = new_sprite
        
        self.set_message("Regenerating player sprite...", 120)
    
    def _regenerate_monster_sprite(self, monster):
        """Regenerate monster sprite."""
        import os
        
        # Get monster cache info
        level = monster.level
        cache_path = f"cache/monsters/monster_level_{level}.png"
        
        # Archive old sprite
        if os.path.exists(cache_path):
            import time
            archived_path = f"cache/monsters/monster_level_{level}_archived_{int(time.time())}.png"
            os.rename(cache_path, archived_path)
            print(f"Archived monster sprite to {archived_path}")
        
        # Remove from sprite manager (both sprites and placeholders)
        monster_key = f"monster_level_{level}"
        if monster_key in self.sprite_manager.sprites:
            del self.sprite_manager.sprites[monster_key]
        if monster_key in self.sprite_manager.placeholders:
            del self.sprite_manager.placeholders[monster_key]
        
        # Queue regeneration and set placeholder
        new_sprite, _ = self.sprite_manager.get_monster_data(monster_key)
        
        # Handle mini-boss scaling
        if monster.is_miniboss:
            scaled_size = int(TILE_SIZE * 1.5)
            monster.sprite = pygame.transform.scale(new_sprite, (scaled_size, scaled_size))
        else:
            monster.sprite = new_sprite
        
        self.set_message(f"Regenerating level {level} monster sprite...", 120)
    
    def _regenerate_loot_sprite(self, loot_item):
        """Regenerate loot item sprite."""
        import os
        
        # Get loot cache info
        item_type = loot_item.item_type
        item_variant = getattr(loot_item, 'item_variant', item_type)
        cache_path = f"cache/items/item_{item_type}_{item_variant}.png"
        
        # Archive old sprite
        if os.path.exists(cache_path):
            import time
            archived_path = f"cache/items/item_{item_type}_{item_variant}_archived_{int(time.time())}.png"
            os.rename(cache_path, archived_path)
            print(f"Archived loot sprite to {archived_path}")
        
        # Remove from sprite manager (both sprites and placeholders)
        variant_key = f"item_{item_type}_{item_variant}"
        if variant_key in self.sprite_manager.sprites:
            del self.sprite_manager.sprites[variant_key]
        if variant_key in self.sprite_manager.placeholders:
            del self.sprite_manager.placeholders[variant_key]
        
        # Queue regeneration and set placeholder
        cache_key = f"item_{item_type}_{item_variant}"
        params = {'item_type': item_type, 'item_variant': item_variant}
        new_sprite = self.sprite_manager.get_sprite(cache_key, 'item', params, priority=1)
        loot_item.sprite = new_sprite
        
        self.set_message(f"Regenerating {item_variant} {item_type} sprite...", 120)
    
    def _regenerate_stairway_sprite(self):
        """Regenerate stairway sprite."""
        import os
        
        # Archive old sprite
        cache_path = "cache/sprites/stairway.png"
        if os.path.exists(cache_path):
            import time
            archived_path = f"cache/sprites/stairway_archived_{int(time.time())}.png"
            os.rename(cache_path, archived_path)
            print(f"Archived stairway sprite to {archived_path}")
        
        # Remove from sprite manager (both sprites and placeholders)
        if 'stairway' in self.sprite_manager.sprites:
            del self.sprite_manager.sprites['stairway']
        if 'stairway' in self.sprite_manager.placeholders:
            del self.sprite_manager.placeholders['stairway']
        
        # Queue regeneration and set placeholder
        new_sprite = self.sprite_manager.get_sprite('stairway', 'stairway', priority=1)
        self.stairway.sprite = new_sprite
        
        self.set_message("Regenerating stairway sprite...", 120)
    
    def _regenerate_death_sprite(self):
        """Regenerate death sprite."""
        import os
        
        # Archive old sprite
        cache_path = "cache/sprites/death.png"
        if os.path.exists(cache_path):
            import time
            archived_path = f"cache/sprites/death_archived_{int(time.time())}.png"
            os.rename(cache_path, archived_path)
            print(f"Archived death sprite to {archived_path}")
        
        # Remove from sprite manager (both sprites and placeholders)
        if 'death' in self.sprite_manager.sprites:
            del self.sprite_manager.sprites['death']
        if 'death' in self.sprite_manager.placeholders:
            del self.sprite_manager.placeholders['death']
        
        # Queue regeneration and set placeholder for all death sprites
        new_sprite = self.sprite_manager.get_sprite('death', 'death', priority=1)
        
        # Update all current death sprites to use the new placeholder
        for death_sprite in self.death_sprites:
            if death_sprite.is_miniboss:
                scaled_size = int(TILE_SIZE * DEATH_SPRITE_MINIBOSS_SCALE)
                death_sprite.sprite = pygame.transform.scale(new_sprite, (scaled_size, scaled_size))
            else:
                death_sprite.sprite = new_sprite
        
        self.set_message("Regenerating death sprite...", 120)