import sqlite3
import time
import json
import os

database = sqlite3.connect(f"{os.path.dirname(__file__)}/points_database.db", check_same_thread=False)

def _setup_database():
    database.execute('''CREATE TABLE IF NOT EXISTS "USER_POINTS"(
	"ID"	INTEGER NOT NULL,
	"USER_ID"	        INTEGER NOT NULL,
	"POINTS"	        INTEGER,
	PRIMARY KEY("ID" AUTOINCREMENT)
    );''')

    database.execute('''CREATE TABLE IF NOT EXISTS "USER_TOKENS"(
	"ID"	INTEGER NOT NULL,
	"USER_ID"	        INTEGER NOT NULL,
	"TOKENS"	        INTEGER,
	PRIMARY KEY("ID" AUTOINCREMENT)
    );''')

    database.execute('''CREATE TABLE IF NOT EXISTS "USER_DAILY"(
	"ID"	INTEGER NOT NULL,
	"USER_ID"	        INTEGER NOT NULL,
	"LAST_CLAIM"	    INTEGER NOT NULL,
	PRIMARY KEY("ID" AUTOINCREMENT)
    );''')

    database.execute('''CREATE TABLE IF NOT EXISTS "CURRENCY_NAME"(
	"ID"	INTEGER NOT NULL,
	"GUILD_ID"	        INTEGER NOT NULL,
	"CURRENCY_NAME"	    TEXT NOT NULL,
	PRIMARY KEY("ID" AUTOINCREMENT)
    );''')

    database.execute('''CREATE TABLE IF NOT EXISTS "MARKET_INVENTORY"(
	"ID"	INTEGER NOT NULL,
	"USER_ID"	        INTEGER NOT NULL,
	"GUILD_ID"	        INTEGER NOT NULL,
    "ITEM_NAME"	        TEXT NOT NULL,
    "ITEM_PRICE"	    INTEGER NOT NULL,
    "ITEM_IMAGE_URL"    TEXT NOT NULL,
    "SELLER_ID"	        INTEGER NOT NULL,
	PRIMARY KEY("ID" AUTOINCREMENT)
    );''')

    database.execute('''CREATE TABLE IF NOT EXISTS "STAKE_LEADERBOARD"(
	"ID"	INTEGER NOT NULL,
	"USER_ID"	        INTEGER NOT NULL,
	"STAKE_POINTS"	    INTEGER NOT NULL,
	PRIMARY KEY("ID" AUTOINCREMENT)
    );''')

    database.execute('''CREATE TABLE IF NOT EXISTS "POINTS_SHOP"(
	"ID"	INTEGER NOT NULL,
	"USER_ID"	        INTEGER NOT NULL,
	"DESTINATION_TAG"	INTEGER NOT NULL,
    "CHANNEL_ID"        INTEGER NOT NULL,
	PRIMARY KEY("ID" AUTOINCREMENT)
    );''')

    database.execute('''CREATE TABLE IF NOT EXISTS "GOODMORNING"(
	"ID"	INTEGER NOT NULL,
	"USER_ID"	        INTEGER NOT NULL,
	"LAST_CLAIM"	    INTEGER NOT NULL,
	PRIMARY KEY("ID" AUTOINCREMENT)
    );''')

    database.execute('''CREATE TABLE IF NOT EXISTS "UNITY_TRANSFER"(
	"ID"	INTEGER NOT NULL,
	"USER_ID"	        INTEGER NOT NULL,
	PRIMARY KEY("ID" AUTOINCREMENT)
    );''')

    database.execute('''CREATE TABLE IF NOT EXISTS "MARKET_NOTIFICATION"(
	"ID"	INTEGER NOT NULL,
	"GUILD_ID"	        INTEGER NOT NULL,
	"CHANNEL_ID"	    INTEGER NOT NULL,
	PRIMARY KEY("ID" AUTOINCREMENT)
    );''')

    database.execute('''CREATE TABLE IF NOT EXISTS "MARKET_BUTTONS"(
	"ID"	INTEGER NOT NULL,
	"MESSAGE_ID"	    INTEGER NOT NULL,
	"ITEM_NAME"	        TEXT NOT NULL,
    "PRICE"             INTEGER NOT NULL,
    "STOCK"             INTEGER NOT NULL,
    "BUYERS_LIST"       INTEGER,
    "ITEM_IMAGE_URL"    TEXT, 
    "CURRENCY"          TEXT,
	PRIMARY KEY("ID" AUTOINCREMENT)
    );''')

    database.execute('''CREATE TABLE IF NOT EXISTS "AUCTIONS"(
	"ID"	INTEGER NOT NULL,
	"MESSAGE_ID"	    INTEGER NOT NULL,
	"AUCTION_TITLE"	    TEXT NOT NULL,
    "STARTING_BID"	    INTEGER NOT NULL,
    "MIN_OVERBID"       INTEGER NOT NULL,
    "EXPIRATION_EPOCH"  INTEGER NOT NULL,
    "HIGHEST_BID"       INTEGER NOT NULL,
    "HIGHEST_BIDDER_ID" INTEGER,
    "CURRENCY"          TEXT NOT NULL,
    "IMAGE_URL"         TEXT NOT NULL,
    "TOTAL_BIDDERS"     INTEGER NOT NULL,
	PRIMARY KEY("ID" AUTOINCREMENT)
    );''')

    database.execute('''CREATE TABLE IF NOT EXISTS "USER_EXP"(
	"ID"	INTEGER NOT NULL,
    "USER_ID"           INTEGER NOT NULL,
    "EXP"               INTEGER NOT NULL,
	PRIMARY KEY("ID" AUTOINCREMENT)
    );''')

    database.commit()
