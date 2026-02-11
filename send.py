import os
import discord
import aiohttp
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
    embed.add_field(name="💀 Sudo",
                    value="`$sudo kill`\n`$sudo orbital`\n`$sudo eliminate`\n"
                          "`$sudo impersonate`\n`$sudo invite`\n"
                          "`$sudo info <mc_user>`",
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

# ================= SUDO GROUP =================
@bot.group(name="sudo", invoke_without_command=True)
async def sudo(ctx):
    await ctx.send("❌ Usage: `$sudo <command>`")

# ================= SUDO INFO (UUID + NAME HISTORY) =================
@sudo.command(name="info")
@commands.has_permissions(administrator=True)
async def sudo_info(ctx, mc_username: str):

    async with aiohttp.ClientSession() as session:

        async with session.get(
            f"https://api.mojang.com/users/profiles/minecraft/{mc_username}"
        ) as response:

            if response.status != 200:
                return await ctx.send(f"❌ No Minecraft account found for `{mc_username}`.")

            data = await response.json()
            uuid_raw = data["id"]

            formatted_uuid = (
                f"{uuid_raw[:8]}-"
                f"{uuid_raw[8:12]}-"
                f"{uuid_raw[12:16]}-"
                f"{uuid_raw[16:20]}-"
                f"{uuid_raw[20:]}"
            )

        async with session.get(
            f"https://api.mojang.com/user/profiles/{uuid_raw}/names"
        ) as history_response:

            history_data = await history_response.json()
            name_history = "\n".join([entry["name"] for entry in history_data])

        embed = discord.Embed(
            title="🎮 Minecraft Account Info",
            color=discord.Color.green()
        )

        embed.add_field(name="Username", value=mc_username, inline=False)
        embed.add_field(name="UUID", value=formatted_uuid, inline=False)
        embed.add_field(
            name="Name History",
            value=name_history if name_history else "No previous names",
            inline=False
        )

        await ctx.send(embed=embed)

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
