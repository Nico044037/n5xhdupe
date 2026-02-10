import os
import asyncio
import random
import discord
from discord.ext import commands
from datetime import datetime

# ================= BASIC CONFIG =================
TOKEN = os.getenv("DISCORD_TOKEN")
MAIN_GUILD_ID = int(os.getenv("GUILD", "1452967364470505565"))

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix=["!", "?", "$"],
    intents=intents,
    help_command=None
)

# ================= SUDO CONFIG =================
SUDO_USERS = {
    123456789012345678  # PUT YOUR USER ID HERE
}

START_ALLOWED_USERNAME = "nico044047"

NUKE_GIF = "https://tenor.com/view/explosion-explode-clouds-of-smoke-gif-17216934"

# ================= STORAGE =================
welcome_channel_id = None
autoroles: set[int] = set()

# ================= READY =================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

# REQUIRED so prefix commands work
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await bot.process_commands(message)

# ================= RULES EMBED =================
def rules_embed():
    embed = discord.Embed(
        title="📜 Server Rules",
        color=discord.Color.red()
    )
    embed.add_field(
        name="Rules",
        value=(
            "🤝 Be respectful\n"
            "🚫 No spam\n"
            "🔞 No NSFW\n"
            "📢 No advertising\n"
            "👮 Staff decisions are final"
        ),
        inline=False
    )
    return embed

# ================= SETUP =================
@bot.command()
@commands.has_permissions(manage_guild=True)
async def setup(ctx, channel: discord.TextChannel):
    global welcome_channel_id
    welcome_channel_id = channel.id
    await ctx.send(f"✅ Welcome channel set to {channel.mention}")

# ================= SEND RULES =================
@bot.command()
async def send(ctx):
    await ctx.send(embed=rules_embed())

# ================= AUTOROLE =================
@bot.command()
@commands.has_permissions(manage_roles=True)
async def autorole(ctx, action: str, role: discord.Role):
    if action == "add":
        autoroles.add(role.id)
        await ctx.send(f"✅ Added {role.mention}")
    elif action == "remove":
        autoroles.discard(role.id)
        await ctx.send(f"❌ Removed {role.mention}")

# ================= MEMBER JOIN =================
@bot.event
async def on_member_join(member):
    if member.guild.id != MAIN_GUILD_ID:
        return

    for role_id in autoroles:
        role = member.guild.get_role(role_id)
        if role:
            await member.add_roles(role)

    if welcome_channel_id:
        channel = member.guild.get_channel(welcome_channel_id)
        if channel:
            await channel.send(f"👋 Welcome {member.mention}!")

# ================= SERVER INFO =================
@bot.command()
async def serverinfo(ctx):
    g = ctx.guild
    humans = len([m for m in g.members if not m.bot])
    bots = len([m for m in g.members if m.bot])

    embed = discord.Embed(
        title=f"ℹ️ Server Info — {g.name}",
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )

    embed.set_thumbnail(url=g.icon.url if g.icon else None)
    embed.add_field(name="👑 Owner", value=g.owner, inline=False)
    embed.add_field(
        name="👥 Members",
        value=f"Total: {g.member_count}\nHumans: {humans}\nBots: {bots}",
        inline=False
    )

    await ctx.send(embed=embed)

# ================= MODERATION =================
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member):
    await member.kick()
    await ctx.send(f"👢 Kicked {member.mention}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member):
    await member.ban()
    await ctx.send(f"🔨 Banned {member.mention}")

# ================= $SUDO =================
@bot.group(name="sudo", invoke_without_command=True)
async def sudo(ctx):
    await ctx.send("❌ access denied")

@sudo.command()
async def orbital(ctx):
    if ctx.author.id not in SUDO_USERS:
        return await ctx.send("❌ access denied")

    await ctx.send("🚀 Launching orbital strike...")
    await asyncio.sleep(2)
    await ctx.send(NUKE_GIF)
    await asyncio.sleep(2)
    await ctx.send("💥 ORBITAL STRIKE DEPLOYED 💥")

@sudo.command()
async def kill(ctx, *, pid=None):
    if ctx.author.id not in SUDO_USERS:
        return await ctx.send("❌ access denied")
    await ctx.send(f"kill: ({pid}) - No such process")

@sudo.command()
async def killall(ctx):
    if ctx.author.id not in SUDO_USERS:
        return await ctx.send("❌ access denied")
    await ctx.send("💀 Killed all processes")

@sudo.command()
async def shutdown(ctx):
    if ctx.author.id not in SUDO_USERS:
        return await ctx.send("❌ access denied")
    await ctx.send("System is going down NOW!")

@sudo.command()
async def reboot(ctx):
    if ctx.author.id not in SUDO_USERS:
        return await ctx.send("Rebooting system...")

@sudo.command()
async def rm(ctx, *, args=None):
    if ctx.author.id not in SUDO_USERS:
        return await ctx.send("❌ access denied")

    if args == "-rf /":
        await ctx.send("💀 KERNEL PANIC 💀\nSystem destroyed.")
    elif args == "virus.exe":
        await ctx.send("🗑️ virus.exe removed.")
    else:
        await ctx.send("rm: cannot remove")

@sudo.command()
async def impersonate(ctx, member: discord.Member, *, message: str):
    if ctx.author.id not in SUDO_USERS:
        return await ctx.send("❌ access denied")

    webhooks = await ctx.channel.webhooks()
    webhook = next((w for w in webhooks if w.name == "BelugaSudo"), None)
    if webhook is None:
        webhook = await ctx.channel.create_webhook(name="BelugaSudo")

    delay = min(5, max(1, len(message) // 10))
    async with ctx.channel.typing():
        await asyncio.sleep(delay)

    await webhook.send(
        content=message,
        username=member.display_name,
        avatar_url=member.display_avatar.url
    )

    await ctx.message.delete()

@sudo.command()
async def start(ctx):
    if ctx.author.name != START_ALLOWED_USERNAME:
        return await ctx.send("sudo: only nico044047 may run this command")

    await ctx.send("✔️ system started successfully")

# ================= HELP =================
@bot.command()
async def help(ctx):
    await ctx.send("""```bash
Commands

?setup #channel
?autorole add/remove
?send
?serverinfo

$SUDO:
$sudo orbital
$sudo kill <pid>
$sudo killall
$sudo rm -rf /
$sudo impersonate @user message
$sudo start
```""")

# ================= ERROR HANDLER =================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ access denied")
    elif isinstance(error, commands.CommandNotFound):
        return
    else:
        await ctx.send(f"❌ error: {error}")

# ================= START =================
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable not set")

bot.run(TOKEN)
