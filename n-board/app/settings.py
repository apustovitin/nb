from urllib.parse import urlparse

from pydantic import BaseSettings


class Settings(BaseSettings):
    """
    See https://pydantic-docs.helpmanual.io/#settings for details on using and overriding this
    """
    name = 'n-board'
    pg_dsn = 'postgres://postgres:0okmASDF@localhost:5432/n_board'
    auth_key = '_aycNdwHw4A7mfhHR1sq2IXM_WrQho3OQh1e3wRYGwQ='
    cookie_name = 'n_board'

    @property
    def _pg_dsn_parsed(self):
        return urlparse(self.pg_dsn)

    @property
    def pg_name(self):
        return self._pg_dsn_parsed.path.lstrip('/')
