import pygame
import os
import json
import random
import numpy as np
from PIL import Image
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

# Constants
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
TILE_SIZE = 32
LEVEL_WIDTH = 25
LEVEL_HEIGHT = 20

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

# Cache directories
CACHE_DIR = 'cache'
MONSTER_DIR = os.path.join(CACHE_DIR, 'monsters')
ITEM_DIR = os.path.join(CACHE_DIR, 'items')

# Initialize directories
for dir in [CACHE_DIR, MONSTER_DIR, ITEM_DIR]:
    os.makedirs(dir, exist_ok=True)

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("AI Dungeon Crawler")
        self.clock = pygame.time.Clock()
        self.level = 1
        self.player = Player()
        self.dungeon = Dungeon()
        self.running = True

    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(60)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_UP:
                    self.player.move(0, -1)
                elif event.key == pygame.K_DOWN:
                    self.player.move(0, 1)
                elif event.key == pygame.K_LEFT:
                    self.player.move(-1, 0)
                elif event.key == pygame.K_RIGHT:
                    self.player.move(1, 0)

    def update(self):
        self.dungeon.update()
        self.player.update()

    def draw(self):
        self.screen.fill(BLACK)
        self.dungeon.draw(self.screen)
        self.player.draw(self.screen)
        pygame.display.flip()

class Player:
    def __init__(self):
        self.x = LEVEL_WIDTH // 2
        self.y = LEVEL_HEIGHT // 2
        self.health = 100
        self.attack = 10
        self.defense = 5
        self.level = 1
        self.exp = 0
        self.exp_to_level = 100

    def move(self, dx, dy):
        new_x = self.x + dx
        new_y = self.y + dy
        if 0 <= new_x < LEVEL_WIDTH and 0 <= new_y < LEVEL_HEIGHT:
            self.x = new_x
            self.y = new_y

    def update(self):
        # Simple level progression
        if self.exp >= self.exp_to_level:
            self.level += 1
            self.exp = 0
            self.exp_to_level *= 1.5
            self.health += 10
            self.attack += 2
            self.defense += 1

    def draw(self, screen):
        # Draw player (simple placeholder)
        pygame.draw.rect(screen, BLUE, (self.x * TILE_SIZE, self.y * TILE_SIZE, TILE_SIZE, TILE_SIZE))

class Dungeon:
    def __init__(self):
        self.grid = self.generate_level()
        self.monsters = []
        self.items = []
        self.spawn_monsters()

    def generate_level(self):
        grid = np.zeros((LEVEL_WIDTH, LEVEL_HEIGHT), dtype=int)
        # Simple dungeon generation - expand this later
        for x in range(LEVEL_WIDTH):
            for y in range(LEVEL_HEIGHT):
                if x == 0 or x == LEVEL_WIDTH - 1 or y == 0 or y == LEVEL_HEIGHT - 1:
                    grid[x][y] = 1  # Wall
                else:
                    grid[x][y] = 0  # Floor
        return grid

    def spawn_monsters(self):
        # Spawn monsters based on level
        num_monsters = random.randint(1, 3)
        for _ in range(num_monsters):
            x = random.randint(1, LEVEL_WIDTH - 2)
            y = random.randint(1, LEVEL_HEIGHT - 2)
            monster = self.generate_monster()
            monster.x = x
            monster.y = y
            self.monsters.append(monster)

    def generate_monster(self):
        # Generate monster description using AI
        prompt = f"Generate a unique monster name and description for level {self.level}"
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        monster_data = response.choices[0].message.content
        
        # Parse the response and create monster
        monster = Monster(
            name="Unknown",  # Placeholder
            health=50 + (self.level * 10),
            attack=5 + self.level,
            defense=3 + (self.level // 2)
        )
        return monster

    def update(self):
        for monster in self.monsters:
            monster.update()

    def draw(self, screen):
        for x in range(LEVEL_WIDTH):
            for y in range(LEVEL_HEIGHT):
                if self.grid[x][y] == 1:  # Wall
                    pygame.draw.rect(screen, WHITE, (x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))
                else:  # Floor
                    pygame.draw.rect(screen, GREEN, (x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))
        
        # Draw monsters
        for monster in self.monsters:
            monster.draw(screen)

class Monster:
    def __init__(self, name, health, attack, defense):
        self.name = name
        self.health = health
        self.attack = attack
        self.defense = defense
        self.x = 0
        self.y = 0

    def update(self):
        # Simple AI - move randomly
        dx = random.choice([-1, 0, 1])
        dy = random.choice([-1, 0, 1])
        if dx != 0 or dy != 0:
            self.x += dx
            self.y += dy

    def draw(self, screen):
        # Draw monster (simple placeholder)
        pygame.draw.rect(screen, RED, (self.x * TILE_SIZE, self.y * TILE_SIZE, TILE_SIZE, TILE_SIZE))

def main():
    game = Game()
    game.run()
    pygame.quit()

if __name__ == "__main__":
    main()
