from flask import Flask, request, render_template
from components import twitter_settings, xaman_settings
import requests
import tweepy
import toml

CONFIG = toml.load("./src/config.toml")
app = Flask(__name__)

def _response(title: str, message: str, status_code: int):
    return render_template("response.html", title=title, message=message), status_code

@app.route("/link-twitter")
def link_twitter():
    if not all(["state" in request.args, "code" in request.args]):
        return _response(title="Error!", message="ERROR: Invalid URL!", status_code=400)

    oauth_state = request.args.get("state")
    oauth_code = request.args.get("code")

    try:
        oauth_state_info = twitter_settings.get_oauth_state(oauth_state=oauth_state)
        if not oauth_state:
            raise Exception
        
        user_discord_id = oauth_state_info[1]
        channel_id = oauth_state_info[6]
        
        required_keys = ["access_token", "refresh_token", "scope"]
        required_scopes = twitter_settings.twitter_oauth2.scope

        token_info = requests.post("http://127.0.0.1:5001/twitter-validate-oauth", json={"url": request.url}).json()
        
        for key in required_keys:
            if not key in token_info:
                raise Exception
        
        for scope in required_scopes:
            if not scope in token_info["scope"]:
                raise Exception
        
        twitter_user_info = requests.get("https://api.twitter.com/2/users/me", headers={"Authorization": f"Bearer {token_info['access_token']}"}).json()["data"]
        user_twitter_id = twitter_user_info["id"]

        twitter_id_info = twitter_settings.get_twitter_user(user_twitter_id=user_twitter_id)
        if twitter_id_info:
            if not (twitter_id_info[1] == user_discord_id):
                requests.post(
                    "https://discord.com/api/v9/channels/<REDACTED>/messages",
                    headers={
                        "Authorization": f"Bot {CONFIG['DISCORD_BOT_TOKEN']}"
                    },
                    json={
                        "embeds": [{
                            "title": "Multi-Account Detection System",
                            "description": f"<@{user_discord_id}> just tried to link an already linked Twitter account!\n**Twitter ID**: {user_twitter_id}\n**Linked Discord**: <@{twitter_id_info[1]}>",
                            "color": 0xff0000
                        }]
                    })
                return _response(title="Error!", message="This Twitter account has already been linked to another Discord account!", status_code=400)
    except Exception as e:
        return _response(title="Error!", message=f"An error has occured while trying to verify your request.", status_code=400)

    requests.post(
        f"https://discord.com/api/v9/channels/{channel_id}/messages",
        headers={
            "Authorization": f"Bot {CONFIG['DISCORD_BOT_TOKEN']}"
        },
        json={
            "embeds": [{
                "title": "Successfully Linked!",
                "description": f"<@{user_discord_id}> Your Twitter account has successfully been linked!",
                "color": 0x00ff00
            }]
        })
    
    twitter_settings.user_verified(user_discord_id=user_discord_id, user_twitter_id=user_twitter_id, access_token=token_info["access_token"], refresh_token=token_info["refresh_token"], token_url=request.url)
    return _response(title="Success!", message=f"You have successfully linked your Twitter account. Your Twitter ID: {user_twitter_id}", status_code=200)


@app.route("/link-instagram")
def link_instagram():
    oauth_state = request.args.get("state")
    oauth_code = request.args.get("code")
    if not all([oauth_code, oauth_state]):
        return _response(title="Error!", message="ERROR: Invalid URL.", status_code=400)
    
    try:
        oauth_validate = requests.post("http://127.0.0.1:5001/instagram-validate-oauth", json={"code": oauth_code}).json()
    except Exception:
        return _response(title="Error!", message="An error has occured while trying to verify your request.", status_code=400)

    return _response(title="Success!", message=f"You have successfully linked your Instagram account. Validate: {oauth_validate}", status_code=200)

@app.route("/link-xaman", methods=["POST"])
def link_xaman():
    data = request.get_json(force=True)

    if not "meta" in data:
        return
    
    if not "payload_uuidv4" in data["meta"]:
        return
    payload_uuid = data["meta"]["payload_uuidv4"]

    url = f"https://xumm.app/api/v1/platform/payload/{payload_uuid}"

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "X-API-Key": "<REDACTED>",
        "X-API-Secret": "<REDACTED>"
    }

    payload_get = requests.get(url, headers=headers).json()
    if not "response" in payload_get:
        return
    if not "account" in payload_get["response"]:
        return
    account_address = payload_get["response"]["account"]

    xaman_settings.set_uuid_wallet(uuid=payload_uuid, xrp_address=account_address)

    return 200, "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
