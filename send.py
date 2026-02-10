import os
import asyncio
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

PROTECTED_USERNAME = "nico044047"
NUKE_GIF = "https://tenor.com/view/explosion-explode-clouds-of-smoke-gif-17216934"

# ================= STORAGE =================
welcome_channel_id: int | None = None
autoroles: set[int] = set()

# ================= MESSAGE TASKS =================
message_tasks: dict[int, asyncio.Task] = {}

async def spam_dm(member: discord.Member):
    while True:
        await member.send("🚨 Nuke activated")
        await asyncio.sleep(0.6)

# ================= READY =================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

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
    if action.lower() == "add":
        autoroles.add(role.id)
        await ctx.send(f"✅ Added {role.mention} to autoroles")
    elif action.lower() == "remove":
        autoroles.discard(role.id)
        await ctx.send(f"❌ Removed {role.mention} from autoroles")
    else:
        await ctx.send("❌ Use `?autorole add @role` or `?autorole remove @role`")

# ================= MEMBER JOIN =================
@bot.event
async def on_member_join(member: discord.Member):
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

# ================= HELP =================
@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(title="📖 Help Menu", color=discord.Color.blurple())

    embed.add_field(
        name="⚙️ Setup",
        value="`?setup #channel`",
        inline=False
    )

    embed.add_field(
        name="📜 Rules",
        value="`?send`",
        inline=False
    )

    embed.add_field(
        name="🏷️ Autorole",
        value="`?autorole add @role`\n`?autorole remove @role`",
        inline=False
    )

    embed.add_field(
        name="🔨 Moderation",
        value="`?kick @user`\n`?ban @user`",
        inline=False
    )

    embed.add_field(
        name="💀 Sudo",
        value="`$sudo help (see sudo commands)`",
        inline=False
    )

    await ctx.send(embed=embed)

# ================= SERVER INFO =================
@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild
    humans = len([m for m in guild.members if not m.bot])
    bots = len([m for m in guild.members if m.bot])

    embed = discord.Embed(
        title=f"ℹ️ Server Info — {guild.name}",
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )

    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.add_field(name="👑 Owner", value=guild.owner, inline=False)
    embed.add_field(
        name="👥 Members",
        value=f"Total: {guild.member_count}\nHumans: {humans}\nBots: {bots}",
        inline=False
    )
    embed.add_field(
        name="📅 Created",
        value=guild.created_at.strftime("%B %d, %Y"),
        inline=False
    )

    await ctx.send(embed=embed)

# ================= NORMAL MODERATION =================
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

# ================= $SUDO (UNCHANGED) =================
@bot.group(name="sudo", invoke_without_command=True)
async def sudo(ctx):
    await ctx.send("❌ access denied")

# (all your sudo subcommands remain EXACTLY the same below)

# ================= ERROR HANDLER =================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ access denied")
    elif isinstance(error, commands.CommandNotFound):
        return
    else:
        await ctx.send(f"❌ error: {error}")
        raise error

# ================= START =================
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable not set")

bot.run(TOKEN)
