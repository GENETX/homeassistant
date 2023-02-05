import appdaemon.plugins.hass.hassapi as hass
import const

import math
import time
import datetime as dt

class RunlevelApp(hass.Hass):
	def initialize(self):
		# Monitor change in the input field
		self.listen_state(self.changed_status, "input_select.status")
		self.listen_state(self.changed_runlevel, "input_number.runlevel")
		
		self.listen_state(self.changed_kodi, "media_player.kodi_kamer")
		self.listen_state(self.changed_phonecharging, "binary_sensor.smartphone_is_charging")
		self.listen_state(self.changed_bedroomlight, "light.slaapkamer", old="on", new="off")
		
		# Presence detection options
		self.listen_state(self.changed_gps, "person.gerwin_hoogsteen")
		self.listen_state(self.changed_wifi, "sensor.smartphone_wifi_connection")
		#self.listen_state(self.changed_tracking, "sensor.smartphone_beacon_monitor", attribute="all")
		
		self.listen_state(self.button_action, "sensor.thuisschakelaar_voor_action")
		self.listen_state(self.button_action, "sensor.thuisschakelaar_achter_action")
	
		# Beacons to be monitored
		self.known_beacons = [	'9eb6d838-976d-11ed-a8fc-0242ac120002_10167_61958', 
							'a5846ad6-976d-11ed-a8fc-0242ac120002_10167_61958', 
							'c0932610-976c-11ed-a8fc-0242ac120002_10167_61958'
						]
	
		self.rlTimer = None
		self.time_delay = None
		
		self.beacons_available = True
		self.beacons_state = {	'9eb6d838-976d-11ed-a8fc-0242ac120002_10167_61958': "unknown",
								'a5846ad6-976d-11ed-a8fc-0242ac120002_10167_61958': "unknown",
								'c0932610-976c-11ed-a8fc-0242ac120002_10167_61958': "unknown"
								}
								
		self.track_beacons(None)
		

	# Restore the state upon restart
	def restore(self):
		location = self.get_state("person.gerwin_hoogsteen")
		
		kodi_state = self.get_state("media_player.kodi_kamer")
		kodi_type = self.get_state("media_player.kodi_kamer", attribute="media_content_type")
		kodi_duration = self.get_state("media_player.kodi_kamer", attribute="media_duration")
		
		phone_charging = self.get_state("inary_sensor.smartphone_is_charging")
		hour = dt.datetime.now().hour

		# Try to revocer the state
		if self.get_state("input_boolean.auto_runlevel") == 'on':
			if location == "home":
				# Check sleeping
				if phone_charging == "on" and (hour >= 22 or hour <= 6):
					self.set_value("input_number.runlevel", int(const.rlSleep))
					
				# Kodi	
				elif kodi_state != "idle" and kodi_state != "paused":
					if kodi_type == "movie" and int(kodi_duration) >= 4500:
						self.set_value("input_number.runlevel", int(const.rlMovie))
					elif kodi_type != "music":
						self.set_value("input_number.runlevel", int(const.rlMedia))
					else:
						self.set_value("input_number.runlevel", int(const.rlHome))
				else:
					self.set_value("input_number.runlevel", int(const.rlHome))
			
			# GPS based		
			else:
				if location == "Omgeving" or location == "Campus":
					self.set_value("input_number.runlevel", int(const.rlGone))
				if location == "away" or location == "not_home" or location == "Fryslân":
					self.set_value("input_number.runlevel", int(const.rlAway))
				else:
					self.set_value("input_number.runlevel", int(const.rlHome))

#### BASIC FUNCTIONALITY
	# Select Runlevel accordingly
	def changed_status(self, entity, attribute, old, new, kwargs):
		if new != old:		
			if new == "Weg":
				self.set_value("input_number.runlevel", int(const.rlAway))
			if new == "Afwezig":
				self.set_value("input_number.runlevel", int(const.rlGone))
			if new == "Slapen":
				self.set_value("input_number.runlevel", int(const.rlSleep))
			if new == "Thuis":
				self.set_value("input_number.runlevel", int(const.rlHome))
			if new == "Media":
				self.set_value("input_number.runlevel", int(const.rlMedia))
			if new == "Film":
				self.set_value("input_number.runlevel", int(const.rlMovie))

	# Select State accordingly
	def changed_runlevel(self, entity, attribute, old, new, kwargs):	
		# This is the one that is triggered manually
		if new != old:
			if int(float(new)) == const.rlAway:
				self.select_option("input_select.status", "Weg")
			if int(float(new)) == const.rlGone:
				self.select_option("input_select.status", "Afwezig")
			if int(float(new)) == const.rlSleep:
				self.select_option("input_select.status", "Slapen")
			if int(float(new)) == const.rlHome:
				self.select_option("input_select.status", "Thuis")
			if int(float(new)) == const.rlMedia:
				self.select_option("input_select.status", "Media")
			if int(float(new)) == const.rlMovie:
				self.select_option("input_select.status", "Film")	


