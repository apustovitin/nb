import logging

import aiohttp
import aiohttp_jinja2
from aiohttp import web
from faker import Faker
from aiohttp.hdrs import METH_POST
from aiohttp.web_exceptions import HTTPFound
from aiohttp.web_response import Response
from aiohttp_jinja2 import template
from aiohttp_session import get_session
from pydantic import BaseModel, ValidationError, constr

log = logging.getLogger(__name__)


def get_random_name():
    fake = Faker()
    return fake.name()


class FormModel(BaseModel):
    username: constr(max_length=40)
    message: str


async def process_form(request):
    data = dict(await request.post())
    try:
        m = FormModel(**data)
    except ValidationError as exc:
        return exc.errors()

    # simple demonstration of sessions by saving the username and pre-populating it in the form next time
    session = await get_session(request)
    session['username'] = m.username

    await request.app['pg'].execute('insert into messages (username, message) values ($1, $2)', m.username, m.message)


async def index(request):
    ws_current = web.WebSocketResponse()
    ws_ready = ws_current.can_prepare(request)
    if not ws_ready.ok:
        return aiohttp_jinja2.render_template('index.html', request, {})

    await ws_current.prepare(request)

    username = get_random_name()
    log.info('%s joined.', username)

    await ws_current.send_json({'action': 'connect', 'username': username})

    for ws in request.app['websockets'].values():
        await ws.send_json({'action': 'join', 'username': username})
    request.app['websockets'][username] = ws_current

    while True:
        msg = await ws_current.receive()

        if msg.type == aiohttp.WSMsgType.text:
            for ws in request.app['websockets'].values():
                if ws is not ws_current:
                    await ws.send_json(
                        {'action': 'sent', 'username': username, 'message': msg.data})
        else:
            break

    del request.app['websockets'][username]
    log.info('%s disconnected.', username)
    for ws in request.app['websockets'].values():
        await ws.send_json({'action': 'disconnect', 'username': username})

    return ws_current
