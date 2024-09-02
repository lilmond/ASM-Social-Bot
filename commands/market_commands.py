from components import points_settings, command_respond
from discord.ext import commands
from discord import app_commands
import discord
import qrcode
import random
import toml
import time
import os
import io


CONFIG = toml.load(f"{os.path.dirname(__file__)}/../src/config.toml")


class MarketItemButtons(discord.ui.View):
    def __init__(self, client: commands.Bot, item_name: str, price: int, stock: int, item_image_url: str, currency: str):
        self.client = client
        self.item_name = item_name
        self.price = price
        self.stock = stock
        self.item_image_url = item_image_url
        self.currency = currency

        super().__init__(timeout=None)
    
    async def _purchased(self, interaction: discord.Interaction):
        points_settings.market_button_add_buyer(message_id=interaction.message.id, user_id=interaction.user.id)
        currency_name = points_settings.get_currency_name(interaction.guild_id) if self.currency == "social_credits" else "Social Tokens"
        buyers_list = points_settings.market_button_get_buyers(message_id=interaction.message.id)
        current_stock = (self.stock - len(buyers_list))
        message_embed = discord.Embed()
        message_embed.title = "Purchased!"
        message_embed.description = f"{interaction.user.mention} just bought **{self.item_name}**!\n**Price**: **{self.price} {currency_name}**\n**Current Stock**: **{current_stock}/{self.stock}**"
        message_embed.color = 0xfc6500
        message_embed.set_image(url=self.item_image_url)

        notification_channel_id = points_settings.get_market_notification_id(guild_id=interaction.guild_id)

        if not notification_channel_id:
            notification_channel_id = 1263169181143142552

        await self.client.get_channel(notification_channel_id).send(embed=message_embed)

        if current_stock == 0:
            self.purchase_button.disabled = True
            await self._ranout_stock(interaction)
    

    async def _ranout_stock(self, interaction: discord.Interaction):
        message_embed = discord.Embed()
        message_embed.title = "SOLD OUT!!!"
        message_embed.description = f"**{self.item_name}** has just ran out of stock!"
        message_embed.color = 0xfc6500
        message_embed.set_image(url=self.item_image_url)

        notification_channel_id = points_settings.get_market_notification_id(guild_id=interaction.guild_id)

        if not notification_channel_id:
            notification_channel_id = 1263169181143142552

        await self.client.get_channel(notification_channel_id).send(embed=message_embed)

    
    @discord.ui.button(label="Purchase", style=discord.ButtonStyle.green, custom_id="market_item_buttons:purchase")
    async def purchase_button(self, interaction: discord.Interaction, button: discord.Button):
        user_points = points_settings.get_user_points(user_id=interaction.user.id) if self.currency == "social_credits" else points_settings.get_user_tokens(user_id=interaction.user.id)

        currency_name = points_settings.get_currency_name(interaction.guild_id) if self.currency == "social_credits" else "Social Tokens"

        if (user_points < self.price):
            return await command_respond.respond(interaction, color=0xff0000, title="Purchase Failed!", description=f"You do not have the sufficient amount of {currency_name} to purchase this item.")

        if self.currency == "social_credits":
            points_settings.add_user_points(user_id=interaction.user.id, points=-self.price)
        else:
            points_settings.add_user_tokens(user_id=interaction.user.id, points=-self.price)

        await self._purchased(interaction)

        current_stock = (self.stock - len(points_settings.market_button_get_buyers(message_id=interaction.message.id)))

        embed = interaction.message.embeds[0]
        embed.set_field_at(2, name="🏷️Stock", value=f"{current_stock}/{self.stock}")

        if current_stock == 0:
            embed.set_footer(text="SOLD OUT!")
        
        await command_respond.respond(interaction, color=0x00ff00, title="Purchase Successful!", description=f"You have successfully bought **{self.item_name}** for **{self.price} {currency_name}**.")
        await interaction.message.edit(embed=embed, view=self)


