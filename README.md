# AI-Generated Roguelike Dungeon Crawler

A roguelike dungeon crawler where all sprites, monsters, items, and effects are generated using AI at runtime.

## Features

- AI-generated sprites using DALL-E
- AI-generated monster stats and effects using OpenAI
- Level progression system
- Simple controls (arrow keys to move)
- Cached sprites for faster loading

## Setup

### Local Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

3. Run the game:
```bash
python game.py
```

### Docker Setup

1. Build the Docker image:
```bash
docker build -t ai-dungeon-crawler .
```

2. Run the container:
```bash
docker run -it --env-file .env ai-dungeon-crawler
```

Note: When running in Docker, you may need to configure X11 forwarding or use a VNC server to display the game window. The exact configuration will depend on your host operating system and display setup.

## Controls

- Arrow keys: Move player
- ESC: Quit game

## Requirements

- Python 3.8+
- OpenAI API key
- Internet connection for first-time sprite generation

## Note

The first time you run the game, it will generate all sprites using DALL-E, which may take some time. Subsequent runs will be faster as sprites are cached locally.
