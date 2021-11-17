from pathlib import Path

import aiohttp_jinja2
import aiohttp_session
import asyncpg
import jinja2
from aiohttp import web
from aiohttp_session.cookie_storage import EncryptedCookieStorage

from .db import prepare_database
from .settings import Settings
# from .views import index, message_data, messages, news
from .views import index

THIS_DIR = Path(__file__).parent


async def startup(app: web.Application):
    settings: Settings = app['settings']
    await prepare_database(settings, False)
    app['pg'] = await asyncpg.create_pool(dsn=settings.pg_dsn, min_size=2)
    app['websockets'] = {}


async def cleanup(app: web.Application):
    await app['pg'].close()


async def shutdown(app):
    for ws in app['websockets'].values():
        await ws.close()
    app['websockets'].clear()


async def create_app():
    app = web.Application()
    settings = Settings()
    app.update(
        settings=settings,
        static_root_url='/static/',
    )

    jinja2_loader = jinja2.FileSystemLoader(str(THIS_DIR / 'templates'))
    aiohttp_jinja2.setup(app, loader=jinja2_loader)

    app.on_startup.append(startup)
    app.on_cleanup.append(cleanup)
    app.on_shutdown.append(shutdown)

    aiohttp_session.setup(app, EncryptedCookieStorage(settings.auth_key, cookie_name=settings.cookie_name))

    app.router.add_route('*', '/', index, name='index')
    # app.router.add_route('*', '/messages', messages, name='messages')
    # app.router.add_route('*', '/news', news, name='news')
    # app.router.add_get('/messages/data', message_data, name='message-data')
    return app


async def get_app():
    """Used by aiohttp-devtools for local development."""
    import aiohttp_debugtoolbar
    app = await create_app()
    aiohttp_debugtoolbar.setup(app)
    return app


def main():
    logging.basicConfig(level=logging.DEBUG)

    app = create_app()
    web.run_app(app)


if __name__ == '__main__':
    main()