class PlaceBidModal(discord.ui.Modal, title="Place A Bid!"):
    def __init__(self, auction_message: discord.Message):
        self.auction_message = auction_message
        super().__init__()


    bid_price = discord.ui.TextInput(
        label="Bid Price",
        style=discord.TextStyle.short,
        placeholder="Your bid price here...",
        required=True,
        min_length=1,
        max_length=20
    )


    async def on_submit(self, interaction: discord.Interaction):
        try:
            message_id = self.auction_message.id
            bid_value = self.bid_price.value

            try:
                bid_value = int(bid_value)
            except Exception:
                return await command_respond.respond(interaction, color=0xff0000, title="Invalid Bid Value!", description="Bid value must be integer!")
            
            auction = points_settings.get_auction(message_id=message_id)
            min_overbid = auction[4]
            expiration_epoch = auction[5]
            highest_bid = auction[6]
            currency = auction[8]
            total_bidders = auction[10]

            if currency == "social_credits":
                user_balance = points_settings.get_user_points(user_id=interaction.user.id)
            elif currency == "social_tokens":
                user_balance = points_settings.get_user_tokens(user_id=interaction.user.id)
            else:
                return await command_respond.respond(interaction, color=0xff0000, title="Unexpected Error!", description=f"An unexpected error has occured: currency is neither social_credits or social_tokens, please report this to the developers in the server. Thank you for your patience!", ephemeral=False)

            min_bid = int(highest_bid + min_overbid)

            if not auction:
                return await command_respond.respond(interaction, color=0xff0000, title="Auction Not Found!", description=f"This auction does not exist! Please contact a developer in the server if you think this is a mistake.")

            if (time.time() > expiration_epoch):
                return await command_respond.respond(interaction, color=0xff0000, title="Auction Expired!", description="This auction has already expired!")
            
            if (user_balance < bid_value):
                return await command_respond.respond(interaction, color=0xff0000, title="Insufficient Balance!", description="You do not have enough balance to place this bid!")

            if (bid_value < min_bid):
                return await command_respond.respond(interaction, color=0xff0000, title="Invalid Bid!", description=f"Your bid must be at least {min_bid} (highest bid: {highest_bid} + min overbid: {min_overbid}).")

            await command_respond.respond(interaction, color=0x00ff00, title="Bid Placed Successfully!", description=f"You have successfully placed your bid: {bid_value}")

            points_settings.set_auction_bid(message_id=message_id, highest_bid=bid_value, highest_bidder_id=interaction.user.id)

            auction_embed = self.auction_message.embeds[0]
            auction_embed.set_field_at(1, name=auction_embed.fields[1].name, value=f"<@{interaction.user.id}> `{bid_value}`")
            auction_embed.set_field_at(4, name=auction_embed.fields[4].name, value=f"`{total_bidders + 1}`")
            await self.auction_message.edit(embed=auction_embed)
        except Exception as e:
            print(f"Auction Place Bid Error: {e}")


class AuctionButtons(discord.ui.View):
    def __init__(self, auction_title: str, starting_bid: int, min_overbid: int, expiration_epoch: int):
        self.auction_title = auction_title
        self.starting_bid = starting_bid
        self.min_overbid = min_overbid
        self.expiration_epoch = expiration_epoch
        super().__init__(timeout=None)
    

    @discord.ui.button(label="PLACE BID", style=discord.ButtonStyle.green, custom_id="auction_buttons:place_bid")
    async def place_bid(self, interaction: discord.Interaction, button: discord.Button):
        modal = PlaceBidModal(auction_message=interaction.message)
        await interaction.response.send_modal(modal)


class ClaimStakeButtons(discord.ui.View):
    def __init__(self, user: discord.User):
        self.pressed = False
        self.user = user
        super().__init__(timeout=None)


    @discord.ui.button(label="YES!!!", style=discord.ButtonStyle.green, emoji="<:pepe_yes:1278871979650318378>")
    async def yes_button(self, interaction: discord.Interaction, button: discord.Button):
        if not (interaction.user.id == self.user.id):
            return
        
        if (self.pressed == True):
            return
        
        self.pressed = True


        embed = interaction.message.embeds[0]

        self.yes_button.disabled = True
        self.no_button.disabled = True

        if (points_settings.get_user_stake_points(user_id=interaction.user.id) < 1000):
            embed.color = 0xff0000
            embed.set_footer(text="ALREADY CLAIMED!")
        else:
            embed.set_footer(text="CLAIMED!")

            stake_points = points_settings.get_user_stake_points(interaction.user.id)
            cashback = int(3 * stake_points / 100)

            points_settings.set_user_stake_points(user_id=interaction.user.id, stake_points=0)
            points_settings.add_user_points(user_id=interaction.user.id, points=cashback) 

        await interaction.response.edit_message(embed=embed, view=self)


    @discord.ui.button(label="NO!!!", style=discord.ButtonStyle.red, emoji="<:pepe_cry:1278872016765849681>")
    async def no_button(self, interaction: discord.Interaction, button: discord.Button):
        if not (interaction.user.id == self.user.id):
            return
        
        if (self.pressed == True):
            return
        
        self.pressed = True
        
        embed = interaction.message.embeds[0]
        embed.color = 0xff0000
        embed.set_footer(text="CANCELLED!")

        self.yes_button.disabled = True
        self.no_button.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)


