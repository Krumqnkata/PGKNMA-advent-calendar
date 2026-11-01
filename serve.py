"""
Production сървър: Django през Waitress, зад Apache и Cloudflare (виж DEPLOY.md).

    .venv/bin/python serve.py

Waitress слуша само на 127.0.0.1 и вярва на X-Forwarded-For / X-Forwarded-Proto
единствено когато заявката идва от Apache на същата машина. Така REMOTE_ADDR е
истинският IP на посетителя (от CF-Connecting-IP), а request.is_secure() е True.
"""

import os

from waitress import serve

from advent.wsgi import application  # зарежда и .env

if __name__ == "__main__":
    serve(
        application,
        listen=os.environ.get("WAITRESS_LISTEN", "127.0.0.1:8003"),
        threads=int(os.environ.get("WAITRESS_THREADS", "8")),
        trusted_proxy="127.0.0.1",
        trusted_proxy_count=1,
        trusted_proxy_headers={"x-forwarded-for", "x-forwarded-proto"},
        clear_untrusted_proxy_headers=True,
        ident="koleda",
    )
