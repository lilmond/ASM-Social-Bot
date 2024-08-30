from flask import Flask, request
from components import twitter_settings, instagram_settings


twitter_oauth = twitter_settings.twitter_oauth2
app = Flask(__name__)


@app.route("/twitter-generate-oauth")
def twitter_generate_oauth():
    return twitter_oauth.get_authorization_url(), 200


@app.route("/twitter-refresh-token", methods=["POST"])
def twitter_refresh_token():
    data = request.get_json()

    if not data.get("access_token"):
        return "", 400
    
    token = data.get("access_token")

    token_info = twitter_settings.get_access_token(access_token=token)

    if not token_info:
        return "", 400
    
    refresh_token = token_info[4]

    new_token = twitter_oauth.refresh_token("https://api.x.com/2/oauth2/token", refresh_token=refresh_token)
    new_access_token = new_token["access_token"]
    new_refresh_token = new_token["refresh_token"]

    twitter_settings.oauth2_refresh_token(access_token=token, new_access_token=new_access_token, new_refresh_token=new_refresh_token)

    return new_token, 200


@app.route("/twitter-validate-oauth", methods=["POST"])
def twitter_validate_oauth():
    data = request.get_json()

    if not data.get("url"):
        return "", 400
    
    token_url = data.get("url")

    try:
        token_info = twitter_oauth.fetch_token(token_url)
    except Exception:
        return "", 400
    
    return token_info, 200


@app.route("/instagram-generate-oauth")
def instagram_generate_oauth():
    return instagram_settings.instagram_oauth.get_login_url()


@app.route("/instagram-validate-oauth", methods=["POST"])
def instagram_validate_oauth():
    # This function and endpoint is under development, and currently not being used by the bot.
    data = request.get_json()

    if not data.get("code"):
        return "", 400
    
    code = data.get("code")

    short_lived_token = instagram_settings.instagram_oauth.get_o_auth_token(code)
    long_lived_token = instagram_settings.instagram_oauth.get_long_lived_token(short_lived_token["access_token"])

    print(f"Short: {short_lived_token}\nLong: {long_lived_token}")

    return {"short_lived_token": short_lived_token, "long_lived_token": long_lived_token}, 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
