"""Player preferences and persistent progression system."""

import json
import os
from typing import Dict, List, Any


class PreferencesManager:
    """Manages player preferences and sprite variant unlocking progression."""
    
    def __init__(self, preferences_file="preferences.json"):
        self.preferences_file = preferences_file
        self.data = self._load_preferences()
    
    def _load_preferences(self) -> Dict[str, Any]:
        """Load preferences from file, or create defaults if file doesn't exist."""
        if os.path.exists(self.preferences_file):
            try:
                with open(self.preferences_file, 'r') as f:
                    data = json.load(f)
                    # Migrate old format to new format
                    return self._migrate_preferences(data)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading preferences: {e}, using defaults")
        
        # Return default preferences
        return {
            "lifetime_stats": {
                "total_monsters_killed": 0,
                "total_levels_completed": 0,
                "games_played": 0
            },
            "unlocked_variants": {
                "weapon": ["sword"],  # Start with basic variants
                "armor": ["helmet"],
                "potion": ["bottle"]
            },
            "available_variants": {
                "weapon": ["sword"],  # Start with basic variants (sprites exist)
                "armor": ["helmet"],
                "potion": ["bottle"]
            },
            "variant_definitions": {
                "weapon": ["sword", "axe", "dagger", "mace", "spear"],
                "armor": ["helmet", "shield", "chestplate", "gauntlets", "boots"],
                "potion": ["bottle", "vial", "flask", "orb", "crystal"]
            },
            "unlock_thresholds": {
                "monsters_per_weapon": 10,
                "monsters_per_armor": 15,
                "levels_per_potion": 3
            }
        }
    
    def _migrate_preferences(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate old preferences format to new format with available_variants."""
        # Add available_variants if missing
        if "available_variants" not in data:
            data["available_variants"] = {}
            unlocked = data.get("unlocked_variants", {})
            
            # Initially, all unlocked variants are available (backward compatibility)
            for item_type, variants in unlocked.items():
                data["available_variants"][item_type] = variants.copy()
            
            print("Migrated preferences to include available_variants")
        
        return data
    
    def save_preferences(self):
        """Save current preferences to file."""
        try:
            with open(self.preferences_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except IOError as e:
            print(f"Error saving preferences: {e}")
    
    def get_unlocked_variants(self, item_type: str) -> List[str]:
        """Get list of unlocked variants for given item type."""
        return self.data.get("unlocked_variants", {}).get(item_type, [])
    
    def get_available_variants(self, item_type: str) -> List[str]:
        """Get list of available (sprite-ready) variants for given item type."""
        return self.data.get("available_variants", {}).get(item_type, [])
    
    def get_random_variant(self, item_type: str) -> str:
        """Get a random available variant for the given item type."""
        import random
        variants = self.get_available_variants(item_type)
        return random.choice(variants) if variants else item_type
    
    def update_game_stats(self, monsters_killed: int = 0, levels_completed: int = 0, game_finished: bool = False, sprite_manager=None):
        """Update lifetime statistics and check for new unlocks."""
        stats = self.data["lifetime_stats"]
        
        # Update stats
        stats["total_monsters_killed"] += monsters_killed
        stats["total_levels_completed"] += levels_completed
        if game_finished:
            stats["games_played"] += 1
        
        # Check for new unlocks
        newly_unlocked = self._check_unlocks()
        
        # Pre-generate sprites for newly unlocked variants
        if newly_unlocked and sprite_manager:
            self._queue_variant_generation(newly_unlocked, sprite_manager)
        
        # Save after updates
        self.save_preferences()
        
        return newly_unlocked
    
    def _check_unlocks(self) -> List[str]:
        """Check if any new variants should be unlocked based on current stats."""
        newly_unlocked = []
        stats = self.data["lifetime_stats"]
        thresholds = self.data["unlock_thresholds"]
        unlocked = self.data["unlocked_variants"]
        definitions = self.data["variant_definitions"]
        
        # Check weapon unlocks (based on monsters killed)
        monsters_killed = stats["total_monsters_killed"]
        weapon_unlocks_earned = monsters_killed // thresholds["monsters_per_weapon"]
        current_weapon_count = len(unlocked["weapon"])
        available_weapons = definitions["weapon"]
        
        if weapon_unlocks_earned > current_weapon_count - 1 and current_weapon_count < len(available_weapons):
            new_weapon = available_weapons[current_weapon_count]
            unlocked["weapon"].append(new_weapon)
            newly_unlocked.append(f"weapon_{new_weapon}")
        
        # Check armor unlocks (based on monsters killed, slower rate)
        armor_unlocks_earned = monsters_killed // thresholds["monsters_per_armor"]
        current_armor_count = len(unlocked["armor"])
        available_armor = definitions["armor"]
        
        if armor_unlocks_earned > current_armor_count - 1 and current_armor_count < len(available_armor):
            new_armor = available_armor[current_armor_count]
            unlocked["armor"].append(new_armor)
            newly_unlocked.append(f"armor_{new_armor}")
        
        # Check potion unlocks (based on levels completed)
        levels_completed = stats["total_levels_completed"]
        potion_unlocks_earned = levels_completed // thresholds["levels_per_potion"]
        current_potion_count = len(unlocked["potion"])
        available_potions = definitions["potion"]
        
        if potion_unlocks_earned > current_potion_count - 1 and current_potion_count < len(available_potions):
            new_potion = available_potions[current_potion_count]
            unlocked["potion"].append(new_potion)
            newly_unlocked.append(f"potion_{new_potion}")
        
        return newly_unlocked
    
    def _queue_variant_generation(self, newly_unlocked: List[str], sprite_manager):
        """Queue sprite generation for newly unlocked variants."""
        for variant_name in newly_unlocked:
            # Parse variant name (e.g., "weapon_axe" -> item_type="weapon", variant="axe")
            if '_' in variant_name:
                item_type, variant = variant_name.split('_', 1)
                
                # Queue generation with high priority for immediate feedback
                cache_key = f"item_{item_type}_{variant}"
                params = {'item_type': item_type, 'item_variant': variant}
                sprite_manager.get_sprite(cache_key, 'item', params, priority=1)
                
                print(f"Queued generation for {variant_name}")
    
    def queue_initial_variants(self, sprite_manager):
        """Queue generation for all currently unlocked variants on game start."""
        unlocked = self.data["unlocked_variants"]
        
        for item_type, variants in unlocked.items():
            for variant in variants:
                cache_key = f"item_{item_type}_{variant}"
                params = {'item_type': item_type, 'item_variant': variant}
                
                # Lower priority for initial generation to not block other sprites
                sprite_manager.get_sprite(cache_key, 'item', params, priority=3)
                
        print(f"Queued initial variant generation: {sum(len(v) for v in unlocked.values())} variants")
    
    def mark_variant_available(self, item_type: str, variant: str) -> bool:
        """Mark a variant as available (sprite ready) and return True if it was newly available."""
        available = self.data.get("available_variants", {})
        if item_type not in available:
            available[item_type] = []
        
        if variant not in available[item_type]:
            available[item_type].append(variant)
            self.save_preferences()
            print(f"Variant {item_type}_{variant} is now available!")
            return True
        return False
    
    def sync_available_with_existing_sprites(self, sprite_manager):
        """Sync available variants with existing cached sprites on startup."""
        import os
        newly_available = []
        
        unlocked = self.data.get("unlocked_variants", {})
        available = self.data.get("available_variants", {})
        
        for item_type, variants in unlocked.items():
            if item_type not in available:
                available[item_type] = []
            
            for variant in variants:
                if variant not in available[item_type]:
                    # Check if sprite exists on disk
                    cache_path = f"cache/items/item_{item_type}_{variant}.png"
                    if os.path.exists(cache_path):
                        available[item_type].append(variant)
                        newly_available.append(f"{item_type}_{variant}")
        
        if newly_available:
            self.save_preferences()
            print(f"Synced {len(newly_available)} existing sprites to available variants")
        
        return newly_available
    
    def get_progress_summary(self) -> str:
        """Get a summary of current unlock progress."""
        stats = self.data["lifetime_stats"]
        unlocked = self.data["unlocked_variants"]
        definitions = self.data["variant_definitions"]
        
        weapon_progress = f"{len(unlocked['weapon'])}/{len(definitions['weapon'])} weapons"
        armor_progress = f"{len(unlocked['armor'])}/{len(definitions['armor'])} armor"
        potion_progress = f"{len(unlocked['potion'])}/{len(definitions['potion'])} potions"
        
        return f"Unlocked: {weapon_progress}, {armor_progress}, {potion_progress}"