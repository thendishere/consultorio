from fastapi.templating import Jinja2Templates
from markupsafe import Markup
import hmac
import hashlib

templates = Jinja2Templates(directory="app/templates")


def _csrf_input(request) -> Markup:
    from .config import get_settings
    cookie_token = request.cookies.get("csrf_token", "")
    signed = hmac.new(get_settings().secret_key.encode(), cookie_token.encode(), hashlib.sha256).hexdigest()
    return Markup(f'<input type="hidden" name="csrf_token" value="{signed}">')


templates.env.globals["csrf_input"] = _csrf_input
templates.env.globals["enumerate"] = enumerate
