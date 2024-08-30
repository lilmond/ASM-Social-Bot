from components import points_settings, twitter_settings
from commands import market_commands, twitter_commands
from discord.ext import commands
import discord
import asyncio
import random
import toml
import time
import os

CONFIG = toml.load("./src/config.toml")
client = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@client.event
async def on_ready():
    await client.tree.sync()
    print(f"Logged In: {client.user}")

@client.event
async def setup_hook():
    for twitter_event_button in twitter_settings.get_event_buttons():
        message_id = twitter_event_button[1]
        tweet_id = twitter_event_button[2]
        reward = twitter_event_button[3]
        winners = twitter_event_button[4]
        expires_epoch = twitter_event_button[6]
        currency = twitter_event_button[7]

        view = twitter_commands.TwitterEventButtons(tweet_id=tweet_id, reward=reward, winners=winners, expires_epoch=expires_epoch, currency=currency)

        client.add_view(view, message_id=message_id)

    for market_button in points_settings.get_market_buttons():
        message_id = market_button[1]
        item_name = market_button[2]
        price = market_button[3]
        stock = market_button[4]
        buyers = market_button[5]
        item_image_url = market_button[6]
        currency = market_button[7]

        view = market_commands.MarketItemButtons(client=client, item_name=item_name, price=price, stock=stock, item_image_url=item_image_url, currency=currency)

        client.add_view(view, message_id=message_id)
    
    for auction in points_settings.get_auctions():
        message_id = auction[1]
        auction_title = auction[2]
        starting_bid = auction[3]
        min_overbid = auction[4]
        expiration_epoch = auction[5]

        view = market_commands.AuctionButtons(auction_title=auction_title, starting_bid=starting_bid, min_overbid=min_overbid, expiration_epoch=expiration_epoch)

        client.add_view(view, message_id=message_id)

@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    
    points_settings.add_user_exp(user_id=message.author.id, exp=1)

    mentioned_bot = False

    for mentioned in message.mentions:
        if (mentioned.id == client.user.id):
            mentioned_bot = True

    if not mentioned_bot:
        return
    
    greeted_gm = False
    gm_messages = ["good morning", "goodmorning", "morning", "mornin'", "mornin", "gm"]
    for gm_message in gm_messages:
        if gm_message in message.content.lower():
            greeted_gm = True

    if not greeted_gm:
        return
    
    claimed_gm = points_settings.user_claim_goodmorning(user_id=message.author.id)
    if not claimed_gm:
        return
    
    with open("./src/goodmorning.txt", "r") as file:
        gm_message = random.choice(file.read().splitlines())

    await message.author.send(content=f"{message.author.mention} {gm_message}. You have received **50 {points_settings.get_currency_name(guild_id=message.guild.id)}**. You may claim again tomorrow at <t:{int(time.time() + 86400)}:t> by greeting to everyone.")

async def load():
    for filename in os.listdir("./commands"):
        if filename.endswith(".py"):
            await client.load_extension(f"commands.{filename[:-3]}")

@client.hybrid_command(name="ping", description="Check if the bot is responsive.")
async def ping(ctx):
    embed_images = [
        "https://media1.tenor.com/m/dxY45sJPqrkAAAAC/cats-cat.gif",
        "https://media1.tenor.com/m/c9WptHOa_LMAAAAC/pong.gif",
        "https://media1.tenor.com/m/elbTGz7NjE4AAAAC/game-sports.gif"
    ]
    message_embed = discord.Embed()
    message_embed.color = 0x00ff00
    message_embed.title = "Pong!"
    message_embed.set_image(url=random.choice(embed_images))

    await ctx.send(embed=message_embed)

async def main():
    async with client:
        await load()
        await client.start(token=CONFIG["DISCORD_BOT_TOKEN"])

if __name__ == "__main__":
    asyncio.run(main())
