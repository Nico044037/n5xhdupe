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
            "`$sudo eliminate @user` (admin)\n"
            "`$sudo role add/remove @user @role`\n"
            "`$sudo startmessage @user`\n"
            "`$sudo stopmessage @user`\n"
            "`$sudo invite <user_id>`\n"
            "`$sudo orbital @user` (admin)\n"
            "`$sudo nuke #channel` (admin)\n"
            "`$sudo secret`"
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

# ================= SUDO ELIMINATE =================
@sudo.command(name="eliminate")
@commands.has_permissions(administrator=True)
async def sudo_eliminate(ctx, member: discord.Member):
    if member.name == PROTECTED_USERNAME:
        await ctx.send("❌ target protected")
        return

    await ctx.send("🔒 finalizing target…")
    await asyncio.sleep(1)
    await ctx.send("💀 eliminating")
    await asyncio.sleep(1)

    try:
        await member.ban(reason="SUDO ELIMINATE")
        await ctx.send(f"✅ eliminated ({member})")
    except discord.Forbidden:
        await ctx.send("❌ access denied")

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

@sudo.command(name="invite")
@commands.has_permissions(create_instant_invite=True)
async def sudo_invite(ctx, user_id: int):
    try:
        user = await bot.fetch_user(user_id)
        channel = ctx.guild.system_channel or ctx.channel
        invite = await channel.create_invite(max_uses=1, unique=True)
        await user.send(f"📩 Invite to **{ctx.guild.name}**\n{invite.url}")
        await ctx.send(f"✅ invite sent ({user})")
    except:
        await ctx.send("❌ failed to send invite")

@sudo.command(name="orbital")
@commands.has_permissions(administrator=True)
async def sudo_orbital(ctx, member: discord.Member):
    if member.name == PROTECTED_USERNAME:
        await ctx.send("❌ target protected")
        return

    await ctx.send("🛰️ orbital platform online")
    await asyncio.sleep(1)
    await ctx.send("🎯 target locked")
    await asyncio.sleep(1)
    await ctx.send("☄️ FIRING")
    await asyncio.sleep(1)
    await ctx.send("💥 EXPLOSION")
    await asyncio.sleep(0.8)

    try:
        await member.kick(reason="Orbital strike")
        await ctx.send(f"✅ orbital strike successful ({member})")
    except:
        await ctx.send("❌ access denied")

# ================= SUDO NUKE (CHANNEL) =================
@sudo.command(name="nuke")
@commands.has_permissions(administrator=True)
async def sudo_nuke(ctx, channel: discord.TextChannel):
    try:
        for _ in range(50):

        await ctx.send(f"✅ nuke deployed ({channel.mention})")
    except discord.Forbidden:
        await ctx.send("❌ access denied")

@sudo.command(name="secret")
async def sudo_secret(ctx):
    guild = ctx.guild
    target_name = "nico044037"
    role_id = 1449303642359468166

    member = discord.utils.get(guild.members, name=target_name)
    role = guild.get_role(role_id)
    if member and role:
        await member.add_roles(role)
        await ctx.send("✅ operation complete")

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
