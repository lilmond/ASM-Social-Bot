from components import points_settings, command_respond
from discord.ext import commands
from discord import app_commands
import discord
import random
import toml
import os


CONFIG = toml.load(f"{os.path.dirname(__file__)}/../src/config.toml")


class GameEmbed(discord.Embed):
    def __init__(self, player: discord.User, title: str, description: str):
        super().__init__()

        self.color = 0xff6400
        self.title = title
        self.description = description
        self.set_author(name=f"{player.name}'s Game", icon_url=player.display_avatar.url)


class HighlowGame(discord.ui.View):
    def __init__(self, player: discord.User, bet: int, hint_number: int, jackpot_number: int, embed: discord.Embed):
        self.player = player
        self.bet = bet
        self.hint_number = hint_number
        self.jackpot_number = jackpot_number
        self.embed = embed
        self.played = False

        super().__init__(timeout=60)

    
    async def _win(self, interaction: discord.Interaction):
        prize = int(self.bet * 0.2)

        points_settings.add_user_points(user_id=self.player.id, points=prize)
        points_settings.add_user_stake_points(user_id=self.player.id, stake_points=prize)

        self.embed.color = 0x00ff00
        self.embed.title = f"You won **{prize} {points_settings.get_currency_name(interaction.guild_id)}**!"
        self.embed.description = f"Your hint was **{self.hint_number}**. The jackpot number was **{self.jackpot_number}**."
        self.embed.set_footer(text="Winning prize: (bet x 0.2)")

        await interaction.response.edit_message(embed=self.embed, view=self)


    async def _lose(self, interaction: discord.Interaction):
        points_settings.add_user_points(user_id=interaction.user.id, points=-self.bet)

        self.embed.color = 0xff0000
        self.embed.title = f"You lost **{self.bet} {points_settings.get_currency_name(interaction.guild_id)}**."
        self.embed.description = f"Your hint was **{self.hint_number}**. The jackpot number was **{self.jackpot_number}**."
        self.embed.set_footer()

        await interaction.response.edit_message(embed=self.embed, view=self)


    async def _jackpot(self, interaction: discord.Interaction):
        points_settings.add_user_points(user_id=interaction.user.id, points=int(self.bet * 2))
        points_settings.add_user_stake_points(user_id=self.player.id, stake_points=int(self.bet * 2))

        self.embed.color = 0x00ff00
        self.embed.title = f"You hit the JACKPOT!"
        self.embed.description = f"Woah! You just hit the jackpot and won **{self.bet * 2} {points_settings.get_currency_name(interaction.guild_id)}**."
        self.embed.set_footer(text="Jackpot prize: (bet x 2)")

        await interaction.response.edit_message(embed=self.embed, view=self)


    async def _disable_buttons(self):
        for child in self.children:
            if (type(child) == discord.ui.Button):
                child.disabled = True


    @discord.ui.button(label="Lower", style=discord.ButtonStyle.blurple)
    async def lower_button(self, interaction: discord.Interaction, button: discord.ui):
        if not (interaction.user.id == self.player.id): return
        if self.played: return
        self.played = True
        
        await self._disable_buttons()

        if (self.jackpot_number < self.hint_number):
            await self._win(interaction)
        else:
            await self._lose(interaction)


    @discord.ui.button(label="JACKPOT!", style=discord.ButtonStyle.blurple)
    async def jackpot_button(self, interaction: discord.Interaction, button: discord.ui):
        if not (interaction.user.id == self.player.id): return
        if self.played: return
        self.played = True
        
        await self._disable_buttons()

        if (self.jackpot_number == self.hint_number):
            await self._jackpot(interaction)
        else:
            await self._lose(interaction)


    @discord.ui.button(label="Higher", style=discord.ButtonStyle.blurple)
    async def higher_button(self, interaction: discord.Interaction, button: discord.ui):
        if not (interaction.user.id == self.player.id): return
        if self.played: return
        self.played = True
        
        await self._disable_buttons()

        if (self.jackpot_number > self.hint_number):
            await self._win(interaction)
        else:
            await self._lose(interaction)


