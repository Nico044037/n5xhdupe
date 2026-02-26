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

bot = commands.Bot(command_prefix="?", intents=intents, help_command=None)

db = None
ticket_owners = {}

# ================= EMBEDS =================
def success(t, d): return discord.Embed(title=f"✅ {t}", description=d, color=discord.Color.green())
def error(t, d): return discord.Embed(title=f"❌ {t}", description=d, color=discord.Color.red())
def info(t, d): return discord.Embed(title=f"ℹ️ {t}", description=d, color=discord.Color.blurple())
def log_embed(t, d): return discord.Embed(title=f"📜 {t}", description=d, color=discord.Color.orange())
# ================= BREAD COMMAND =================
@bot.command(name="bread")
async def bread(ctx):
    await ctx.send("https://tenor.com/view/falling-toast-live-toast-reaction-toast-dies-gif-7238761997416289033")


@bot.command(name="banana")
async def banana(ctx):
    await ctx.send("https://tenor.com/view/dancing-banana-gif-gif-5720216842034688392")
@bot.command()
@commands.has_permissions(administrator=True)
async def roleeveryone(ctx, role: discord.Role):
    """Give a role to everyone in the server: ?roleeveryone @role"""
    
    await ctx.send(f"Adding {role.name} to everyone... This may take a while.")

    success = 0
    failed = 0

    for member in ctx.guild.members:
        if role not in member.roles:
            try:
                await member.add_roles(role, reason="Roleeveryone command used")
                success += 1
            except discord.Forbidden:
                failed += 1
            except discord.HTTPException:
                failed += 1

    await ctx.send(f"Done! ✅\nGiven role to {success} members.\nFailed: {failed}")
# ================= TEST COMMAND =================
@bot.command()
async def ping(ctx):
    await ctx.send("Pong! Bot is running.")
