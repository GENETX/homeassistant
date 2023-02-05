import appdaemon.plugins.hass.hassapi as hass
import const

import math
import time
import datetime as dt

class KlimaatApp(hass.Hass):
	def initialize(self):
		# Default values
		self.temp_heating = 19.0
		self.temp_away = 17.0
	
		# Monitor change in the input field
		self.listen_state(self.changed_runlevel, "input_number.runlevel")
		
		# Monitor movement
		self.listen_state(self.changed_gps, "person.gerwin_hoogsteen")
		self.listen_state(self.agenda_changed, "calendar.thermostaat")
		self.listen_state(self.setpoint_changed, "climate.nefit_nefit", attribute="temperature")
		
		self.listen_state(self.temperature_changed, "sensor.buienradar_temperature")
		self.listen_state(self.forecast_changed, "weather.buienradar")
		
		# Windows
		self.windowNotificationOpen = False
		self.windowNotificationClose = False
		self.tapNotification = False
		t = dt.time(14, 0, 0)
		self.run_daily(self.windowNotifyReset, t)
		
		self.nefit_timer = None
		# Desired state
		self.nefit_preset = "Clock"
		self.nefit_setpoint = 19.0
	
	
	
	# We often lose connection to Nefit, so here's a helper function that tries over and over
	def nefit_set_setpoint(self, setpoint=None, preset=None):
		# cancel the last timer, if any, to ensure no backlashes are still in flight
		if self.nefit_timer is not None:
			try:
				self.cancel_timer(self.nefit_timer)
				self.nefit_timer = None
			except:
				pass
		
		# Set the setpoint
		try:
			# test if we have connection
			current_temp = float(self.get_state("climate.nefit_nefit", attribute="temperature"))
			
			# Force the setpoint
			if setpoint is not None:
				self.call_service("climate/set_temperature", entity_id = "climate.nefit_nefit", temperature=setpoint)
			if preset is not None:
				self.call_service("climate/set_preset_mode", entity_id = "climate.nefit_nefit", preset_mode=preset)
				
		except:
			# Error in connection
			# Force setpoint anyways
			if setpoint is not None:
				self.call_service("climate/set_temperature", entity_id = "climate.nefit_nefit", temperature=setpoint)
			if preset is not None:
				self.call_service("climate/set_preset_mode", entity_id = "climate.nefit_nefit", preset_mode=preset)
			
			# update globals
			self.nefit_setpoint = setpoint
			self.nefit_preset = preset
			
			# and set a timer for in 2 minutes:
			self.run_in(self.nefit_delayed_setpoint, 120)
				
	
	# retry timer
	def nefit_delayed_setpoint(self, kwargs):
		# Just call the old function
		self.nefit_set_setpoint(self.nefit_setpoint, self.nefit_preset)

	# Modify the setpoint baseed on GPS
	def changed_gps(self, entity, attribute, old, new, kwargs):
		override = self.get_state("calendar.thermostaat") == "on"
		if self.get_state(const.auto) == "on" and not override:
			# Only my way home:
			if old == "Fryslân":
				self.call_service("climate/set_temperature", entity_id = "climate.nefit_nefit", temperature=self.temp_heating)			

	# Modify the setpoint baseed on Runlevel
	def changed_runlevel(self, entity, attribute, old, new, kwargs):	
		override = self.get_state("calendar.thermostaat") == "on"
		if self.get_state(const.auto) == "on" and not override:
			location = self.get_state("person.gerwin_hoogsteen")
			
			new = int(float(new))
			old = int(float(old))
			
			# Only my way home:
			if new == const.rlAway:
				self.nefit_set_setpoint(self.temp_away, "Manual")
				#self.call_service("climate/set_temperature", entity_id = "climate.nefit_nefit", temperature=self.temp_away)
				#self.call_service("climate/set_preset_mode", entity_id = "climate.nefit_nefit", preset_mode="Manual")
			elif old == const.rlAway and new == const.rlGone:
				self.nefit_set_setpoint(self.temp_heating)
				# self.call_service("climate/set_temperature", entity_id = "climate.nefit_nefit", temperature=self.temp_heating)	
			elif old >= const.rlHome and new <= const.rlGone:
				self.nefit_set_setpoint(self.temp_away)
				# self.call_service("climate/set_temperature", entity_id = "climate.nefit_nefit", temperature=self.temp_away)	
			elif old >= const.rlHome and new == const.rlSleep:
				self.nefit_set_setpoint(self.temp_away)
				# self.call_service("climate/set_temperature", entity_id = "climate.nefit_nefit", temperature=self.temp_away)
			elif old <= const.rlGone and new >= const.rlHome:
				self.nefit_set_setpoint(self.temp_heating, "Clock")
				# self.call_service("climate/set_temperature", entity_id = "climate.nefit_nefit", temperature=self.temp_heating)	
				# self.call_service("climate/set_preset_mode", entity_id = "climate.nefit_nefit", preset_mode="Clock")
			
			
	def agenda_changed(self, entity, attribute, old, new, kwargs):	
		if self.get_state(const.auto) == "on":
			if new == "on":
				try:
					tempSet = float(self.get_state("calendar.thermostaat", attribute="message"))	
					self.nefit_set_setpoint(tempSet, "Manual")
					# self.call_service("climate/set_temperature", entity_id = "climate.nefit_nefit", temperature=tempSet)
					# self.call_service("climate/set_preset_mode", entity_id = "climate.nefit_nefit", preset_mode="Manual")
				except:	
					self.nefit_set_setpoint(self.temp_away, "Manual")
					self.log("Cannot read setpoint")
					# self.call_service("climate/set_temperature", entity_id = "climate.nefit_nefit", temperature=self.temp_away)
					# self.call_service("climate/set_preset_mode", entity_id = "climate.nefit_nefit", preset_mode="Manual")
			else:
				rl = int(float(self.get_state("input_number.runlevel")))
				if rl >= const.rlSleep:
					self.nefit_set_setpoint(None, "Clock")
					# self.call_service("climate/set_preqset_mode", entity_id = "climate.nefit_nefit", preset_mode="Clock")
			
			
		
	# Observe changes, revert if not home after an hour	
	def setpoint_changed(self, entity, attribute, old, new, kwargs):
		override = self.get_state("calendar.thermostaat") == "on"
		if self.get_state(const.auto) == "on" and not override:
			rl = int(float(self.get_state("input_number.runlevel")))
			
			try:
				setpoint = float(self.get_state("climate.nefit_nefit", attribute="temperature"))
				if rl < const.rlSleep and setpoint >= self.temp_away + 1:
					self.run_in(self.revert_setpoint, 3600) 
			except:
				self.log("Nefit connection failed")
				if rl < const.rlSleep:
					self.run_in(self.revert_setpoint, 3600) 
				
		
	def revert_setpoint(self, kwargs):
		override = self.get_state("calendar.thermostaat") == "on"
		if self.get_state(const.auto) == "on" and not override:
			rl = int(float(self.get_state("input_number.runlevel")))
			
			try:
				setpoint = float(self.get_state("climate.nefit_nefit", attribute="temperature"))
				if rl < const.rlSleep and setpoint > self.temp_away + 1:
					self.nefit_set_setpoint(self.temp_away, "Manual")
					# self.call_service("climate/set_temperature", entity_id = "climate.nefit_nefit", temperature=self.temp_away)
					# self.call_service("climate/set_preset_mode", entity_id = "climate.nefit_nefit", preset_mode="Manual")
			except:
				self.log("Nefit connection failed")
				if rl < const.rlSleep:
					self.nefit_set_setpoint(self.temp_away, "Manual")
					# self.call_service("climate/set_temperature", entity_id = "climate.nefit_nefit", temperature=self.temp_away)
					# self.call_service("climate/set_preset_mode", entity_id = "climate.nefit_nefit", preset_mode="Manual")
			
			

	# Track if we need to open windows
	def temperature_changed(self, entity, attribute, old, new, kwargs):
		try:
			tout = float(self.get_state("sensor.buienradar_temperature"))
			tin = float(self.get_state("sensor.nefit_inhouse_temperature"))
			
			rl = int(float(self.get_state("input_number.runlevel")))	
			if rl >= const.rlHome:	
				if self.windowNotificationOpen == False and (tout +0.5) < tin and tin > 22.0:
					self.windowNotificationOpen = True
					self.call_service("notify/mobile_app_smartphone", message="De ramen kunnen open om het huis af te koelen!", title="Klimaat")
					self.call_service("tts/google_say", entity_id = "gc_media_player.huiskamer", message="De ramen kunnen open om het huis af te koelen!")
					self.call_service("tts/google_say", entity_id = "gc_media_player.keuken", message="De ramen kunnen open om het huis af te koelen!")
					self.call_service("tts/google_say", entity_id = "media_player.gc_studeerkamer", message="De ramen kunnen open om het huis af te koelen!")
					
				elif self.windowNotificationClose == False and tout > tin and tin > 22.5:
					self.windowNotificationClose = True
					self.call_service("notify/mobile_app_smartphone", message="De ramen moeten dicht om het huis niet op te laten warmen!", title="Klimaat")
					self.call_service("tts/google_say", entity_id = "media_gc_player.huiskamer", message="De ramen moeten dicht om het huis niet op te laten warmen!")
					self.call_service("tts/google_say", entity_id = "media_gc_player.keuken", message="De ramen moeten dicht om het huis niet op te laten warmen!")
					self.call_service("tts/google_say", entity_id = "media_player.gc_studeerkamer", message="De ramen moeten dicht om het huis niet op te laten warmen!")
		except:
			pass
	
	
	
	def forecast_changed(self, entity, attribute, old, new, kwargs):
		if self.get_state("input_boolean.buitenkraan") == "on":
			lowest = 100
			radar = self.get_state("weather.buienradar", attribute="all")
			
			# Loop:
			for i in range(0, len(radar['attributes']['forecast'])):
				templow = radar['attributes']['forecast'][i]['templow']
				if templow < lowest:
					lowest = templow
					
			if lowest < -1 and not self.tapNotification:
				self.tapNotification = True
				self.call_service("notify/mobile_app_smartphone", message="Het gaat vriezen. Zorg er voor dat de buitenkraan gesloten is", title="Klimaat")
		
	
	def windowNotifyReset(self, kwargs):
		self.windowNotificationOpen = False
		self.windowNotificationClose = False
		self.tapNotification = False