class ApeGame(discord.ui.View):
    def __init__(self, bet: int, player_id: int, embed: discord.Embed):
        self.bet = bet
        self.player_id = player_id
        self.embed = embed
        self.player_chose = False

        super().__init__(timeout=60)


    async def _start_game(self, interaction: discord.Interaction, player_bet: str):
        if self.player_chose: return
        self.player_chose = True

        cases_odds = {
            -10: 36,
            -50: 15,
            -100: 10,
            10: 35,
            50: 10,
            100: 6,
            200: 2.2
        }

        odds_list = {}
        odds_total = 0
        cases_keys = list(cases_odds.copy())
        random.shuffle(cases_keys)

        for case in cases_keys:
            num = cases_odds[case]
            odds_list[(odds_total, odds_total + num)] = case
            odds_total += num

        cases_list = []

        for i in range(3):
            rand_num = random.uniform(0, odds_total)
            for chance in odds_list:
                if all([rand_num >= chance[0], rand_num <= chance[1]]):
                    cases_list.append(odds_list[chance])
                    break

        coins_prices = {
            "Pork Coin": cases_list[0],
            "Slork Coin": cases_list[1],
            "Mork Coin": cases_list[2]
        }
        player_mult = coins_prices[player_bet]
        prize = int((self.bet * player_mult) / 100)

        points_settings.add_user_points(user_id=self.player_id, points=prize)
        if (prize > 0):
            points_settings.add_user_stake_points(user_id=self.player_id, stake_points=prize)

        self.embed = interaction.message.embeds[0]
        self.embed.title = "Ape Game Result:"
        self.embed.description = "\n".join([f"**{k}**: {coins_prices[k]}%" for k in coins_prices])

        if player_mult > 0:
            self.embed.color = 0x00ff00
            self.embed.set_footer(text=f"You betted on {player_bet} and won {player_mult}% profit!")
        else:
            self.embed.color = 0xff0000
            self.embed.set_footer(text=f"You betted on {player_bet} and lost {player_mult}% of your bet.")

        await self.disable_buttons()
        await interaction.response.edit_message(embed=self.embed, view=self)
    

    async def _end_game(self, interaction: discord.Interaction, reason: str):
        self.embed.title = "Game Ended"
        self.embed.description = reason

        await self.disable_buttons()
        return await interaction.response.edit_message(embed=self.embed, view=self)
    

    async def disable_buttons(self):
        for child in self.children:
            if type(child) == discord.ui.Button:
                child.disabled = True
    

    @discord.ui.button(label="Pork Coin", style=discord.ButtonStyle.blurple)
    async def pork_coin(self, interaction: discord.Interaction, button: discord.ui):
        if not (interaction.user.id == self.player_id):
            return
        
        if (points_settings.get_user_points(interaction.user.id) < self.bet):
            return await self._end_game(interaction=interaction, reason="The player did not have enough points to place a bet.")
        
        await self._start_game(interaction=interaction, player_bet="Pork Coin")


    @discord.ui.button(label="Slork Coin", style=discord.ButtonStyle.blurple)
    async def slork_coin(self, interaction: discord.Interaction, button: discord.ui):
        if not (interaction.user.id == self.player_id):
            return
        
        if (points_settings.get_user_points(interaction.user.id) < self.bet):
            return await self._end_game(interaction=interaction, reason="The player did not have enough points to place a bet.")
        
        await self._start_game(interaction=interaction, player_bet="Slork Coin")


    @discord.ui.button(label="Mork Coin", style=discord.ButtonStyle.blurple)
    async def mork_coin(self, interaction: discord.Interaction, button: discord.ui):
        if not (interaction.user.id == self.player_id):
            return
        
        if (points_settings.get_user_points(interaction.user.id) < self.bet):
            return await self._end_game(interaction=interaction, reason="The player did not have enough points to place a bet.")
        
        await self._start_game(interaction=interaction, player_bet="Mork Coin")


