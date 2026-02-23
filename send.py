@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.guild_id is None or payload.user_id == bot.user.id:
        return

    print("Reaction detected")  # DEBUG

    config = autorole_config.get(payload.guild_id)
    if not config:
        print("No config found")
        return

    if payload.message_id != config["message_id"]:
        print("Wrong message")
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        print("Guild not found")
        return

    member = guild.get_member(payload.user_id)
    if not member:
        print("Member not found (INTENTS ISSUE)")
        return

    role_ids = config["role_ids"]
    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    emoji_str = str(payload.emoji)

    if emoji_str not in emojis:
        print("Wrong emoji")
        return

    index = emojis.index(emoji_str)
    if index >= len(role_ids):
        return

    role = guild.get_role(role_ids[index])
    if not role:
        print("Role not found")
        return

    try:
        await member.add_roles(role)
        print(f"Added role {role.name} to {member.name}")
    except Exception as e:
        print("ERROR ADDING ROLE:", e)