#### ROUTINES	
	# Sleep mode
	def changed_phonecharging(self, entity, attribute, old, new, kwargs):
		if self.get_state("input_boolean.auto_runlevel") == 'on':
			rl = int(float(self.get_state("input_number.runlevel")))
			if rl >= const.rlHome:
				hour = dt.datetime.now().hour
				if new == "on" and (hour >= 22 or hour <= 6):
						self.set_value("input_number.runlevel", int(const.rlSleep))
	
	def changed_bedroomlight(self, entity, attribute, old, new, kwargs):
		if self.get_state("input_boolean.auto_runlevel") == 'on':
			rl = int(float(self.get_state("input_number.runlevel")))
			if rl == const.rlSleep:
				hour = dt.datetime.now().hour
				if old == "on" and new == "off" and (hour >= 6 and hour <= 21):
					self.set_value("input_number.runlevel", int(const.rlHome))
				
	def changed_kodi(self, entity, attribute, old, new, kwargs):
		if self.get_state("input_boolean.auto_runlevel") == 'on':
			rl = int(float(self.get_state("input_number.runlevel")))
			if rl >= const.rlHome:
				kodi_state = self.get_state("media_player.kodi_kamer")
				kodi_type = self.get_state("media_player.kodi_kamer", attribute="media_content_type")
				kodi_duration = self.get_state("media_player.kodi_kamer", attribute="media_duration")
				
				if new == "playing" and old != "paused":
					if kodi_type == "movie" and int(kodi_duration) >= 4500:
						self.set_value("input_number.runlevel", int(const.rlMovie))
					elif kodi_type != "music" and old != "paused":
						self.set_value("input_number.runlevel", int(const.rlMedia))
				if new == "idle":
					self.set_value("input_number.runlevel", int(const.rlHome))
				
