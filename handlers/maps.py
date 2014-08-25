import os
from main import root_dir
from google.appengine.ext import db
from handlers.base import AppHandler
from google.appengine.api import memcache
import json
from random import randint
import hmac
from google.appengine.api import mail
import secret


# Function to help with cookie hashing
def hash_str(s):
	return hmac.new(secret.SECRET, s).hexdigest()
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
	self.response.headers.add_header('Set-Cookie', '%s=%s' % ('distance',0))

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
			distance = 0   # distance shouldn't increase for successes
			
		# Update Place object with new stats
		count = bar.connect + bar.miss
		bar.avg_distance = ((bar.avg_distance * count) + distance) / count+1
		memcache.set(barname,bar)
		bar.put()
		
		total = int(total) + 1
		
		# Set new cookie
		self.update_cookie(score,total,barname,array['correct'],distance)
		
		# Pass Back Data to AJAX
		array['score'] = [str(score),str(total)]
		self.response.headers['Content-Type'] = 'application/json'
		self.response.out.write(json.dumps(array))
	
	# Updates Cookie information after a submission
	def update_cookie(self,score,total,barname,correct,distance):
		self.response.headers.add_header('Set-Cookie', '%s=%s' % ('score',make_secure_val(score)))
		self.response.headers.add_header('Set-Cookie', '%s=%s' % ('total',str(total)))
		total_distance = int(self.request.cookies.get('distance')) + distance
		self.response.headers.add_header('Set-Cookie', '%s=%s' % ('distance',str(total_distance)))
		
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
		while places and len(names)<25:
			which = randint(0,len(places)-1)
			place = places.pop(which)
			names.append(place.name)
		array = {"bars":names}
		self.response.headers['Content-Type'] = 'application/json'
		self.response.out.write(json.dumps(array))
	
	# When the game is over, route to new screen.
	def gameOver(self):
		params = {}
		# User's Results
		params['score'] = str(self.request.cookies.get('score')).split('|')[0]
		params['total'] = str(self.request.cookies.get('total'))
		params['clist'] = str(self.request.cookies.get('correct_list')).replace('-',', ').replace('_',' ')
		params['iclist'] = str(self.request.cookies.get('incorrect_list')).replace('-',', ').replace('_',' ')
		params['distance'] = str(self.request.cookies.get('distance'))
		
		if not params['score']:
			params['error'] = 1
		
		self.render('gameover.html',params=params)
		
	# Add to the leaderboard
	def post_leaderboard(self):
		# Make sure cookie shows legit score (prevent cheating)
		score = self.request.cookies.get('score')
		total = self.request.cookies.get('total')
		distance = self.request.cookies.get('distance')
		if not total or not check_secure_val(score):
			# have some error message for them
			self.redirect_to('leaderboard')
			return None
		
		score = int(score.split('|')[0])
		total = int(total)
		distance = int(distance)
		name = self.request.get('name')
		if not name:
			# Just Return Leaderboard (no update)
			self.redirect_to('leaderboard')
			return None
		
		# Reset cookies to prevent duplicate additions
		init_cookies(self)
		
		# Grab current leaderboard
		leaderboard = memcache.get('leaderboard')
		if not leaderboard:
			leaderboard = LeaderBoard.all().order('-score').fetch(25)
			leaderboard = list(leaderboard)
		
		# Create new LB object
		lb = LeaderBoard(name=name,
						 score=score,
						 total=total,
						 distance=distance)
		lb.put()
		
		# Add to already cachedleaderboard
		# sort based on score/distance
		# then remove if list longer than 25 entries
		leaderboard.append(lb)
		leaderboard = sorted(leaderboard, key=lambda x: (-x.score,x.distance))
		if len(leaderboard) > 25:
			leaderboard.pop()   #remove the now 26th place.	
		memcache.set('leaderboard',leaderboard)

		
		
		self.redirect_to('leaderboard')
		
	# Display the leaderboard
	def leaderboard(self):
		leaderboard = memcache.get('leaderboard')
		if not leaderboard:
			leaderboard = LeaderBoard.all().order('-score').fetch(25)
			leaderboard = list(leaderboard)
			memcache.set('leaderboard',leaderboard)
		leaderboard = sorted(leaderboard, key=lambda x: (-x.score,x.distance))
		self.render('leaderboard.html',leaderboard=leaderboard)
	def get_stats(self):
		# Overall Results
		stats = ""
		if not stats:
			self.render('stats.html',params="")
			return None
		barlist = memcache.get('barlist')
		params = {}
		params['barstats'] = []
		if not barlist:
			barlist = getAllBars(self)
			memcache.set('barlist',barlist)
		for barname in barlist:
			bar = memcache.get(barname.name)
			if not bar:
				bar = Place.all().filter('name =',barname.name).get()
				memcache.set(barname.name,bar)
			params['barstats'].append(bar.name)
		self.render('stats.html',params=params)
	def contact(self):
		confirmation = self.request.get('confirmation')
		if confirmation:
			confirmation = "Email sent, thanks!"
		self.render('contact.html',confirmation=confirmation)
	def test(self):
		self.render('test.html')
	def bars(self):
		bars = memcache.get('barlist')
		if not bars:
			bars = Place.all().fetch(1000)
			memcache.set('barlist',bars)
		bars = sorted(bars, key=lambda bar: bar.name)
		self.render('barlist.html',bars=bars)
	def faq(self):
		self.render('FAQ.html')
	def email(self):
		email = self.request.get('email')
		message = self.request.get('message')
		mail.send_mail(sender="Place Mapper Game <crazcarl@gmail.com>",
              to = "crazcarl@gmail.com",
              subject = "Message from Place Mapper Game",
              body = "Email: " + email +
			  "\n" + "Message: " + message)
		self.redirect_to('contact',confirmation=1)
		
		
#For adding new points. Eventually will be protected (either non-public or requiring verification before adding to DB)
class NewPointHandler(AppHandler):
	def get(self):
		places = Place.all().fetch(200)
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
				mc.append(newpt)
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
		mc.append(bar)
	return mc
	

		
class Place(db.Model):
	location = db.GeoPtProperty(required=True)
	name = db.StringProperty(required=True)
	miss = db.IntegerProperty(default=0)
	connect = db.IntegerProperty(default=0)
	avg_distance = db.IntegerProperty(default=0)
class LeaderBoard(db.Model):
	name = db.StringProperty(required=True)
	score = db.IntegerProperty(default=0)
	total = db.IntegerProperty(default=0)
	distance = db.IntegerProperty(default=0)
	created = db.DateTimeProperty(auto_now_add = True)