class MarketCommands(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client


    @commands.Cog.listener()
    async def on_ready(self):
        await self.client.tree.sync()
        print(f"{__name__} has ben loaded.")
    

    @app_commands.command(name="market_create_item", description="Create a market item for users to buy.")
    @app_commands.guild_only()
    @app_commands.choices(
        currency=[
            app_commands.Choice(name="Social Credits", value="social_credits"),
            app_commands.Choice(name="Social Tokens", value="social_tokens")
        ]
    )
    async def market_create_item(self, interaction: discord.Interaction, name: str, description: str, image: discord.Attachment, price: int, stock: int, currency: str = "social_credits"):
        if not (self.client.get_guild(CONFIG["DISCORD_DEVELOPMENT_SERVER"]).get_member(interaction.user.id).guild_permissions.administrator == True):
            return await command_respond.respond(interaction, color=0xff0000, title="Permission Error", description="You do not have permission to use this command.")
        
        if (price < 1):
            return await command_respond.respond(interaction, color=0xff0000, title="Item Drop Failed", description="Item price cannot be less than 1!")
        
        if (stock < 1):
            return await command_respond.respond(interaction, color=0xff0000, title="Item Drop Failed", description="This item has been sold out!")
        
        currency_name = points_settings.get_currency_name(guild_id=interaction.guild.id) if currency == "social_credits" else "Social Tokens"

        message_embed = discord.Embed()
        message_embed.title = name
        message_embed.description = description
        message_embed.color = 0xfc6500
        message_embed.add_field(name="🪧Type", value="`ITEM`", inline=True)
        message_embed.add_field(name="💸Price", value=f"`{price} {currency_name}`", inline=True)
        message_embed.add_field(name="🏷️Stock", value=f"`{stock}/{stock}`", inline=True)
        message_embed.set_image(url=image.url)


        message = await interaction.channel.send(embed=message_embed, view=MarketItemButtons(client=self.client, item_name=name, price=price, stock=stock, item_image_url=image.url, currency=currency))
        points_settings.add_market_button(message_id=message.id, item_name=name, price=price, stock=stock, item_image_url=image.url, currency=currency)
        await command_respond.respond(interaction, color=0x00ff00, title="Item Dropped!", description="Successfully created an item to be sold.")


    @app_commands.command(name="pointshop", description="Looking for a faster way to earn points? Why not buy it?")
    @app_commands.guild_only()
    async def pointshop(self, interaction: discord.Interaction):
        while True:
            destination_tag = random.randint(1, 1000000000)
            if not points_settings.points_shop_get_destination_tag(destination_tag=destination_tag):
                points_settings.points_shop_register(user_id=interaction.user.id, destination_tag=destination_tag, channel_id=interaction.channel_id)
                break

        qr_data = f"{CONFIG['POINTS_SHOP_WALLET']}:{destination_tag}"

        qr_image = qrcode.make(qr_data)

        embed = discord.Embed()
        embed.color = 0x00ff00
        embed.title = f"{points_settings.get_currency_name(interaction.guild_id)} Shop"
        embed.description = f"Your payment is ready to be made. Please send XRP to the address below.\n\n**Wallet Address**: {CONFIG['POINTS_SHOP_WALLET']}\n**Destination Tag**: {destination_tag}\n**Rate**: **100 {points_settings.get_currency_name(interaction.guild_id)}**/**1 XRP**"
        embed.set_image(url="attachment://qr.png")

        with io.BytesIO() as image_binary:
            qr_image.save(image_binary, "PNG")
            image_binary.seek(0)
            await interaction.response.send_message(embed=embed, ephemeral=False, file=discord.File(fp=image_binary, filename="qr.png"))


    @app_commands.command(name="item_buyers", description="Show a list of users who have bought the NFT.")
    @app_commands.guild_only()
    async def item_buyers(self, interaction: discord.Interaction, message_id: str):
        if not (self.client.get_guild(CONFIG["DISCORD_DEVELOPMENT_SERVER"]).get_member(interaction.user.id).guild_permissions.administrator == True):
            return await command_respond.respond(interaction, color=0xff0000, title="Permission Error", description="You do not have permission to use this command.")
        
        try:
            message_id = int(message_id)
        except ValueError:
            return await command_respond.respond(interaction, color=0xff0000, title="Error!", description="Invalid message ID.")
        
        market_item = points_settings.get_market_button(message_id=message_id)
        buyers = points_settings.market_button_get_buyers(message_id=message_id)

        if not all([market_item, buyers]):
            return await command_respond.respond(interaction, color=0xff0000, title="Error!", description="Unable to get information from the message ID. Please make sure it is correct.")
        
        item_name = market_item[2]
        price = market_item[3]
        stock = market_item[4]
        item_image_url =market_item[6]
        
        embed = discord.Embed()
        embed.color = 0xfc6500
        embed.title = f"{item_name} Buyers List"
        embed.set_thumbnail(url=item_image_url)
        embed.add_field(name="Item Name", value=item_name, inline=True)
        embed.add_field(name="Price", value=f"`{price} {points_settings.get_currency_name(guild_id=interaction.guild_id)}`", inline=True)
        embed.add_field(name="Stock(s)", value=f"{stock}", inline=False)
        embed.description = ""
        
        for i, buyer in enumerate(buyers, 1):
            embed.description += f"**{i}**. <@{buyer}>\n"
            if i == 11:
                break
        
        embed.description = embed.description.strip()

        await interaction.response.send_message(embed=embed)


    @app_commands.command(name="auction_create", description="Create an Auction for everyone to put a bid on.")
    @app_commands.guild_only()
    @app_commands.choices(currency=[
        app_commands.Choice(name="Social Credits", value="social_credits"),
        app_commands.Choice(name="Social Tokens", value="social_tokens")
    ])
    @app_commands.describe(title="Title of the auction item.")
    @app_commands.describe(description="Description of the auction embed.")
    @app_commands.describe(image="Image file that will be shown in the embed.")
    @app_commands.describe(expiration="Expiration date for the auction by hours.")
    @app_commands.describe(currency="Social Bot currency, either Social Credits or Social Tokens.")
    @app_commands.describe(starting_bid="Starting bid for the auction.")
    @app_commands.describe(min_overbid="Minimum overbid for the auction.")
    @app_commands.describe(custom_message="Custom message to send above the embed.")
    async def auction_create(self, interaction: discord.Interaction, title: str, description: str, image: discord.Attachment, expiration: int, currency: str, starting_bid: int, min_overbid: int, custom_message: str = None):
        try:
            if not (interaction.guild.get_member(interaction.user.id).guild_permissions.administrator == True):
                return await command_respond.respond(interaction, color=0xff0000, title="Permission Error!", description="You do not have permission to use this command.")
        
            if (currency == "social_credits"):
                currency_name = points_settings.get_currency_name(guild_id=interaction.guild_id)
            else:
                currency_name = "Social Tokens"

            expiration_epoch = int(time.time() + (expiration * 3600))

            embed = discord.Embed()
            embed.color = 0xffffff
            embed.title = title
            embed.description = description
            embed.set_image(url=image.url)
            embed.add_field(name="💎Starting Bid", value=f"`{starting_bid} {currency_name}`", inline=True)
            embed.add_field(name="👑Winning Bid", value=f"No one", inline=True)
            embed.add_field(name="💸Minimum Overbid", value=f"`{min_overbid} {currency_name}`", inline=True)
            embed.add_field(name="🪙Currency Type", value=f"{currency_name}", inline=True)
            embed.add_field(name="👥Total Bidders", value=f"`0`", inline=True)
            embed.add_field(name="⌛Auction Ends", value=f"<t:{expiration_epoch}:R>", inline=True)

            embed_buttons = AuctionButtons(auction_title=title, starting_bid=starting_bid, min_overbid=min_overbid, expiration_epoch=expiration_epoch)
            auction_message = await interaction.channel.send(content=custom_message, embed=embed, view=embed_buttons)
            
            points_settings.register_auction(message_id=auction_message.id, auction_title=title, starting_bid=starting_bid, min_overbid=min_overbid, expiration_epoch=expiration_epoch, currency=currency, image_url=image.url)

            await command_respond.respond(interaction, color=0x00ff00, title="Auction Created", description="Auction has been successfully been listed!")
        except Exception as e:
            print(f"Auction Create Error: {e}")


    @app_commands.command(name="claim_stake", description="Claim all your stake points to your wallet.")
    @app_commands.guild_only()
    async def claim_stake(self, interaction: discord.Interaction):
        stake_points = points_settings.get_user_stake_points(user_id=interaction.user.id)

        if (stake_points < 1000):
            return await command_respond.respond(interaction, color=0xff0000, title="Insufficient Stake Points!", description=f"You must have at least **1,000** stake points to claim it. Your current stake points: **{stake_points}**")
        
        embed = discord.Embed()
        embed.color = 0x00ff00
        embed.title = "Claim Stake Points?"
        embed.description = f"<:pepe_think:1278880821331366009> Are you sure you would like to claim **3%** (**{int(3 * stake_points / 100)}**) cashback from your stake points of **{stake_points}**? You will lose all your stake points once you hit yes."
        buttons = ClaimStakeButtons(user=interaction.user)

        await interaction.response.send_message(embed=embed, view=buttons)


async def setup(client: commands.Bot):
    await client.add_cog(MarketCommands(client))
