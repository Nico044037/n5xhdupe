# ================= SUDO INFO =================
@sudo.command(name="info")
@commands.has_permissions(administrator=True)
async def sudo_info(ctx, mc_username: str):

    await ctx.send("🔎 Fetching Minecraft data...")

    try:
        async with aiohttp.ClientSession() as session:

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

        head_render = f"https://mc-heads.net/head/{uuid}"
        body_render = f"https://mc-heads.net/body/{uuid}"
        namemc_link = f"https://namemc.com/profile/{uuid}"

        embed = discord.Embed(
            title="🎮 Minecraft Account Info",
            color=discord.Color.green()
        )

        embed.add_field(name="Username", value=mc_username, inline=False)
        embed.add_field(name="UUID", value=uuid, inline=False)

        embed.set_thumbnail(url=head_render)
        embed.set_image(url=body_render)

        # ===== BUTTON VIEW =====
        class InfoView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=120)

            @discord.ui.button(
                label="Copy command to get head",
                style=discord.ButtonStyle.primary
            )
            async def copy_head_command(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.send_message(
                    f"Copy this command:\n```\n$sudo head {mc_username}\n```",
                    ephemeral=True
                )

        view = InfoView()
        view.add_item(discord.ui.Button(label="Open NameMC", url=namemc_link))

        await ctx.send(embed=embed, view=view)

    except Exception as e:
        await ctx.send(f"❌ Unexpected error: `{str(e)}`")
