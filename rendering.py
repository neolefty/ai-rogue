"""Rendering system for drawing all game entities and UI."""

import pygame
from constants import *


class RenderSystem:
    """Handles all rendering of game entities and UI."""
    
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
    
    def render_game(self, game_state):
        """Render the complete game state."""
        if game_state.loading:
            self._render_loading_screen(game_state.loading_message)
        else:
            # Always render the game world
            self.screen.fill(BACKGROUND_COLOR)
            self._render_player(game_state.player)
            self._render_monsters(game_state.monsters)
            self._render_loot(game_state.loot_items)
            self._render_stairway(game_state.stairway)
            self._render_ui(game_state)
            
            # Render overlays on top
            if game_state.paused:
                self._render_paused_overlay()
            elif game_state.game_over:
                self._render_game_over_overlay(game_state)
                
            pygame.display.flip()
    
    def _render_player(self, player):
        """Render the player sprite and effects."""
        if player.sprite:
            # Draw effect circle behind sprite
            self._render_entity_effect_circle(player, player.x, player.y, player.sprite)
            
            # Draw sprite
            self.screen.blit(player.sprite, (player.x, player.y))
            
            # Draw health bar
            self._render_player_health_bar(player)
    
    def _render_monsters(self, monsters):
        """Render all monsters and their effects."""
        for monster in monsters:
            if not monster.is_alive:
                continue
                
            # Draw effect circle behind sprite
            self._render_entity_effect_circle(monster, monster.x, monster.y, monster.sprite)
            
            # Draw sprite
            if monster.sprite:
                self.screen.blit(monster.sprite, (monster.x, monster.y))
            
            # Draw health bar and level indicator
            self._render_monster_health_bar(monster)
            self._render_monster_level_indicator(monster)
    
    def _render_loot(self, loot_items):
        """Render all loot items."""
        for loot_item in loot_items:
            if loot_item.sprite:
                self.screen.blit(loot_item.sprite, (loot_item.x, loot_item.y))
    
    def _render_stairway(self, stairway):
        """Render the stairway if it exists."""
        if stairway and stairway.sprite:
            self.screen.blit(stairway.sprite, (stairway.x, stairway.y))
    
    def _render_entity_effect_circle(self, entity, x, y, sprite):
        """Render standardized effect circle for any entity."""
        if not sprite:
            return
            
        sprite_w = sprite.get_width()
        sprite_h = sprite.get_height()
        center_x = x + sprite_w // 2
        center_y = y + sprite_h // 2
        
        # Circle radius based on entity's attack range
        if hasattr(entity, 'attack_range'):  # Player
            radius = int(entity.attack_range)
        else:  # Monster
            radius = int(MONSTER_ATTACK_RANGE)
        
        circle_size = radius * 2
        
        # Determine effect color and alpha based on entity state
        color = None
        alpha = 0
        
        if entity.damage_flash_timer > 0:
            # Red: Entity took damage (highest priority)
            color = RED
            alpha = 100
        elif entity.attack_flash_timer > 0:
            # Cyan: Entity just dealt damage
            color = CYAN
            alpha = 100
        else:
            # Check attack readiness
            current_time = pygame.time.get_ticks()
            if hasattr(entity, 'last_attack_time'):
                if hasattr(entity, 'attack_power'):  # Player
                    cooldown = PLAYER_ATTACK_COOLDOWN
                else:  # Monster
                    cooldown = MONSTER_ATTACK_COOLDOWN
                
                time_since_attack = current_time - entity.last_attack_time
                can_attack = time_since_attack >= cooldown
                
                if can_attack:
                    # Light green: Ready to attack (subtle)
                    color = GREEN
                    alpha = 35
                else:
                    # Dark gray: Attack cooldown
                    color = DARK_GRAY
                    alpha = 60
        
        # Draw the circle if we have a color
        if color and alpha > 0:
            flash_surface = pygame.Surface((circle_size, circle_size), pygame.SRCALPHA)
            pygame.draw.circle(flash_surface, (*color, alpha), (radius, radius), radius)
            flash_rect = flash_surface.get_rect(center=(center_x, center_y))
            self.screen.blit(flash_surface, flash_rect)
    
    def _render_player_health_bar(self, player):
        """Render health bar for the player with bonus health in cyan."""
        x, y = player.x, player.y
        max_health = player.get_max_health()
        current_health = player.health
        
        # Draw background (red)
        pygame.draw.rect(self.screen, RED, 
                       (x, y - 10, HEALTH_BAR_WIDTH, HEALTH_BAR_HEIGHT))
        
        if current_health > 0:
            if current_health <= max_health:
                # Normal health (green)
                health_ratio = current_health / max_health
                pygame.draw.rect(self.screen, GREEN, 
                               (x, y - 10, 
                                HEALTH_BAR_WIDTH * health_ratio, 
                                HEALTH_BAR_HEIGHT))
            else:
                # Player has bonus health beyond max
                # Draw max health portion (green)
                pygame.draw.rect(self.screen, GREEN, 
                               (x, y - 10, HEALTH_BAR_WIDTH, HEALTH_BAR_HEIGHT))
                
                # Draw bonus health portion (cyan) - extends beyond normal bar
                bonus_health = current_health - max_health
                bonus_ratio = bonus_health / max_health  # Bonus relative to max health
                bonus_width = min(HEALTH_BAR_WIDTH * bonus_ratio, HEALTH_BAR_WIDTH)  # Cap at bar width
                
                pygame.draw.rect(self.screen, CYAN, 
                               (x, y - 15, bonus_width, HEALTH_BAR_HEIGHT))
    
    def _render_monster_health_bar(self, monster):
        """Render health bar for a monster."""
        x, y = monster.x, monster.y
        bar_width = monster.sprite.get_width() if monster.sprite else TILE_SIZE

        # Draw background (red)
        pygame.draw.rect(self.screen, RED,
                       (x, y - 10, bar_width, HEALTH_BAR_HEIGHT))
        # Draw health (green)
        pygame.draw.rect(self.screen, GREEN,
                       (x, y - 10,
                        bar_width * monster.get_health_ratio(),
                        HEALTH_BAR_HEIGHT))
    
    def _render_monster_level_indicator(self, monster):
        """Render level number on monster to show difficulty."""
        color = GOLD if monster.is_miniboss else WHITE
        font_size = 24 if monster.is_miniboss else 20
        font = pygame.font.Font(None, font_size)
        level_text = font.render(str(monster.level), True, color)

        # Position in top-right corner of monster
        sprite_w = monster.sprite.get_width() if monster.sprite else TILE_SIZE
        text_x = monster.x + sprite_w - 15
        text_y = monster.y - 5

        # Draw small dark background circle for readability
        bg_color_outer = (100, 80, 0) if monster.is_miniboss else (0, 0, 0)
        bg_color_inner = (150, 120, 0) if monster.is_miniboss else DARK_GRAY
        pygame.draw.circle(self.screen, bg_color_outer, (text_x + 8, text_y + 8), 10)
        pygame.draw.circle(self.screen, bg_color_inner, (text_x + 8, text_y + 8), 9)

        self.screen.blit(level_text, (text_x, text_y))
    
    def _render_ui(self, game_state):
        """Render user interface elements."""
        player = game_state.player
        
        # Level display
        level_text = self.font.render(f"Level: {game_state.level}", True, WHITE)
        self.screen.blit(level_text, (10, 10))
        
        # Inventory count
        inventory_text = self.small_font.render(f"Inventory: {len(player.inventory)} items", True, (200, 200, 200))
        self.screen.blit(inventory_text, (10, 50))
        
        # Player stats
        health_text = self.small_font.render(f"Health: {player.health}/{player.get_max_health()}", True, (255, 100, 100))
        self.screen.blit(health_text, (10, 75))
        
        attack_text = self.small_font.render(f"Attack: {player.attack_power:.2f}", True, (100, 255, 100))
        self.screen.blit(attack_text, (10, 100))
        
        # Message display
        if game_state.message_timer > 0:
            message_text = self.font.render(game_state.message, True, YELLOW)
            self.screen.blit(message_text, (WINDOW_WIDTH // 2 - 100, WINDOW_HEIGHT // 2 - 50))
        
        # Sprite generation status (if any pending)
        sprite_status = game_state.sprite_manager.get_status()
        if sprite_status['pending'] > 0 or sprite_status['active'] > 0:
            status_text = f"Generating sprites: {sprite_status['active']} active, {sprite_status['pending']} pending"
            status_surface = self.small_font.render(status_text, True, (150, 150, 255))
            self.screen.blit(status_surface, (10, WINDOW_HEIGHT - 25))
    
    def _render_loading_screen(self, loading_message):
        """Render loading screen when generating sprites."""
        self.screen.fill(BACKGROUND_COLOR)
        loading_text = self.font.render(loading_message, True, WHITE)
        text_rect = loading_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
        self.screen.blit(loading_text, text_rect)
        
        # Draw animated indicator
        dots = "." * ((pygame.time.get_ticks() // 500) % 4)
        dots_text = self.font.render(dots, True, WHITE)
        dots_rect = dots_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 50))
        self.screen.blit(dots_text, dots_rect)

        pygame.display.flip()
    
    def _render_paused_overlay(self):
        """Render a transparent overlay indicating the game is paused."""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))  # Semi-transparent black
        font = pygame.font.Font(None, 72)
        pause_text = font.render("Paused", True, WHITE)
        text_rect = pause_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
        overlay.blit(pause_text, text_rect)
        self.screen.blit(overlay, (0, 0))
    
    def _render_game_over_overlay(self, game_state):
        """Render the game over overlay with stats and restart option."""
        # Create translucent overlay
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))  # Semi-transparent black
        
        # Title
        title_font = pygame.font.Font(None, 72)
        title_text = title_font.render("GAME OVER", True, RED)
        title_rect = title_text.get_rect(center=(WINDOW_WIDTH // 2, 150))
        overlay.blit(title_text, title_rect)
        
        # Statistics
        stats_y = 250
        line_height = 40
        
        stats = [
            f"Level Reached: {game_state.level}",
            f"Levels Completed: {game_state.levels_completed}",
            f"Monsters Defeated: {game_state.monsters_defeated}",
            f"Items Collected: {game_state.items_collected}",
            f"Final Attack Power: {game_state.player.attack_power:.2f}" if game_state.player else "",
            f"Inventory Items: {len(game_state.player.inventory)}" if game_state.player else ""
        ]
        
        for i, stat in enumerate(stats):
            if stat:  # Skip empty strings
                stat_text = self.font.render(stat, True, WHITE)
                stat_rect = stat_text.get_rect(center=(WINDOW_WIDTH // 2, stats_y + i * line_height))
                overlay.blit(stat_text, stat_rect)
        
        # Instructions
        instructions_y = stats_y + len([s for s in stats if s]) * line_height + 60
        instruction_text = self.font.render("Press SPACE to play again or ESC to quit", True, YELLOW)
        instruction_rect = instruction_text.get_rect(center=(WINDOW_WIDTH // 2, instructions_y))
        overlay.blit(instruction_text, instruction_rect)
        
        # Blit the overlay to the screen
        self.screen.blit(overlay, (0, 0))