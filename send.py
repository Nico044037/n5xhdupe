import os
import discord
import aiohttp
from discord.ext import commands
from datetime import datetime

# ================= BASIC CONFIG =================
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix=["!", "?", "$"],
    intents=intents,
    help_command=None
)

# ================= READY =================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

# ================= HELP =================
@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(title="📖 Help Menu", color=discord.Color.blurple())

    embed.add_field(name="Moderation",
                    value="`?kick @user`\n`?ban @user`\n`?role @user @role`",
                    inline=False)

    embed.add_field(name="Minecraft",
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

    if role >= ctx.guild.me.top_role:
        return await ctx.send("❌ I cannot manage that role.")

    embed = discord.Embed(color=discord.Color.blurple())
    embed.set_footer(text=f"Moderator: {ctx.author}",
                     icon_url=ctx.author.display_avatar.url)
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

        embed.description = (
            f"**Member:** {member.mention}\n"
            f"**Role:** {role.mention}"
        )

        await ctx.send(embed=embed)

    except discord.Forbidden:
        await ctx.send("❌ I don’t have permission to manage that role.")

# ================= SUDO GROUP (FIXED) =================
@bot.group(name="sudo")
async def sudo(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(
            "⚠️ Subcommands: info"
        )

# ================= SUDO INFO =================
@sudo.command(name="info")
@commands.has_permissions(administrator=True)
async def sudo_info(ctx, mc_username: str):

    await ctx.send("🔎 Fetching Minecraft data...")

    try:
        async with aiohttp.ClientSession() as session:

            # ===== GET UUID =====
            async with session.get(
                f"https://api.mojang.com/users/profiles/minecraft/{mc_username}"
            ) as response:

                if response.status != 200:
                    return await ctx.send(
                        f"❌ No Minecraft account found for `{mc_username}`."
                    )

                data = await response.json()
                uuid_raw = data.get("id")

                if not uuid_raw:
                    return await ctx.send("❌ Invalid Mojang response.")

                uuid = (
                    f"{uuid_raw[:8]}-"
                    f"{uuid_raw[8:12]}-"
                    f"{uuid_raw[12:16]}-"
                    f"{uuid_raw[16:20]}-"
                    f"{uuid_raw[20:]}"
                )

            # ===== NAME HISTORY =====
            async with session.get(
                f"https://api.mojang.com/user/profiles/{uuid_raw}/names"
            ) as history_response:

                name_history = "Unknown"
                creation_date = "Unknown"

                if history_response.status == 200:
                    history_data = await history_response.json()

                    names = []
                    timestamps = []

                    for entry in history_data:
                        names.append(entry.get("name", "Unknown"))
                        if "changedToAt" in entry:
                            timestamps.append(entry["changedToAt"])

                    name_history = "\n".join(names)

                    if timestamps:
                        earliest = min(timestamps)
                        creation_date = datetime.utcfromtimestamp(
                            earliest / 1000
                        ).strftime("%Y-%m-%d")

        # ===== RENDERS =====
        head_render = f"https://mc-heads.net/head/{uuid}"
        body_render = f"https://mc-heads.net/body/{uuid}"
        namemc_link = f"https://namemc.com/profile/{uuid}"

        embed = discord.Embed(
            title="🎮 Minecraft Account Info",
            color=discord.Color.green()
        )

        embed.add_field(name="Username", value=mc_username, inline=False)
        embed.add_field(name="UUID", value=uuid, inline=False)
        embed.add_field(name="Approx. Creation Date",
                        value=creation_date,
                        inline=False)
        embed.add_field(name="Name History",
                        value=name_history,
                        inline=False)

        embed.set_thumbnail(url=head_render)
        embed.set_image(url=body_render)

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(label="Open NameMC",
                              url=namemc_link)
        )

        await ctx.send(embed=embed, view=view)

    except Exception as e:
        await ctx.send(f"❌ Unexpected error: `{str(e)}`")

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
    raise RuntimeError("DISCORD_TOKEN not set")

bot.run(TOKEN)
