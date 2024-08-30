import sqlite3
import tweepy
import toml
import json
import os

APP_CONFIG = toml.load(f"{os.path.dirname(__file__)}/../src/config.toml")

twitter_oauth2 = tweepy.OAuth2UserHandler(
    client_id=APP_CONFIG["TWITTER_CLIENT_ID"],
    client_secret=APP_CONFIG["TWITTER_CLIENT_SECRET"],
    scope=["tweet.read", "tweet.write", "users.read", "offline.access", "like.read", "like.write"],
    redirect_uri=APP_CONFIG["TWITTER_REDIRECT_URI"],
)

TwitterClient = tweepy.Client(
    bearer_token=APP_CONFIG["TWITTER_BEARER_TOKEN"],
    consumer_key=APP_CONFIG["TWITTER_API_KEY"],
    consumer_secret=APP_CONFIG["TWITTER_API_KEY_SECRET"],
    access_token=APP_CONFIG["TWITTER_ACCESS_TOKEN"],
    access_token_secret=APP_CONFIG["TWITTER_ACCESS_TOKEN_SECRET"]
)

database = sqlite3.connect(f"{os.path.dirname(__file__)}/twitter_database.db", check_same_thread=False)

def _setup_database():
    database.execute('''CREATE TABLE IF NOT EXISTS "VERIFIED_TWITTERS"(
	"ID"	INTEGER NOT NULL,
	"USER_DISCORD_ID"	INTEGER NOT NULL,
	"USER_TWITTER_ID"	INTEGER,
	"ACCESS_TOKEN"	    TEXT,
    "REFRESH_TOKEN"     TEXT,
    "OAUTH_STATE"       TEXT    NOT NULL,
    "CHANNEL_ID"	    INTEGER NOT NULL,
    "TOKEN_URL"         TEXT,
	PRIMARY KEY("ID" AUTOINCREMENT)
    );''')

    database.execute('''CREATE TABLE IF NOT EXISTS "TWITTER_EVENTS"(
    "ID"	INTEGER NOT NULL,
	"TWEET_ID"	        INTEGER NOT NULL,
	"USER_TWITTER_ID"	INTEGER NOT NULL,
	"INTERACTIONS"	    TEXT NOT NULL,
	PRIMARY KEY("ID" AUTOINCREMENT)
    );''')

    database.execute('''CREATE TABLE IF NOT EXISTS "TWITTER_EVENT_BUTTONS"(
    "ID"	INTEGER NOT NULL,
	"MESSAGE_ID"	    INTEGER NOT NULL,
	"TWEET_ID"	        INTEGER NOT NULL,
	"REWARD"	        INTEGER NOT NULL,
    "WINNERS"	        INTEGER NOT NULL,
    "WINNERS_LIST"      TEXT NOT NULL,
    "EXPIRES_EPOCH"     INTEGER NOT NULL,
    "CURRENCY"          TEXT,
	PRIMARY KEY("ID" AUTOINCREMENT)
    );''')
_setup_database()

def user_verify_start(user_discord_id: int, oauth_state: str, channel_id: int):
    if get_discord_user(user_discord_id=user_discord_id):
        database.execute(f'UPDATE VERIFIED_TWITTERS SET OAUTH_STATE="{oauth_state}", CHANNEL_ID={channel_id} WHERE USER_DISCORD_ID={user_discord_id};')
        database.commit()
        return
    
    database.execute(f'INSERT INTO VERIFIED_TWITTERS (USER_DISCORD_ID, OAUTH_STATE, CHANNEL_ID) VALUES ({user_discord_id}, "{oauth_state}", {channel_id});')
    database.commit()

def oauth2_refresh_token(access_token: str, new_access_token: str, new_refresh_token: str):
    database.execute(f'UPDATE VERIFIED_TWITTERS SET ACCESS_TOKEN="{new_access_token}", REFRESH_TOKEN="{new_refresh_token}" WHERE ACCESS_TOKEN="{access_token}";')
    database.commit()

def get_discord_user(user_discord_id: int):
    return database.execute(f'SELECT * FROM VERIFIED_TWITTERS WHERE USER_DISCORD_ID={user_discord_id};').fetchone()

