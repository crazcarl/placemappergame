import os
from main import root_dir
from google.appengine.ext import db
from handlers.base import AppHandler
from google.appengine.api import memcache
import json
from random import randint



class MapHandler(AppHandler):
	def get(self):
		self.render("intro.html")
		self.response.headers.add_header('Set-Cookie', '%s=%s' % ('correct',0))
		self.response.headers.add_header('Set-Cookie', '%s=%s' % ('total',0))
	# AJAX helper function for returning messages of pass/fail.
	# kind of useless right now. May eliminate or add more useful features.
	def post(self):
		distance=int(float(self.request.get('distance')))
		array={'distance':distance}
		# Get Cookie Val
		correct = self.request.cookies.get('correct')
		total = self.request.cookies.get('total')
		if not correct or not total:
			correct = 0
			total = 0
		# Validate it
		if not self.valid_cookie(correct,total):
			pass
		# Check user answer
		if not distance or distance > 100:
			array['correct'] = "False"
		else:
			array['correct'] = "True"
			correct = int(correct) + 1
		total = int(total) + 1
		array['score'] = [str(correct),str(total)]
		# Set new val
		self.update_cookie(correct,total)
		self.response.headers['Content-Type'] = 'application/json'
		self.response.out.write(json.dumps(array))
		
	def valid_cookie(self,correct,total):
		return 1
	
	def update_cookie(self,correct,total):
		self.response.headers.add_header('Set-Cookie', '%s=%s' % ('correct',str(correct)))
		self.response.headers.add_header('Set-Cookie', '%s=%s' % ('total',str(total)))
		pass
		
	# AJAX helper function to return the lat/long for a bar based on the name
	# This is used when computing the distance between the bar dn the marker placed
	# by the user.
	def getBarLatLong(self):
		name = self.request.get("barname");
		#get lat and long based on name of bar.
		bar = memcache.get(name)
		if not bar:
			bar = Place.all().filter("name =", name).get()
			if bar:
				memcache.set(bar.name,bar)
		if not bar:
			return None
		lat = bar.location.lat
		long = bar.location.lon
		array = {"lat":lat,"long":long}
		self.response.headers['Content-Type'] = 'application/json'
		self.response.out.write(json.dumps(array))
	
	# AJAX helper function to get the list of bars to use
	def getBarList(self):
		places = memcache.get("barlist")
		if not places:
			places = Place.all().fetch(1000)
			places = list(places)
			if places:
				memcache.set("barlist",places)
		if not places:
			return None;
		
		# get a random list of places
		names = []
		while places:
			which = randint(0,len(places)-1)
			place = places.pop(which)
			names.append(place.name)
		array = {"bars":names}
		self.response.headers['Content-Type'] = 'application/json'
		self.response.out.write(json.dumps(array))
	
	# When the game is over, route to new screen. Eventually will contain stats,etc..
	def gameOver(self):
		self.render('gameover.html')
		
#For adding new points. Eventually will be protected (either non-public or requiring verification before adding to DB)
class NewPointHandler(AppHandler):
	def get(self):
		places = Place.all().fetch(50)
		places = list(places)
		self.render("add.html",barlist=places)
	def post(self):
		name = self.request.get("barname")
		lat = self.request.get("lat")
		lng = self.request.get("lng")
		if name and lat and lng:
			newGeoPt = db.GeoPt(lat=lat,lon=lng)
			newpt = Place(name=name,location=newGeoPt)
			newpt.put()
			memcache.set(name,newpt)
			mc = memcache.get("barlist")
			if mc:
				mc.append(newpt)
				memcache.set("barlist",mc)
		self.response.headers['Content-Type'] = 'application/json'
		output = {"ok":"yeah"}
		self.response.out.write(json.dumps(output))
		
		
class Place(db.Model):
	location = db.GeoPtProperty(required=True)
	name = db.StringProperty(required=True)