# https://github.com/lgc-NB2Dev/nonebot-plugin-fix-qq-img-ssl/blob/master/nonebot_plugin_fix_qq_img_ssl/__main__.py

from ssl import SSLContext
from functools import wraps

from httpx import AsyncClient
from httpx._config import create_ssl_context
from aiohttp.connector import _SSL_CONTEXT_VERIFIED, _SSL_CONTEXT_UNVERIFIED

# region httpx

_old_httpx_async_client_init = AsyncClient.__init__


@wraps(_old_httpx_async_client_init)
def _new_httpx_async_client_init(self: AsyncClient, **kwargs):
    if ("verify" not in kwargs) or (not isinstance(kwargs["verify"], SSLContext)):
        context = create_ssl_context(
            verify=kwargs.get("verify", True),
            cert=kwargs.get("cert"),
            trust_env=kwargs.get("trust_env", True),
        )
        context.set_ciphers("DEFAULT")
        kwargs["verify"] = context
    _old_httpx_async_client_init(self, **kwargs)


AsyncClient.__init__ = _new_httpx_async_client_init

# endregion

# region aiohttp

_SSL_CONTEXT_VERIFIED.set_ciphers("DEFAULT")
_SSL_CONTEXT_UNVERIFIED.set_ciphers("DEFAULT")

# endregion
