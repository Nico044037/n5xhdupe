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

        # ================= NAME HISTORY =================
        async with session.get(
            f"https://api.mojang.com/user/profiles/{uuid_raw}/names"
        ) as history_response:

            if history_response.status == 200:
                history_data = await history_response.json()

                names = []
                timestamps = []

                for entry in history_data:
                    names.append(entry.get("name", "Unknown"))
                    if "changedToAt" in entry:
                        timestamps.append(entry["changedToAt"])

                name_history = "\n".join(names)

                # Approximate account creation date
                if timestamps:
                    earliest = min(timestamps)
                    creation_date = datetime.utcfromtimestamp(
                        earliest / 1000
                    ).strftime("%Y-%m-%d")
                else:
                    creation_date = "Unknown"
            else:
                name_history = "Unavailable"
                creation_date = "Unknown"

        # ================= RENDERS =================
        head_render = f"https://mc-heads.net/head/{uuid}"
        body_render = f"https://mc-heads.net/body/{uuid}"
        namemc_link = f"https://namemc.com/profile/{uuid}"

        # ================= EMBED =================
        embed = discord.Embed(
            title="🎮 Minecraft Account Info",
            color=discord.Color.green()
        )

        embed.add_field(name="Username", value=mc_username, inline=False)
        embed.add_field(name="UUID", value=uuid, inline=False)
        embed.add_field(name="Approx. Creation Date", value=creation_date, inline=False)
        embed.add_field(name="Name History", value=name_history, inline=False)

        embed.set_thumbnail(url=head_render)
        embed.set_image(url=body_render)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Open NameMC", url=namemc_link))

        await ctx.send(embed=embed, view=view)
