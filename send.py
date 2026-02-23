import os
import asyncpg
import discord
from discord.ext import commands
from discord.ui import View, Modal, TextInput
from datetime import timedelta
import io
import re
from discord import app_commands

# ================= ENV (RAILWAY SAFE) =================
TOKEN = os.getenv("TOKEN") or os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not TOKEN:
    raise RuntimeError("Bot token not found. Set TOKEN or DISCORD_TOKEN in Railway variables.")

# ================= INTENTS =================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.moderation = True

# ================= BOT CLASS (FIXED) =================
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="?", intents=intents, help_command=None)
        self.db: asyncpg.Pool | None = None
        self.ticket_owners = {}

    async def setup_hook(self):
        """Runs ONCE at startup (correct place for DB + persistent views)"""
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not set in Railway variables.")

        # Create ONE pool only (Railway optimized)
        self.db = await asyncpg.create_pool(
            dsn=DATABASE_URL,
            min_size=1,
            max_size=5,
            command_timeout=60
        )

        # Create tables safely
        await self.db.execute("""
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id BIGINT PRIMARY KEY,
            welcome_channel BIGINT,
            verify_channel BIGINT,
            verified_role BIGINT,
            logs_channel BIGINT,
            rules_channel BIGINT,
            ticket_category BIGINT
        );
        """)

        await self.db.execute("""
        CREATE TABLE IF NOT EXISTS autoroles (
            guild_id BIGINT,
            role_id BIGINT
        );
        """)

        # Persistent Views (MUST be here, not on_ready)
        self.add_view(VerifyView())
        self.add_view(TicketView())
        self.add_view(CloseView())

        await self.tree.sync()
        print("🌐 Database connected & views loaded.")

bot = MyBot()

# ================= EMBEDS =================
def success(t, d): return discord.Embed(title=f"✅ {t}", description=d, color=discord.Color.green())
def error(t, d): return discord.Embed(title=f"❌ {t}", description=d, color=discord.Color.red())
def info(t, d): return discord.Embed(title=f"ℹ️ {t}", description=d, color=discord.Color.blurple())
def log_embed(t, d): return discord.Embed(title=f"📜 {t}", description=d, color=discord.Color.orange())

# ================= READY =================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")

# ================= DURATION PARSER =================
def parse_duration(duration: str):
    match = re.match(r"(\d+)([smhd])", duration.lower())
    if not match:
        return None
    value, unit = int(match.group(1)), match.group(2)
    if unit == "s": return timedelta(seconds=value)
    if unit == "m": return timedelta(minutes=value)
    if unit == "h": return timedelta(hours=value)
    if unit == "d": return timedelta(days=value)
    return None

# ================= DATABASE HELPERS (FIXED) =================
async def ensure_row(guild_id: int):
    await bot.db.execute(
        "INSERT INTO guild_settings (guild_id) VALUES ($1) ON CONFLICT (guild_id) DO NOTHING",
        guild_id
    )

async def get_settings(guild_id: int):
    await ensure_row(guild_id)
    return await bot.db.fetchrow(
        "SELECT * FROM guild_settings WHERE guild_id=$1",
        guild_id
    )

async def update_setting(guild_id: int, column: str, value: int):
    await ensure_row(guild_id)
    await bot.db.execute(
        f"UPDATE guild_settings SET {column}=$1 WHERE guild_id=$2",
        value, guild_id
    )

# ================= LOG SYSTEM =================
async def log(guild, embed, file=None):
    settings = await get_settings(guild.id)
    if not settings or not settings["logs_channel"]:
        return

    channel = guild.get_channel(settings["logs_channel"])
    if channel:
        await channel.send(embed=embed, file=file)

# ================= VERIFY VIEW =================
class VerifyView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Verify", style=discord.ButtonStyle.green, custom_id="verify_button")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = await get_settings(interaction.guild.id)
        role = interaction.guild.get_role(settings["verified_role"])

        if not role:
            return await interaction.response.send_message(
                embed=error("Error", "Verified role not set. Use ?setup verifiedrole @role"),
                ephemeral=True
            )

        await interaction.user.add_roles(role)
        await interaction.response.send_message(
            embed=success("Verified", "Access granted."),
            ephemeral=True
        )
        await log(interaction.guild, log_embed("User Verified", interaction.user.mention))

# ================= TICKET VIEW =================
class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary, custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = await get_settings(interaction.guild.id)
        category = interaction.guild.get_channel(settings["ticket_category"])

        if not category:
            return await interaction.response.send_message(
                embed=error("Not Setup", "Use ?setup ticket #category"),
                ephemeral=True
            )

        channel = await interaction.guild.create_text_channel(
            f"ticket-{interaction.user.name}",
            category=category
        )

        bot.ticket_owners[channel.id] = interaction.user.id

        await channel.set_permissions(interaction.guild.default_role, view_channel=False)
        await channel.set_permissions(interaction.user, view_channel=True)

        await channel.send(embed=info("Ticket Opened", "Describe your issue."), view=CloseView())
        await interaction.response.send_message(
            embed=success("Created", channel.mention),
            ephemeral=True
        )

# ================= RUN (RAILWAY SAFE) =================
if __name__ == "__main__":
    bot.run(TOKEN)
