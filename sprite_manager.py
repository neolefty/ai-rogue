"""Sprite management system with background generation and placeholders."""

import threading
import queue
import pygame
from collections import defaultdict
import time
from constants import TILE_SIZE
from image_utils import process_generated_image, save_and_load_sprite


class SpriteManager:
    """
    Manages sprite generation with placeholders and background loading.
    
    Thread Safety:
    - Uses threading.Lock for sprites dict access
    - Background worker threads process generation queue
    - Safe to call from multiple threads
    
    Flow:
    1. get_sprite() returns placeholder immediately if not cached
    2. Background thread generates real sprite asynchronously  
    3. Real sprite replaces placeholder when ready
    4. Entities automatically get updated sprite on next frame
    """
    
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
        
        # Completion callbacks
        self.completion_callbacks = []
        
        # Start worker threads
        self._start_workers()
        
        # Load any existing cached sprites immediately
        self._preload_cache()
    
    def add_completion_callback(self, callback):
        """Add a callback to be called when sprite generation completes."""
        self.completion_callbacks.append(callback)
    
    def _notify_completion(self, key, sprite_type, params):
        """Notify all callbacks that a sprite generation completed."""
        for callback in self.completion_callbacks:
            try:
                callback(key, sprite_type, params)
            except Exception as e:
                print(f"Error in completion callback: {e}")
    
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
                        import os
                        item_type = params.get('item_type') if params else None
                        if item_type:
                            # Generate sprite for specific item type and variant using consistent cache path
                            item_variant = params.get('item_variant', item_type)
                            cache_path = f"cache/items/item_{item_type}_{item_variant}.png"
                            if os.path.exists(cache_path):
                                sprite = pygame.image.load(cache_path)
                            else:
                                from prompts import WEAPON_VARIANTS, ARMOR_VARIANTS, POTION_VARIANTS, SPRITE_STYLE
                                
                                # Use variant-specific prompts if available
                                item_variant = params.get('item_variant', item_type)
                                if item_type == 'weapon':
                                    prompt = WEAPON_VARIANTS.get(item_variant, f"Simple {item_variant} weapon")
                                elif item_type == 'armor':
                                    prompt = ARMOR_VARIANTS.get(item_variant, f"Simple {item_variant} armor")
                                else:  # potion
                                    prompt = POTION_VARIANTS.get(item_variant, f"Simple {item_variant} potion")
                                    
                                image_bytes = self.sprite_generator.client.generate_image(f"{prompt}. {SPRITE_STYLE}")
                                
                                # Process the image using shared utility
                                img = process_generated_image(image_bytes)
                                sprite = save_and_load_sprite(img, cache_path)
                        else:
                            sprite, item_type = self.sprite_generator.generate_item_sprite()
                            self.sprites[f"{key}_type"] = item_type
                    elif sprite_type == 'stairway':
                        sprite = self.sprite_generator.generate_stairway_sprite()
                    elif sprite_type == 'death':
                        sprite = self.sprite_generator.generate_death_sprite()
                    else:
                        sprite = None
                    
                    if sprite:
                        with self.generation_lock:
                            self.sprites[key] = sprite
                            self.completed_count += 1
                            self.pending_count = max(0, self.pending_count - 1)
                        
                        # Notify completion callbacks
                        self._notify_completion(key, sprite_type, params)
                
                except Exception as e:
                    print(f"Error generating sprite {key}: {e}")
                    import traceback
                    traceback.print_exc()
                
                finally:
                    with self.generation_lock:
                        self.active_generations.discard(key)
                    self.generation_queue.task_done()
                    
            except queue.Empty:
                continue
    
    def get_sprite(self, key, sprite_type, params=None, priority=5):
        """Get a sprite, returning placeholder if not ready."""
        # For items, use type and variant-based keys to share sprites of the same type and variant
        cache_key = key
        if sprite_type == 'item' and params and 'item_type' in params:
            item_type = params['item_type']
            item_variant = params.get('item_variant', item_type)
            cache_key = f"item_{item_type}_{item_variant}"
        
        # Check if sprite is ready in memory
        with self.generation_lock:
            if cache_key in self.sprites:
                return self.sprites[cache_key]
        
        # Check if sprite exists in cache on disk
        cached_sprite = self._check_disk_cache(cache_key, sprite_type, params)
        if cached_sprite:
            with self.generation_lock:
                self.sprites[cache_key] = cached_sprite
                # Remove from placeholders if it was there
                if cache_key in self.placeholders:
                    del self.placeholders[cache_key]
                    self.pending_count = max(0, self.pending_count - 1)
            return cached_sprite
        
        # Queue for generation if not already queued or active
        with self.generation_lock:
            already_queued = cache_key in self.placeholders or cache_key in self.active_generations
        
        if not already_queued:
            self.placeholders[cache_key] = self._create_placeholder(sprite_type, params)
            with self.generation_lock:
                self.pending_count += 1
            self.generation_queue.put((priority, cache_key, sprite_type, params or {}))
        
        # Handle case where placeholder might have been deleted (e.g., during regeneration)
        if cache_key not in self.placeholders:
            self.placeholders[cache_key] = self._create_placeholder(sprite_type, params)
        
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
            item_variant = params.get('item_variant') if params else None
            if item_type and item_variant:
                # Use consistent type and variant-based cache path
                cache_path = f"cache/items/item_{item_type}_{item_variant}.png"
            elif item_type:
                # Fallback to old format for backward compatibility
                cache_path = f"cache/items/item_{item_type}.png"
            else:
                # Fallback: try to extract type from key or find any cached item
                if key.startswith('item_'):
                    parts = key.split('_')
                    if len(parts) >= 3:  # item_type_variant_timestamp
                        type_from_key = parts[1]
                        variant_from_key = parts[2]
                        if type_from_key in ['weapon', 'armor', 'potion']:
                            cache_path = f"cache/items/item_{type_from_key}_{variant_from_key}.png"
                        else:
                            cache_path = None
                    else:
                        cache_path = None
                else:
                    cache_path = None
        elif sprite_type == 'stairway':
            cache_path = "cache/sprites/stairway.png"
        elif sprite_type == 'death':
            cache_path = "cache/sprites/death.png"
        
        if cache_path and os.path.exists(cache_path):
            try:
                sprite = pygame.image.load(cache_path)
                
                # Handle scaling for special sprite types
                if sprite_type == 'monster' and params:
                    level = params.get('level', 1)
                    current_level = getattr(self, '_current_level', 1)
                    if level >= current_level + 2:  # Is mini-boss
                        from constants import TILE_SIZE
                        scaled_size = int(TILE_SIZE * 1.5)
                        sprite = pygame.transform.scale(sprite, (scaled_size, scaled_size))
                elif sprite_type == 'stairway':
                    # Scale stairway sprites to be more prominent
                    from constants import TILE_SIZE, STAIRWAY_SCALE
                    scaled_size = int(TILE_SIZE * STAIRWAY_SCALE)
                    sprite = pygame.transform.scale(sprite, (scaled_size, scaled_size))
                
                return sprite
            except Exception as e:
                print(f"Error loading cached sprite {cache_path}: {e}")
        
        return None
    
    def _create_placeholder(self, sprite_type, params):
        """Create a placeholder sprite for the given type."""
        # Determine size based on sprite type
        if sprite_type == 'stairway':
            from constants import STAIRWAY_SCALE
            size = int(TILE_SIZE * STAIRWAY_SCALE)
        else:
            size = TILE_SIZE
        
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        
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
        elif sprite_type == 'death':
            bg_color = (150, 150, 150, 200)  # Light gray
            text = "†"  # Dagger/cross symbol for death
            text_color = (64, 64, 64)  # Dark gray text
        else:
            bg_color = (128, 128, 128, 200)  # Default gray
            text = "?"
            text_color = (255, 255, 255)
        
        # Draw background
        pygame.draw.rect(surface, bg_color, (0, 0, size, size))
        pygame.draw.rect(surface, (255, 255, 255, 255), (0, 0, size, size), 2)
        
        # Draw text
        font_size = int(20 * (size / TILE_SIZE))  # Scale font with sprite size
        font = pygame.font.Font(None, font_size)
        text_surface = font.render(text, True, text_color)
        text_rect = text_surface.get_rect(center=(size // 2, size // 2))
        surface.blit(text_surface, text_rect)
        
        return surface
    
    def _preload_cache(self):
        """Load commonly used cached sprites immediately."""
        import os
        
        # Preload player sprite if cached
        player_path = "cache/sprites/player.png"
        if os.path.exists(player_path):
            try:
                import pygame
                self.sprites['player'] = pygame.image.load(player_path)
            except Exception as e:
                print(f"Error preloading player sprite: {e}")
        
        # Preload stairway sprite if cached
        stairway_path = "cache/sprites/stairway.png"
        if os.path.exists(stairway_path):
            try:
                import pygame
                self.sprites['stairway'] = pygame.image.load(stairway_path)
            except Exception as e:
                print(f"Error preloading stairway sprite: {e}")
        
        # Preload common item types
        for item_type in ['weapon', 'armor', 'potion']:
            item_path = f"cache/items/item_{item_type}.png"
            if os.path.exists(item_path):
                try:
                    import pygame
                    self.sprites[f'item_{item_type}'] = pygame.image.load(item_path)
                except Exception as e:
                    print(f"Error preloading {item_type} sprite: {e}")
    
    def get_status(self):
        """Get generation status for UI display."""
        with self.generation_lock:
            # Sync pending count with actual queue state
            actual_pending = len(self.placeholders) - len([k for k in self.placeholders.keys() if k in self.sprites])
            self.pending_count = max(0, actual_pending)
            
            queue_size = self.generation_queue.qsize()
            
            # Debug output if queue seems stuck
            if queue_size > 0 and len(self.active_generations) == 0:
                print(f"WARNING: Queue has {queue_size} items but no active generations!")
                print(f"Placeholders: {len(self.placeholders)}, Sprites: {len(self.sprites)}")
            
            return {
                'pending': self.pending_count,
                'completed': self.completed_count,
                'active': len(self.active_generations),
                'queue_size': queue_size
            }
    
    def debug_queue_state(self):
        """Print detailed queue state for debugging."""
        with self.generation_lock:
            print(f"=== Sprite Manager Debug ===")
            print(f"Queue size: {self.generation_queue.qsize()}")
            print(f"Active generations: {len(self.active_generations)} - {list(self.active_generations)}")
            print(f"Placeholders: {len(self.placeholders)} - {list(self.placeholders.keys())[:5]}...")
            print(f"Sprites: {len(self.sprites)}")
            print(f"Workers: {len(self.workers)} threads")
            
            # Check if workers are alive
            alive_workers = [w for w in self.workers if w.is_alive()]
            print(f"Alive workers: {len(alive_workers)}")
            
            if len(alive_workers) < self.max_concurrent:
                print("WARNING: Some worker threads have died!")
                self._restart_dead_workers()
    
    def _restart_dead_workers(self):
        """Restart any dead worker threads."""
        alive_workers = [w for w in self.workers if w.is_alive()]
        if len(alive_workers) < self.max_concurrent:
            print(f"Restarting {self.max_concurrent - len(alive_workers)} dead workers...")
            self.workers = alive_workers
            
            # Start new workers to replace dead ones
            for i in range(self.max_concurrent - len(alive_workers)):
                worker = threading.Thread(target=self._generation_worker, daemon=True)
                worker.start()
                self.workers.append(worker)
                print(f"Started replacement worker {i+1}")