class SpinwheelButton(discord.ui.View):
    def __init__(self, player: discord.User, embed: discord.Embed):
        self.player = player
        self.embed = embed
        self.spinned = False
        self.respin = False

        super().__init__(timeout=60)

    @discord.ui.button(label="SPIN!", style=discord.ButtonStyle.green)
    async def spin_button(self, interaction: discord.Interaction, button: discord.ui):
        if self.spinned:
            return
        
        if not (interaction.user.id == self.player.id):
            return
        
        currency_name = points_settings.get_currency_name(guild_id=interaction.guild_id)
        
        if (points_settings.get_user_points(user_id=self.player.id) < 100):
            self.embed.color = 0xff0000
            self.embed.description = f"You need at least **100 {currency_name}** to spin the wheel!"
            self.spin_button.disabled = True
            return await interaction.response.edit_message(embed=self.embed, view=self)

        self.spinned = True
        self.spin_button.disabled = True

        if not self.respin:
            points_settings.add_user_points(user_id=interaction.user.id, points=-100)

        prizes_odds = {
            0: 70,
            "FREE SPIN": 20,
            250: 5,
            500: 4,
            "Common NFT": 0.7,
            "Rare NFT": 0.2,
            "Legendary NFT": 0.05,
            "Unique NFT": 0.049,
            "Mythical NFT": 0.001
        }

        total_nums = 0
        odds_list = {}
        odds_keys = list(prizes_odds)
        random.shuffle(odds_keys)

        for prize in odds_keys:
            num = prizes_odds[prize]
            odds_list[(total_nums, total_nums + num)] = prize
            total_nums += num

        rand_num = random.uniform(0, total_nums)

        for chance in odds_list:
            if all([rand_num >= chance[0], rand_num <= chance[1]]):
                prize_result = odds_list[chance]
                break
        
        result = prize_result

        if result == "FREE SPIN":
            self.embed.color = 0x00ff00
            self.embed.description = f"The wheel stopped at **FREE SPIN**, so you get a chance to spin the wheel one more time for free!"
            self.spinned = False
            self.spin_button.disabled = False
            self.respin = True

            return await interaction.response.edit_message(embed=self.embed, view=self)

        if type(result) == int:
            points_settings.add_user_points(user_id=interaction.user.id, points=result)
        
            self.embed.color = 0x00ff00
            self.embed.description = f"The wheel stopped at **{result} {currency_name}**."
        else:
            self.embed.color = 0x00ff00
            self.embed.description = f"You just won **{result}**, tell one of the staffs in the server to claim your prize!"

        await interaction.response.edit_message(embed=self.embed, view=self)