_setup_database()

def get_user_points(user_id: int):
    user = database.execute(f'SELECT * FROM USER_POINTS WHERE USER_ID={user_id};').fetchone()

    if not user:
        database.execute(f'INSERT INTO USER_POINTS (USER_ID, POINTS) VALUES ({user_id}, 0);')
        database.commit()
        return 0
    
    return user[2]

def set_user_points(user_id: int, points: int):
    get_user_points(user_id=user_id)

    database.execute(f'UPDATE USER_POINTS SET POINTS={points} WHERE USER_ID={user_id};')
    database.commit()

    return True

def add_user_points(user_id: int, points: int):
    user_points = get_user_points(user_id=user_id)

    database.execute(f'UPDATE USER_POINTS SET POINTS={user_points + points} WHERE USER_ID={user_id};')
    database.commit()

    return True

def get_leaderboard():
    return database.execute('SELECT * FROM USER_POINTS WHERE POINTS > 0 ORDER BY POINTS DESC LIMIT 10;').fetchall()

def user_claim_daily(user_id: int):
    get_user_points(user_id=user_id)
    
    last_claim = database.execute(f'SELECT LAST_CLAIM FROM USER_DAILY WHERE USER_ID={user_id};').fetchone()

    if not last_claim:
        database.execute(f'INSERT INTO USER_DAILY (USER_ID, LAST_CLAIM) VALUES ({user_id}, {time.time()});')
        database.commit()
        add_user_points(user_id=user_id, points=100)
        return True
    else:
        time_passed = (time.time() - last_claim[0])
        if time_passed >= 86400:
            database.execute(f'UPDATE USER_DAILY SET LAST_CLAIM="{time.time()}" WHERE USER_ID="{user_id}";')
            database.commit()
            add_user_points(user_id=user_id, points=100)
            return True

    return int(last_claim[0] + 86400)

def user_claim_goodmorning(user_id: int):
    get_user_points(user_id=user_id)
    
    last_claim = database.execute(f'SELECT LAST_CLAIM FROM GOODMORNING WHERE USER_ID={user_id};').fetchone()

    if not last_claim:
        database.execute(f'INSERT INTO GOODMORNING (USER_ID, LAST_CLAIM) VALUES ({user_id}, {time.time()});')
        database.commit()
        add_user_points(user_id=user_id, points=50)
        return True
    else:
        time_passed = (time.time() - last_claim[0])
        if time_passed >= 86400:
            database.execute(f'UPDATE GOODMORNING SET LAST_CLAIM="{time.time()}" WHERE USER_ID="{user_id}";')
            database.commit()
            add_user_points(user_id=user_id, points=50)
            return True

    return False

def get_currency_name(guild_id: int):
    column = database.execute(f'SELECT * FROM CURRENCY_NAME WHERE GUILD_ID={guild_id};').fetchone()

    if not column:
        return "Points"

    return column[2]

def set_currency_name(guild_id: int, currency_name: str):
    exists = database.execute(f'SELECT * FROM CURRENCY_NAME WHERE GUILD_ID={guild_id};').fetchone()

    if exists:
        database.execute(f'UPDATE CURRENCY_NAME SET CURRENCY_NAME="{currency_name}" WHERE GUILD_ID={guild_id};')
    else:
        database.execute(f'INSERT INTO CURRENCY_NAME (GUILD_ID, CURRENCY_NAME) VALUES ({guild_id}, "{currency_name}");')

