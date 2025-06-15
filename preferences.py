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
                    return json.load(f)
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
    
    def get_random_variant(self, item_type: str) -> str:
        """Get a random unlocked variant for the given item type."""
        import random
        variants = self.get_unlocked_variants(item_type)
        return random.choice(variants) if variants else item_type
    
    def update_game_stats(self, monsters_killed: int = 0, levels_completed: int = 0, game_finished: bool = False):
        """Update lifetime statistics and check for new unlocks."""
        stats = self.data["lifetime_stats"]
        
        # Update stats
        stats["total_monsters_killed"] += monsters_killed
        stats["total_levels_completed"] += levels_completed
        if game_finished:
            stats["games_played"] += 1
        
        # Check for new unlocks
        newly_unlocked = self._check_unlocks()
        
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
    
    def get_progress_summary(self) -> str:
        """Get a summary of current unlock progress."""
        stats = self.data["lifetime_stats"]
        unlocked = self.data["unlocked_variants"]
        definitions = self.data["variant_definitions"]
        
        weapon_progress = f"{len(unlocked['weapon'])}/{len(definitions['weapon'])} weapons"
        armor_progress = f"{len(unlocked['armor'])}/{len(definitions['armor'])} armor"
        potion_progress = f"{len(unlocked['potion'])}/{len(definitions['potion'])} potions"
        
        return f"Unlocked: {weapon_progress}, {armor_progress}, {potion_progress}"