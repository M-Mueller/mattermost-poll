#!/usr/bin/env python
import settings

from tornado import wsgi
from tornado import httpserver
from tornado import ioloop

import app

http_server = httpserver.HTTPServer(wsgi.WSGIContainer(app.app))
http_server.listen(settings.WEBSERVER_PORT, address=settings.WEBSERVER_ADDRESS)
ioloop.IOLoop.instance().start()

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
