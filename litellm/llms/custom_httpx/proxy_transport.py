import os
import ssl

import httpx


def _get_http_proxy(proxy_url: str) -> httpx.Proxy:
    from litellm.secret_managers.main import str_to_bool

    if str_to_bool(os.getenv("DISABLE_OUTBOUND_PROXY_TLS_VERIFICATION", "False")):
        # For the case when proxy uses self-signed certificate.
        proxy_ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        proxy_ssl_context.check_hostname = False
        proxy_ssl_context.verify_mode = ssl.CERT_NONE
    else:
        proxy_ssl_context = None

    return httpx.Proxy(url=proxy_url, ssl_context=proxy_ssl_context)


def _rewrite_request(request: httpx.Request) -> httpx.Request:
    # Rewrite URL scheme with http to avoid CONNECT calls to proxy
    request.headers.update({"X-Forwarded-Proto": request.url.scheme})  # rebind-ok: request is single-use
    request.url = request.url.copy_with(scheme="http")  # rebind-ok: request is single-use

    return request


class AsyncProxyTransport(httpx.AsyncHTTPTransport):
    def __init__(self, proxy_url: str) -> None:
        super().__init__(proxy=_get_http_proxy(proxy_url))

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return await super().handle_async_request(_rewrite_request(request))


class ProxyTransport(httpx.HTTPTransport):
    def __init__(self, proxy_url: str) -> None:
        super().__init__(proxy=_get_http_proxy(proxy_url))

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return super().handle_request(_rewrite_request(request))
