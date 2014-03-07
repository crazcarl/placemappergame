import os
from main import root_dir
from google.appengine.ext import db
from handlers.base import AppHandler
from google.appengine.api import memcache
import json
from random import randint
import hmac

# TODO: update this to something else
SECRET = "secret"


# Function to help with cookie hashing
def hash_str(s):
	return hmac.new(SECRET, s).hexdigest()
def check_secure_val(secure_val):
	val = secure_val.split('|')[0]
	if secure_val == make_secure_val(val):
		return val
def make_secure_val(val):
	return '%s|%s' % (val, hash_str(str(val)))

def init_cookies(self):
	init_score = make_secure_val(0)
	self.response.headers.add_header('Set-Cookie', '%s=%s' % ('score',init_score))
	self.response.headers.add_header('Set-Cookie', '%s=%s' % ('total',0))
	self.response.headers.add_header('Set-Cookie', '%s=;' % ('correct_list'))
	self.response.headers.add_header('Set-Cookie', '%s=;' % ('incorrect_list'))

class MapHandler(AppHandler):
	def get(self):
		init_cookies(self)
		self.render("intro.html")
		
	# AJAX helper function for returning messages of pass/fail.
	def post(self):
		distance = int(float(self.request.get('distance')))
		barname = self.request.get('barname')
		array={'distance':distance}
		
		# Get Cookie Val
		score = self.request.cookies.get('score')
		total = self.request.cookies.get('total')
		if not score or not total:
			score = make_secure_val(0)
			total = 0
		
		# Validate it
		if not check_secure_val(score):
			init_score = make_secure_val(0)
			self.response.headers.add_header('Set-Cookie', '%s=%s' % ('score',init_score))
		score = int(score.split('|')[0])
		
		# Get bar's Place object (for stats tracking)
		bar = memcache.get(barname)
		if not bar:
			bar = Place.all().filter('name =',barname).get()
		
		# Check user answer
		if distance > 100:
			bar.miss += 1
			array['correct'] = "False"
		else:
			array['correct'] = "True"
			score = score + 1
			bar.connect += 1
		
		# Update Place object with new stats
		memcache.set(barname,bar)
		bar.put()
		
		total = int(total) + 1
		
		# Set new cookie
		self.update_cookie(score,total,barname,array['correct'])
		
		# Pass Back Data to AJAX
		array['score'] = [str(score),str(total)]
		self.response.headers['Content-Type'] = 'application/json'
		self.response.out.write(json.dumps(array))
	
	# Updates Cookie information after a submission
	def update_cookie(self,score,total,barname,correct):
		self.response.headers.add_header('Set-Cookie', '%s=%s' % ('score',make_secure_val(score)))
		self.response.headers.add_header('Set-Cookie', '%s=%s' % ('total',str(total)))
		
		# GAE Cookies can't have spaces or commas, so using - and _ instead (then will undo when using cookie)
		barname = "_".join(barname.split())
		if correct == 'True':
			correct_list = str(self.request.cookies.get('correct_list'))
			correct_list = correct_list + "-" + barname + "-"
			correct_list = correct_list.strip("-")
			self.response.headers.add_header('Set-Cookie', '%s=%s' % ('correct_list',str(correct_list)))
		else:
			incorrect_list = str(self.request.cookies.get('incorrect_list'))
			incorrect_list = incorrect_list + "-" + barname + "-"
			incorrect_list = incorrect_list.strip("-")
			self.response.headers.add_header('Set-Cookie', '%s=%s' % ('incorrect_list',str(incorrect_list)))
		
	# AJAX helper function to return the lat/long for a bar based on the name
	# This is used when computing the distance between the bar and the marker placed
	# by the user.
	def getBarLatLong(self):
		name = self.request.get("barname");
		#get lat and long based on name of bar.
		bar = memcache.get(name)
		if not bar:
			bar = Place.all().filter("name =", name).get()
			if bar:
				memcache.set(name,bar)
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
			places = getAllBars(self)
			if places:
				memcache.set("barlist",places)
		if not places:
			return None;
		
		# get a random list of places
		names = []
		while places:
			which = randint(0,len(places)-1)
			place = places.pop(which)
			names.append(place)
		array = {"bars":names}
		self.response.headers['Content-Type'] = 'application/json'
		self.response.out.write(json.dumps(array))
	
	# When the game is over, route to new screen. Eventually will contain stats,etc..
	def gameOver(self):
		params = {}
		# User's Results
		params['score'] = str(self.request.cookies.get('score')).split('|')[0]
		params['total'] = str(self.request.cookies.get('total'))
		params['clist'] = str(self.request.cookies.get('correct_list')).replace('-',',').replace('_',' ')
		params['iclist'] = str(self.request.cookies.get('incorrect_list')).replace('-',',').replace('_',' ')
		
		self.render('gameover.html',params=params)
		
	# Add to the leaderboard
	def post_leaderboard(self):
		# Make sure cookie shows legit score (prevent cheating)
		score = self.request.cookies.get('score')
		total = self.request.cookies.get('total')
		if not total or not check_secure_val(score):
			# have some error message for them
			self.redirect_to('leaderboard')
			return None
		
		score = int(score.split('|')[0])
		total = int(total)
		name = self.request.get('name')
		if not name:
			# Just Return Leaderboard (no update)
			self.redirect_to('leaderboard')
			return None
		
		#reset cookies to prevent duplicate additions
		init_cookies(self)
		
		# Create new LB object
		lb = LeaderBoard(name=name,
						 score=score,
						 total=total)
		
		lb.put()
		
		# Handle caching
		leaderboard = memcache.get('leaderboard')
		if not leaderboard:
			leaderboard = LeaderBoard.all().order('-score').fetch(25)
			memcache.set('leaderboard',list(leaderboard))
		else:
			#TODO: Insert at correct location for sorting
			leaderboard.append(lb)
			memcache.set('leaderboard',leaderboard)
		
		self.redirect_to('leaderboard')
		
	# Display the leaderboard
	def leaderboard(self):
		leaderboard = memcache.get('leaderboard')
		if not leaderboard:
			leaderboard = LeaderBoard.all().order('-score').fetch(25)
			leaderboard = list(leaderboard)
			memcache.set('leaderboard',leaderboard)
		self.render('leaderboard.html',leaderboard=leaderboard)
	def get_stats(self):
		# Overall Results
		barlist = memcache.get('barlist')
		params = {}
		params['barstats'] = []
		if not barlist:
			barlist = getAllBars(self)
			memcache.set('barlist',barlist)
		for barname in barlist:
			bar = memcache.get(barname)
			if not bar:
				bar = Place.all().filter('name =',barname).get()
				memcache.set(barname,bar)
			params['barstats'].append(bar)
		self.render('stats.html',params=params)
	def contact(self):
		self.render('contact.html')
		
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
		pw = self.request.get("pw")
		if not pw or pw <> "asdf":
			return None
		if name and lat and lng:
			newGeoPt = db.GeoPt(lat=lat,lon=lng)
			newpt = Place(name=name,location=newGeoPt)
			newpt.put()
			memcache.set(name,newpt)
			mc = memcache.get("barlist")
			if mc:
				mc.append(name)
				memcache.set("barlist",mc)
			else:
				barlist = getAllBars(self)
				barlist.append(name)
				memcache.set("barlist",barlist)
		self.response.headers['Content-Type'] = 'application/json'
		output = {"ok":"yeah"}
		self.response.out.write(json.dumps(output))

# Helper function to return all bars currently populated.
# Used to then populate memcache
def getAllBars(self):
	allbars = Place.all().fetch(1000)
	allbars = list(allbars)
	mc = []
	for bar in allbars:
		mc.append(bar.name)
	return mc		
		
class Place(db.Model):
	location = db.GeoPtProperty(required=True)
	name = db.StringProperty(required=True)
	miss = db.IntegerProperty(default=0)
	connect = db.IntegerProperty(default=0)

class LeaderBoard(db.Model):
	name = db.StringProperty(required=True)
	score = db.IntegerProperty(default=0)
	total = db.IntegerProperty(default=0)
	created = db.DateTimeProperty(auto_now_add = True)