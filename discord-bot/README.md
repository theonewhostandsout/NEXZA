# NEXZA Discord Bot (Public-Friendly)

A minimal Discord bot that forwards slash commands to an existing NEXZA backend via HTTP.
No secrets or business logic are included—this repository is safe to share publicly.

## Features
- `/ask <prompt>`: Ask NEXZA a question.
- `/note <text>`: Add a shift note (ephemeral).
- `/assign @user <task>`: Assign a task (logged to backend).
- `/summary [limit=50]`: Summarize the last N messages in the channel (NEXZA performs the summary server-side).

The bot only relays events to your backend and returns the backend's response.

## Quick Start
1. **Create a Discord application & bot**
   - https://discord.com/developers/applications → *New Application* → *Bot*.
   - Copy the **Bot Token**.
   - Under *Privileged Gateway Intents*, enable **MESSAGE CONTENT** if you need it.

2. **Create an invite URL**
   - OAuth2 → URL Generator → Scopes: `bot` and `applications.commands`.
   - Bot Permissions: `Send Messages`, `Read Message History`, `Use Slash Commands` (add more later as needed).
   - Invite the bot to your server.

3. **Configure environment**
   - Copy `.env.example` to `.env` and set values:
     ```ini
     DISCORD_TOKEN=your-bot-token-here
     NEXZA_ENDPOINT=https://your-backend.example.com/api/discord
     NEXZA_API_KEY=replace-with-shared-secret
     GUILD_ID=optional-single-guild-id-for-faster-command-sync
     ```

4. **Run locally**
   ```bash
   pip install -r requirements.txt
   python bot.py
   ```

5. **Docker (optional)**
   ```bash
   docker compose up -d
   ```

## Backend Contract (minimal)
The bot will POST JSON to `NEXZA_ENDPOINT` with a shared secret in header `X-API-Key`.

Example payloads:
- Ask:
  ```json
  { "type": "ask", "discord": { "user": "123", "channel": "456" }, "prompt": "How do I..." }
  ```
- Note:
  ```json
  { "type": "note", "discord": { "user": "123", "channel": "456" }, "text": "Front lobby clear." }
  ```
- Assign:
  ```json
  { "type": "assign", "discord": { "user": "123", "channel": "456", "assignee": "789" }, "task": "Check loading dock." }
  ```
- Summary:
  ```json
  { "type": "summary", "discord": { "user": "123", "channel": "456" }, "limit": 50 }
  ```

Expected responses:
```json
{ "ok": true, "reply": "Your answer here", "meta": { "extra": "optional" } }
```

Return a non-200 status code or `{ "ok": false, "error": "..." }` to signal failure.

## Permissions & Safety
- Keep permissions minimal; grant role/channel management only after testing.
- All secrets are environment-based; **never** commit `.env`.
- Rate limited requests and basic error backoff included.

## License
MIT (feel free to adapt).