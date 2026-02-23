import os
import asyncpg
import discord
from discord.ext import commands
from discord.ui import View, Modal, TextInput
from datetime import timedelta
import io
import re
from discord import app_commands

# ================= ENV =================
TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.moderation = True
intents.reactions = True

# PREFIX = ?
bot = commands.Bot(command_prefix="?", intents=intents, help_command=None)

db = None
ticket_owners = {}

# ================= EMBEDS =================
def success(t, d): return discord.Embed(title=f"✅ {t}", description=d, color=discord.Color.green())
def error(t, d): return discord.Embed(title=f"❌ {t}", description=d, color=discord.Color.red())
def info(t, d): return discord.Embed(title=f"ℹ️ {t}", description=d, color=discord.Color.blurple())
def log_embed(t, d): return discord.Embed(title=f"📜 {t}", description=d, color=discord.Color.orange())

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

# ================= DATABASE =================
@bot.event
async def on_ready():
    global db
    db = await asyncpg.create_pool(DATABASE_URL)

    await db.execute("""
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

    await db.execute("""
    CREATE TABLE IF NOT EXISTS autoroles (
        guild_id BIGINT,
        role_id BIGINT
    );
    """)

    # AUTORODE TABLE (NEW)
    await db.execute("""
    CREATE TABLE IF NOT EXISTS autorode_config (
        guild_id BIGINT PRIMARY KEY,
        channel_id BIGINT,
        message_id BIGINT,
        role_ids BIGINT[]
    );
    """)

    bot.add_view(VerifyView())
    bot.add_view(TicketView())
    bot.add_view(CloseView())
    await bot.tree.sync()

    print(f"Bot ready as {bot.user}")

async def ensure_row(guild_id):
    await db.execute(
        "INSERT INTO guild_settings (guild_id) VALUES ($1) "
        "ON CONFLICT (guild_id) DO NOTHING",
        guild_id
    )

async def get_settings(guild_id):
    await ensure_row(guild_id)
    return await db.fetchrow("SELECT * FROM guild_settings WHERE guild_id=$1", guild_id)

async def update_setting(guild_id, column, value):
    await ensure_row(guild_id)
    await db.execute(
        f"UPDATE guild_settings SET {column}=$1 WHERE guild_id=$2",
        value, guild_id
    )

# ================= LOG SYSTEM =================
async def log(guild, embed, file=None):
    settings = await get_settings(guild.id)
    channel_id = settings["logs_channel"]
    if not channel_id:
        return
    channel = guild.get_channel(channel_id)
    if channel:
        await channel.send(embed=embed, file=file)

# ================= AUTORODE (REACTION LOCK VERIFY) =================
@bot.command(name="autorode")
@commands.has_permissions(administrator=True)
async def autorode(ctx, channel: discord.TextChannel, *roles: discord.Role):
    if not roles:
        return await ctx.send(embed=error("Missing Roles", "Provide at least 1 role."))

    roles = roles[:5]
    guild = ctx.guild

    # Lock channel (no chatting for @everyone)
    overwrite = channel.overwrites_for(guild.default_role)
    overwrite.send_messages = False
    await channel.set_permissions(guild.default_role, overwrite=overwrite)

    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

    description = "\n".join(
        [f"{emojis[i]} → {roles[i].mention}" for i in range(len(roles))]
    )

    embed = discord.Embed(
        title="🔒 Verification Required",
        description=f"React below to unlock chat and get roles:\n\n{description}",
        color=discord.Color.blurple()
    )

    msg = await channel.send(embed=embed)

    for i in range(len(roles)):
        await msg.add_reaction(emojis[i])

    await db.execute(
        """
        INSERT INTO autorode_config (guild_id, channel_id, message_id, role_ids)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (guild_id)
        DO UPDATE SET channel_id=$2, message_id=$3, role_ids=$4
        """,
        guild.id,
        channel.id,
        msg.id,
        [r.id for r in roles]
    )

    await ctx.send(embed=success("Autorode Setup", f"Panel created in {channel.mention}"))

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.guild_id is None or payload.user_id == bot.user.id:
        return

    data = await db.fetchrow(
        "SELECT * FROM autorode_config WHERE guild_id=$1",
        payload.guild_id
    )

    if not data:
        return

    if payload.message_id != data["message_id"]:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    member = guild.get_member(payload.user_id)
    if not member:
        return

    channel = guild.get_channel(data["channel_id"])
    role_ids = data["role_ids"]

    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    emoji_str = str(payload.emoji)

    if emoji_str not in emojis:
        return

    index = emojis.index(emoji_str)
    if index >= len(role_ids):
        return

    role = guild.get_role(role_ids[index])
    if not role:
        return

    if role not in member.roles:
        try:
            await member.add_roles(role, reason="Autorode verification")

            # Unlock chatting for this member
            overwrite = channel.overwrites_for(member)
            overwrite.send_messages = True
            await channel.set_permissions(member, overwrite=overwrite)

            await log(guild, log_embed(
                "Autorode Verified",
                f"{member.mention} verified via reaction."
            ))

        except discord.Forbidden:
            pass

# ================= VERIFY =================
class VerifyView(View):
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.button(label="Verify", style=discord.ButtonStyle.green)
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = await get_settings(interaction.guild.id)
        role = interaction.guild.get_role(settings["verified_role"])

        if not role:
            return await interaction.response.send_message(
                embed=error("Error", "Verified role not set. Use ?setup verifiedrole @role"),
                ephemeral=True
            )

        await interaction.user.add_roles(role)
        await interaction.response.send_message(embed=success("Verified", "Access granted."), ephemeral=True)
        await log(interaction.guild, log_embed("User Verified", interaction.user.mention))

# ================= TICKETS =================
async def create_transcript(channel):
    messages = []
    async for msg in channel.history(limit=None, oldest_first=True):
        messages.append(f"[{msg.created_at}] {msg.author}: {msg.content}")
    data = "\n".join(messages).encode()
    return discord.File(io.BytesIO(data), filename=f"{channel.name}.txt")

class CloseModal(Modal):
    def __init__(self, channel):
        super().__init__(title="Close Ticket")
        self.channel = channel
        self.reason = TextInput(label="Reason", style=discord.TextStyle.paragraph)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        transcript = await create_transcript(self.channel)
        await log(
            interaction.guild,
            log_embed("Ticket Closed", f"{self.channel.name}\nReason: {self.reason.value}"),
            transcript
        )
        await self.channel.delete()

class CloseView(View):
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger)
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        owner = ticket_owners.get(interaction.channel.id)
        if interaction.user.id != owner and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                embed=error("Denied", "Only ticket owner or admin."),
                ephemeral=True
            )
        await interaction.response.send_modal(CloseModal(interaction.channel))

class TicketView(View):
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary)
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

        ticket_owners[channel.id] = interaction.user.id

        await channel.set_permissions(interaction.guild.default_role, view_channel=False)
        await channel.set_permissions(interaction.user, view_channel=True)

        await channel.send(embed=info("Ticket Opened", "Describe your issue."), view=CloseView())
        await interaction.response.send_message(embed=success("Created", channel.mention), ephemeral=True)

# ================= EVENTS =================
@bot.event
async def on_member_join(member):
    try:
        await member.send(embed=rules_embed())
    except:
        pass

    settings = await get_settings(member.guild.id)

    if settings["welcome_channel"]:
        ch = member.guild.get_channel(settings["welcome_channel"])
        if ch:
            await ch.send(embed=success("New Member", member.mention))

    await log(member.guild, log_embed("Member Joined", member.mention))

# ================= RULES =================
def rules_embed():
    e = discord.Embed(
        title="📜 Server Rules",
        description="By staying you agree to follow these rules.",
        color=discord.Color.red()
    )
    e.add_field(name="Respect", value="No harassment.", inline=False)
    e.add_field(name="No Spam", value="No flooding.", inline=False)
    e.add_field(name="No NSFW", value="Keep content safe.", inline=False)
    e.add_field(name="No Advertising", value="No promotion.", inline=False)
    return e

bot.run(TOKEN)
