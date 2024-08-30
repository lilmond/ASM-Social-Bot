# This code was modified from: https://xrpl.org/docs/tutorials/http-websocket-apis/build-apps/monitor-incoming-payments-with-websocket
# Learn more about incoming payments in the XRPL in the link above.

from components import points_settings
from xrpl.utils import drops_to_xrp
import websockets
import requests
import asyncio
import json
import toml


CONFIG = toml.load("./src/config.toml")


# Using client libraries for ASYNC functions and websockets are needed in python.
# To install, use terminal command 'pip install asyncio && pip install websockets'

# Handles incoming messages
async def handler(websocket):
    message = await websocket.recv()
    return message


# Use this to send API requests
async def api_request(options, websocket):
    try:
        await websocket.send(json.dumps(options))
        message = await websocket.recv()
        return json.loads(message)
    except Exception as e:
        return e


# Tests functionality of API_Requst
async def pingpong(websocket):
    command = {
        "id": "on_open_ping_1",
        "command": "ping"
    }
    value = await api_request(command, websocket)
    print(value)


async def do_subscribe(websocket):
    command = await api_request({
        'command': 'subscribe',
        'accounts': [CONFIG["POINTS_SHOP_WALLET"]]
        }, websocket)

    if command['status'] == 'success':
        print('Successfully Subscribed!')

    else:
        print("Error subscribing: ", command)
    
    message = json.loads(await handler(websocket))
    transaction = message["transaction"]
    sender_address = transaction["Account"]
    destination_tag = transaction["DestinationTag"]
    amount = drops_to_xrp(transaction["Amount"])
    tx_hash = transaction["hash"]

    points_shop_info = points_settings.points_shop_get_destination_tag(destination_tag=destination_tag)
    
    if not points_shop_info:
        return

    points_shop_id, user_discord_id, destination_tag, channel_id = points_shop_info
    points_settings.add_user_points(user_discord_id, points=int(amount * 100))

    print(f"Transaction: {sender_address} -> {destination_tag} {amount} XRP")

    requests.post("https://discord.com/api/v9/channels/<REDACTED>/messages",
        headers={
            "Authorization": f'Bot {CONFIG["DISCORD_BOT_TOKEN"]}'
        },
        json={
            "embeds": [{
                "title": f"{points_settings.get_currency_name(<REDACTED>)} Shop",
                "description": f"**User**: <@{user_discord_id}>\n**Sender**: {sender_address}\n**Destination Tag**: {destination_tag}\n**Amount**: {amount} XRP\n**Transaction**: [Explorer](https://xrpscan.com/tx/{tx_hash})",
                "color": 0x00ff00
            }]
        }
    )

    requests.post(f"https://discord.com/api/v9/channels/{channel_id}/messages",
        headers={
            "Authorization": f'Bot {CONFIG["DISCORD_BOT_TOKEN"]}'
        },
        json={
            "embeds": [{
                "title": f"Purchase Successful!",
                "description": f"<@{user_discord_id}> You have successfully purchased **{int(100 * amount)} {points_settings.get_currency_name(guild_id=<REDACTED>)}** for **{amount} XRP**.\nTransaction: [Explorer](https://xrpscan.com/tx/{tx_hash})",
                "color": 0x00ff00
            }]
        }
    )


async def run():
    # Opens connection to ripple testnet
    async for websocket in websockets.connect('wss://xrplcluster.com/'):
        try:
           await pingpong(websocket)
           await do_subscribe(websocket)
        except websockets.ConnectionClosed:
            print('Disconnected...')


# Runs the webhook on a loop
def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
    loop.close()
    print('Restarting Loop')


if __name__ == '__main__':
    main()
