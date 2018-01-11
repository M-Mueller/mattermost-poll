#!/usr/bin/env python

from tornado import wsgi
from tornado import httpserver
from tornado import ioloop

import app
import settings

http_server = httpserver.HTTPServer(wsgi.WSGIContainer(app.app))
http_server.listen(settings.WEBSERVER_PORT)
ioloop.IOLoop.instance().start()

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
