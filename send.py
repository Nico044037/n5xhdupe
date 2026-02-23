import os
import discord
from discord.ext import commands

# ================= TOKEN (RAILWAY VARIABLE MUST BE: TOKEN) =================
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError("TOKEN environment variable is not set! Add TOKEN in Railway variables.")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # REQUIRED for roles
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Stores panel data (simple memory)
autorole_config = {}

EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

# ================= READY =================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    print("Bot is ready.")

# ================= AUTOROLE COMMAND =================
@bot.command(name="autorole")
@commands.has_permissions(administrator=True)
async def autorole(ctx, channel: discord.TextChannel, *roles: discord.Role):
    if not roles:
        await ctx.send("❌ You must provide at least one role.")
        return

    roles = roles[:5]  # max 5 roles
    guild = ctx.guild

    print(f"Setting autorole in {channel.name} with roles {[r.name for r in roles]}")

    # Lock channel for @everyone (no chat)
    try:
        overwrite = channel.overwrites_for(guild.default_role)
        overwrite.send_messages = False
        await channel.set_permissions(guild.default_role, overwrite=overwrite)
        print("Channel locked for @everyone")
    except Exception as e:
        print("ERROR locking channel:", e)

    description = "\n".join(
        [f"{EMOJIS[i]} → {roles[i].mention}" for i in range(len(roles))]
    )

    embed = discord.Embed(
        title="🔒 Verification Required",
        description=f"React below to get roles and unlock chat:\n\n{description}",
        color=discord.Color.blurple()
    )

    msg = await channel.send(embed=embed)

    # Add reactions
    for i in range(len(roles)):
        await msg.add_reaction(EMOJIS[i])

    # Save config in memory
    autorole_config[guild.id] = {
        "channel_id": channel.id,
        "message_id": msg.id,
        "role_ids": [role.id for role in roles]
    }

    await ctx.send(f"✅ Autorole panel created in {channel.mention}")

# ================= REACTION ADD (GIVE ROLE) =================
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.guild_id is None:
        return
    if payload.user_id == bot.user.id:
        return

    print("Reaction detected")

    config = autorole_config.get(payload.guild_id)
    if not config:
        print("No autorole config found (bot restarted?)")
        return

    if payload.message_id != config["message_id"]:
        print("Reaction not on autorole message")
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        print("Guild not found")
        return

    member = guild.get_member(payload.user_id)
    if not member:
        print("Member not found → ENABLE SERVER MEMBERS INTENT")
        return

    channel = guild.get_channel(config["channel_id"])
    role_ids = config["role_ids"]

    emoji = str(payload.emoji)
    if emoji not in EMOJIS:
        print("Wrong emoji")
        return

    index = EMOJIS.index(emoji)
    if index >= len(role_ids):
        return

    role = guild.get_role(role_ids[index])
    if not role:
        print("Role not found")
        return

    try:
        if role not in member.roles:
            await member.add_roles(role, reason="Autorole verification")
            print(f"Added role {role.name} to {member.name}")

            # Unlock chat for that user
            overwrite = channel.overwrites_for(member)
            overwrite.send_messages = True
            await channel.set_permissions(member, overwrite=overwrite)
            print("Unlocked chat for user")
    except discord.Forbidden:
        print("ERROR: Missing Manage Roles or role hierarchy issue")
    except Exception as e:
        print("Unexpected error:", e)

# ================= REACTION REMOVE (REMOVE ROLE) =================
@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    if payload.guild_id is None:
        return

    config = autorole_config.get(payload.guild_id)
    if not config:
        return

    if payload.message_id != config["message_id"]:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    member = guild.get_member(payload.user_id)
    if not member:
        return

    channel = guild.get_channel(config["channel_id"])
    role_ids = config["role_ids"]

    emoji = str(payload.emoji)
    if emoji not in EMOJIS:
        return

    index = EMOJIS.index(emoji)
    if index >= len(role_ids):
        return

    role = guild.get_role(role_ids[index])
    if not role:
        return

    try:
        if role in member.roles:
            await member.remove_roles(role, reason="Autorole removed")
            print(f"Removed role {role.name} from {member.name}")

            # Lock chat again
            overwrite = channel.overwrites_for(member)
            overwrite.send_messages = False
            await channel.set_permissions(member, overwrite=overwrite)
            print("Locked chat again")
    except discord.Forbidden:
        print("ERROR: Missing Manage Roles permission")

# ================= RUN =================
bot.run(TOKEN)
