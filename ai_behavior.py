"""AI behavior system for monster movement and decision making."""

import random
from constants import *


class AIBehaviorSystem:
    """Handles monster AI behavior and movement."""
    
    def __init__(self, game_state):
        self.game_state = game_state
    
    def update_monsters(self):
        """Update all monster positions and behaviors."""
        player = self.game_state.player
        
        for monster in self.game_state.monsters:
            if not monster.is_alive:
                continue
            
            # Calculate distance to player
            dx_to_player = player.x - monster.x
            dy_to_player = player.y - monster.y
            distance_to_player = (dx_to_player ** 2 + dy_to_player ** 2) ** 0.5
            
            # Determine behavior based on distance to player
            if distance_to_player <= MONSTER_AGGRESSIVE_DISTANCE:
                # Close monsters always follow the player directly
                self._move_toward_target(monster, dx_to_player, dy_to_player)
            elif distance_to_player <= MONSTER_ALERT_DISTANCE:
                # Alert zone - commit to a behavior for a period of time
                self._handle_alert_zone_behavior(monster, dx_to_player, dy_to_player)
            else:
                # Distant monsters wander randomly
                self._wander_monster(monster)
            
            # Update behavior timers
            if monster.alert_behavior_timer > 0:
                monster.alert_behavior_timer -= 1
            
            # Keep monsters within screen bounds
            self._clamp_to_bounds(monster)
    
    def _handle_alert_zone_behavior(self, monster, dx_to_player, dy_to_player):
        """
        Handle monster behavior in the alert zone (between aggressive and passive).
        
        Alert Zone Behavior State Machine:
        - Commits to one behavior for 60-120 frames (1-2 seconds)
        - 30% chance to approach nearby mini-boss (if not mini-boss itself)
        - Remaining 70%: 70% chase player, 30% wander randomly
        
        This creates dynamic, unpredictable movement while maintaining tactical clustering.
        """
        # Choose new behavior if timer expired or no behavior set
        if monster.alert_behavior_timer <= 0 or monster.alert_behavior is None:
            # Check if there's a nearby mini-boss to bias toward (only for regular monsters)
            nearby_miniboss = self._find_nearby_miniboss(monster) if not monster.is_miniboss else None
            
            # Determine behavior with mini-boss bias
            rand = random.random()
            if nearby_miniboss and rand < MINIBOSS_BIAS_CHANCE:
                # 30% chance to approach mini-boss when one is nearby
                monster.alert_behavior = 'approach_miniboss'
                monster.target_miniboss = nearby_miniboss
            else:
                # Remaining 70% split between chase and wander behavior
                chase_rand = random.random()
                if chase_rand < MONSTER_ALERT_CHASE_CHANCE:
                    monster.alert_behavior = 'chase'
                else:
                    monster.alert_behavior = 'wander'
            
            # Commit to this behavior for 60-120 frames (1-2 seconds)
            monster.alert_behavior_timer = random.randint(60, 120)
        
        # Execute chosen behavior
        if monster.alert_behavior == 'chase':
            self._move_toward_target(monster, dx_to_player, dy_to_player)
        elif monster.alert_behavior == 'approach_miniboss' and monster.target_miniboss:
            # Move toward the targeted mini-boss
            dx_to_miniboss = monster.target_miniboss.x - monster.x
            dy_to_miniboss = monster.target_miniboss.y - monster.y
            self._move_toward_target(monster, dx_to_miniboss, dy_to_miniboss)
        else:
            self._wander_monster(monster)
    
    def _move_toward_target(self, monster, dx, dy):
        """Move monster toward target using 8-directional movement with normalized diagonal speed."""
        if dx == 0 and dy == 0:
            return
        
        # Convert to 8-directional movement
        move_x = 1 if dx > 0 else -1 if dx < 0 else 0
        move_y = 1 if dy > 0 else -1 if dy < 0 else 0
        
        # Normalize diagonal movement to maintain consistent speed
        if move_x != 0 and move_y != 0:
            # Diagonal movement: scale by 1/√2 to maintain speed
            diagonal_factor = 1.0 / (2 ** 0.5)  # ≈ 0.707
            move_x *= diagonal_factor
            move_y *= diagonal_factor
        
        # Apply movement
        monster.x += move_x
        monster.y += move_y
    
    def _wander_monster(self, monster):
        """Make monster wander randomly, avoiding walls and other monsters."""
        # Check for dispersion behavior when clustered with other monsters
        dispersion_direction = self._get_dispersion_direction(monster)
        
        # Occasionally change direction
        if random.random() < MONSTER_DIRECTION_CHANGE_CHANCE:
            if dispersion_direction and random.random() < MONSTER_DISPERSION_CHANCE:
                # Apply dispersion - move away from nearby monsters
                monster.wander_direction_x = dispersion_direction[0]
                monster.wander_direction_y = dispersion_direction[1]
            else:
                # Normal random direction change
                monster.wander_direction_x = random.choice([-1, 0, 1])
                monster.wander_direction_y = random.choice([-1, 0, 1])
        
        # Calculate new position
        new_x = monster.x + (monster.wander_direction_x * MONSTER_WANDER_SPEED)
        new_y = monster.y + (monster.wander_direction_y * MONSTER_WANDER_SPEED)
        
        # Check for wall collisions and change direction if needed
        sprite_w = monster.sprite.get_width() if monster.sprite else TILE_SIZE
        sprite_h = monster.sprite.get_height() if monster.sprite else TILE_SIZE

        if new_x <= 0 or new_x >= WINDOW_WIDTH - sprite_w:
            monster.wander_direction_x *= -1
            new_x = monster.x + (monster.wander_direction_x * MONSTER_WANDER_SPEED)

        if new_y <= 0 or new_y >= WINDOW_HEIGHT - sprite_h:
            monster.wander_direction_y *= -1
            new_y = monster.y + (monster.wander_direction_y * MONSTER_WANDER_SPEED)
        
        # Check for collisions with other monsters
        # Allow movement if: no collision, mini-boss, or actively dispersing
        is_dispersing = dispersion_direction is not None
        can_move = (not self._check_monster_collision(monster, new_x, new_y) or 
                   monster.is_miniboss or 
                   is_dispersing)
        
        if can_move:
            # Move to new position
            monster.x = new_x
            monster.y = new_y
        else:
            # Change direction if collision detected
            monster.wander_direction_x = random.choice([-1, 0, 1])
            monster.wander_direction_y = random.choice([-1, 0, 1])
    
    def _check_monster_collision(self, current_monster, new_x, new_y):
        """Check if monster would collide with another monster at new position."""
        for other_monster in self.game_state.monsters:
            if other_monster == current_monster or not other_monster.is_alive:
                continue
                
            # Check if too close to other monster
            dx = abs(new_x - other_monster.x)
            dy = abs(new_y - other_monster.y)
            
            current_w = current_monster.sprite.get_width() if current_monster.sprite else TILE_SIZE
            current_h = current_monster.sprite.get_height() if current_monster.sprite else TILE_SIZE
            other_w = other_monster.sprite.get_width() if other_monster.sprite else TILE_SIZE
            other_h = other_monster.sprite.get_height() if other_monster.sprite else TILE_SIZE
            
            max_w = max(current_w, other_w)
            max_h = max(current_h, other_h)
            
            if dx < max_w and dy < max_h:
                return True
        return False
    
    def _find_nearby_miniboss(self, monster):
        """Find the nearest mini-boss within influence radius."""
        nearest_miniboss = None
        nearest_distance = float('inf')
        
        for other_monster in self.game_state.monsters:
            if (not other_monster.is_miniboss or 
                not other_monster.is_alive or 
                other_monster == monster):
                continue
            
            # Calculate distance to mini-boss
            dx = other_monster.x - monster.x
            dy = other_monster.y - monster.y
            distance = (dx ** 2 + dy ** 2) ** 0.5
            
            if distance <= MINIBOSS_INFLUENCE_RADIUS and distance < nearest_distance:
                nearest_miniboss = other_monster
                nearest_distance = distance
        
        return nearest_miniboss
    
    def _get_dispersion_direction(self, monster):
        """
        Calculate direction to move away from nearby monsters when wandering.
        
        Dispersion System:
        - Only activates when monster is beyond alert distance (not in combat)
        - Finds monsters within 80px dispersion radius
        - Calculates weighted repulsion (closer monsters = stronger push)
        - Returns 8-directional movement vector away from cluster
        - Used to prevent monsters getting permanently stuck together
        """
        # Only apply dispersion when monster is distant from player (not in combat)
        player = self.game_state.player
        dx_to_player = player.x - monster.x
        dy_to_player = player.y - monster.y
        distance_to_player = (dx_to_player ** 2 + dy_to_player ** 2) ** 0.5
        
        # Only disperse when not near player (beyond alert distance)
        if distance_to_player <= MONSTER_ALERT_DISTANCE:
            return None
        
        # Find all nearby monsters within dispersion radius
        nearby_monsters = []
        for other_monster in self.game_state.monsters:
            if (other_monster == monster or not other_monster.is_alive):
                continue
            
            dx = other_monster.x - monster.x
            dy = other_monster.y - monster.y
            distance = (dx ** 2 + dy ** 2) ** 0.5
            
            if distance <= MONSTER_DISPERSION_RADIUS:
                nearby_monsters.append((dx, dy, distance))
        
        # If no nearby monsters, no dispersion needed
        if not nearby_monsters:
            return None
        
        # Calculate average direction away from nearby monsters
        repel_x = 0
        repel_y = 0
        for dx, dy, distance in nearby_monsters:
            # Weight by inverse distance (closer monsters have more repelling force)
            weight = 1.0 / max(distance, 1)  # Avoid division by zero
            repel_x -= dx * weight
            repel_y -= dy * weight
        
        # Convert to normalized 8-directional movement
        if abs(repel_x) < 0.1 and abs(repel_y) < 0.1:
            return None  # No clear direction
        
        direction_x = 1 if repel_x > 0 else -1 if repel_x < 0 else 0
        direction_y = 1 if repel_y > 0 else -1 if repel_y < 0 else 0
        
        return (direction_x, direction_y)
    
    def _clamp_to_bounds(self, monster):
        """Keep monster within screen bounds."""
        sprite_w = monster.sprite.get_width() if monster.sprite else TILE_SIZE
        sprite_h = monster.sprite.get_height() if monster.sprite else TILE_SIZE
        monster.x = max(0, min(WINDOW_WIDTH - sprite_w, monster.x))
        monster.y = max(0, min(WINDOW_HEIGHT - sprite_h, monster.y))