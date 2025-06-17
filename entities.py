"""Game entity classes with improved hierarchy."""

import math
import random
import pygame
from constants import *


class MonsterRenderInfo:
    """Contains all information needed to render a monster properly."""
    
    def __init__(self, monster, player_damage=None):
        self.monster = monster
        self.is_miniboss = monster.is_miniboss
        self.level = monster.level
        
        # Calculate scale factor based on hits to kill
        self.scale_factor = self._calculate_scale_factor(monster, player_damage)
        
        # Calculate sprite size
        self.sprite_size = int(TILE_SIZE * self.scale_factor)
        
        # Calculate font size based on scale
        self.font_size = self._calculate_font_size()
        
        # Calculate colors
        self.level_text_color = GOLD if self.is_miniboss else WHITE
        self.bg_alpha = 180 if self.is_miniboss else 60
        self.bg_color = (100, 80, 0, self.bg_alpha) if self.is_miniboss else (0, 0, 0, self.bg_alpha)
        
        # Calculate positioning offsets
        self.level_indicator_offset_x = 2  # Distance from right edge
        self.level_indicator_offset_y = 2  # Distance from top edge
    
    def _calculate_scale_factor(self, monster, player_damage):
        """Calculate the scale factor based on hits to kill."""
        if monster.is_miniboss:
            return MINIBOSS_SCALE_FACTOR
        
        if player_damage is None or player_damage <= 0:
            return REGULAR_SCALE_FACTOR  # Default to regular size
        
        # Calculate hits to kill based on max health
        hits_to_kill = math.ceil(monster.max_health / player_damage)
        
        if hits_to_kill <= 2:
            return LOW_LEVEL_SCALE_FACTOR
        elif hits_to_kill <= 4:
            return MID_LEVEL_SCALE_FACTOR
        else:
            return REGULAR_SCALE_FACTOR
    
    def _calculate_font_size(self):
        """Calculate appropriate font size based on scale factor."""
        if self.is_miniboss:
            return 24
        elif self.scale_factor < 0.7:  # Low-level monsters
            return 16
        elif self.scale_factor < 1.0:  # Mid-level monsters
            return 16
        else:
            return 20


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
    
    def __init__(self, level, stats, x, y, sprite=None, is_miniboss=False, dungeon_level=1, player_damage=None):
        super().__init__(x, y, sprite)
        self.level = level
        self.dungeon_level = dungeon_level
        self.player_damage = player_damage
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
        
        # Apply sprite scaling using render info
        if sprite:
            self.update_render_info()
            if self.render_info.scale_factor != 1.0:
                self.sprite = pygame.transform.scale(sprite, (self.render_info.sprite_size, self.render_info.sprite_size))
    
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
    
    def update_render_info(self):
        """Update the render info for this monster."""
        self.render_info = MonsterRenderInfo(self, self.player_damage)
    
    def get_render_info(self):
        """Get the current render info, creating it if needed."""
        if not hasattr(self, 'render_info') or self.render_info is None:
            self.update_render_info()
        return self.render_info


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
        return PLAYER_BASE_HEALTH + (armor_count * ARMOR_HEALTH_BONUS)
    
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
            self.attack_power += WEAPON_ATTACK_BONUS
        elif item.item_type == 'armor':
            # Calculate new max health with this armor
            new_max_health = self.get_max_health() + ARMOR_HEALTH_BONUS  # +1 for the new armor
            heal_amount = ARMOR_HEAL_BONUS
            self.health = max(
                min(new_max_health, self.health + heal_amount),
                self.health  # Don't reduce temp health if already above max
            )
        elif item.item_type == 'potion':
            max_health = self.get_max_health()
            temp_heal_amount = POTION_TEMP_HEAL
            
            if self.health >= max_health:
                # Already at max health, give temporary health
                self.health += temp_heal_amount
            else:
                # Scale healing based on missing health: heal half the damage or 5 points, whichever is greater
                missing_health = max_health - self.health
                scaled_heal = max(POTION_HEAL_AMOUNT, missing_health // 2)
                self.health = min(max_health, self.health + scaled_heal)
        
        self.inventory.append(item)
    
    def get_effect_message(self, item):
        """Get the message describing what an item does."""
        if item.item_type == 'weapon':
            return f"Attack +{WEAPON_ATTACK_BONUS}"
        elif item.item_type == 'armor':
            return f"Max Health +{ARMOR_HEALTH_BONUS}, Healed +{ARMOR_HEAL_BONUS}"
        elif item.item_type == 'potion':
            max_health = self.get_max_health()
            if self.health >= max_health:
                return f"+{POTION_TEMP_HEAL} Temporary Health"
            else:
                missing_health = max_health - self.health
                scaled_heal = max(POTION_HEAL_AMOUNT, missing_health // 2)
                return f"Healed +{scaled_heal}"
        return ""


class LootItem(Entity):
    """Loot item entity that can be picked up by the player."""
    
    def __init__(self, item_type, x, y, sprite=None, target_x=None, target_y=None):
        super().__init__(x, y, sprite)
        self.item_type = item_type  # 'weapon', 'armor', 'potion'
        
        # Animation properties
        self.target_x = target_x if target_x is not None else x
        self.target_y = target_y if target_y is not None else y
        self.slide_speed = 3.0  # Pixels per frame
        self.is_sliding = (target_x is not None or target_y is not None)
        self.animation_timer = 0
    
    def update(self):
        """Update loot item animation and return True if done sliding."""
        if not self.is_sliding:
            return True
        
        # Calculate distance to target
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        distance = (dx ** 2 + dy ** 2) ** 0.5
        
        # If close enough, snap to target and stop sliding
        if distance <= self.slide_speed:
            self.x = self.target_x
            self.y = self.target_y
            self.is_sliding = False
            return True
        
        # Move toward target
        if distance > 0:
            # Normalize direction and apply speed
            move_x = (dx / distance) * self.slide_speed
            move_y = (dy / distance) * self.slide_speed
            self.x += move_x
            self.y += move_y
        
        self.animation_timer += 1
        return False


class DeathSprite(Entity):
    """Temporary death sprite that appears when monsters die."""
    
    def __init__(self, x, y, sprite=None, is_miniboss=False):
        super().__init__(x, y, sprite)
        self.is_miniboss = is_miniboss
        self.lifetime = DEATH_SPRITE_MINIBOSS_LIFETIME if is_miniboss else DEATH_SPRITE_LIFETIME
        self.fade_timer = self.lifetime
        self.alpha = 255  # Full opacity initially
        self.original_sprite = None  # Store original sprite for fading
        self.faded_sprite = None  # Store current faded version
        
        # Scale sprite for mini-bosses
        if is_miniboss and sprite:
            import pygame
            scaled_size = int(TILE_SIZE * DEATH_SPRITE_MINIBOSS_SCALE)
            self.sprite = pygame.transform.scale(sprite, (scaled_size, scaled_size))
    
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