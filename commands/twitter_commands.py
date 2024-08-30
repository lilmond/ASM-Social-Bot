from components import twitter_settings, command_respond, points_settings
from discord.ext import commands
from discord import app_commands
import urllib.parse
import requests
import discord
import toml
import time
import os
import re


CONFIG = toml.load(f"{os.path.dirname(__file__)}/../src/config.toml")


class TwitterEventButtons(discord.ui.View):
    def __init__(self, tweet_id: int, reward: int, winners: int, expires_epoch: int, currency: str):
        self.tweet_id = tweet_id
        self.reward = reward
        self.winners = winners
        self.expires_epoch = expires_epoch
        self.currency = currency

        super().__init__(timeout=None)
    

    async def _error_unverified(self, interaction: discord.Interaction):
        return await command_respond.respond(interaction, color=0xff0000, title="Error!", description="Please link your Twitter account first using the `/link_twitter` command.")


    async def _get_user_verify_info(self, user_id: int):
        verify_info = twitter_settings.get_discord_user(user_discord_id=user_id)
        
        if not verify_info:
            return
        
        if not verify_info[2]:
            return
        
        return verify_info


    async def _respond_error(self, interaction: discord.Interaction, message: str):
        return await command_respond.respond(interaction, color=0xff0000, title="Error!", description=message)
    

    async def _respond_dm(self, interaction: discord.Interaction, message: str):
        embed = discord.Embed(
            color=0x00ff00,
            description=message
        )
        embed.set_author(name="ASM Bot", icon_url="https://cdn.discordapp.com/avatars/1264252381776969758/172906f8cabdc0201d11e3e6c65c5878.png?size=1024")
        embed.set_footer(text="- Anti-Social Media Team.")

        await interaction.user.send(embed=embed)
    

    async def disable_buttons(self):
        for child in self.children:
            if type(child) == discord.ui.Button:
                child.disabled = True


    @discord.ui.button(label="Like", style=discord.ButtonStyle.blurple, emoji="❤️", custom_id="twitter_event_buttons:like")
    async def like_button(self, interaction: discord.Interaction, button: discord.ui):
        try:
            if (time.time() > self.expires_epoch):
                await self.disable_buttons()
                await interaction.response.edit_message(content=interaction.message.content, embed=interaction.message.embeds[0], view=self)
                return await command_respond.respond(interaction, color=0xff0000, title="Error!", description="This event has already expired!")

            winners_list = twitter_settings.get_event_button_winners(message_id=interaction.message.id)
            if (len(winners_list) >= self.winners):
                if not (interaction.user.id in winners_list):
                    return await command_respond.respond(interaction, color=0xff0000, title="You were too late!", description="This event has already reached the maximum winners.", ephemeral=True)

            verify_info = await self._get_user_verify_info(interaction.user.id)
            if not verify_info:
                return await self._error_unverified(interaction)
            
            user_twitter_id = verify_info[2]
            user_twitter_access_token = verify_info[3]

            if twitter_settings.event_user_has_interacted(tweet_id=self.tweet_id, user_twitter_id=user_twitter_id, interaction_name="Like"):
                return await self._respond_error(interaction, message="You have already received a reward for liking this Tweet!")

            liked = requests.post(f"https://api.twitter.com/2/users/{user_twitter_id}/likes", json={"tweet_id": str(self.tweet_id)}, headers={"Authorization": f"Bearer {user_twitter_access_token}"}).json()

            if "title" in liked:
                if liked["title"] == "Unauthorized":
                    try:
                        refresh_token = requests.post("http://127.0.0.1:5001/twitter-refresh-token", json={"access_token": user_twitter_access_token}).json()
                        if not "access_token" in refresh_token:
                            raise Exception
                    except Exception as e:
                        await self._respond_error(interaction, message="Your Twitter access token has expired and an error has occured while trying to refresh it. Please try relinking your Twitter account.")
                        with open("twitter_interaction_errors.txt", "a") as file:
                            file.write(f"Twitter Like Error: {e} | refresh_token: {refresh_token}\n")
                            file.close()
                        return
                    
                    return await self._respond_error(interaction, message="Your Twitter access token has expired and been refreshed. Please click the button one more time to receive your reward!")


            if not "data" in liked:
                with open("twitter_interaction_errors.txt", "a") as file:
                    file.write(f"Like Error: 'data' not in liked: {liked}\n")
                    file.close()
                return await self._respond_error(interaction, message="An error has occured while trying to like this Tweet, please try relinking your Twitter account using the `/link_twitter` command.")
            
            if not liked["data"]["liked"] == True:
                with open("twitter_interaction_errors.txt", "a") as file:
                    file.write(f"Like Error: liked[\"data\"][\"liked\"] not True: {liked}\n")
                    file.close()
                return await self._respond_error(interaction, message="An error has occured while trying to like this Tweet, please try relinking your Twitter account using the `/link_twitter` command.")
            
            if not interaction.user.id in winners_list:
                twitter_settings.add_event_button_winner(message_id=interaction.message.id, user_id=interaction.user.id)

                message_content = interaction.message.content
                message_embed = interaction.message.embeds[0]
                message_embed.set_field_at(index=2, name=":trophy: Winners", value=f"{len(twitter_settings.get_event_button_winners(message_id=interaction.message.id))}/{self.winners}")
                await interaction.message.edit(content=message_content, embed=message_embed, view=self)

            twitter_settings.event_add_interaction(tweet_id=self.tweet_id, user_twitter_id=user_twitter_id, interaction="Like")

            if (self.currency == "social_credits"):
                currency_name = points_settings.get_currency_name(interaction.guild_id)
                points_settings.add_user_points(user_id=interaction.user.id, points=self.reward)
            else:
                currency_name = "Social Tokens"
                points_settings.add_user_tokens(user_id=interaction.user.id, points=self.reward)

            await command_respond.respond(interaction=interaction, color=0x00ff00, title="Successful!", description=f"You have succesfully received **{self.reward} {currency_name}** for liking our Tweet!")
            await self._respond_dm(interaction, message=f"You have succesfully received **{self.reward} {currency_name}** for liking our Tweet!")
        except Exception as e:
            print(f"Like Error: {e}")


    @discord.ui.button(label="Retweet", style=discord.ButtonStyle.red, emoji="<:retweet:1258006864298377317>", custom_id="twitter_event_buttons:retweet")
    async def retweet_button(self, interaction: discord.Interaction, button: discord.ui):
        try:
            if (time.time() > self.expires_epoch):
                await self.disable_buttons()
                await interaction.response.edit_message(content=interaction.message.content, embed=interaction.message.embeds[0], view=self)
                return await command_respond.respond(interaction, color=0xff0000, title="Error!", description="This event has already expired!")
            
            winners_list = twitter_settings.get_event_button_winners(message_id=interaction.message.id)
            if (len(winners_list) >= self.winners):
                if not (interaction.user.id in winners_list):
                    return await command_respond.respond(interaction, color=0xff0000, title="You were too late!", description="This event has already reached the maximum winners.", ephemeral=True)
                
            verify_info = await self._get_user_verify_info(interaction.user.id)
            if not verify_info:
                return await self._error_unverified(interaction)
            
            user_twitter_id = verify_info[2]
            user_twitter_access_token = verify_info[3]

            if twitter_settings.event_user_has_interacted(tweet_id=self.tweet_id, user_twitter_id=user_twitter_id, interaction_name="Retweet"):
                return await self._respond_error(interaction, message="You have already received a reward for retweeting this Tweet!")

            retweet = requests.post(f"https://api.twitter.com/2/users/{user_twitter_id}/retweets", json={"tweet_id": str(self.tweet_id)}, headers={"Authorization": f"Bearer {user_twitter_access_token}"}).json()

            if "title" in retweet:
                if retweet["title"] == "Unauthorized":
                    try:
                        refresh_token = requests.post("http://127.0.0.1:5001/twitter-refresh-token", json={"access_token": user_twitter_access_token}).json()
                        if not "access_token" in refresh_token:
                            raise Exception
                    except Exception:
                        return await self._respond_error(interaction, message="Your Twitter access token has expired and an error has occured while trying to refresh it. Please try relinking your Twitter account.")
                    
                    return await self._respond_error(interaction, message="Your Twitter access token has expired and been refreshed. Please click the button one more time to receive your reward!")

            retweeted = False

            if "errors" in retweet:
                if retweet["errors"][0]["message"] == "You cannot retweet a Tweet that you have already retweeted.":
                    retweeted = True

            if not retweeted:
                if not "data" in retweet:
                    with open("twitter_interaction_errors.txt", "a") as file:
                        file.write(f"Retweet Error: data not in retweet response: {retweet}\n")
                        file.close()
                    return await self._respond_error(interaction, message="An error has occured while trying to retweet, please try re-linking your Twitter account.")
                
                if not "retweeted" in retweet["data"]:
                    with open("twitter_interaction_errors.txt", "a") as file:
                        file.write(f"Retweet Error: retweeted not in retweet[\"data\"] response: {retweet}\n")
                        file.close()
                    return await self._respond_error(interaction, message="An error has occured while trying to retweet, please try re-linking your Twitter account.")
                
                if not retweet["data"]["retweeted"] == True:
                    with open("twitter_interaction_errors.txt", "a") as file:
                        file.write(f"Retweet Error: retweet[\"data\"][\"retweeted\"] is not True: {retweet}\n")
                        file.close()
                    return await self._respond_error(interaction, message="An error has occured while trying to retweet, please try re-linking your Twitter account.")
            
            if not interaction.user.id in winners_list:
                twitter_settings.add_event_button_winner(message_id=interaction.message.id, user_id=interaction.user.id)

                message_content = interaction.message.content
                message_embed = interaction.message.embeds[0]
                message_embed.set_field_at(index=2, name=":trophy: Winners", value=f"{len(twitter_settings.get_event_button_winners(message_id=interaction.message.id))}/{self.winners}")
                await interaction.message.edit(content=message_content, embed=message_embed, view=self)

            twitter_settings.event_add_interaction(tweet_id=self.tweet_id, user_twitter_id=user_twitter_id, interaction="Retweet")

            if (self.currency == "social_credits"):
                currency_name = points_settings.get_currency_name(interaction.guild_id)
                points_settings.add_user_points(user_id=interaction.user.id, points=self.reward)
            else:
                currency_name = "Social Tokens"
                points_settings.add_user_tokens(user_id=interaction.user.id, points=self.reward)
            
            await command_respond.respond(interaction=interaction, color=0x00ff00, title="Successful!", description=f"You have succesfully received **{self.reward} {currency_name}** for retweeting our Tweet!")
            await self._respond_dm(interaction, message=f"You have succesfully received **{self.reward} {currency_name}** for retweeting our Tweet!")
        except Exception as e:
            print(f"Retweet Error: {e}")


    @discord.ui.button(label="Comment", style=discord.ButtonStyle.green, emoji="<:comment:1258006997769523211>", custom_id="twitter_event_buttons:comment")
    async def comment_button(self, interaction: discord.Interaction, button: discord.ui):
        if (time.time() > self.expires_epoch):
            await self.disable_buttons()
            await interaction.response.edit_message(content=interaction.message.content, embed=interaction.message.embeds[0], view=self)
            return await command_respond.respond(interaction, color=0xff0000, title="Error!", description="This event has already expired!")
        
        winners_list = twitter_settings.get_event_button_winners(message_id=interaction.message.id)
        if (len(winners_list) >= self.winners):
            if not (interaction.user.id in winners_list):
                return await command_respond.respond(interaction, color=0xff0000, title="You were too late!", description="This event has already reached the maximum winners.", ephemeral=True)
            
        verify_info = await self._get_user_verify_info(interaction.user.id)
        if not verify_info:
            return await self._error_unverified(interaction)
        
        user_twitter_id = verify_info[2]
        user_twitter_access_token = verify_info[3]

        if twitter_settings.event_user_has_interacted(tweet_id=self.tweet_id, user_twitter_id=user_twitter_id, interaction_name="Comment"):
            return await self._respond_error(interaction, message="You have already received a reward for commenting on this Tweet!")

        try:
            params = {
                "expansions": "referenced_tweets.id",
                "max_results": 100
            }
            http = requests.get(f"https://api.x.com/2/users/{user_twitter_id}/tweets", params=params, headers={"Authorization": f"Bearer {user_twitter_access_token}"}).json()

            if "title" in http:
                if http["title"] == "Unauthorized":
                    try:
                        refresh_token = requests.post("http://127.0.0.1:5001/twitter-refresh-token", json={"access_token": user_twitter_access_token}).json()
                        if not "access_token" in refresh_token:
                            raise Exception
                    except Exception:
                        return await self._respond_error(interaction, message="Your Twitter access token has expired and an error has occured while trying to refresh it. Please try relinking your Twitter account.")
                    
                    return await self._respond_error(interaction, message="Your Twitter access token has expired and been refreshed. Please click the button one more time to receive your reward!")

            if "status" in http:
                if http["status"] == 429:
                    return await self._respond_error(interaction, message="You are currently being rate limited to access this feature, please try again in the next 15 minutes.")

            if not "data" in http:
                return await self._respond_error(interaction, message="An error has occured while trying to verify your comment. Please make sure to comment on the Tweet or relinking your Twitter account using the `/link_twitter` command.")
            
            user_commented = False
            
            for tweet in http["data"]:
                if not "referenced_tweets" in tweet:
                    continue

                for ref_tweet in tweet["referenced_tweets"]:
                    if all([ref_tweet["type"] == "replied_to", ref_tweet["id"] == str(self.tweet_id)]):
                        user_commented = True
            
            if not user_commented:
                return await self._respond_error(interaction, message="Oops! It seems that you haven't commented on this Tweet!")

        except Exception as e:
            print(e)

        if not interaction.user.id in winners_list:
            twitter_settings.add_event_button_winner(message_id=interaction.message.id, user_id=interaction.user.id)

            message_content = interaction.message.content
            message_embed = interaction.message.embeds[0]
            message_embed.set_field_at(index=2, name=":trophy: Winners", value=f"{len(twitter_settings.get_event_button_winners(message_id=interaction.message.id))}/{self.winners}")
            await interaction.message.edit(content=message_content, embed=message_embed, view=self)

        twitter_settings.event_add_interaction(tweet_id=self.tweet_id, user_twitter_id=user_twitter_id, interaction="Comment")

        if (self.currency == "social_credits"):
            currency_name = points_settings.get_currency_name(interaction.guild_id)
            points_settings.add_user_points(user_id=interaction.user.id, points=self.reward)
        else:
            currency_name = "Social Tokens"
            points_settings.add_user_tokens(user_id=interaction.user.id, points=self.reward)
        
        await command_respond.respond(interaction=interaction, color=0x00ff00, title="Successful!", description=f"You have succesfully received **{self.reward} {currency_name}** for retweeting our Tweet!")
        await self._respond_dm(interaction, message=f"You have succesfully received **{self.reward} {currency_name}** for commenting on our Tweet!")


