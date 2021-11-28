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
    content: str


async def process_form(request):
    data = dict(await request.post())
    try:
        newsFormated = FormModel(**data)
    except ValidationError as exc:
        return exc.errors()

    # simple demonstration of sessions by saving the username and pre-populating it in the form next time
    session = await get_session(request)
    session['username'] = newsFormated.username

    await request.app['pg'].execute('insert into news (username, content) values ($1, $2)', newsFormated.username, newsFormated.content)


async def index(request):
    ws_current = web.WebSocketResponse()
    ws_ready = ws_current.can_prepare(request)
    if not ws_ready.ok:
        return aiohttp_jinja2.render_template('index.html', request, {})

    await ws_current.prepare(request)
    msg = await ws_current.receive()
    if msg.type == aiohttp.WSMsgType.text:
        username = msg.data
    log.info('%s joined.', username)
    history_json_list = await request.app['pg'].fetchval(
        """
        select coalesce(array_to_json(array_agg(row_to_json(t))), '[]')
        from (
          select username, timestamp, content
          from news
          order by timestamp asc
        ) t
        """
    )
    print(history_json_list)

    await ws_current.send_json({'action': 'connect', 'username': username, 'history': history_json_list})

    for ws in request.app['websockets'].values():
        await ws.send_json({'action': 'join', 'username': username})
    request.app['websockets'][username] = ws_current

    while True:
        msg = await ws_current.receive()

        if msg.type == aiohttp.WSMsgType.text:
            content = msg.data
            await request.app['pg'].execute('insert into news (username, content) values ($1, $2)', username, content)
            for ws in request.app['websockets'].values():
                if ws is not ws_current:
                    await ws.send_json(
                        {'action': 'sent', 'username': username, 'content': content})
        else:
            break

    del request.app['websockets'][username]
    log.info('%s disconnected.', username)
    for ws in request.app['websockets'].values():
        await ws.send_json({'action': 'disconnect', 'username': username})

    return ws_current
