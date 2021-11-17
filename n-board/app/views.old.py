from aiohttp.hdrs import METH_POST
from aiohttp.web_exceptions import HTTPFound
from aiohttp.web_response import Response
from aiohttp_jinja2 import template
from aiohttp_session import get_session
from pydantic import BaseModel, ValidationError, constr
import logging
import aiohttp
import aiohttp_jinja2
from aiohttp import web

log = logging.getLogger(__name__)


async def index(request):
    ws_current = web.WebSocketResponse()
    ws_ready = ws_current.can_prepare(request)
    if not ws_ready.ok:
        return aiohttp_jinja2.render_template('index.html', request, {})

    await ws_current.prepare(request)

    name = get_random_name()
    log.info('%s joined.', name)

    await ws_current.send_json({'action': 'connect', 'name': name})

    for ws in request.app['websockets'].values():
        await ws.send_json({'action': 'join', 'name': name})
    request.app['websockets'][name] = ws_current

    while True:
        msg = await ws_current.receive()

        if msg.type == aiohttp.WSMsgType.text:
            for ws in request.app['websockets'].values():
                if ws is not ws_current:
                    await ws.send_json(
                        {'action': 'sent', 'name': name, 'text': msg.data})
        else:
            break

    del request.app['websockets'][name]
    log.info('%s disconnected.', name)
    for ws in request.app['websockets'].values():
        await ws.send_json({'action': 'disconnect', 'name': name})

    return ws_current


@template('index.jinja')
async def index(request):
    """
    This is the view handler for the "/" url.

    :param request: the request object see http://aiohttp.readthedocs.io/en/stable/web_reference.html#request
    :return: context for the template.
    """
    # Note: we return a dict not a response because of the @template decorator
    return {
        'title': request.app['settings'].name,
        'intro': "Success! you've setup a basic aiohttp app.",
    }


class UserModel(BaseModel):
    username: constr(max_length=40) = 'Аноним'


async def process_user_form(request):
    data = dict(await request.post())
    try:
        u = UserModel(**data)
    except ValidationError as exc:
        return exc.errors()

    # simple demonstration of sessions by saving the username and pre-populating it in the form next time
    session = await get_session(request)
    session['username'] = m.username

    await request.app['pg'].execute('insert into messages (username, message) values ($1, $2)', m.username, m.message)
    raise HTTPFound(request.app.router['messages'].url_for())



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
    raise HTTPFound(request.app.router['messages'].url_for())


@template('messages.jinja')
async def messages(request):
    if request.method == METH_POST:
        # the 302 redirect is processed as an exception, so if this coroutine returns there's a form error
        form_errors = await process_form(request)
    else:
        form_errors = None

    # simple demonstration of sessions by pre-populating username if it's already been set
    session = await get_session(request)
    username = session.get('username', '')

    return {'title': 'Message board', 'form_errors': form_errors, 'username': username}


async def message_data(request):
    """
    As an example of aiohttp providing a non-html response, we load the actual messages for the "messages" view above
    via ajax using this endpoint to get data. see static/message_display.js for details of rendering.
    """
    json_str = await request.app['pg'].fetchval(
        """
        select coalesce(array_to_json(array_agg(row_to_json(t))), '[]')
        from (
          select username, timestamp, message
          from messages
          order by timestamp desc
        ) t
        """
    )
    return Response(text=json_str, content_type='application/json')
