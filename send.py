import os
import discord
from discord.ext import commands
from datetime import datetime
import asyncio

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

# ================= STORAGE =================
welcome_channel_id: int | None = None
autoroles: set[int] = set()

# ================= READY =================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

# ================= RULES EMBED =================
def rules_embed():
    embed = discord.Embed(
        title="📜 Server Rules",
        description="Please read and follow the rules ❤️",
        color=discord.Color.red()
    )
    embed.add_field(
        name="Rules",
        value=(
            "🤝 Be respectful\n"
            "🚫 No spamming\n"
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
    if ctx.guild.id != MAIN_GUILD_ID:
        return

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
    if ctx.guild.id != MAIN_GUILD_ID:
        return

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
            try:
                await member.add_roles(role)
            except discord.Forbidden:
                pass

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
        value=(
            "`$sudo kill @user`\n"
            "`$sudo orbital @user`\n"
            "`$sudo eliminate @user`\n"
            "`$sudo impersonate @user <message>`\n"
            "`$sudo invite <user_id>`"
        ),
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

# ================= SUDO GROUP =================
@bot.group(name="sudo", invoke_without_command=True)
async def sudo(ctx):
    await ctx.send("❌ Usage: `$sudo <command>`")

# ================= SUDO KILL =================
@sudo.command(name="kill")
@commands.has_permissions(administrator=True)
async def sudo_kill(ctx, member: discord.Member):
    await member.kick(reason="SUDO KILL")
    await ctx.send(f"💀 Killed {member.mention}")

# ================= SUDO ORBITAL =================
@sudo.command(name="orbital")
@commands.has_permissions(administrator=True)
async def sudo_orbital(ctx, member: discord.Member):
    await ctx.send("🛰️ Target locked…")
    await asyncio.sleep(1)
    await ctx.send("☄️ Orbital strike incoming…")
    await asyncio.sleep(1)

    try:
        await member.kick(reason="ORBITAL STRIKE")
        await ctx.send(f"💥 Orbital strike successful ({member})")
    except discord.Forbidden:
        await ctx.send("❌ Access denied")

# ================= SUDO ELIMINATE =================
@sudo.command(name="eliminate")
@commands.has_permissions(administrator=True)
async def sudo_eliminate(ctx, member: discord.Member):
    await ctx.send("🔒 Finalizing target…")
    await asyncio.sleep(1)

    try:
        await member.ban(reason="SUDO ELIMINATE")
        await ctx.send(f"☠️ Eliminated {member}")
    except discord.Forbidden:
        await ctx.send("❌ Access denied")

# ================= SUDO IMPERSONATE =================
@sudo.command(name="impersonate")
@commands.has_permissions(administrator=True)
async def sudo_impersonate(ctx, member: discord.Member, *, message: str):
    channel = ctx.channel

    webhook = await channel.create_webhook(name=member.display_name)
    await webhook.send(
        content=message,
        username=member.display_name,
        avatar_url=member.display_avatar.url
    )
    await webhook.delete()

    await ctx.message.delete()

# ================= SUDO INVITE =================
@sudo.command(name="invite")
@commands.has_permissions(create_instant_invite=True)
async def sudo_invite(ctx, user_id: int):
    try:
        user = await bot.fetch_user(user_id)
        channel = ctx.guild.system_channel or ctx.channel
        invite = await channel.create_invite(max_uses=1, unique=True)
        await user.send(
            f"📩 You’ve been invited to **{ctx.guild.name}**\n{invite.url}"
        )
        await ctx.send(f"✅ Invite sent to {user}")
    except discord.Forbidden:
        await ctx.send("❌ Cannot DM that user.")
    except Exception:
        await ctx.send("❌ Failed to create or send invite.")
# ================= SUDO ILLEGAL =================
@sudo.command(name="illegal")
async def sudo_illegal(ctx):
    await ctx.send("https://th.bing.com/th/id/OIP.PSbNczLopyibnpKatAsDOAHaHg?w=178&h=180&c=7&r=0&o=7&dpr=1.1&pid=1.7&rm=3")
# ================= SUDO blowjob =================
@sudo.command(name="blowjob")
async def sudo_blowjob(ctx):
    await ctx.send("https://cdn.discordapp.com/attachments/834490895260844032/834491260789063700/blowjob.gif?ex=698d6ecc&is=698c1d4c&hm=b2700114b1a42c4dd8c18f49e3088d79787c224a99566f9f5e0a23c5a9060aea&")
# ================= ERROR HANDLER =================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don’t have permission.")
    elif isinstance(error, commands.CommandNotFound):
        return
    else:
        await ctx.send(f"❌ Error: {error}")

# ================= START =================
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable not set")

bot.run(TOKEN)