class TwitterCommands(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client


    @commands.Cog.listener()
    async def on_ready(self):
        await self.client.tree.sync()
        print(f"{__name__} has been loaded.")
    

    @app_commands.command(name="link_twitter", description="Link your Twitter account with us!")
    @app_commands.guild_only()
    async def link_twitter(self, interaction: discord.Interaction):
        try:
            login_url = requests.get("http://127.0.0.1:5001/twitter-generate-oauth").text
            oauth_state = urllib.parse.parse_qs(login_url)["state"][0]

            twitter_settings.user_verify_start(user_discord_id=interaction.user.id, oauth_state=oauth_state, channel_id=interaction.channel_id)

            await command_respond.respond(interaction, color=0x00ff00, title="Link Twitter", description=f"To link your Twitter account, click [here]({login_url})!", ephemeral=True, footer_text="Do not share this link with others!")
        except Exception as e:
            print(e)


    @app_commands.command(name="twitter_event_create", description="Create a Twitter event for users to earn points.")
    @app_commands.guild_only()
    @app_commands.choices(
        currency=[
            app_commands.Choice(name="Social Credits", value="social_credits"),
            app_commands.Choice(name="Social Tokens", value="social_tokens")
        ]
    )
    async def twitter_event_create(self, interaction: discord.Interaction, tweet: str, reward: int, winners: int, role_to_ping: discord.Role, currency: str = "social_credits"):
        if not (self.client.get_guild(CONFIG["DISCORD_DEVELOPMENT_SERVER"]).get_member(interaction.user.id).guild_permissions.create_events == True):
            return await command_respond.respond(interaction, color=0xff0000, title="Permission Error", description="You do not have permission to use this command.")
        
        tweet_id = re.search(r"/status/(\d+)", tweet).group(1)
        tweet_obj = twitter_settings.TwitterClient.get_tweet(id=tweet_id, user_auth=True, expansions=["author_id"])
        tweet_content = tweet_obj.data.text
        tweet_author_username = tweet_obj.includes["users"][0].username
        tweet_author_url = f"https://x.com/{tweet_author_username}"
        expires_epoch = int(time.time() + 172800)

        currency_name = points_settings.get_currency_name(guild_id=interaction.guild_id) if currency == "social_credits" else "Social Tokens"

        content = f"{role_to_ping.mention}.\n\n**Like**, **Retweet**, and **Reply** to the **[Tweet]({tweet})** for a chance to win!\n*Make sure your Twitter account is linked! To link it use __/link_twitter__!*"
        embed = discord.Embed()
        embed.color = 0x00ffff
        embed.title = f"<:twitter:1266266887017336914> Tweet"
        embed.url = tweet
        embed.description = tweet_content
        embed.add_field(name=":writing_hand: Author", value=f"[@{tweet_author_username}]({tweet_author_url})", inline=True)
        embed.add_field(name=":money_with_wings: Reward", value=f"{reward} {currency_name}", inline=True)
        embed.add_field(name=":trophy: Winners", value=f"0/{winners}", inline=True)
        embed.add_field(name=":white_check_mark: Status", value="Active", inline=True)
        embed.add_field(name=":hourglass: Expires", value=f"<t:{expires_epoch}:R>", inline=True)
        embed.add_field(name=":link: Tweet", value=f"[Open In Browser]({tweet})", inline=True)
        embed.set_footer(text="- Anti-Social Media Team.")

        message: discord.Message = await interaction.channel.send(content=content, embed=embed, view=TwitterEventButtons(tweet_id=tweet_id, reward=reward, winners=winners, expires_epoch=expires_epoch, currency=currency))
        twitter_settings.add_event_button(message_id=message.id, tweet_id=tweet_id, reward=reward, winners=winners, expires_epoch=expires_epoch, currency=currency)
        await command_respond.respond(interaction, color=0x00ff00, title="Twitter Event Create", description="Successfully created a Twitter event for users to earn points.")
        

async def setup(client: commands.Bot):
    await client.add_cog(TwitterCommands(client))