# ================= MODERATION COMMANDS =================
@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban_member(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    if not ctx.guild.me.guild_permissions.ban_members:
        return await ctx.send(embed=error("Permission Error", "I need Ban Members permission."))

    if member.top_role >= ctx.guild.me.top_role:
        return await ctx.send(embed=error("Hierarchy Error", "User role is higher than mine."))

    try:
        await member.ban(reason=reason)
        await ctx.send(embed=success("User Banned", f"{member.mention} has been banned.\nReason: {reason}"))
        await log(ctx.guild, log_embed("User Banned", f"{member} was banned by {ctx.author}\nReason: {reason}"))
    except discord.Forbidden:
        await ctx.send(embed=error("Forbidden", "I cannot ban this user due to role hierarchy."))


@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick_member(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    if not ctx.guild.me.guild_permissions.kick_members:
        return await ctx.send(embed=error("Permission Error", "I need Kick Members permission."))

    if member.top_role >= ctx.guild.me.top_role:
        return await ctx.send(embed=error("Hierarchy Error", "User role is higher than mine."))

    try:
        await member.kick(reason=reason)
        await ctx.send(embed=success("User Kicked", f"{member.mention} has been kicked.\nReason: {reason}"))
        await log(ctx.guild, log_embed("User Kicked", f"{member} was kicked by {ctx.author}\nReason: {reason}"))
    except discord.Forbidden:
        await ctx.send(embed=error("Forbidden", "I cannot kick this user due to role hierarchy."))


@bot.command(name="timeout")
@commands.has_permissions(moderate_members=True)
async def timeout_member(ctx, member: discord.Member, duration: str, *, reason: str = "No reason provided"):
    if not ctx.guild.me.guild_permissions.moderate_members:
        return await ctx.send(embed=error("Permission Error", "I need Moderate Members permission."))

    if member.top_role >= ctx.guild.me.top_role:
        return await ctx.send(embed=error("Hierarchy Error", "User role is higher than mine."))

    delta = parse_duration(duration)
    if not delta:
        return await ctx.send(embed=error("Invalid Duration", "Use formats like 10s, 5m, 2h, 1d"))

    try:
        await member.timeout(delta, reason=reason)
        await ctx.send(embed=success(
            "User Timed Out",
            f"{member.mention} has been timed out for `{duration}`.\nReason: {reason}"
        ))
        await log(
            ctx.guild,
            log_embed("User Timed Out", f"{member} timed out by {ctx.author}\nDuration: {duration}\nReason: {reason}")
        )
    except discord.Forbidden:
        await ctx.send(embed=error("Forbidden", "I cannot timeout this user due to role hierarchy."))
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
    print("Starting bot...")

    if DATABASE_URL:
        try:
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
            print("Database connected.")
        except Exception as e:
            print(f"Database failed: {e}")
            db = None
    else:
        print("No DATABASE_URL provided. Running without database.")

    bot.add_view(VerifyView())
    bot.add_view(TicketView())
    bot.add_view(CloseView())

    try:
        await bot.tree.sync()
    except Exception as e:
        print(f"Slash sync error: {e}")

    print(f"Bot ready as {bot.user}")

async def ensure_row(guild_id):
    if not db:
        return
    await db.execute(
        "INSERT INTO guild_settings (guild_id) VALUES ($1) ON CONFLICT (guild_id) DO NOTHING",
        guild_id
    )

async def get_settings(guild_id):
    if not db:
        return None
    await ensure_row(guild_id)
    return await db.fetchrow("SELECT * FROM guild_settings WHERE guild_id=$1", guild_id)

async def update_setting(guild_id, column, value):
    if not db:
        return
    await ensure_row(guild_id)
    await db.execute(
        f"UPDATE guild_settings SET {column}=$1 WHERE guild_id=$2",
        value, guild_id
    )

# ================= LOG SYSTEM =================
async def log(guild, embed, file=None):
    settings = await get_settings(guild.id)
    if not settings:
        return
    channel_id = settings["logs_channel"]
    if not channel_id:
        return
    channel = guild.get_channel(channel_id)
    if channel:
        await channel.send(embed=embed, file=file)

# ================= VERIFY =================
class VerifyView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Verify", style=discord.ButtonStyle.green)
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = await get_settings(interaction.guild.id)
        if not settings:
            return await interaction.response.send_message(
                embed=error("Error", "Database not configured."),
                ephemeral=True
            )

        role = interaction.guild.get_role(settings["verified_role"])

        if not role:
            return await interaction.response.send_message(
                embed=error("Error", "Verified role not set. Use ?setup verifiedrole @role"),
                ephemeral=True
            )

        try:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(
                embed=success("Verified", "Access granted."),
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error("Permission Error", "Move my bot role above the verified role."),
                ephemeral=True
            )

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
    def __init__(self):
        super().__init__(timeout=None)

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
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary)
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = await get_settings(interaction.guild.id)
        if not settings:
            return await interaction.response.send_message(
                embed=error("Error", "Database not configured."),
                ephemeral=True
            )

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
        await interaction.response.send_message(
            embed=success("Created", channel.mention),
            ephemeral=True
        )

# ================= ROLE TOGGLE =================
@bot.command(name="role")
@commands.has_permissions(manage_roles=True)
async def role_toggle(ctx, member: discord.Member, role: discord.Role):
    if not ctx.guild.me.guild_permissions.manage_roles:
        return await ctx.send(embed=error("Permission Error", "I need Manage Roles permission."))

    if role >= ctx.guild.me.top_role:
        return await ctx.send(embed=error("Hierarchy Error", "Role is higher than my top role."))

    if member.top_role >= ctx.guild.me.top_role:
        return await ctx.send(embed=error("Hierarchy Error", "User role is higher than mine."))

    try:
        if role in member.roles:
            await member.remove_roles(role)
            await ctx.send(embed=success("Role Removed", f"{role.mention} removed from {member.mention}"))
        else:
            await member.add_roles(role)
            await ctx.send(embed=success("Role Added", f"{role.mention} added to {member.mention}"))
    except discord.Forbidden:
        await ctx.send(embed=error("Forbidden", "Move my bot role above the target role."))

# ================= ERROR HANDLER =================
@bot.event
async def on_command_error(ctx, exc):
    if isinstance(exc, commands.MissingPermissions):
        await ctx.send(embed=error("No Permission", "You need Manage Roles permission."))
    elif isinstance(exc, commands.MissingRequiredArgument):
        await ctx.send(embed=error("Usage", "Correct usage: ?role @user @role"))
    elif isinstance(exc, commands.BadArgument):
        await ctx.send(embed=error("Invalid Argument", "Mention a valid user and role."))
    else:
        await ctx.send(embed=error("Error", str(exc)))

bot.run(TOKEN)