def get_user_stake_points(user_id: int):
    user = database.execute(f'SELECT * FROM STAKE_LEADERBOARD WHERE USER_ID={user_id};').fetchone()

    if not user:
        database.execute(f'INSERT INTO STAKE_LEADERBOARD (USER_ID, STAKE_POINTS) VALUES ({user_id}, 0);')
        database.commit()
        return 0
    
    return user[2]

def set_user_stake_points(user_id: int, stake_points: int):
    get_user_stake_points(user_id=user_id)

    database.execute(f'UPDATE STAKE_LEADERBOARD SET STAKE_POINTS={stake_points} WHERE USER_ID={user_id};')
    database.commit()

    return True

def add_user_stake_points(user_id: int, stake_points: int):
    user_stake_points = get_user_stake_points(user_id=user_id)

    database.execute(f'UPDATE STAKE_LEADERBOARD SET STAKE_POINTS={user_stake_points + stake_points} WHERE USER_ID={user_id};')
    database.commit()

    return True

def get_stake_leaderboard():
    return database.execute('SELECT * FROM STAKE_LEADERBOARD WHERE STAKE_POINTS > 0 ORDER BY STAKE_POINTS DESC LIMIT 10;').fetchall()

def points_shop_get_destination_tag(destination_tag: int):
    return database.execute(f'SELECT * FROM POINTS_SHOP WHERE DESTINATION_TAG={destination_tag};').fetchone()

def points_shop_get_user(user_id: int):
    return database.execute(f'SELECT * FROM POINTS_SHOP WHERE USER_ID={user_id};').fetchone()

def points_shop_register(user_id: int, destination_tag: int, channel_id: int):
    user = points_shop_get_user(user_id=user_id)
    
    if points_shop_get_destination_tag(destination_tag=destination_tag):
        return False

    if user:
        database.execute(f'UPDATE POINTS_SHOP SET DESTINATION_TAG={destination_tag}, CHANNEL_ID={channel_id} WHERE USER_ID={user_id};')
        database.commit()
        return True
    
    else:
        database.execute(f'INSERT INTO POINTS_SHOP (USER_ID, DESTINATION_TAG, CHANNEL_ID) VALUES ({user_id}, {destination_tag}, {channel_id});')
        database.commit()
        return True

def unity_balance_transfer_check(user_id: int):
    user_exists = database.execute(f'SELECT * FROM UNITY_TRANSFER WHERE USER_ID={user_id};').fetchone()

    if user_exists:
        return True
    else:
        return False

def unity_balance_transfer_insert(user_id: int):
    user_exists = database.execute(f'SELECT * FROM UNITY_TRANSFER WHERE USER_ID={user_id};').fetchone()

    if user_exists:
        return False
    else:
        database.execute(f'INSERT INTO UNITY_TRANSFER (USER_ID) VALUES ({user_id});')
        database.commit()
        return True
    
def get_market_notification_id(guild_id: int):
    col = database.execute(f'SELECT CHANNEL_ID FROM MARKET_NOTIFICATION WHERE GUILD_ID={guild_id};').fetchone()

    if not col:
        return

    return col[0]

def set_market_notification(guild_id: int, channel_id: int):
    if get_market_notification_id(guild_id):
        database.execute(f'UPDATE MARKET_NOTIFICATION SET CHANNEL_ID={channel_id} WHERE GUILD_ID={guild_id};')
        database.commit()
    else:
        database.execute(f'INSERT INTO MARKET_NOTIFICATION (GUILD_ID, CHANNEL_ID) VALUES ({guild_id}, {channel_id});')
        database.commit()
    
def add_market_button(message_id: int, item_name: str, price: int, stock: int, item_image_url: str, currency: str):
    if database.execute(f'SELECT * FROM MARKET_BUTTONS WHERE MESSAGE_ID={message_id};').fetchone():
        return
    
    database.execute(f'''INSERT INTO MARKET_BUTTONS
    (MESSAGE_ID, ITEM_NAME, PRICE, STOCK, BUYERS_LIST, ITEM_IMAGE_URL, CURRENCY)
    VALUES
    ({message_id}, "{item_name}", {price}, {stock}, \'[]\', "{item_image_url}", "{currency}");''')
    database.commit()


