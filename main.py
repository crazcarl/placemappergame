#!/usr/bin/env python

from webapp2 import WSGIApplication, Route
import re
import os
# Set useful fields
root_dir = os.path.dirname(__file__)
template_dir = os.path.join(root_dir, 'templates')
								
from google.appengine.ext import db



		
# Create the WSGI application and define route handlers
app = WSGIApplication([
	Route(r'/', handler='handlers.maps.MapHandler', name='map'),
	Route(r'/add', handler='handlers.maps.NewPointHandler', name='add'),
	Route(r'/getbarlatlong',handler='handlers.maps.MapHandler', handler_method='getBarLatLong'),
	Route(r'/getbarlist',handler='handlers.maps.MapHandler',handler_method='getBarList'),
	Route(r'/gameover',handler='handlers.maps.MapHandler',handler_method='gameOver')
], debug=True)