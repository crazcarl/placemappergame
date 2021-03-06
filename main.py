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
	Route(r'/getbarlist', handler='handlers.maps.MapHandler',handler_method='getBarList'),
	Route(r'/gameover', handler='handlers.maps.MapHandler',handler_method='gameOver'),
	Route(r'/leaderboard', handler='handlers.maps.MapHandler', handler_method='leaderboard', name='leaderboard'),
	Route(r'/post_leaderboard', handler='handlers.maps.MapHandler',handler_method='post_leaderboard'),
	Route(r'/stats', handler='handlers.maps.MapHandler',handler_method='get_stats'),
	Route(r'/contact',handler='handlers.maps.MapHandler',handler_method='contact', name='contact'),
	Route(r'/bars',handler='handlers.maps.MapHandler',handler_method='bars'),
	Route(r'/faq',handler='handlers.maps.MapHandler',handler_method='faq'),
	Route(r'/email',handler='handlers.maps.MapHandler',handler_method='email')
	
], debug=True)