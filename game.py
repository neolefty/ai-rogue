"""Main game coordination and input handling."""

import pygame
from constants import *
from ai_client import SpriteGenerator
from game_state import GameState
from combat import CombatSystem
from ai_behavior import AIBehaviorSystem
from rendering import RenderSystem


class Game:
    """Main game class that coordinates all systems."""
    
    def __init__(self):
        # Initialize pygame
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Dungeon Crawler")
        self.clock = pygame.time.Clock()
        
        # Initialize systems
        self.sprite_generator = SpriteGenerator()
        self.game_state = GameState(self.sprite_generator)
        self.combat_system = CombatSystem(self.game_state)
        self.ai_system = AIBehaviorSystem(self.game_state)
        self.render_system = RenderSystem(self.screen)
        
        # Loading screens removed - using background generation
        
        # Generate first level
        self.game_state.generate_level()
    
    def run(self):
        """Main game loop."""
        while self.game_state.running:
            self.handle_events()
            if not self.game_state.paused:
                self.update()
            self.render()
            self.clock.tick(60)
        
        pygame.quit()
    
    def handle_events(self):
        """Handle input events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.game_state.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game_state.running = False
                elif event.key == pygame.K_SPACE and self.game_state.game_over:
                    # Restart the game
                    self.game_state.restart_game()
            elif event.type == pygame.WINDOWFOCUSLOST:
                print("Window focus lost - pausing game")
                self.game_state.paused = True
            elif event.type == pygame.WINDOWFOCUSGAINED:
                print("Window focus gained - resuming game")
                self.game_state.paused = False
    
    def update(self):
        """Update all game systems."""
        if self.game_state.game_over:
            return
        
        # Handle player movement
        self._update_player_movement()
        
        # Update game systems
        self.ai_system.update_monsters()
        self.combat_system.update()
        
        # Handle interactions
        self._handle_loot_pickup()
        self._handle_stairway_interaction()
        
        # Update timers and sprites
        self.game_state.update_timers()
        self.game_state.update_sprites()
    
    def _update_player_movement(self):
        """Update player position based on input with normalized diagonal movement."""
        keys = pygame.key.get_pressed()
        player = self.game_state.player
        
        # Calculate movement direction
        move_x = 0
        move_y = 0
        
        if keys[pygame.K_LEFT]:
            move_x -= 1
        if keys[pygame.K_RIGHT]:
            move_x += 1
        if keys[pygame.K_UP]:
            move_y -= 1
        if keys[pygame.K_DOWN]:
            move_y += 1
        
        # Normalize diagonal movement to maintain consistent speed
        if move_x != 0 or move_y != 0:
            # Calculate magnitude and normalize
            magnitude = (move_x * move_x + move_y * move_y) ** 0.5
            move_x = (move_x / magnitude) * PLAYER_SPEED
            move_y = (move_y / magnitude) * PLAYER_SPEED
            
            # Apply movement
            player.x += move_x
            player.y += move_y

        # Keep player within bounds
        player.x = max(0, min(WINDOW_WIDTH - TILE_SIZE, player.x))
        player.y = max(0, min(WINDOW_HEIGHT - TILE_SIZE, player.y))
    
    def _handle_loot_pickup(self):
        """Handle player picking up loot items."""
        player = self.game_state.player
        
        for loot_item in self.game_state.loot_items[:]:  # Use slice copy to avoid modification during iteration
            # Check if player is close enough to pick up item
            dx = abs(player.x - loot_item.x)
            dy = abs(player.y - loot_item.y)
            if dx <= TILE_SIZE and dy <= TILE_SIZE:
                # Apply loot effects and add to inventory
                effect_msg = player.get_effect_message(loot_item)
                player.add_to_inventory(loot_item)
                self.game_state.remove_loot_item(loot_item)
                
                # Show pickup message
                self.game_state.set_message(f"Picked up {loot_item.item_type}! {effect_msg}", 180)
                print(f"Picked up {loot_item.item_type}! {effect_msg}")
    
    def _handle_stairway_interaction(self):
        """Handle player interacting with stairway to advance level."""
        if not self.game_state.stairway:
            return
            
        player = self.game_state.player
        stairway = self.game_state.stairway
        
        dx = abs(player.x - stairway.x)
        dy = abs(player.y - stairway.y)
        if dx <= TILE_SIZE and dy <= TILE_SIZE:
            self.game_state.advance_level()
    
    def render(self):
        """Render the game."""
        self.render_system.render_game(self.game_state)


def main():
    """Entry point for the game."""
    game = Game()
    game.run()


if __name__ == "__main__":
    main()