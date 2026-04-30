"""MIT License

Copyright (c) 2023 - present Vocard Development
"""

import discord
import function as func

from discord import app_commands
from discord.ext import commands
from voicelink import Config


def _owner_only(interaction: discord.Interaction) -> bool:
    return interaction.user.id in Config().bot_access_user


async def _deny(interaction: discord.Interaction, msg: str = "⛔ This command is restricted to the bot owner.") -> None:
    embed = discord.Embed(description=msg, color=0xFF2B5E)
    await interaction.response.send_message(embed=embed, ephemeral=True)


class ServiceGroup(app_commands.Group, name="service", description="[Owner] Control music service availability."):
    """Sub-group of commands for service management."""

    @app_commands.command(name="disable", description="[Owner] Temporarily disable the music service for all users.")
    @app_commands.describe(reason="Message shown to users (e.g. 'Maintenance until 22:00')")
    async def disable(self, interaction: discord.Interaction, reason: str = "") -> None:
        if not _owner_only(interaction):
            return await _deny(interaction)

        if not func.is_service_enabled():
            return await _deny(interaction, "⚠️ The service is already disabled.")

        func.set_service_state(enabled=False, reason=reason)
        func.logger.info(f"[Owner] {interaction.user} DISABLED the music service. Reason: {reason or 'none'}")

        desc = "🔒 **Music service has been disabled.**\nAll users will see a maintenance message."
        if reason:
            desc += f"\n\n**User-facing message:**\n> {reason}"
        await interaction.response.send_message(embed=discord.Embed(description=desc, color=0xFFAA00), ephemeral=True)

    @app_commands.command(name="enable", description="[Owner] Re-enable the music service.")
    async def enable(self, interaction: discord.Interaction) -> None:
        if not _owner_only(interaction):
            return await _deny(interaction)

        if func.is_service_enabled():
            return await _deny(interaction, "✅ The service is already enabled.")

        func.set_service_state(enabled=True, reason="")
        func.logger.info(f"[Owner] {interaction.user} ENABLED the music service.")
        await interaction.response.send_message(
            embed=discord.Embed(description="✅ **Music service has been re-enabled.**", color=0x2ECC71),
            ephemeral=True
        )

    @app_commands.command(name="status", description="[Owner] Check current service & ban status.")
    async def status(self, interaction: discord.Interaction) -> None:
        if not _owner_only(interaction):
            return await _deny(interaction)

        enabled = func.is_service_enabled()
        reason  = func.get_service_reason()
        bans    = func.get_banlist()

        embed = discord.Embed(title="📊 Bot Control Panel", color=0x2ECC71 if enabled else 0xFF2B5E)
        embed.add_field(name="Music Service", value="✅ Online" if enabled else "🔒 Disabled", inline=True)
        embed.add_field(name="Banned Users",  value=str(len(bans)),                            inline=True)
        if not enabled and reason:
            embed.add_field(name="Disable Reason", value=reason, inline=False)

        temp_bans = sum(1 for v in bans.values() if v is not None)
        perm_bans = len(bans) - temp_bans
        if bans:
            embed.add_field(name="Ban breakdown", value=f"Permanent: {perm_bans} · Temporary: {temp_bans}", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)


class Owner(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ── /ban ──────────────────────────────────────────────────────────────────
    @app_commands.command(name="ban", description="[Owner] Ban a user from using the bot.")
    @app_commands.describe(
        user="The user to ban",
        duration="Duration: 30m / 2h / 1d / 1w — leave empty for permanent",
        reason="Reason (for logs only)"
    )
    async def ban(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        duration: str = "",
        reason: str = ""
    ) -> None:
        if not _owner_only(interaction):
            return await _deny(interaction)

        if user.id in Config().bot_access_user:
            return await _deny(interaction, "❌ You cannot ban another bot owner.")

        expiry = func.parse_duration(duration)
        if duration and expiry is None:
            return await _deny(interaction, "❌ Invalid duration. Use formats like: `30m`, `2h`, `1d`, `1w`.")

        func.ban_user(user.id, expiry)

        ban_type = f"Temporary ({func.format_ban_remaining(expiry)})" if expiry else "Permanent"
        func.logger.info(
            f"[Owner] {interaction.user} banned {user} (id={user.id}) "
            f"[{ban_type}]. Reason: {reason or 'none'}"
        )

        embed = discord.Embed(title="🔨 User Banned", color=0xFF2B5E)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="User",    value=f"{user.mention} (`{user.id}`)", inline=True)
        embed.add_field(name="Type",    value=ban_type,                         inline=True)
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /unban ────────────────────────────────────────────────────────────────
    @app_commands.command(name="unban", description="[Owner] Remove a user from the ban list.")
    @app_commands.describe(user="The user to unban")
    async def unban(self, interaction: discord.Interaction, user: discord.User) -> None:
        if not _owner_only(interaction):
            return await _deny(interaction)

        if not func.unban_user(user.id):
            return await _deny(interaction, f"❌ **{user}** is not in the ban list.")

        func.logger.info(f"[Owner] {interaction.user} unbanned {user} (id={user.id})")
        embed = discord.Embed(
            title="✅ User Unbanned",
            description=f"**{user.mention}** (`{user.id}`) has been removed from the ban list.",
            color=0x2ECC71
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /banlist ──────────────────────────────────────────────────────────────
    @app_commands.command(name="banlist", description="[Owner] Show all banned users.")
    async def banlist(self, interaction: discord.Interaction) -> None:
        if not _owner_only(interaction):
            return await _deny(interaction)

        bans = func.get_banlist()
        if not bans:
            return await interaction.response.send_message(
                embed=discord.Embed(description="✅ The ban list is empty.", color=0x2ECC71),
                ephemeral=True
            )

        lines = []
        for uid, expiry in sorted(bans.items()):
            user = self.bot.get_user(uid)
            tag  = f"**{user}** (`{uid}`)" if user else f"`{uid}` *(unknown)*"
            if expiry is None:
                lines.append(f"🔒 {tag} — permanent")
            else:
                lines.append(f"⏱️ {tag} — expires in {func.format_ban_remaining(expiry)}")

        embed = discord.Embed(
            title=f"🔨 Ban List ({len(bans)} users)",
            description="\n".join(lines),
            color=0xFF2B5E
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    cog = Owner(bot)
    bot.tree.add_command(ServiceGroup())
    await bot.add_cog(cog)
