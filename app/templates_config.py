from fastapi.templating import Jinja2Templates
from markupsafe import Markup
from datetime import datetime
import hmac
import hashlib

templates = Jinja2Templates(directory="app/templates")


def _csrf_input(request) -> Markup:
    from .config import get_settings
    cookie_token = request.cookies.get("csrf_token", "")
    signed = hmac.new(get_settings().secret_key.encode(), cookie_token.encode(), hashlib.sha256).hexdigest()
    return Markup(f'<input type="hidden" name="csrf_token" value="{signed}">')


def _format_miles(n) -> str:
    try:
        return f"{int(n):,}".replace(",", ".")
    except (TypeError, ValueError):
        return str(n)

import json as _json
def _fromjson(s):
    return _json.loads(s)

templates.env.globals["csrf_input"] = _csrf_input
templates.env.globals["enumerate"] = enumerate
templates.env.globals["now"] = datetime.now
templates.env.filters["format_miles"] = _format_miles
templates.env.filters["fromjson"] = _fromjson
