"""Sprite management system with background generation and placeholders."""

import threading
import queue
import pygame
from collections import defaultdict
import time
from constants import TILE_SIZE


class SpriteManager:
    """Manages sprite generation with placeholders and background loading."""
    
    def __init__(self, sprite_generator, max_concurrent=3):
        self.sprite_generator = sprite_generator
        self.max_concurrent = max_concurrent
        
        # Sprite storage
        self.sprites = {}  # key -> sprite mapping
        self.placeholders = {}  # key -> placeholder sprite
        
        # Background generation
        self.generation_queue = queue.PriorityQueue()
        self.active_generations = set()
        self.generation_lock = threading.Lock()
        self.workers = []
        
        # Statistics
        self.pending_count = 0
        self.completed_count = 0
        
        # Start worker threads
        self._start_workers()
    
    def _start_workers(self):
        """Start background worker threads for sprite generation."""
        for i in range(self.max_concurrent):
            worker = threading.Thread(target=self._generation_worker, daemon=True)
            worker.start()
            self.workers.append(worker)
    
    def _generation_worker(self):
        """Worker thread that processes sprite generation queue."""
        while True:
            try:
                # Get next item from queue (blocks if empty)
                priority, key, sprite_type, params = self.generation_queue.get(timeout=1)
                
                with self.generation_lock:
                    if key in self.sprites:
                        # Already generated, skip
                        self.generation_queue.task_done()
                        continue
                    self.active_generations.add(key)
                
                # Generate sprite based on type
                try:
                    if sprite_type == 'player':
                        sprite = self.sprite_generator.generate_player_sprite()
                    elif sprite_type == 'monster':
                        level = params['level']
                        sprite, stats = self.sprite_generator.generate_monster_sprite_and_stats(level)
                        # Store both sprite and stats
                        self.sprites[f"{key}_stats"] = stats
                    elif sprite_type == 'item':
                        # Use specific item type if provided, otherwise generate random
                        item_type = params.get('item_type') if params else None
                        if item_type:
                            # Generate sprite for specific item type using consistent cache path
                            cache_path = f"cache/items/item_{item_type}.png"
                            if os.path.exists(cache_path):
                                sprite = pygame.image.load(cache_path)
                            else:
                                from prompts import ITEM_SPRITE_PROMPT, SPRITE_STYLE
                                prompt = ITEM_SPRITE_PROMPT.format(item_type=item_type)
                                image_bytes = self.sprite_generator.client.generate_image(f"{prompt}. {SPRITE_STYLE}")
                                from io import BytesIO
                                from PIL import Image
                                import pygame
                                import os
                                
                                img = Image.open(BytesIO(image_bytes))
                                img = img.convert("RGBA")
                                img = img.resize((32, 32), Image.Resampling.NEAREST)
                                
                                # Convert dark background pixels to transparent
                                data = img.getdata()
                                new_data = []
                                for item in data:
                                    if item[0] + item[1] + item[2] < 30:
                                        new_data.append((255, 255, 255, 0))
                                    else:
                                        new_data.append(item)
                                img.putdata(new_data)
                                
                                # Save using consistent type-based cache path
                                img.save(cache_path, "PNG")
                                sprite = pygame.image.load(cache_path)
                        else:
                            sprite, item_type = self.sprite_generator.generate_item_sprite()
                            self.sprites[f"{key}_type"] = item_type
                    elif sprite_type == 'stairway':
                        sprite = self.sprite_generator.generate_stairway_sprite()
                    else:
                        sprite = None
                    
                    if sprite:
                        with self.generation_lock:
                            self.sprites[key] = sprite
                            self.completed_count += 1
                            self.pending_count = max(0, self.pending_count - 1)
                
                except Exception as e:
                    print(f"Error generating sprite {key}: {e}")
                
                finally:
                    with self.generation_lock:
                        self.active_generations.discard(key)
                    self.generation_queue.task_done()
                    
            except queue.Empty:
                continue
    
    def get_sprite(self, key, sprite_type, params=None, priority=5):
        """Get a sprite, returning placeholder if not ready."""
        # For items, use type-based keys to share sprites of the same type
        cache_key = key
        if sprite_type == 'item' and params and 'item_type' in params:
            cache_key = f"item_{params['item_type']}"
        
        # Check if sprite is ready in memory
        with self.generation_lock:
            if cache_key in self.sprites:
                return self.sprites[cache_key]
        
        # Check if sprite exists in cache on disk
        cached_sprite = self._check_disk_cache(cache_key, sprite_type, params)
        if cached_sprite:
            with self.generation_lock:
                self.sprites[cache_key] = cached_sprite
            return cached_sprite
        
        # Queue for generation if not already queued
        if cache_key not in self.placeholders:
            self.placeholders[cache_key] = self._create_placeholder(sprite_type, params)
            with self.generation_lock:
                self.pending_count += 1
            self.generation_queue.put((priority, cache_key, sprite_type, params or {}))
        
        return self.placeholders[cache_key]
    
    def get_monster_data(self, key):
        """Get monster sprite and stats, using placeholders if needed."""
        level = int(key.split('_')[-1])
        sprite = self.get_sprite(key, 'monster', {'level': level})
        
        # Check for cached stats
        stats_key = f"{key}_stats"
        if stats_key not in self.sprites:
            # Try to load stats from disk cache
            import os
            stats_path = f"cache/monsters/monster_level_{level}_stats.txt"
            if os.path.exists(stats_path):
                try:
                    with open(stats_path, 'r') as f:
                        stats = f.read()
                        self.sprites[stats_key] = stats
                except Exception as e:
                    print(f"Error loading cached stats {stats_path}: {e}")
        
        stats = self.sprites.get(stats_key, f"Level {level} monster")
        return sprite, stats
    
    
    def is_ready(self, key):
        """Check if a sprite is ready (not a placeholder)."""
        with self.generation_lock:
            return key in self.sprites
    
    def _check_disk_cache(self, key, sprite_type, params):
        """Check if sprite exists in disk cache and load it."""
        import os
        import pygame
        
        cache_path = None
        
        if sprite_type == 'player':
            cache_path = "cache/sprites/player.png"
        elif sprite_type == 'monster':
            level = params.get('level') if params else int(key.split('_')[-1])
            cache_path = f"cache/monsters/monster_level_{level}.png"
        elif sprite_type == 'item':
            item_type = params.get('item_type') if params else None
            if item_type:
                # Use consistent type-based cache path
                cache_path = f"cache/items/item_{item_type}.png"
            else:
                # Fallback: try to extract type from key or find any cached item
                if key.startswith('item_'):
                    type_from_key = key.split('_')[1] if len(key.split('_')) > 1 else None
                    if type_from_key in ['weapon', 'armor', 'potion']:
                        cache_path = f"cache/items/item_{type_from_key}.png"
                    else:
                        cache_path = None
                else:
                    cache_path = None
        elif sprite_type == 'stairway':
            cache_path = "cache/sprites/stairway.png"
        
        if cache_path and os.path.exists(cache_path):
            try:
                sprite = pygame.image.load(cache_path)
                
                # Handle mini-boss scaling for monsters
                if sprite_type == 'monster' and params:
                    level = params.get('level', 1)
                    current_level = getattr(self, '_current_level', 1)
                    if level >= current_level + 2:  # Is mini-boss
                        from constants import TILE_SIZE
                        scaled_size = int(TILE_SIZE * 1.5)
                        sprite = pygame.transform.scale(sprite, (scaled_size, scaled_size))
                
                return sprite
            except Exception as e:
                print(f"Error loading cached sprite {cache_path}: {e}")
        
        return None
    
    def _create_placeholder(self, sprite_type, params):
        """Create a placeholder sprite for the given type."""
        surface = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        
        # Choose colors and text based on type
        if sprite_type == 'player':
            bg_color = (0, 100, 200, 200)  # Blue
            text = "@"
            text_color = (255, 255, 255)
        elif sprite_type == 'monster':
            level = params.get('level', 1) if params else 1
            if level >= 10:
                bg_color = (200, 0, 0, 200)  # Red for high level
            elif level >= 5:
                bg_color = (200, 100, 0, 200)  # Orange for mid level
            else:
                bg_color = (100, 50, 0, 200)  # Brown for low level
            text = str(level)
            text_color = (255, 255, 255)
        elif sprite_type == 'item':
            item_type = params.get('item_type', 'item') if params else 'item'
            if item_type == 'weapon':
                bg_color = (200, 100, 0, 200)  # Orange
                text = "W"
            elif item_type == 'armor':
                bg_color = (100, 200, 100, 200)  # Green
                text = "A"
            elif item_type == 'potion':
                bg_color = (200, 0, 200, 200)  # Purple
                text = "P"
            else:
                bg_color = (200, 200, 0, 200)  # Yellow
                text = "?"
            text_color = (255, 255, 255)
        elif sprite_type == 'stairway':
            bg_color = (100, 100, 100, 200)  # Gray
            text = ">"
            text_color = (255, 255, 255)
        else:
            bg_color = (128, 128, 128, 200)  # Default gray
            text = "?"
            text_color = (255, 255, 255)
        
        # Draw background
        pygame.draw.rect(surface, bg_color, (0, 0, TILE_SIZE, TILE_SIZE))
        pygame.draw.rect(surface, (255, 255, 255, 255), (0, 0, TILE_SIZE, TILE_SIZE), 2)
        
        # Draw text
        font = pygame.font.Font(None, 20)
        text_surface = font.render(text, True, text_color)
        text_rect = text_surface.get_rect(center=(TILE_SIZE // 2, TILE_SIZE // 2))
        surface.blit(text_surface, text_rect)
        
        return surface
    
    def get_status(self):
        """Get generation status for UI display."""
        with self.generation_lock:
            return {
                'pending': self.pending_count,
                'completed': self.completed_count,
                'active': len(self.active_generations)
            }