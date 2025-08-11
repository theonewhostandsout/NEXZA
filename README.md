# NEXZA Backend + Discord Bot

This bundle contains:
- `backend/` — Flask server with `/chat` and `/api/discord` endpoints.
- `discord-bot/` — Discord slash-command bot that calls `backend /api/discord`.

## Quick start

### Backend
1. `cd backend`
2. `python -m venv venv && source venv/bin/activate` (Windows: `venv\Scripts\activate`)
3. `pip install -r requirements.txt` (if present) or `pip install flask flask-cors flask-limiter python-dotenv requests`
4. Copy `.env.example` to `.env` and set `DISCORD_SHARED_KEY`.
5. `python app.py`

### Discord Bot
1. `cd discord-bot`
2. Copy `.env.example` to `.env` and set `DISCORD_TOKEN`, `NEXZA_ENDPOINT`, `NEXZA_API_KEY` (must match backend `DISCORD_SHARED_KEY`).
3. `pip install -r requirements.txt`
4. `python bot.py`

## Endpoint contract

`POST /api/discord` accepts either:
- `{ "type": "ask", "prompt": "...", "discord": {"user":"<id>","channel":"<id>"} }`
- `{ "message": "...", "session_id": "...", "persona": "..." }`

Returns:
`{ "ok": true, "reply": "<text>", "session_id": "<id>" }`