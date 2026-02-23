import discord
from discord.ext import commands
import os
import json

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

CONFIG_FILE = "config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

config = load_config()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command()
@commands.has_permissions(administrator=True)
async def autorode(ctx, channel: discord.TextChannel, *roles: discord.Role):
    if not roles:
        await ctx.send("You must provide at least one role.")
        return

    roles = roles[:5]  # max 5 roles

    # Lock channel (no chatting for @everyone)
    overwrite = channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = False
    await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)

    # Create reaction message
    role_list = "\n".join([f"React to get {role.mention}" for role in roles])
    msg = await channel.send(
        f"React below to unlock the server and get roles:\n\n{role_list}"
    )

    # Add reactions (1️⃣ 2️⃣ 3️⃣ 4️⃣ 5️⃣)
    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    for i in range(len(roles)):
        await msg.add_reaction(emojis[i])

    # Save config
    config[str(ctx.guild.id)] = {
        "channel_id": channel.id,
        "message_id": msg.id,
        "role_ids": [role.id for role in roles]
    }
    save_config(config)

    await ctx.send(f"Autorode reaction system set in {channel.mention}!")

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return

    guild_id = str(payload.guild_id)
    if guild_id not in config:
        return

    data = config[guild_id]

    if payload.message_id != data["message_id"]:
        return

    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)

    if not member:
        return

    channel = guild.get_channel(data["channel_id"])
    roles = [guild.get_role(rid) for rid in data["role_ids"]]

    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

    if str(payload.emoji) in emojis:
        index = emojis.index(str(payload.emoji))
        if index < len(roles):
            role = roles[index]
            if role and role not in member.roles:
                try:
                    await member.add_roles(role, reason="Reaction autorole")

                    # Unlock chatting for this member
                    overwrite = channel.overwrites_for(member)
                    overwrite.send_messages = True
                    await channel.set_permissions(member, overwrite=overwrite)

                except discord.Forbidden:
                    pass

bot.run(os.getenv("TOKEN"))