def get_twitter_user(user_twitter_id: int):
    return database.execute(f'SELECT * FROM VERIFIED_TWITTERS WHERE USER_TWITTER_ID={user_twitter_id};').fetchone()

def get_oauth_state(oauth_state: str):
    return database.execute(f'SELECT * FROM VERIFIED_TWITTERS WHERE OAUTH_STATE="{oauth_state}";').fetchone()

def get_access_token(access_token: str):
    return database.execute(f'SELECT * FROM VERIFIED_TWITTERS WHERE ACCESS_TOKEN="{access_token}";').fetchone()

def user_verified(user_discord_id: int, user_twitter_id: int, access_token: str, refresh_token: str, token_url: str):
    database.execute(f'UPDATE VERIFIED_TWITTERS SET USER_TWITTER_ID={user_twitter_id}, ACCESS_TOKEN="{access_token}", REFRESH_TOKEN="{refresh_token}", TOKEN_URL="{token_url}" WHERE USER_DISCORD_ID={user_discord_id};')
    database.commit()

def event_get_interactions(tweet_id: int, user_twitter_id: int):
    return database.execute(f'SELECT * FROM TWITTER_EVENTS WHERE TWEET_ID={tweet_id} AND USER_TWITTER_ID={user_twitter_id};').fetchone()

def event_user_has_interacted(tweet_id: int, user_twitter_id: int, interaction_name: str):
    interactions = event_get_interactions(tweet_id=tweet_id, user_twitter_id=user_twitter_id)

    if not interactions:
        return False
    
    if interaction_name in json.loads(interactions[3]):
        return True
    else:
        return False

def event_add_interaction(tweet_id: int, user_twitter_id: int, interaction: str):
    interactions = event_get_interactions(tweet_id=tweet_id, user_twitter_id=user_twitter_id)

    if interactions:
        user_twitter_id = interactions[2]
        interaction_list: list = json.loads(interactions[3])

        if interaction in interaction_list:
            return False
        
        interaction_list.append(interaction)
        interaction_list = json.dumps(interaction_list)

        database.execute(f'UPDATE TWITTER_EVENTS SET INTERACTIONS=\'{interaction_list}\' WHERE TWEET_ID={tweet_id} AND USER_TWITTER_ID={user_twitter_id};')
        database.commit()
        
        return True
    else:
        interaction_list = json.dumps([interaction])
        
        database.execute(f'INSERT INTO TWITTER_EVENTS (TWEET_ID, USER_TWITTER_ID, INTERACTIONS) VALUES ({tweet_id}, {user_twitter_id}, \'{interaction_list}\');')
        database.commit()

        return True

def add_event_button(message_id: int, tweet_id: int, reward: int, winners: int, expires_epoch: int, currency: str):
    if database.execute(f'SELECT * FROM TWITTER_EVENT_BUTTONS WHERE MESSAGE_ID={message_id}').fetchone(): return

    database.execute(f'''INSERT INTO TWITTER_EVENT_BUTTONS
    (MESSAGE_ID, TWEET_ID, REWARD, WINNERS, WINNERS_LIST, EXPIRES_EPOCH, CURRENCY)
    VALUES
    ({message_id}, {tweet_id}, {reward}, {winners}, \'[]\', {expires_epoch}, "{currency}");
    ''')
    database.commit()

def get_event_buttons():
    return database.execute(f'SELECT * FROM TWITTER_EVENT_BUTTONS;').fetchall()

def get_event_button_winners(message_id: int):
    winners = database.execute(f'SELECT WINNERS_LIST FROM TWITTER_EVENT_BUTTONS WHERE MESSAGE_ID={message_id};').fetchone()
    if not winners:
        return
    return json.loads(winners[0])


def add_event_button_winner(message_id: int, user_id: int):
    current_winners = get_event_button_winners(message_id=message_id)

    if not type(current_winners) == list:
        return
    
    if user_id in current_winners:
        return
    
    current_winners.append(user_id)

    database.execute(f'UPDATE TWITTER_EVENT_BUTTONS SET WINNERS_LIST=\"{json.dumps(current_winners)}\" WHERE MESSAGE_ID={message_id};')
    database.commit()
