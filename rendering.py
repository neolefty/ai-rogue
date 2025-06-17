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
        # Always render the game world
        self.screen.fill(BACKGROUND_COLOR)
        self._render_player(game_state.player)
        self._render_monsters(game_state.monsters)
        self._render_loot(game_state.loot_items)
        self._render_stairway(game_state.stairway)
        self._render_death_sprites(game_state.death_sprites)
        self._render_ui(game_state)
        
        # Render overlays on top
        if game_state.regeneration_dialog:
            self._render_regeneration_dialog(game_state)
        elif game_state.reset_confirmation_dialog:
            self._render_reset_confirmation_dialog()
        elif game_state.paused:
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
    
    def _render_death_sprites(self, death_sprites):
        """Render all death sprites with fade effect."""
        for death_sprite in death_sprites:
            # Use faded sprite if available, otherwise use regular sprite
            sprite_to_render = death_sprite.faded_sprite if death_sprite.faded_sprite else death_sprite.sprite
            if sprite_to_render:
                self.screen.blit(sprite_to_render, (death_sprite.x, death_sprite.y))
    
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
        # Get render info for this monster
        render_info = monster.get_render_info()
        
        # Skip rendering if level indicator should not be shown
        if not render_info.show_level_indicator:
            return
        
        # Create font and text
        font = pygame.font.Font(None, render_info.font_size)
        level_text = font.render(str(render_info.level), True, render_info.level_text_color)

        # Position in top-right corner of monster
        sprite_w = monster.sprite.get_width() if monster.sprite else TILE_SIZE
        text_rect = level_text.get_rect()
        text_x = monster.x + sprite_w - text_rect.width - render_info.level_indicator_offset_x
        text_y = monster.y - render_info.level_indicator_offset_y

        # Create translucent surface for background
        bg_size = max(text_rect.width + 4, text_rect.height + 4)
        bg_surface = pygame.Surface((bg_size, bg_size), pygame.SRCALPHA)
        
        # Draw translucent background circle
        pygame.draw.circle(bg_surface, render_info.bg_color, (bg_size//2, bg_size//2), bg_size//2)
        
        # Blit background and text
        self.screen.blit(bg_surface, (text_x - 2, text_y - 2))
        self.screen.blit(level_text, (text_x, text_y))
    
    def _render_ui(self, game_state):
        """Render user interface elements."""
        player = game_state.player
        
        # Level display (playthrough-level format)
        playthrough = game_state.deaths + 1
        level_text = self.font.render(f"Level: {playthrough}-{game_state.level}", True, WHITE)
        self.screen.blit(level_text, (10, 10))
        
        # Prowess (monster levels defeated)
        prowess_text = self.small_font.render(f"Prowess: {game_state.monster_levels_defeated}", True, (200, 200, 200))
        self.screen.blit(prowess_text, (10, 50))
        
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
    
    # Loading screen rendering removed - using background generation with placeholders
    
    def _render_paused_overlay(self):
        """Render a transparent overlay with pause menu options."""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))  # Semi-transparent black
        
        # Title
        title_font = pygame.font.Font(None, 72)
        pause_text = title_font.render("Paused", True, WHITE)
        title_rect = pause_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 80))
        overlay.blit(pause_text, title_rect)
        
        # Menu options
        menu_font = pygame.font.Font(None, 36)
        options = [
            "Press SPACE to Resume",
            "Press Q to Quit (saves game)",
            "Press R to Reset Progress"
        ]
        
        for i, option in enumerate(options):
            option_surface = menu_font.render(option, True, WHITE)
            option_rect = option_surface.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 10 + i * 40))
            overlay.blit(option_surface, option_rect)
        
        self.screen.blit(overlay, (0, 0))
    
    def _render_regeneration_dialog(self, game_state):
        """Render the sprite regeneration dialog."""
        # Create translucent overlay
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))  # Semi-transparent black
        
        # Dialog box - larger for better readability
        dialog_width = 400
        dialog_height = 200
        dialog_x = (WINDOW_WIDTH - dialog_width) // 2
        dialog_y = (WINDOW_HEIGHT - dialog_height) // 2
        
        # Draw dialog background
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)
        pygame.draw.rect(overlay, (40, 40, 60, 240), dialog_rect)
        pygame.draw.rect(overlay, WHITE, dialog_rect, 3)
        
        # Title
        title_font = pygame.font.Font(None, 36)
        title_text = f"Regenerate {game_state.regeneration_type.title()} Sprite?"
        title_surface = title_font.render(title_text, True, WHITE)
        title_rect = title_surface.get_rect(center=(WINDOW_WIDTH // 2, dialog_y + 35))
        overlay.blit(title_surface, title_rect)
        
        # Show the sprite being regenerated at 2x size
        entity = game_state.regeneration_entity
        if entity and entity.sprite:
            sprite_2x = pygame.transform.scale(entity.sprite, (entity.sprite.get_width() * 2, entity.sprite.get_height() * 2))
            sprite_rect = sprite_2x.get_rect(center=(WINDOW_WIDTH // 2, dialog_y + 100))
            overlay.blit(sprite_2x, sprite_rect)
        
        # Instructions at bottom
        instruction_font = pygame.font.Font(None, 24)
        instruction_text = "Press R to Regenerate  |  Press ESC to Cancel"
        instruction_surface = instruction_font.render(instruction_text, True, WHITE)
        instruction_rect = instruction_surface.get_rect(center=(WINDOW_WIDTH // 2, dialog_y + 165))
        overlay.blit(instruction_surface, instruction_rect)
        
        self.screen.blit(overlay, (0, 0))
    
    def _render_reset_confirmation_dialog(self):
        """Render the reset confirmation dialog."""
        # Create translucent overlay
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))  # Darker overlay for important dialog
        
        # Dialog box
        dialog_width = 500
        dialog_height = 180
        dialog_x = (WINDOW_WIDTH - dialog_width) // 2
        dialog_y = (WINDOW_HEIGHT - dialog_height) // 2
        
        # Draw dialog background
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)
        pygame.draw.rect(overlay, (60, 20, 20, 240), dialog_rect)  # Reddish background for warning
        pygame.draw.rect(overlay, WHITE, dialog_rect, 3)
        
        # Title
        title_font = pygame.font.Font(None, 42)
        title_text = "Reset Progress?"
        title_surface = title_font.render(title_text, True, WHITE)
        title_rect = title_surface.get_rect(center=(WINDOW_WIDTH // 2, dialog_y + 40))
        overlay.blit(title_surface, title_rect)
        
        # Warning text
        warning_font = pygame.font.Font(None, 28)
        warning_text = "This will delete your save and start completely fresh!"
        warning_surface = warning_font.render(warning_text, True, (255, 200, 200))  # Light red
        warning_rect = warning_surface.get_rect(center=(WINDOW_WIDTH // 2, dialog_y + 80))
        overlay.blit(warning_surface, warning_rect)
        
        # Instructions
        instruction_font = pygame.font.Font(None, 24)
        instruction_text = "Press Y to Reset  |  Press ESC to Cancel"
        instruction_surface = instruction_font.render(instruction_text, True, WHITE)
        instruction_rect = instruction_surface.get_rect(center=(WINDOW_WIDTH // 2, dialog_y + 130))
        overlay.blit(instruction_surface, instruction_rect)
        
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
            f"Monster Levels Defeated: {game_state.monster_levels_defeated}",
            f"Deaths: {game_state.deaths}",
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