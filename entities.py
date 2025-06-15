"""Game entity classes with improved hierarchy."""

import random
import pygame
from constants import *


class Entity:
    """Base class for all game entities with position and sprite."""
    
    def __init__(self, x, y, sprite=None):
        self.x = x
        self.y = y
        self.sprite = sprite
        self.damage_flash_timer = 0
        self.attack_flash_timer = 0
    
    def get_center(self):
        """Get the center coordinates of the entity."""
        if self.sprite:
            return (
                self.x + self.sprite.get_width() // 2,
                self.y + self.sprite.get_height() // 2
            )
        return (self.x + TILE_SIZE // 2, self.y + TILE_SIZE // 2)
    
    def get_rect(self):
        """Get pygame rect for collision detection."""
        if self.sprite:
            return pygame.Rect(self.x, self.y, self.sprite.get_width(), self.sprite.get_height())
        return pygame.Rect(self.x, self.y, TILE_SIZE, TILE_SIZE)


class Monster(Entity):
    """Monster entity with health, AI behavior, and combat capabilities."""
    
    def __init__(self, level, stats, x, y, sprite=None, is_miniboss=False):
        super().__init__(x, y, sprite)
        self.level = level
        self.health = MONSTER_HEALTH_MULTIPLIER * level
        self.max_health = self.health
        self.damage = MONSTER_DAMAGE_MULTIPLIER * level
        self.stats = stats  # AI-generated flavor text
        self.is_alive = True
        self.is_miniboss = is_miniboss
        self.last_attack_time = 0
        
        # AI behavior variables
        self.wander_direction_x = random.choice([-1, 0, 1])
        self.wander_direction_y = random.choice([-1, 0, 1])
        self.direction_change_timer = 0
        self.alert_behavior = None  # 'chase', 'wander', 'approach_miniboss'
        self.alert_behavior_timer = 0
        self.target_miniboss = None  # Reference to targeted mini-boss
        
        # Scale sprite for mini-bosses
        if is_miniboss and sprite:
            scaled_size = int(TILE_SIZE * 1.5)
            self.sprite = pygame.transform.scale(sprite, (scaled_size, scaled_size))
    
    def take_damage(self, amount):
        """Apply damage to the monster."""
        self.health -= amount
        self.damage_flash_timer = 20  # Flash for ~1/3 second
        if self.health <= 0:
            self.is_alive = False
    
    def get_health_ratio(self):
        """Get current health as a ratio of max health."""
        return self.health / self.max_health if self.max_health > 0 else 0
    
    def can_attack(self, current_time):
        """Check if monster can attack based on cooldown."""
        return current_time - self.last_attack_time >= MONSTER_ATTACK_COOLDOWN
    
    def attack(self, current_time):
        """Perform an attack (updates last attack time)."""
        self.attack_flash_timer = 10
        self.last_attack_time = current_time
        return self.damage


class Player(Entity):
    """Player entity with inventory, stats, and combat capabilities."""
    
    def __init__(self, x, y, sprite=None):
        super().__init__(x, y, sprite)
        self.health = PLAYER_BASE_HEALTH
        self.level = 1
        self.inventory = []
        self.attack_power = PLAYER_BASE_ATTACK
        self.attack_range = TILE_SIZE * 2.5  # 2.5 tiles range for hit-and-run tactics
        self.last_attack_time = 0
    
    def get_max_health(self):
        """Calculate player's current max health based on armor."""
        armor_count = len([item for item in self.inventory if item.item_type == 'armor'])
        return PLAYER_BASE_HEALTH + (armor_count * 1)
    
    def can_attack(self, current_time):
        """Check if player can attack based on cooldown."""
        return current_time - self.last_attack_time >= PLAYER_ATTACK_COOLDOWN
    
    def attack(self, current_time):
        """Perform an attack (updates last attack time and returns damage)."""
        self.attack_flash_timer = 10
        self.last_attack_time = current_time
        return self.attack_power
    
    def take_damage(self, amount):
        """Apply damage to the player."""
        self.health -= amount
        self.damage_flash_timer = 20
        return self.health <= 0  # Return True if player died
    
    def add_to_inventory(self, item):
        """Add an item to inventory and apply its effects."""
        if item.item_type == 'weapon':
            self.attack_power += 0.05
        elif item.item_type == 'armor':
            # Calculate new max health with this armor
            new_max_health = self.get_max_health() + 1  # +1 for the new armor
            heal_amount = 1
            self.health = max(
                min(new_max_health, self.health + heal_amount),
                self.health  # Don't reduce temp health if already above max
            )
        elif item.item_type == 'potion':
            heal_amount = 5
            temp_heal_amount = 1
            max_health = self.get_max_health()
            self.health = max(
                min(max_health, self.health + heal_amount),
                self.health + temp_heal_amount
            )
        
        self.inventory.append(item)
    
    def get_effect_message(self, item):
        """Get the message describing what an item does."""
        if item.item_type == 'weapon':
            return "Attack +0.05"
        elif item.item_type == 'armor':
            return "Max Health +1, Healed +1"
        elif item.item_type == 'potion':
            if self.health >= self.get_max_health():
                return "+1 Temporary Health"
            else:
                return "Healed +5"
        return ""


class LootItem(Entity):
    """Loot item entity that can be picked up by the player."""
    
    def __init__(self, item_type, x, y, sprite=None):
        super().__init__(x, y, sprite)
        self.item_type = item_type  # 'weapon', 'armor', 'potion'


class DeathSprite(Entity):
    """Temporary death sprite that appears when monsters die."""
    
    def __init__(self, x, y, sprite=None):
        super().__init__(x, y, sprite)
        self.lifetime = DEATH_SPRITE_LIFETIME  # Total time to exist
        self.fade_timer = self.lifetime
        self.alpha = 255  # Full opacity initially
        self.original_sprite = None  # Store original sprite for fading
        self.faded_sprite = None  # Store current faded version
    
    def update(self):
        """Update fade animation and return True if sprite should be removed."""
        self.fade_timer -= 1
        
        # Calculate fade steps (fade in discrete steps over lifetime)
        fade_steps = 4  # Number of discrete fade levels
        step_duration = self.lifetime // fade_steps
        current_step = (self.lifetime - self.fade_timer) // step_duration
        
        # Set alpha based on current fade step
        if current_step >= fade_steps:
            self.alpha = 0
        else:
            self.alpha = max(0, 255 - (current_step * (255 // fade_steps)))
        
        # Update faded sprite when sprite changes or alpha changes
        if self.sprite != self.original_sprite or self.faded_sprite is None:
            self.original_sprite = self.sprite
            if self.sprite:
                self.faded_sprite = self.sprite.copy()
                self.faded_sprite.set_alpha(self.alpha)
        elif self.original_sprite and self.alpha < 255:
            # Apply current alpha to original sprite
            self.faded_sprite = self.original_sprite.copy()
            self.faded_sprite.set_alpha(self.alpha)
        
        return self.fade_timer <= 0


class Stairway(Entity):
    """Stairway entity for level progression."""
    
    def __init__(self, x, y, sprite=None):
        super().__init__(x, y, sprite)