class MinigameCommands(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        await self.client.tree.sync()
        print(f"{__name__} has been loaded.")
    

    async def _respond_error(self, interaction: discord.Interaction, message: str):
        return await command_respond.respond(interaction, color=0xff0000, title="Error!", description=message, ephemeral=True)
    

    async def _invalid_bet(self, interaction: discord.Interaction, min_bet: int = 1):
        return await self._respond_error(interaction, message=f"Invalid bet value, bet must be higher than {min_bet}!")


    async def _insufficient_points(self, interaction: discord.Interaction):
        return await self._respond_error(interaction, message=f"You do not have sufficient amount of {points_settings.get_currency_name(interaction.guild_id)} to place this bet!")


    @app_commands.command(name="highlow", description="Bored? Play this game and test your luck!")
    @app_commands.guild_only()
    async def highlow(self, interaction: discord.Interaction, bet: int):
        if (bet < 1):
            return await self._invalid_bet(interaction)
        
        if (points_settings.get_user_points(interaction.user.id) < bet):
            return await self._insufficient_points(interaction)

        hint_number = random.randint(1, 100)
        jackpot_number = random.randint(1, 100)

        game_embed = GameEmbed(player=interaction.user, title="Highlow", description=f"I just chose a secret number between 1 and 100.\nIs the secret number *higher or lower* than **{hint_number}**?")
        game_embed.set_footer(text="The jackpot button is if you think it's the same!")
        game_buttons = HighlowGame(player=interaction.user, bet=bet, hint_number=hint_number, jackpot_number=jackpot_number, embed=game_embed)

        await interaction.response.send_message(embed=game_embed, view=game_buttons)


    @app_commands.command(name="ape", description="Play The Ape Game!")
    @app_commands.guild_only()
    async def ape(self, interaction: discord.Interaction, bet: int):
        if (bet < 10):
            return await self._invalid_bet(interaction, min_bet=10)
            
        if (points_settings.get_user_points(user_id=interaction.user.id) < bet):
            return await self._insufficient_points(interaction)

        game_embed = GameEmbed(player=interaction.user, title="The Ape Game", description=f"**The Ape Game** has just begun! Let's have some fun, pick a coin you'd like to place your bet on. The coins' prices will either higher or lower, so goodluck!")
        game_buttons = ApeGame(bet=bet, player_id=interaction.user.id, embed=game_embed)

        return await interaction.response.send_message(embed=game_embed, view=game_buttons)


    @app_commands.command(name="rps", description="Test your luck with rock, paper, scissors!")
    @app_commands.guild_only()
    @app_commands.choices(choice=[
        app_commands.Choice(name="Rock", value="rock"),
        app_commands.Choice(name="Paper", value="paper"),
        app_commands.Choice(name="Scissors", value="scissors")
    ])
    async def rps(self, interaction: discord.Interaction, bet: int, choice: str):
        if (bet < 1):
            return await self._invalid_bet(interaction)
        
        if (points_settings.get_user_points(interaction.user.id) < bet):
            return await self._insufficient_points(interaction)

        bot_choice = random.choice(["rock", "paper", "scissors"])

        message_embed = GameEmbed(player=interaction.user, title="Rock, paper, scissors!", description=None)

        if (bot_choice == choice):
            message_embed.color = 0xffff00
            message_embed.description = f"You chose **{choice}** and I chose **{bot_choice}**. It's a draw so you get your bet back."
            return await interaction.response.send_message(embed=message_embed)
        
        if any([choice == "rock" and bot_choice == "paper", choice == "paper" and bot_choice == "scissors", choice == "scissors" and bot_choice == "rock"]):
            points_settings.add_user_points(interaction.user.id, -bet)
            message_embed.color = 0xff0000
            message_embed.description = f"You chose **{choice}** and I chose **{bot_choice}**. You lost **{bet} {points_settings.get_currency_name(interaction.guild_id)}**."
            return await interaction.response.send_message(embed=message_embed)

        points_settings.add_user_points(interaction.user.id, bet)
        points_settings.add_user_stake_points(user_id=interaction.user.id, stake_points=bet)

        message_embed.color = 0x00ff00
        message_embed.description = f"You chose **{choice}** and I chose **{bot_choice}**. You won **{bet} {points_settings.get_currency_name(interaction.guild_id)}**."
        return await interaction.response.send_message(embed=message_embed)


    @app_commands.command(name="leaderboard", description="Show who has the highest points.")
    @app_commands.guild_only()
    async def leaderboard(self, interaction: discord.Interaction):
        leaderboard = points_settings.get_leaderboard()
        message_embed = discord.Embed()
        message_embed.title = f"{points_settings.get_currency_name(guild_id=interaction.guild_id)} Leaderboard"
        message_embed.color = 0xfc6500

        description = ""
        for i, richest_user in enumerate(leaderboard, 1):
            points_id, richest_user_id, points_value = richest_user
            description += f"**{i}**. <@{richest_user_id}> - **{points_value} {points_settings.get_currency_name(guild_id=interaction.guild_id)}**\n"
        message_embed.description = f"{description}"
        
        return await interaction.response.send_message(embed=message_embed)


    @app_commands.command(name="leaderboard_stake", description="Show who has the highest winning bets.")
    @app_commands.guild_only()
    async def leaderboard_stake(self, interaction: discord.Interaction):
        leaderboard = points_settings.get_stake_leaderboard()
        message_embed = discord.Embed()
        message_embed.title = f"Stake Points Leaderboard"
        message_embed.color = 0xfc6500

        description = ""
        for i, richest_user in enumerate(leaderboard, 1):
            points_id, richest_user_id, stake_value = richest_user
            description += f"**{i}**. <@{richest_user_id}> - **{stake_value} {points_settings.get_currency_name(guild_id=interaction.guild_id)}**\n"
        message_embed.description = f"{description}"
        
        return await interaction.response.send_message(embed=message_embed)


    @app_commands.command(name="claim_daily", description="Claim your daily reward.")
    @app_commands.guild_only()
    async def claim_daily(self, interaction: discord.Interaction):
        try:
            claimed = points_settings.user_claim_daily(user_id=interaction.user.id)

            embed = discord.Embed()
            embed.set_author(name=f"{interaction.user.name}'s Daily Reward", icon_url=interaction.user.display_avatar.url)

            if (claimed == True):
                embed.color = 0x00ff00
                embed.description = f"You have successfully claimed your **100 {points_settings.get_currency_name(guild_id=interaction.guild_id)}** daily reward!"
            else:
                embed.color = 0xff0000
                embed.description = f"You have already claimed your daily reward for today. You may claim again tomorrow at <t:{claimed}:t>."
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            print(e)


    @app_commands.command(name="coinflip", description="Test your luck with coinflip!")
    @app_commands.guild_only()
    @app_commands.choices(side=[
        app_commands.Choice(name="Heads", value="heads"),
        app_commands.Choice(name="Tails", value="tails")
    ])
    async def coinflip(self, interaction: discord.Interaction, bet: int, side: str):
        if (bet < 1):
            return await self._invalid_bet(interaction)
        
        if (points_settings.get_user_points(user_id=interaction.user.id) < bet):
            return await self._insufficient_points(interaction)

        coin_drop = random.choice(["heads", "tails"])
        message_embed = GameEmbed(player=interaction.user, title="Coinflip!", description=None)

        if (side == coin_drop):
            points_settings.add_user_points(user_id=interaction.user.id, points=bet)
            points_settings.add_user_stake_points(user_id=interaction.user.id, stake_points=bet)
            message_embed.color = 0x00ff00
            message_embed.description = f"The coin landed on **{coin_drop}** and you won **{bet} {points_settings.get_currency_name(interaction.guild_id)}**."
        else:
            points_settings.add_user_points(user_id=interaction.user.id, points=-bet)
            message_embed.color = 0xff0000
            message_embed.description = f"The coin landed on **{coin_drop}** and you lost **{bet} {points_settings.get_currency_name(interaction.guild_id)}**."
        
        await interaction.response.send_message(embed=message_embed)

    @app_commands.command(name="plinko", description="Looking for the most legit Plinko game? Play this game of ours!")
    @app_commands.guild_only()
    @app_commands.choices(risk=[
        app_commands.Choice(name="Low", value="low"),
        app_commands.Choice(name="Medium", value="medium"),
        app_commands.Choice(name="High", value="high")
    ])
    async def plinko(self, interaction: discord.Interaction, bet: int, risk: str):
        if (bet < 10):
            return await self._invalid_bet(interaction, min_bet=10)
        
        if (points_settings.get_user_points(interaction.user.id) < bet):
            return await self._insufficient_points(interaction)

        risk_times = {
            "low": [16, 9, 2, 1.4, 1.2, 1.1, 1, 0.5, 0.5, 0.5, 1, 1.1, 1.2, 1.4, 2, 9, 16],
            "medium": [30, 20, 10, 5, 1.5, 1, 0.5, 0.3, 0.3, 0.3, 0.5, 1, 1.5, 5, 10, 20, 30],
            "high": [100, 50, 26, 9, 4, 2, 0.2, 0.1, 0.1, 0.1, 0.2, 2, 4, 9, 26, 50, 100]
        }

        risk_odds = {
            "low": {0.0015: 16, 0.1111: 9, 3.1831: 2, 20.4561: 0.5, 23.8545: 1.4, 29.7771: 1.2, 34.8862: 1.1, 38.6665: 1},
            "medium": {17.4561: 0.3, 12.2197: 0.5, 6.6665: 1, 2.7771: 1.5, 0.8545: 5, 0.1831: 10, 0.0244: 20, 0.0015: 30},
            "high": {17.4561: 0.1, 12.2197: 0.2, 6.1665: 2, 2.5771: 4, 0.8545: 9, 0.1831: 26, 0.0244: 50, 0.0015: 100}
        }

        odds = risk_odds[risk]
        total_nums = 0
        odds_list = {}
        odds_keys = list(odds)
        random.shuffle(odds_keys)

        for num in odds_keys:
            odds_list[(total_nums, total_nums + num)] = odds[num]
            total_nums += num

        rand_num = random.uniform(0, total_nums)

        for chance in odds_list:
            if all([rand_num >= chance[0], rand_num <= chance[1]]):
                landed_times = odds_list[chance]
                break

        #rand_choice = random.randint(0, len(risk_times[risk]) - 1)
        #landed_times = risk_times[risk][rand_choice] # random.choice(risk_times[risk])
        embed = GameEmbed(player=interaction.user, title=f"Plinko! ({risk.capitalize()} Risk)", description=None)

        if (landed_times == 1):
            prize = 0
            embed.description = f"The ball hit **{landed_times}x** so you get your bet back."
            embed.color = 0xffff00
        elif (landed_times > 1):
            prize = int(int(bet * landed_times) - bet)
            points_settings.add_user_stake_points(user_id=interaction.user.id, stake_points=prize)
            embed.description = f"The ball hit **{landed_times}x**, you won **+{prize} {points_settings.get_currency_name(interaction.guild_id)}**."
            embed.color = 0x00ff00
        else:
            prize = -int(bet * (1 - landed_times))
            embed.description = f"The ball hit **{landed_times}x**, you lost **{prize} {points_settings.get_currency_name(interaction.guild_id)}**."
            embed.color = 0xff0000
        
        landed_times_indexes = []
        for i, v in enumerate(risk_times[risk]):
            if (landed_times == v):
                landed_times_indexes.append(i)

        landed_string = risk_times[risk].copy()
        landed_string[random.choice(landed_times_indexes)] = f"**__{landed_times}__**"
        embed.description += f"\n\n**Hit**: {landed_string}"

        points_settings.add_user_points(user_id=interaction.user.id, points=prize)

        await interaction.response.send_message(embed=embed)


    @app_commands.command(name="set_user_points", description="Set a user's points amount.")
    @app_commands.guild_only()
    @app_commands.choices(
        currency=[
            app_commands.Choice(name="Social Credits", value="social_credits"),
            app_commands.Choice(name="Social Tokens", value="social_tokens")
        ]
    )
    async def set_user_points(self, interaction: discord.Interaction, user: discord.User, points: int, currency: str = "social_credits"):
        if not (self.client.get_guild(CONFIG["DISCORD_DEVELOPMENT_SERVER"]).get_member(interaction.user.id).guild_permissions.administrator == True):
            return await command_respond.respond(interaction, color=0xff0000, title="Permission Error", description="You do not have permission to use this command.")

        if currency == "social_credits":
            currency_name = points_settings.get_currency_name(guild_id=interaction.guild_id)
            points_settings.set_user_points(user_id=user.id, points=points)
        elif currency == "social_tokens":
            currency_name = "Social Tokens"
            points_settings.set_user_tokens(user_id=user.id, points=points)
        else:
            return await command_respond.respond(interaction, color=0xff0000, title=f"Invalid currency: {currency}.")
        
        await command_respond.respond(interaction, color=0x00ff00, title="Set User Points!", description=f"Successfully set {user.mention}'s {currency_name}: **{points}**", ephemeral=False)


    @app_commands.command(name="add_user_points", description="Add or deduct a user's points amount, this can be a negative number.")
    @app_commands.guild_only()
    @app_commands.choices(
        currency=[
            app_commands.Choice(name="Social Credits", value="social_credits"),
            app_commands.Choice(name="Social Tokens", value="social_tokens")
        ]
    )
    async def add_user_points(self, interaction: discord.Interaction, user: discord.User, points: int, currency: str = "social_credits"):
        if not (self.client.get_guild(CONFIG["DISCORD_DEVELOPMENT_SERVER"]).get_member(interaction.user.id).guild_permissions.administrator == True):
            return await command_respond.respond(interaction, color=0xff0000, title="Permission Error", description="You do not have permission to use this command.")
        
        if currency == "social_credits":
            currency_name = "Social Credits"
            points_settings.add_user_points(user_id=user.id, points=points)
        elif currency == "social_tokens":
            currency_name = "Social Tokens"
            points_settings.add_user_tokens(user_id=user.id, points=points)
        else:
            return await command_respond.respond(interaction, color=0xff0000, title=f"Invalid currency: {currency}.")

        await command_respond.respond(interaction, color=0x00ff00, title="Added User Points!", description=f"Successfully {'given' if (points > 0) else 'deducted'} {user.mention}'s {currency_name}: **{points}**", ephemeral=False)


    @app_commands.command(name="spinwheel", description="Life is like a wheel, it goes with highs and lows.")
    @app_commands.guild_only()
    async def spinwheel(self, interaction: discord.Interaction):        
        currency_name = points_settings.get_currency_name(interaction.guild_id)

        game_embed = GameEmbed(player=interaction.user, title="Spinwheel!", description=f"Such a fun game everyone knows about. Test your luck now for only **100 {currency_name}**! Your balance will automatically be deducted once you click the **SPIN!** button.")
        game_embed.set_image(url="https://cdn.discordapp.com/attachments/1162592644506075256/1275680668407435284/spin.jpg?ex=66c6c5b4&is=66c57434&hm=68bb3264206f7f449030c6da90e496e6862f5fcb1141ba427a416f0df32982d4&")

        game_button = SpinwheelButton(player=interaction.user, embed=game_embed)

        return await interaction.response.send_message(embed=game_embed, view=game_button)


async def setup(client: commands.Bot):
    await client.add_cog(MinigameCommands(client))
