# Discord Spotify AI Detect

A Discord bot that monitors members' Spotify activity and notifies them via DM when they're listening to artists listed on [souloverai.com](https://souloverai.com) as potential AI-generated music artists.

## What it does

- Watches all guilds it's on for member Spotify listening activity
- Checks artists against the [Soul Over AI](https://souloverai.com/) database
- Sends DMs to notify users about potential AI artists
- Updates the AI music catalogue regularly
- Tracks total incidents reported (only a number)
- When each artist was detected for teh first time and how often it was detected over all

There is **no logging of listening data** beside logging failed message delivery attempts if an AI artist was detected and the message couldn't be delivered.
In this case your username + id and the artist you were listening to are logged (with a timestamp).

**Note:** This bot is not affiliated with the Soul Over AI project. It's a community tool that uses their public database.

## Setup

1. Create a virtual environment (optional but recommended):
```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set your Discord bot token:
```bash
export TOKEN="your-discord-bot-token"
```

4. Run the bot:
```bash
python3 -m discord_bot
```

Or install as an editable package:
```bash
python3 -m pip install -e .
discord-bot
```

## Configuration

Required environment variables:
- `TOKEN` - Your Discord bot token

Optional environment variables:
- `PREFIX` - Command prefix (default: `"b!"`)
- `ACTIVITY_NAME` - Bot activity status (default: `"{PREFIX}help"`)

## Intents

The bot requires privileged gateway intents (Member Intents) to monitor Spotify activity. Enable them in the [Discord Developer Portal](https://discord.com/developers/applications) under your application's Bot settings.

## Commands

- `/about` - Display information about the bot

## License

This bot aims to operate under the licensing terms of [Soul Over AI](https://github.com/xoundbyte/soul-over-ai/blob/main/LICENSE.md).

The bot itself is licensed under MIT.

## AI Disclosure
I used AI to accelerate parts of the development process.
Everything in this Repo was audited by myself, I only accept (AI) changes manually.

I know, it's funny that a tool against AI music written with the aid of AI.

But I don't feel about code the same way I feel about music, which is strange, especially because code affects me even more... do with this standpoint whatever you think.

I'm happy if you use my bot/ tool, but I can (somewhat) understand if it's a dealbreaker for you. No hard feelings!
