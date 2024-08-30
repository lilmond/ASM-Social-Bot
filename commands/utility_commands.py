from components import command_respond, points_settings, twitter_settings, xaman_settings
from discord.ext import commands
from discord import app_commands
import requests
import discord
import toml
import os
import re


CONFIG = toml.load(f"{os.path.dirname(__file__)}/../src/config.toml")


class PurgeButtons(discord.ui.View):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.required_confirmations = 2
        self.confirmed_user_ids = []
        self.cancelled = False

        super().__init__(timeout=None)
    

    async def _wipe(self, interaction: discord.Interaction):
        self.proceed_button.disabled = True
        self.cancel_button.disabled = True

        points_settings.purge()

        purge_embed = interaction.message.embeds[0]
        purge_embed.color = 0x00ff00
        purge_embed.title = "The purge event has successfully been executed!"
        purge_embed.description = "This means that all user' Social Credits and Stake Points have been wiped. This cannot be undone."

        await interaction.message.edit(embed=purge_embed, view=self)
        await command_respond.respond(interaction, color=0x00ff00, title="Access Granted!", description=f"You have successfully confirmed to proceed with this action. It seems that you were the last one to decide. Actions will now be taken in a short moment...")


    @discord.ui.button(label="Proceed!", style=discord.ButtonStyle.danger, emoji="<a:nuke:1278887060752830555>")
    async def proceed_button(self, interaction: discord.Interaction, button: discord.Button):
        user_roles = self.client.get_guild(CONFIG["DISCORD_DEVELOPMENT_SERVER"]).get_member(interaction.user.id).roles
        
        if not any(role.id == <REDACTED> for role in user_roles):
            return await command_respond.respond(interaction, color=0xff0000, title="Access Denied!", description="Only the world elites are able to take this action!")
        
        if (self.cancelled == True):
            return await command_respond.respond(interaction, color=0xff0000, title="Already Cancelled!", description="This action has already been cancelled!")

        if (interaction.user.id in self.confirmed_user_ids):
            return await command_respond.respond(interaction, color=0xff0000, title="Already Confirmed!", description="You have already confirmed this action! Please let the others decide.")

        self.confirmed_user_ids.append(interaction.user.id)
        embed = interaction.message.embeds[0]
        embed.set_footer(text=f"VOTES: {len(self.confirmed_user_ids)}")

        await interaction.message.edit(embed=embed, view=self)

        if (len(self.confirmed_user_ids) >= self.required_confirmations):
            return await self._wipe(interaction)
        else:
            return await command_respond.respond(interaction, color=0x00ff00, title="Access Granted!", description=f"You have successfully confirmed to proceed with this action. At least {int(self.required_confirmations - len(self.confirmed_user_ids))} more confirmations are required to begin the purge.")
        

    @discord.ui.button(label="Cancel!", style=discord.ButtonStyle.green, emoji="<a:cancel:1278941913432588394>")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.Button):
        user_roles = self.client.get_guild(CONFIG["DISCORD_DEVELOPMENT_SERVER"]).get_member(interaction.user.id).roles
        
        if not any(role.id == <REDACTED> for role in user_roles):
            return await command_respond.respond(interaction, color=0xff0000, title="Access Denied!", description="Only the world elites are able to take this action!")

        if (self.cancelled == True):
            return await command_respond.respond(interaction, color=0xff0000, title="Already Cancelled!", description="This action has already been cancelled!")

        self.cancelled = True

        embed = interaction.message.embeds[0]
        embed.color = 0x00ff00
        embed.title = "Action Cancelled!"
        embed.description = f"The purge has been cancelled by {interaction.user.mention}. Phew! That was too close!"
        embed.set_footer()

        self.proceed_button.disabled = True
        self.cancel_button.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)


