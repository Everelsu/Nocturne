import asyncio
import os
import functools
import update

from dotenv import load_dotenv
from datetime import timedelta

from hypercorn import Config
from hypercorn.asyncio import serve
from babel import Locale

from quart_babel import Babel
from quart import (
    Quart,
    render_template,
    redirect,
    url_for,
    jsonify,
    session,
    websocket,
    request
)

from objects import (
    Settings,
    UserPool,
    BotPool,
    User
)

from utils import (
    DISCORD_API_BASE_URL,
    ROOT_DIR,
    LANGUAGES,
    get_locale,
    requests_api,
    process_js_files,
    compile_scss,
    download_geoip_db,
    check_country_with_ip,
    check_version,
    setup_logging
)

SETTINGS: Settings = Settings()

app = Quart(__name__)
app.secret_key = SETTINGS.secret_key

babel = Babel(app)
babel.init_app(app, locale_selector=get_locale)

load_dotenv()

def login_required(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        token = session.get("discord_token", None)
        if not token:
            return redirect(url_for('login'))

        user = UserPool.get(token=token)
        if not user:
            resp = await requests_api(f'{DISCORD_API_BASE_URL}/users/@me', headers={'Authorization': f'Bearer {token}'})
            if resp:
                resp["access_token"] = token
                user = UserPool.add(resp)
            else:
                return redirect(url_for('login'))
            
        return await func(user, *args, **kwargs)
    return wrapper

@app.before_serving
async def setup():
    lang_codes = ["en"] + [
        lang for lang in os.listdir(os.path.join(ROOT_DIR, "translations"))
        if not lang.startswith(".")
    ]
    for lang_code in lang_codes:
        LANGUAGES[lang_code] = {"name": Locale.parse(lang_code).get_display_name(lang_code).capitalize()}

    process_js_files()
    compile_scss()
    asyncio.ensure_future(download_geoip_db())

@app.route("/health", methods=["GET"])
async def health():
    return jsonify({"status": "ok"}), 200

@app.route("/", methods=["GET"])
async def home():
    token = session.get("discord_token", None)
    if not token:
        return redirect(url_for('login'))
    
    user = UserPool.get(token=token)

    forwarded_for = request.headers.get('X-Forwarded-For')
    user_ip = forwarded_for.split(',')[0] if forwarded_for else request.remote_addr
    country = await check_country_with_ip(user_ip)

    if not user:
        resp = await requests_api(f'{DISCORD_API_BASE_URL}/users/@me', headers={'Authorization': f'Bearer {token}'})
        if resp:
            resp["access_token"] = token
            resp["country"] = country
            user = UserPool.add(resp)
        else:
            return redirect(url_for('login'))

    else:
        user.country = country

    return await render_template("index.html", user=user, languages=LANGUAGES)

@app.route("/login", methods=["GET"])
async def login():
    params = {
        'client_id': SETTINGS.client_id,
        'response_type': 'code',
        'redirect_uri': SETTINGS.redirect_url,
        'scope': 'identify+guilds'
    }
    return redirect(f'{DISCORD_API_BASE_URL}/oauth2/authorize?{"&".join([f"{k}={v}" for k, v in params.items()])}')

@app.route('/logout', methods=["GET"])
@login_required
async def logout(user: User):
    session.pop("discord_token", None)
    
    return redirect(url_for("home"))

@app.route('/callback')
async def callback():
    code = request.args.get('code')
    data = {
        'client_id': SETTINGS.client_id,
        'client_secret': SETTINGS.client_secret_id,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': SETTINGS.redirect_url,
        'scope': 'identify'
    }
    token_data = await requests_api(f'{DISCORD_API_BASE_URL}/oauth2/token', 'POST', data=data)
    if token_data:
        session.permanent = True
        app.permanent_session_lifetime = timedelta(days=30)
        session['discord_token'] = token_data.get("access_token")

    return redirect(url_for("home"))

@app.route('/language/<language>')
@login_required
async def set_language(user: User, language = None):
    if language in LANGUAGES:
        session["language_code"] = language
    return redirect(url_for('home'))

@app.errorhandler(404)
async def not_found(error):
    return redirect(url_for("home"))

@app.route("/proxy/image")
async def proxy_image():
    from urllib.parse import urlparse
    import aiohttp as _aiohttp
    url = request.args.get("url", "")
    try:
        parsed = urlparse(url)
    except Exception:
        return "", 400

    ALLOWED_HOSTS = {
        "avatars.mds.yandex.net",
        "avatars.yandex.net",
        "sun9-north.userapi.com",
        "sun9-south.userapi.com",
        "e-cdns-images.dzcdn.net",
        "is1-ssl.mzstatic.com",
    }
    if not url or parsed.scheme not in ("http", "https") or parsed.hostname not in ALLOWED_HOSTS:
        return "", 400

    try:
        async with _aiohttp.ClientSession() as client:
            async with client.get(url, timeout=_aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return "", resp.status
                content = await resp.read()
                content_type = resp.headers.get("Content-Type", "image/jpeg")
        return content, 200, {
            "Content-Type": content_type,
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=86400",
        }
    except Exception:
        return "", 502

@app.websocket("/ws_bot")
async def ws_bot():
    try:
        header = websocket.headers
        if header.get("Authorization") != SETTINGS.password:
            return await websocket.close(1008, "Incorrect password!")
            
        if not (bot_id := header.get("User-Id")):
            return await websocket.close(1001, "Missing user id!")
        
        if not check_version(header.get("Client-Version")):
            return await websocket.close(1002, "Version mismatch!")
        
        await BotPool.create(bot_id, websocket._get_current_object())
        
    except asyncio.CancelledError:
        raise

@app.websocket("/ws_user")
@login_required
async def ws_user(user: User):
    try:
        await user.connect(websocket._get_current_object())
    except asyncio.CancelledError:
        raise

if __name__ == "__main__":
    update.check_version(with_msg=True)
    setup_logging(SETTINGS.logging)
    config = Config()
    config.bind = [f"{SETTINGS.host}:{SETTINGS.port}"]
    asyncio.run(serve(app, config))

    # For Testing
    # app.run(host=SETTINGS.host, port=SETTINGS.port, debug=True)