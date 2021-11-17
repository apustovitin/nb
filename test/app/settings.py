from urllib.parse import urlparse

from pydantic import BaseSettings


class Settings(BaseSettings):
    """
    See https://pydantic-docs.helpmanual.io/#settings for details on using and overriding this
    """
    name = 'test'
    pg_dsn = 'postgres://postgres@localhost:5432/demo_app'
    auth_key = 'ihO-97P8Ln7xfTeaZR0q_GUKz8LEr8tNO4SR9BlYm2E='
    cookie_name = 'test'

    @property
    def _pg_dsn_parsed(self):
        return urlparse(self.pg_dsn)

    @property
    def pg_name(self):
        return self._pg_dsn_parsed.path.lstrip('/')
