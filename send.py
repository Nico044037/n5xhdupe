import os
import json
import asyncio
import discord
from discord.ext import commands
from datetime import datetime

# ================= BASIC CONFIG =================
TOKEN = os.getenv("DISCORD_TOKEN")
MAIN_GUILD_ID = int(os.getenv("GUILD", "1452967364470505565"))
DATA_FILE = "data.json"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix=["!", "?", "$"],
    intents=intents,
    help_command=None
)

# ================= STORAGE =================
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({"welcome_channel": None, "autoroles": []}, f)

with open(DATA_FILE, "r") as f:
    data = json.load(f)

welcome_channel_id = data.get("welcome_channel")
autoroles = set(data.get("autoroles", []))

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

# ================= HELP =================
@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(title="📖 Help", color=discord.Color.blurple())

    embed.add_field(
        name="Moderation",
        value="`?kick @user`\n`?ban @user`",
        inline=False
    )

    embed.add_field(
        name="Sudo",
        value=(
            "`$sudo kill @user`\n"
            "`$sudo kick @user`\n"
            "`$sudo ban @user`\n"
            "`$sudo role add @user @role`\n"
            "`$sudo role remove @user @role`\n"
            "`$sudo startmessage @user`\n"
            "`$sudo stopmessage @user`"
        ),
        inline=False
    )

    embed.add_field(name="Info", value="`?serverinfo`", inline=False)
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

# ================= $SUDO =================
@bot.group(name="sudo", invoke_without_command=True)
async def sudo(ctx):
    await ctx.send("❌ access denied")

@sudo.command(name="kill")
@commands.has_permissions(kick_members=True)
async def sudo_kill(ctx, member: discord.Member):
    await member.kick()
    await ctx.send(f"✅ killed ({member})")

@sudo.command(name="kick")
@commands.has_permissions(kick_members=True)
async def sudo_kick(ctx, member: discord.Member):
    await member.kick()
    await ctx.send(f"✅ kicked ({member})")

@sudo.command(name="ban")
@commands.has_permissions(ban_members=True)
async def sudo_ban(ctx, member: discord.Member):
    await member.ban()
    await ctx.send(f"✅ banned ({member})")

@sudo.command(name="role")
@commands.has_permissions(manage_roles=True)
async def sudo_role(ctx, action: str, member: discord.Member, role: discord.Role):
    if action.lower() == "add":
        await member.add_roles(role)
        await ctx.send(f"✅ role added ({member})")
    elif action.lower() == "remove":
        await member.remove_roles(role)
        await ctx.send(f"✅ role removed ({member})")
    else:
        await ctx.send("❌ usage: `$sudo role add/remove @user @role`")

@sudo.command(name="startmessage")
@commands.has_permissions(kick_members=True)
async def sudo_startmessage(ctx, member: discord.Member):
    if member.id in message_tasks:
        await ctx.send("❌ already running")
        return

    task = asyncio.create_task(spam_dm(member))
    message_tasks[member.id] = task
    await ctx.send(f"✅ started ({member})")

@sudo.command(name="stopmessage")
@commands.has_permissions(kick_members=True)
async def sudo_stopmessage(ctx, member: discord.Member):
    task = message_tasks.get(member.id)
    if not task:
        await ctx.send("❌ no active process")
        return

    task.cancel()
    message_tasks.pop(member.id, None)
    await ctx.send(f"✅ stopped ({member})")

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