@sudo.command(name="info")
@commands.has_permissions(administrator=True)
async def sudo_info(ctx, mc_username: str):

    async with aiohttp.ClientSession() as session:

        # ================= GET UUID =================
        async with session.get(
            f"https://api.mojang.com/users/profiles/minecraft/{mc_username}"
        ) as response:

            if response.status != 200:
                return await ctx.send(f"❌ No Minecraft account found for `{mc_username}`.")

            try:
                data = await response.json()
            except:
                return await ctx.send("❌ Mojang API error (invalid response).")

            if not isinstance(data, dict) or "id" not in data:
                return await ctx.send("❌ Invalid Mojang response.")

            uuid_raw = data["id"]

            formatted_uuid = (
                f"{uuid_raw[:8]}-"
                f"{uuid_raw[8:12]}-"
                f"{uuid_raw[12:16]}-"
                f"{uuid_raw[16:20]}-"
                f"{uuid_raw[20:]}"
            )

        # ================= GET NAME HISTORY =================
        async with session.get(
            f"https://api.mojang.com/user/profiles/{uuid_raw}/names"
        ) as history_response:

            if history_response.status != 200:
                name_history = "Could not fetch name history."
            else:
                try:
                    history_data = await history_response.json()
                    name_history = "\n".join(
                        [entry.get("name", "Unknown") for entry in history_data]
                    )
                except:
                    name_history = "Error reading name history."

        # ================= EMBED =================
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
