import sqlite3
import os

database = sqlite3.connect(f"{os.path.dirname(__file__)}/xaman_database.db", check_same_thread=False)

def _setup_database():
    database.execute('''CREATE TABLE IF NOT EXISTS "XAMAN_WALLETS"(
	"ID"	INTEGER NOT NULL,
	"DISCORD_ID"	    INTEGER NOT NULL,
	"XRP_ADDRESS"	    TEXT,
    "UUID"              TEXT NOT NULL,
	PRIMARY KEY("ID" AUTOINCREMENT)
    );''')

_setup_database()

def get_discord_id(discord_id: int):
    return database.execute(f'SELECT * FROM XAMAN_WALLETS WHERE DISCORD_ID={discord_id};').fetchone()

def register_user(discord_id: int, uuid: str):
    if get_discord_id(discord_id=discord_id):
        database.execute(f'UPDATE XAMAN_WALLETS SET UUID="{uuid}" WHERE DISCORD_ID={discord_id}')
        database.commit()
        return True
    else:
        database.execute(f'INSERT INTO XAMAN_WALLETS (DISCORD_ID, UUID) VALUES ({discord_id}, "{uuid}");')
        database.commit()
        return True

def set_uuid_wallet(uuid: str, xrp_address: str):
    if not database.execute(f'SELECT * FROM XAMAN_WALLETS WHERE UUID="{uuid}";').fetchone():
        return
    
    database.execute(f'UPDATE XAMAN_WALLETS SET XRP_ADDRESS="{xrp_address}" WHERE UUID="{uuid}";')
    database.commit()