#### TRACKING CODE	
	# Change runlevel based on GPS
	def changed_gps(self, entity, attribute, old, new, kwargs):
		if self.get_state("input_boolean.auto_runlevel") == 'on':
			if new != old:
				rl = int(float(self.get_state("input_number.runlevel")))
				wifi = self.get_state("sensor.smartphone_wifi_connection")
				
				if new == "home" and rl <= const.rlGone:
					self.set_value("input_number.runlevel", int(const.rlHome))
					try:
						if self.time_delay is not None:
							self.cancel_timer(self.time_delay)
					except:
						pass
						
				elif new == "away" or new == "not_home" or new == "Omgeving" or new == "Fryslân" or new == "Campus":
					if rl > const.rlGone and wifi != "WLANHOOGSTEEN" and wifi != "WLANHOOGSTEEN2G" and not self.beacons_available:
						try:
							if self.time_delay is None:
								self.time_delay = self.run_in(self.delayed_change, 120)	# Wait two minutes
						except:
							pass
					else:
						self.delayed_change(None)
					
	# Monitor Wifi Change
	def changed_wifi(self, entity, attribute, old, new, kwargs):
		if self.get_state("input_boolean.auto_runlevel") == 'on':
			self.changed_tracking()
	
	
	def changed_tracking(self):
		if self.get_state("input_boolean.auto_runlevel") == 'on':
			rl = int(float(self.get_state("input_number.runlevel")))
			location = self.get_state("person.gerwin_hoogsteen")
			wifi = self.get_state("sensor.smartphone_wifi_connection")
			
			# Also have the home state depend on wifi + beacons
			if location != "home":
				# Check if we are not home based on wifi + beacons
				if wifi != "WLANHOOGSTEEN" and wifi != "WLANHOOGSTEEN2G" and not self.beacons_available:
					if rl > const.rlGone:
						try:
							if self.time_delay is None:
								self.time_delay = self.run_in(self.delayed_change, 120)	# Wait two minutes
						except:
							pass
					else:
						self.delayed_change(None)
				
				# Otherwise, we might have just gotten home and connected to WiFi again:
				if wifi == "WLANHOOGSTEEN" or wifi == "WLANHOOGSTEEN2G" or self.beacons_available:
					if rl == const.rlGone:
						if location == "Omgeving" or location == "home":
							# We must be home for sure
							self.set_value("input_number.runlevel", int(const.rlHome))		
					
					
	# Delay the runlevel for away states based on GPS jitter
	def delayed_change(self, kwargs):
		if self.get_state("input_boolean.auto_runlevel") == 'on':
			location = self.get_state("person.gerwin_hoogsteen")
			wifi = self.get_state("sensor.smartphone_wifi_connection")
			
			if not self.beacons_available:
				if location == "Omgeving":
					if wifi != "WLANHOOGSTEEN" and wifi != "WLANHOOGSTEEN2G":
						self.set_value("input_number.runlevel", int(const.rlGone))
				elif location == "Campus":
					self.set_value("input_number.runlevel", int(const.rlGone))
				elif location == "away" or location == "not_home" or location == "Fryslân":
					self.set_value("input_number.runlevel", int(const.rlAway))
				
			try:
				if self.time_delay is not None:
					self.cancel_timer(self.time_delay)
			except:
				pass
			
			self.time_delay = None
		
	# Beacon tracker
	def track_beacons(self, kwargs):
		try:
			result = False
			closest = 1000000
			
			try:
				# First read the beacons
				beacons = self.get_state("sensor.smartphone_beacon_monitor", attribute="all")['attributes']
				for b in self.known_beacons:
					if b in beacons:
						# Read the state of each beacon
						try:
							d = beacons[b]				
						except:
							d = "unknown"
							
						# Now compare with the existing state:
						if self.beacons_state[b] != d:
							# Change detected so we should be close to a beacon
							result = True
							self.beacons_state[b] = d
							
						# Track how far we are away from the nearest beacon
						try:
							if float(d) < closest:
								closest = d
						except:
							pass
					
					else:
						# Beacon not in state, so it is likely to be offline, reset to unknown
						self.beacons_state[b] = "unknown"
						
			except:
				self.log("Overall beacon error")
				
			# Check if we have an update that we should notify
			if result != self.beacons_available:
				self.beacons_available = result
				if self.get_state("input_boolean.auto_runlevel") == 'on':
					self.changed_tracking()
			
			# Keep a monitoring sensor for the time being
			if result:
				self.set_state("sensor.beacons_nearby", state="on")
			else:
				self.set_state("sensor.beacons_nearby", state="off")
				
			self.set_state("sensor.beacons_distance", state=closest)
		except:
			pass
			
		# Frequency depends on state
		if not result:
			self.run_in(self.track_beacons, 15)
		else:
			self.run_in(self.track_beacons, 65)	
		
		
		
#### BUTTON ACTIONS		
	# Button actions to change runlevel away <-> Home
	def button_action(self, entity, attribute, old, new, kwargs):
		if self.get_state(const.auto) == "on":
			doorbell_active = self.get_state("input_boolean.deurbel")

			# Doorbell is an exceptional case
			if not doorbell_active == "on":	
				rl = int(float(self.get_state("input_number.runlevel")))
				# Setting runlevel to away
				if new == "brightness_move_down" and rl >= const.rlHome:
					self.select_option("input_select.status", "Weg")
					
					# Disable auto mode for an hour if auto mode is on:
					if self.get_state("input_boolean.auto_runlevel") == 'on':
						self.turn_off("input_boolean.auto_runlevel")
						if self.rlTimer is not None:
							try:
								self.cancel_timer(self.rlTimer)
							except:
								pass
						
						# set the reenable timer
						self.rlTimer = self.run_in(self.enable_autorunlevel, 3600)
					
				# Setting runlevel to home
				if new == "brightness_move_up" and rl < const.rlHome:
					self.select_option("input_select.status", "Thuis")
	
	# Autorunlevel toggle timer
	def timer_enable_autorunlevel(self, kwargs):
		self.turn_on("input_boolean.auto_runlevel")