def get_market_buttons():
    return database.execute(f'SELECT * FROM MARKET_BUTTONS;').fetchall()

def get_market_button(message_id: int):
    return database.execute(f'SELECT * FROM MARKET_BUTTONS WHERE MESSAGE_ID={message_id};').fetchone()

def market_button_get_buyers(message_id: int):
    current_stocks = database.execute(f'SELECT BUYERS_LIST FROM MARKET_BUTTONS WHERE MESSAGE_ID={message_id};').fetchone()
    if not current_stocks:
        return
    
    return json.loads(current_stocks[0])

def market_button_add_buyer(message_id: int, user_id: int):
    current_buyers = market_button_get_buyers(message_id=message_id)
    if not type(current_buyers) == list:
        return
    
    current_buyers.append(user_id)
    current_buyers = json.dumps(current_buyers)

    database.execute(f'UPDATE MARKET_BUTTONS SET BUYERS_LIST=\'{current_buyers}\' WHERE MESSAGE_ID={message_id};')
    database.commit()

def get_auction(message_id: int):
    return database.execute(f'SELECT * FROM AUCTIONS WHERE MESSAGE_ID={message_id};').fetchone()

def get_auctions():
    return database.execute(f'SELECT * FROM AUCTIONS;').fetchall()

def register_auction(message_id: int, auction_title: str, starting_bid: int, min_overbid: int, expiration_epoch: int, currency: str, image_url: str):
    if get_auction(message_id=message_id):
        return False
    
    database.execute(f'''INSERT INTO AUCTIONS
    (MESSAGE_ID, AUCTION_TITLE, STARTING_BID, MIN_OVERBID, EXPIRATION_EPOCH, HIGHEST_BID, HIGHEST_BIDDER_ID, CURRENCY, IMAGE_URL, TOTAL_BIDDERS)
    VALUES
    ({message_id}, "{auction_title}", {starting_bid}, {min_overbid}, {expiration_epoch}, {min_overbid}, NULL, "{currency}", "{image_url}", 0);''')
    database.commit()

def set_auction_bid(message_id: int, highest_bid: int, highest_bidder_id: int):
    if not get_auction(message_id=message_id):
        return False

    database.execute(f'UPDATE AUCTIONS SET TOTAL_BIDDERS = TOTAL_BIDDERS + 1 WHERE MESSAGE_ID={message_id};')
    database.execute(f'UPDATE AUCTIONS SET HIGHEST_BID={highest_bid}, HIGHEST_BIDDER_ID={highest_bidder_id} WHERE MESSAGE_ID={message_id};')
    database.commit()

def get_user_tokens(user_id: int):
    user = database.execute(f'SELECT * FROM USER_TOKENS WHERE USER_ID={user_id};').fetchone()

    if not user:
        database.execute(f'INSERT INTO USER_TOKENS (USER_ID, TOKENS) VALUES ({user_id}, 0);')
        database.commit()
        return 0
    
    return user[2]

def set_user_tokens(user_id: int, points: int):
    get_user_tokens(user_id=user_id)

    database.execute(f'UPDATE USER_TOKENS SET TOKENS={points} WHERE USER_ID={user_id};')
    database.commit()

    return True

def add_user_tokens(user_id: int, points: int):
    user_points = get_user_tokens(user_id=user_id)

    database.execute(f'UPDATE USER_TOKENS SET TOKENS={user_points + points} WHERE USER_ID={user_id};')
    database.commit()

    return True

def get_user_exp(user_id: int):
    user_exp = database.execute(f'SELECT * FROM USER_EXP WHERE USER_ID={user_id};').fetchone()

    if user_exp:
        return user_exp[2]
    
    else:
        database.execute(f'INSERT INTO USER_EXP (USER_ID, EXP) VALUES ({user_id}, 0);')
        database.commit()

        return 0

def set_user_exp(user_id: int, exp: int):
    get_user_exp(user_id=user_id)

    database.execute(f'UPDATE USER_EXP SET EXP={exp} WHERE USER_ID={user_id};')
    database.commit()

def add_user_exp(user_id: int, exp: int):
    current_exp = get_user_exp(user_id=user_id)

    database.execute(f'UPDATE USER_EXP SET EXP={current_exp}+{exp} WHERE USER_ID={user_id};')
    database.commit()

def purge():
    database.execute(f'UPDATE USER_POINTS SET POINTS=0;')
    database.execute(f'UPDATE STAKE_LEADERBOARD SET STAKE_POINTS=0;')
    database.commit()
