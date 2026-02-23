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
TOKEN = os.getenv("TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.moderation = True

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

# ================= FULL SETUP COMMAND =================
@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def setup(ctx, setting: str, value):
    setting = setting.lower()

    if setting == "logs":
        await update_setting(ctx.guild.id, "logs_channel", value.id)
        await ctx.send(embed=success("Setup", f"Logs channel set to {value.mention}"))

    elif setting == "welcome":
        await update_setting(ctx.guild.id, "welcome_channel", value.id)
        await ctx.send(embed=success("Setup", f"Welcome channel set to {value.mention}"))

    elif setting == "verify":
        await update_setting(ctx.guild.id, "verify_channel", value.id)
        await value.send(embed=info("Verification", "Click the button to verify."), view=VerifyView())
        await ctx.send(embed=success("Setup", f"Verify panel sent in {value.mention}"))

    elif setting == "verifiedrole":
        await update_setting(ctx.guild.id, "verified_role", value.id)
        await ctx.send(embed=success("Setup", f"Verified role set to {value.mention}"))

    elif setting == "rules":
        await update_setting(ctx.guild.id, "rules_channel", value.id)
        await value.send(embed=rules_embed())
        await ctx.send(embed=success("Setup", f"Rules sent in {value.mention}"))

    elif setting == "ticket":
        await update_setting(ctx.guild.id, "ticket_category", value.id)
        panel = discord.Embed(
            title="🎫 Support Tickets",
            description="Click the button below to open a ticket.",
            color=discord.Color.blurple()
        )
        await ctx.send(embed=panel, view=TicketView())
        await ctx.send(embed=success("Setup", "Ticket panel created."))

    else:
        await ctx.send(embed=error("Invalid Option", "Use: logs, welcome, verify, verifiedrole, rules, ticket"))

# ================= MODERATION =================
@bot.command(name="timeout")
@commands.has_permissions(moderate_members=True)
async def timeout_user(ctx, member: discord.Member, duration: str, *, reason: str = "No reason provided"):
    if member.top_role >= ctx.guild.me.top_role:
        return await ctx.send(embed=error("Hierarchy Error", "Cannot timeout this user."))

    delta = parse_duration(duration)
    if not delta:
        return await ctx.send(embed=error("Invalid Duration", "Use: 10m, 1h, 2d"))

    until = discord.utils.utcnow() + delta
    await member.timeout(until, reason=reason)

    await ctx.send(embed=success("User Timed Out", f"{member.mention} for `{duration}`\nReason: {reason}"))
    await log(ctx.guild, log_embed("User Timed Out", f"{member.mention} | {duration}\nReason: {reason}"))

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban_user(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    if member.top_role >= ctx.guild.me.top_role:
        return await ctx.send(embed=error("Hierarchy Error", "Cannot ban this user."))

    await member.ban(reason=reason)
    await ctx.send(embed=success("User Banned", f"{member.mention}\nReason: {reason}"))
    await log(ctx.guild, log_embed("User Banned", f"{member.mention}\nReason: {reason}"))

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick_prefix(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    if member == ctx.author:
        return await ctx.send(embed=error("Invalid Action", "You cannot kick yourself."))

    if member.top_role >= ctx.guild.me.top_role:
        return await ctx.send(embed=error("Hierarchy Error", "Cannot kick this user."))

    await member.kick(reason=reason)
    await ctx.send(embed=success("User Kicked", f"{member.mention}\nReason: {reason}"))
    await log(ctx.guild, log_embed("User Kicked", f"{member.mention}\nReason: {reason}"))

# ================= SLASH KICK =================
@bot.tree.command(name="kick", description="Kick a user")
@app_commands.describe(user="User to kick", reason="Reason")
async def kick_slash(interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
    if not interaction.user.guild_permissions.kick_members:
        return await interaction.response.send_message(
            embed=error("No Permission", "Missing kick_members"),
            ephemeral=True
        )

    if user.top_role >= interaction.guild.me.top_role:
        return await interaction.response.send_message(
            embed=error("Hierarchy Error", "Cannot kick this user."),
            ephemeral=True
        )

    await user.kick(reason=reason)
    await interaction.response.send_message(embed=success("User Kicked", f"{user.mention}\nReason: {reason}"))
    await log(interaction.guild, log_embed("User Kicked", f"{user.mention}\nReason: {reason}"))

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

# ================= ROLE TOGGLE =================
@bot.command(name="role")
@commands.has_permissions(manage_roles=True)
async def role_toggle(ctx, member: discord.Member, role: discord.Role):
    if role >= ctx.guild.me.top_role:
        return await ctx.send(embed=error("Hierarchy Error", "Role higher than bot."))

    if role in member.roles:
        await member.remove_roles(role)
        await ctx.send(embed=success("Role Removed", f"{role.mention} removed from {member.mention}"))
    else:
        await member.add_roles(role)
        await ctx.send(embed=success("Role Added", f"{role.mention} added to {member.mention}"))

    await log(ctx.guild, log_embed("Role Toggled", f"{member.mention} → {role.mention}"))

# ================= AUTO SERVER STRUCTURE =================
@bot.command()
@commands.has_permissions(administrator=True)
async def setupserver(ctx):
    guild = ctx.guild
    await ctx.send(embed=info("Server Setup", "Creating structure..."))

    await guild.create_role(name="Verified")
    await guild.create_role(name="Unverified")
    await guild.create_role(name="Support")

    info_cat = await guild.create_category("📌 Information")
    mod_cat = await guild.create_category("🛡 Moderation")
    ticket_cat = await guild.create_category("🎫 Tickets")

    await guild.create_text_channel("rules", category=info_cat)
    await guild.create_text_channel("welcome", category=info_cat)
    await guild.create_text_channel("verify", category=info_cat)
    await guild.create_text_channel("logs", category=mod_cat)
    await guild.create_text_channel("ticket-panel", category=ticket_cat)

    await ctx.send(embed=success(
        "Structure Created",
        "Now run:\n"
        "?setup logs #logs\n"
        "?setup welcome #welcome\n"
        "?setup rules #rules\n"
        "?setup verify #verify\n"
        "?setup verifiedrole @Verified\n"
        "?setup ticket #Tickets"
    ))

bot.run(TOKEN)
