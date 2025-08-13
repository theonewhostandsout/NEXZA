# bot.py
import os
import json
import requests
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

# --------- ENV ---------
load_dotenv()
DISCORD_TOKEN   = os.getenv("DISCORD_TOKEN")            # REQUIRED
NEXZA_ENDPOINT  = os.getenv("NEXZA_ENDPOINT", "http://localhost:5000/api/discord?interface=discord")
NEXZA_API_KEY   = os.getenv("NEXZA_API_KEY", "")
GUILD_ID_STR    = os.getenv("GUILD_ID", "").strip()     # optional but recommended
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "25"))

if not DISCORD_TOKEN:
    raise SystemExit("Missing DISCORD_TOKEN in .env")

# --------- DISCORD CLIENT ---------
intents = discord.Intents.default()
# message_content not required for slash commands; leave False for fewer perms
intents.message_content = False

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree  # single command tree ONLY

def _headers():
    return {
        "Content-Type": "application/json",
        "X-API-Key": NEXZA_API_KEY,
        "X-Client": "discord",
    }

def call_backend(payload: dict) -> dict:
    r = requests.post(NEXZA_ENDPOINT, headers=_headers(),
                      data=json.dumps(payload), timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()

# --------- SLASH COMMANDS ---------
@tree.command(name="ask", description="Ask NEXZA a question")
@app_commands.describe(prompt="Your question or request")
async def ask_cmd(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer(thinking=True)
    data = call_backend({
        "type": "ask",
        "discord": {"user": str(interaction.user.id), "channel": str(interaction.channel.id)},
        "prompt": prompt
    })
    reply = data.get("reply", "(no reply)")
    # split long messages
    for i in range(0, len(reply) or 1, 1900):
        await interaction.followup.send(reply[i:i+1900])

@tree.command(name="note", description="Add a shift note (ephemeral)")
@app_commands.describe(text="Note text")
async def note_cmd(interaction: discord.Interaction, text: str):
    await interaction.response.defer(ephemeral=True)
    data = call_backend({
        "type": "note",
        "discord": {"user": str(interaction.user.id), "channel": str(interaction.channel.id)},
        "text": text
    })
    await interaction.followup.send("Saved." if data.get("ok", True) else "Failed.", ephemeral=True)

@tree.command(name="assign", description="Assign a task to a member")
@app_commands.describe(user="Assignee", task="Task details")
async def assign_cmd(interaction: discord.Interaction, user: discord.Member, task: str):
    await interaction.response.defer(thinking=True)
    data = call_backend({
        "type": "assign",
        "discord": {
            "user": str(interaction.user.id),
            "channel": str(interaction.channel.id),
            "assignee": str(user.id)
        },
        "task": task
    })
    await interaction.followup.send(data.get("reply", f"Assigned to {user.mention}: {task}"))

@tree.command(name="summary", description="Summarize last N messages (server-side)")
@app_commands.describe(limit="How many messages to include (5-200)")
async def summary_cmd(interaction: discord.Interaction, limit: app_commands.Range[int, 5, 200]=50):
    await interaction.response.defer(thinking=True)
    data = call_backend({
        "type": "summary",
        "discord": {"user": str(interaction.user.id), "channel": str(interaction.channel.id)},
        "limit": int(limit)
    })
    await interaction.followup.send(data.get("reply", "(no summary)"))

# --------- SYNC COMMANDS ON STARTUP ---------
@bot.event
async def on_ready():
    try:
        # Global sync (can take time to propagate)
        g = await tree.sync()
        print(f"[SYNC] Global commands: {len(g)}")

        # Guild sync (instant)
        if GUILD_ID_STR:
            guild = discord.Object(id=int(GUILD_ID_STR))
            tree.copy_global_to(guild=guild)
            gg = await tree.sync(guild=guild)
            print(f"[SYNC] Guild({GUILD_ID_STR}) commands: {len(gg)}")

        print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    except Exception as e:
        print("[SYNC ERROR]", e)

# --------- RUN ---------
bot.run(DISCORD_TOKEN)