class UtilityCommands(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client


    @commands.Cog.listener()
    async def on_ready(self):
        await self.client.tree.sync()
        print(f"{__name__} has been loaded.")
    

    @app_commands.command(name="set_currency_name", description="Set the server currency name from \"points\".")
    @app_commands.guild_only()
    async def set_currency_name(self, interaction: discord.Interaction, currency_name: str):
        if not (self.client.get_guild(CONFIG["DISCORD_DEVELOPMENT_SERVER"]).get_member(interaction.user.id).guild_permissions.create_events == True):
            if not (interaction.user.guild_permissions.administrator == True):
                return await command_respond.respond(interaction, color=0xff0000, title="Permission Error", description="You do not have permission to use this command.", ephemeral=False)
        
        points_settings.set_currency_name(guild_id=interaction.guild_id, currency_name=currency_name)

        await command_respond.respond(interaction, color=0x00ff00, title="Success!", description=f"Currency name has successfully set to **{currency_name}** for this guild.", ephemeral=False)


    @app_commands.command(name="unity_transfer_balance", description="Transfer your unity points to social bot.")
    @app_commands.guild_only()
    async def unity_transfer_balance(self, interaction: discord.Interaction, message_id: str):
        ephemeral = False

        if (points_settings.unity_balance_transfer_check(user_id=interaction.user.id)):
            return await command_respond.respond(interaction, color=0xff0000, title="Transfer Error!", description="You have already transferred your balance from the Unity bot before!", ephemeral=ephemeral)

        try:
            message = await interaction.channel.fetch_message(message_id)
        except Exception as e:
            return await command_respond.respond(interaction, color=0xff0000, title="Transfer Error!", description=f"Unable to fetch message by ID.", ephemeral=ephemeral)

        if not (message.interaction_metadata.user.id == interaction.user.id):
            return await command_respond.respond(interaction, color=0xff0000, title="Transfer Error!", description="This command wasn't executed by you.", ephemeral=ephemeral)

        if (not message.author.id == 1176342265996775565):
            return await command_respond.respond(interaction, color=0xff0000, title="Transfer Error!", description="This is not a command response from <@1176342265996775565>.", ephemeral=ephemeral)
        
        if not message.embeds:
            return await command_respond.respond(interaction, color=0xff0000, title="Transfer Error!", description="Unable to fetch message embed.", ephemeral=ephemeral)

        embed_description = message.embeds[0].description
        text = embed_description

        if not text.startswith("You have withdrawn"):
            return await command_respond.respond(interaction, color=0xff0000, title="Transfer Error!", description="This isn't a withdraw command from Unity bot.", ephemeral=ephemeral)
        
        matches = re.findall(r'\b\d+\b', text)
        if matches:
            number = int(matches[0])
        else:
            return await command_respond.respond(interaction, color=0xff0000, title="Transfer Error!", description="An error has occured while trying to fetch your Unity amount withdraw command response. Please try again.", ephemeral=ephemeral)

        if (number < 0):
            return await command_respond.respond(interaction, color=0xff0000, title="Transfer Error!", description="You cannot transfer zero or negative balance from Unity.", ephemeral=ephemeral)

        points_settings.add_user_points(user_id=interaction.user.id, points=number)
        points_settings.unity_balance_transfer_insert(user_id=interaction.user.id)

        await command_respond.respond(interaction, color=0x00ff00, title="Success!", description=f"You have successfully transferred your **{number}** Unity balance to Social Bot.", ephemeral=ephemeral)


    @app_commands.command(name="market_set_notification", description="Set the notification channel for the market.")
    @app_commands.guild_only()
    async def set_notification(self, interaction: discord.Interaction, channel_id: str):
        if not (interaction.guild.get_member(interaction.user.id).guild_permissions.administrator == True):
            return await command_respond.respond(interaction, color=0xff0000, title="Permission Error", description="You do not have permission to use this command.")
        
        channel_exists = False

        for channel in interaction.guild.channels:
            if str(channel.id) == channel_id:
                channel_exists = True

        if not channel_exists:
            return await command_respond.respond(interaction, color=0xff0000, title="Error!", description="This channel does not exist.")
        
        points_settings.set_market_notification(guild_id=interaction.guild_id, channel_id=channel_id)
        
        await command_respond.respond(interaction, color=0x00ff00, title="Success!", description=f"Market notifications will now be sent to <#{channel_id}> from now on.")


    @app_commands.command(name="profile", description="Show your or someone else's profile.")
    @app_commands.guild_only()
    async def profile(self, interaction: discord.Interaction, user: discord.User = None):
        if not user:
            user = interaction.user

        guild_currency_name = points_settings.get_currency_name(guild_id=interaction.guild_id)
        user_points = points_settings.get_user_points(user_id=user.id)
        user_tokens = points_settings.get_user_tokens(user_id=user.id)
        twitter_info = twitter_settings.get_discord_user(user_discord_id=user.id)
        xrp_wallet = xaman_settings.get_discord_id(discord_id=user.id)
        user_exp = points_settings.get_user_exp(user_id=user.id)

        level_addups = 40

        level = 1
        required_exp = level_addups

        while True:
            if (user_exp <= required_exp):
                break
            level += 1
            required_exp += level_addups

        if not twitter_info:
            twitter_field_value = "Not linked"
        else:
            twitter_field_value = f"[Profile](https://twitter.com/intent/user?user_id={twitter_info[2]})"

        xrp_wallet_field_value = "Not linked"
        if xrp_wallet:
            if xrp_wallet[2]:
                xrp_wallet_field_value = f"[Explorer](https://xrpscan.com/account/{xrp_wallet[2]})"

        embed = discord.Embed()
        embed.color = 0x9632ff
        embed.title = f"{user.name}'s Profile"
        embed.add_field(name=f"💸{guild_currency_name}", value=f"`{user_points}`", inline=True)
        embed.add_field(name=f"🪙Social Tokens", value=f"`{user_tokens}`", inline=True)
        embed.add_field(name=f"<:twitter:1266266887017336914>Twitter", value=twitter_field_value, inline=True)
        embed.add_field(name=f"<:xrp:1276149151184326767>XRP Wallet", value=xrp_wallet_field_value, inline=True)
        embed.add_field(name="🎮Level", value=f"**{level}** ({user_exp}/{required_exp})", inline=True)
        embed.set_thumbnail(url=user.display_avatar.url)

        await interaction.response.send_message(embed=embed)
    

    @app_commands.command(name="link_xaman", description="Link your Xaman wallet with us to receive NFT's!")
    @app_commands.guild_only()
    async def link_xaman(self, interaction: discord.Interaction):
        payload = {
            "txjson": { "TransactionType": "SignIn" }
        }
        headers = headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "X-API-Key": "<REDACTED>",
            "X-API-Secret": "<REDACTED>"
        }
        http = requests.post("https://xumm.app/api/v1/platform/payload", json=payload, headers=headers).json()

        if not "uuid" in http:
            return await command_respond.respond(interaction, color=0xff0000, title="Error!", description="An error has occured while trying to generate a sign QR code for you. Please try again!")
        
        uuid = http["uuid"]
        qr_code_url = http["refs"]["qr_png"]
        sign_url = http["next"]["always"]

        embed = discord.Embed()
        embed.title = "Link your Xaman!"
        embed.description = f"Open your **Xaman** app to scan the QR code below!\n[Click here]({sign_url}) if you're on mobile."
        embed.color = 0x00ff00
        embed.set_image(url=qr_code_url)

        xaman_settings.register_user(discord_id=interaction.user.id, uuid=uuid)

        await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command(name="set_user_exp", description="Set a user's XP points.")
    async def set_user_exp(self, interaction: discord.Interaction, user: discord.User, xp: int):
        if not (self.client.get_guild(CONFIG["DISCORD_DEVELOPMENT_SERVER"]).get_member(interaction.user.id).guild_permissions.administrator == True):
            return await command_respond.respond(interaction, color=0xff0000, title="Permission Error", description="You do not have permission to use this command.", ephemeral=False)
        
        points_settings.set_user_exp(user_id=user.id, exp=xp)

        await command_respond.respond(interaction, color=0x00ff00, title="Success!", description=f"Successfully set {user.mention}'s EXP points to **{xp}**.", ephemeral=False)
    

    @app_commands.command(name="add_user_exp", description="Add or decrease a user's XP points.")
    async def add_user_exp(self, interaction: discord.Interaction, user: discord.User, xp: int):
        if not (self.client.get_guild(CONFIG["DISCORD_DEVELOPMENT_SERVER"]).get_member(interaction.user.id).guild_permissions.administrator == True):
            return await command_respond.respond(interaction, color=0xff0000, title="Permission Error", description="You do not have permission to use this command.", ephemeral=False)
        
        points_settings.add_user_exp(user_id=user.id, exp=xp)

        await command_respond.respond(interaction, color=0x00ff00, title="Success!", description=f"Successfully {'added' if xp > 0 else 'decreased'} {user.mention}'s XP points **{xp}**.", ephemeral=False)


    @app_commands.command(name="set_user_stake", description="Set a user's stake points.")
    async def set_user_stake(self, interaction: discord.Interaction, user: discord.User, stake: int):
        if not (self.client.get_guild(CONFIG["DISCORD_DEVELOPMENT_SERVER"]).get_member(interaction.user.id).guild_permissions.administrator == True):
            return await command_respond.respond(interaction, color=0xff0000, title="Permission Error", description="You do not have permission to use this command.", ephemeral=False)
        
        points_settings.set_user_stake_points(user_id=user.id, stake_points=stake)

        await command_respond.respond(interaction, color=0x00ff00, title="Success!", description=f"Successfully set {user.mention}'s stake points **{stake}**.", ephemeral=False)


    @app_commands.command(name="purge", description="Wipe everything off the face of the world like Thanos.")
    @app_commands.guild_only()
    async def purge(self, interaction: discord.Interaction):
        user_roles = self.client.get_guild(CONFIG["DISCORD_DEVELOPMENT_SERVER"]).get_member(interaction.user.id).roles
        
        if not any(role.id == <REDACTED> for role in user_roles):
            return await command_respond.respond(interaction, color=0xff0000, title="Permission Error", description="You do not have permission to use this command.", ephemeral=False)
    
        buttons = PurgeButtons(client=self.client)

        embed = discord.Embed()
        embed.color = 0xffff00
        embed.title = "The purge is about to begin... But wait!"
        embed.description = f"At least {buttons.required_confirmations} confirmations from the world elites are needed to complete this action, if you are one of them, please decide..."
        embed.set_footer(text="VOTES: 0")

        await interaction.response.send_message(embed=embed, view=buttons)

async def setup(client: commands.Bot):
    await client.add_cog(UtilityCommands(client=client))
