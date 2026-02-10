import os
import json
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

# ================= BASIC CONFIG =================
TOKEN = os.getenv("DISCORD_TOKEN")

MAIN_GUILD_ID = int(os.getenv("GUILD", "1452967364470505565"))
DATA_FILE = "data.json"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix=["!", "?", "$"],  # ← added $
    intents=intents,
    help_command=None
)

# ================= STORAGE =================
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({"welcome_channel": None, "autoroles": []}, f)

with open(DATA_FILE, "r") as f:
    data = json.load(f)

welcome_channel_id: int | None = data.get("welcome_channel")
autoroles: set[int] = set(data.get("autoroles", []))

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(
            {
                "welcome_channel": welcome_channel_id,
                "autoroles": list(autoroles)
            },
            f,
            indent=4
        )

# ================= EMBEDS =================
def rules_embed():
    embed = discord.Embed(
        title="📜 Welcome to the Server!",
        description="Please read the rules carefully ❤️",
        color=discord.Color.red()
    )

    embed.add_field(
        name="💬 Discord Rules",
        value=(
            "🤝 Be respectful\n"
            "🚫 No spamming\n"
            "🔞 No NSFW\n"
            "📢 No advertising\n"
            "⚠️ No illegal content\n"
            "👮 Staff decisions are final"
        ),
        inline=False
    )

    embed.set_footer(text="⚠️ Breaking rules may result in punishment")
    return embed

# ================= READY =================
@bot.event
async def on_ready():
    guild = discord.Object(id=MAIN_GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)
    print(f"✅ Logged in as {bot.user}")

# ================= MEMBER JOIN =================
@bot.event
async def on_member_join(member: discord.Member):
    if member.guild.id != MAIN_GUILD_ID:
        return

    await asyncio.sleep(2)

    try:
        await member.send(embed=rules_embed())
    except:
        pass

    for role_id in autoroles:
        role = member.guild.get_role(role_id)
        if role:
            try:
                await member.add_roles(role)
            except:
                pass

    if welcome_channel_id:
        channel = member.guild.get_channel(welcome_channel_id)
        if channel:
            await channel.send(
                f"👋 Welcome {member.mention}!\n"
                f"📜 Check your DMs for the rules ❤️"
            )

# ================= SETUP =================
@bot.command()
@commands.has_permissions(manage_guild=True)
async def setup(ctx, channel: discord.TextChannel):
    global welcome_channel_id
    welcome_channel_id = channel.id
    save_data()
    await ctx.send(f"✅ Welcome channel set to {channel.mention}")

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
        name="🚀 Boosts",
        value=f"Level {guild.premium_tier} ({guild.premium_subscription_count})",
        inline=False
    )
    embed.add_field(
        name="📅 Created",
        value=guild.created_at.strftime("%B %d, %Y"),
        inline=False
    )

    await ctx.send(embed=embed)

# ================= MODERATION =================
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.kick(reason=reason)
    await ctx.send(f"👢 Kicked {member.mention}\n📄 Reason: {reason}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 Banned {member.mention}\n📄 Reason: {reason}")

# ================= $SUDO =================
@bot.group(name="sudo", invoke_without_command=True)
async def sudo(ctx):
    await ctx.send("❌ Use: `$sudo kill @user [reason]`")

@sudo.command(name="kill")
@commands.has_permissions(kick_members=True)
async def sudo_kill(ctx, member: discord.Member, *, reason="No reason provided"):
    try:
        await member.kick(reason=reason)
        await ctx.send(
            f"💀 **SUDO KILL EXECUTED**\n"
            f"👢 User: {member.mention}\n"
            f"📄 Reason: {reason}"
        )
    except discord.Forbidden:
        await ctx.send("❌ I can't kick this user.")

# ================= AUTOROLE =================
@bot.command()
@commands.has_permissions(manage_roles=True)
async def autorole(ctx, action: str, role: discord.Role):
    if action.lower() == "add":
        autoroles.add(role.id)
        save_data()
        await ctx.send(f"✅ Added {role.mention} to autoroles")
    elif action.lower() == "remove":
        autoroles.discard(role.id)
        save_data()
        await ctx.send(f"❌ Removed {role.mention} from autoroles")
    else:
        await ctx.send("❌ Use: `?autorole add @role` or `?autorole remove @role`")

# ================= START =================
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable not set")

bot.run(TOKEN)