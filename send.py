import os
import discord
import aiohttp
import re
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

    embed.add_field(name="⚙️ Setup", value="`?setup #channel`", inline=False)
    embed.add_field(name="📜 Rules", value="`?send`", inline=False)
    embed.add_field(name="🏷️ Autorole",
                    value="`?autorole add @role`\n`?autorole remove @role`",
                    inline=False)
    embed.add_field(name="🔨 Moderation",
                    value="`?kick @user`\n`?ban @user`",
                    inline=False)
    embed.add_field(name="🎮 Minecraft",
                    value="`$sudo info <username>`",
                    inline=False)

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

# ================= ROLE TOGGLE =================
@bot.command()
@commands.has_permissions(manage_roles=True)
async def role(ctx, member: discord.Member, role: discord.Role):
    if ctx.guild.id != MAIN_GUILD_ID:
        return

    if role >= ctx.guild.me.top_role:
        return await ctx.send("❌ I cannot manage that role.")

    embed = discord.Embed(color=discord.Color.blurple())
    embed.set_footer(text=f"Moderator: {ctx.author}", icon_url=ctx.author.display_avatar.url)
    embed.timestamp = datetime.utcnow()

    try:
        if role in member.roles:
            await member.remove_roles(role)
            embed.title = "Role Removed"
            embed.color = discord.Color.red()
        else:
            await member.add_roles(role)
            embed.title = "Role Added"
            embed.color = discord.Color.green()

        embed.description = f"**Member:** {member.mention}\n**Role:** {role.mention}"
        await ctx.send(embed=embed)

    except discord.Forbidden:
        await ctx.send("❌ I don’t have permission to manage that role.")

# ================= SUDO GROUP =================
@bot.group(name="sudo", invoke_without_command=True)
async def sudo(ctx):
    await ctx.send("❌ Usage: `$sudo <command>`")

# ================= SUDO INFO (NameMC Scraper) =================
@sudo.command(name="info")
@commands.has_permissions(administrator=True)
async def sudo_info(ctx, mc_username: str):

    url = f"https://namemc.com/profile/{mc_username}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                return await ctx.send("❌ Could not fetch NameMC profile.")

            html = await response.text()

    uuid_match = re.search(
        r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
        html
    )

    if not uuid_match:
        return await ctx.send("❌ Could not find UUID on NameMC.")

    uuid = uuid_match.group(1)

    names = re.findall(r'/search\?q=([A-Za-z0-9_]+)"', html)
    name_history = "\n".join(dict.fromkeys(names))

    first_seen_match = re.search(
        r"First seen.*?(\d{4}-\d{2}-\d{2})",
        html
    )

    first_seen = first_seen_match.group(1) if first_seen_match else "Unknown"

    head_render = f"https://mc-heads.net/head/{uuid}"
    body_render = f"https://mc-heads.net/body/{uuid}"

    embed = discord.Embed(
        title="🎮 Minecraft Account (NameMC)",
        color=discord.Color.green()
    )

    embed.add_field(name="Username", value=mc_username, inline=False)
    embed.add_field(name="UUID", value=uuid, inline=False)
    embed.add_field(name="First Seen", value=first_seen, inline=False)
    embed.add_field(
        name="Name History",
        value=name_history if name_history else "No history found",
        inline=False
    )

    embed.set_thumbnail(url=head_render)
    embed.set_image(url=body_render)

    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Open NameMC", url=url))

    await ctx.send(embed=embed, view=view)

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
