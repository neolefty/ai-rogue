# AI Rogue - Project Context for Claude

This document provides context for AI assistants working on this project.

## Project Overview
AI Rogue is a fast-paced dungeon crawler that demonstrates AI integration by dynamically generating sprites and monster stats using OpenAI's APIs. It showcases AI capabilities through real-time content generation.

## Core Architecture
**Modular design with clean separation of concerns:**
- `game.py` - Main game loop and event handling
- `entities.py` - Entity hierarchy with MonsterRenderInfo for visual scaling
- `combat.py` - Multi-target combat with damage falloff and danger-based loot rewards
- `ai_behavior.py` - Three-zone monster AI with clustering/dispersion
- `rendering.py` - Visual rendering and UI with effect circles
- `game_state.py` - Game data management with optimized save format (98.4% smaller)
- `sprite_manager.py` - Background sprite generation with threading
- `preferences.py` - Progression system with 12 variant types per item

## Key Systems

### Combat & Balance
- **Fast-paced tactical gameplay**: Player 5+armor HP, 0.5s attacks; Monsters HP=level, 1s attacks
- **Multi-target damage falloff**: 1st target full damage, 2nd ½, 3rd ⅓, etc.
- **Danger-based loot rewards**: One-shot monsters (damage ≥ player health) drop 10 loot, mini-bosses drop 3

### Visual Systems
- **Dynamic monster scaling**: Based on hits-to-kill relative to player damage
  - Low-level (≤2 hits): 60% size, Mid-level (3-4 hits): 75% size
  - Regular (≥5 hits): 100% size, Mini-bosses: 150% size
- **Effect circles**: Colorblind-friendly combat state indicators (red=damaged, cyan=attacking, green=ready, gray=cooldown)
- **Level indicators**: Hidden for 1-hit monsters, translucent for others

### AI & Generation
- **Background sprite generation**: DALL-E 3 with specialized prompts, threading with placeholders
- **Monster AI**: Three behavior zones (aggressive ≤150px, alert ≤300px, passive)
- **Progression system**: 12 variants each for weapons/armor/potions, unlocked by gameplay

### Save System
- **Optimized format**: 98.4% size reduction (inventory counts vs individual items)
- **Backward compatibility**: Supports both v1.0 (legacy) and v2.0 (optimized) formats
- **Essential data preserved**: All monster positions, loot, game state maintained

## Technical Stack
- **Python 3.13.2** with pygame 2.6.1
- **OpenAI Python Client 1.86.0** for DALL-E/GPT integration
- **Threading**: Background sprite generation with placeholder system

## Development Notes
- **Monster scaling**: Uses MonsterRenderInfo class for centralized calculations
- **Sprite prompts**: Keep simple and specific to avoid complex generation
- **AI stats**: Generated stats are visual only; gameplay uses balanced formulas
- **Testing**: Verify sprite generation, AI behavior, and threading stability

## Cache Structure
- `cache/sprites/`: Player and stairway sprites
- `cache/monsters/`: Monster sprites by level
- `cache/items/`: Item sprites with variant-specific prompts