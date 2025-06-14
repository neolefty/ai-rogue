"""Combat system for player-monster interactions."""

import pygame
import random
from constants import *


class CombatSystem:
    """Handles all combat logic between player and monsters."""
    
    def __init__(self, game_state):
        self.game_state = game_state
    
    def update(self):
        """Update combat for all entities."""
        current_time = pygame.time.get_ticks()
        player = self.game_state.player
        
        # Handle player attacks
        if player.can_attack(current_time):
            attacked_monsters = self._get_monsters_in_attack_range(player)
            if attacked_monsters:
                self._player_attack(attacked_monsters, current_time)
        
        # Handle monster attacks
        for monster in self.game_state.monsters:
            if (monster.is_alive and 
                monster.can_attack(current_time) and 
                self._is_in_melee_range(player, monster)):
                self._monster_attack(monster, player, current_time)
    
    def _get_monsters_in_attack_range(self, player):
        """Get all monsters within player's attack range, sorted by distance."""
        monsters_in_range = []
        
        for monster in self.game_state.monsters:
            if not monster.is_alive:
                continue
                
            if self._is_within_range(player, monster, player.attack_range):
                # Calculate distance for sorting
                dx = player.x - monster.x
                dy = player.y - monster.y
                distance = (dx ** 2 + dy ** 2) ** 0.5
                monsters_in_range.append((distance, monster))
        
        # Sort by distance (closest first)
        monsters_in_range.sort(key=lambda x: x[0])
        return [monster for distance, monster in monsters_in_range]
    
    def _player_attack(self, monsters, current_time):
        """Handle player attacking multiple monsters with damage falloff."""
        player = self.game_state.player
        player.attack(current_time)
        
        for i, monster in enumerate(monsters):
            # Damage falloff: 1st gets full, 2nd gets 1/2, 3rd gets 1/3, etc.
            damage_multiplier = 1.0 / (i + 1)
            damage = player.attack_power * damage_multiplier
            
            monster.take_damage(damage)
            
            if not monster.is_alive:
                self._handle_monster_death(monster)
    
    def _monster_attack(self, monster, player, current_time):
        """Handle monster attacking player."""
        damage = monster.attack(current_time)
        player_died = player.take_damage(damage)
        
        # Set message for UI
        self.game_state.set_message(f"Monster hits for {damage} damage!", 120)
        print(f"Player takes {damage} damage! Health: {player.health}")
        
        if player_died:
            self.game_state.game_over = True
    
    def _handle_monster_death(self, monster):
        """Handle when a monster dies."""
        # Determine loot drop chance based on monster level vs player level
        player_level = self.game_state.level
        if monster.level > player_level:
            loot_count = 3  # Higher level monsters drop more
        elif monster.level < player_level - 1:
            loot_count = LOOT_DROP_CHANCE * 0.5  # Lower level monsters drop less
        else:
            loot_count = LOOT_DROP_CHANCE  # Current level monsters drop normal amount
        
        # Remove monster and generate loot
        self.game_state.remove_monster(monster)
        self.game_state.generate_loot(loot_count)
        
        # Check if level is complete
        if len(self.game_state.monsters) == 0:
            self.game_state.spawn_stairway()
    
    def _is_within_range(self, entity1, entity2, max_range):
        """Check if two entities are within a given range."""
        dx = abs(entity1.x - entity2.x)
        dy = abs(entity1.y - entity2.y)
        return dx <= max_range and dy <= max_range
    
    def _is_in_melee_range(self, entity1, entity2):
        """Check if entities are in melee range."""
        return self._is_within_range(entity1, entity2, MONSTER_ATTACK_RANGE)