import appdaemon.plugins.hass.hassapi as hass
import const

import math
import time
import datetime as dt

class LightApp(hass.Hass):
	def initialize(self):
		# States
		self.dark = False
		self.lightAutoOn = False
	
		# Helper vars
		self.threshold = 500
		self.irr_threshold = 30
		self.lux_threshold = 350
		self.elevation_threshold = 1.0
		
		# Automatic light
		t1 = dt.time(13, 0, 0)
		self.run_daily(self.autoLightOff, t1)
		t2 = dt.time(3, 0, 0)
		self.run_daily(self.autoLightOn, t2)
		t3 = dt.time(22, 30, 0)
		self.run_daily(self.awayLightOff, t3)
		
		# Listeners
		self.listen_state(self.irradiance_changed, "sensor.buienradar_irradiance")
		self.listen_state(self.irradiance_changed, "sensor.lichtsensor_kamer_illuminance_lux")
		self.listen_state(self.irradiance_changed, "sun.sun", attribute="elevation")
		self.listen_state(self.lightmaster_changed, "input_number.master_verlichting")
		self.listen_state(self.doorbel_changed, "input_boolean.deurbel")
		self.listen_state(self.light_buiten_changed, "light.licht_buiten")
		self.listen_state(self.light_hal_changed, "light.group_hal")
		self.listen_state(self.light_overloop_changed, "light.group_overloop")
		
		# Movements
		self.listen_state(self.move_hal_changed, "binary_sensor.beweging_onder_occupancy")
		self.listen_state(self.move_overloop_changed, "binary_sensor.beweging_boven_occupancy")
		self.listen_state(self.move_buiten_changed, "binary_sensor.beweging_buiten_occupancy")
		
		# Adapt overloop light if runlevel changed for lighting
		self.listen_state(self.move_overloop_changed, "input_number.runlevel")
		
		# Light when coming home
		self.listen_state(self.changed_gps, "person.gerwin_hoogsteen")
		
		# Buttons
		self.listen_state(self.schakelaar_keuken, "sensor.schakelaar_keuken_action")
		self.listen_state(self.schakelaar_voor, "sensor.thuisschakelaar_voor_action")
		self.listen_state(self.schakelaar_achter, "sensor.thuisschakelaar_achter_action")

		# State 
		self.listen_state(self.runlevel_changed, "input_number.runlevel")
		
		# Manual hal+overloop
		self.override_motion = False
		self.override_motion_buiten = False
		self.override_motion_hal = False
		self.override_motion_overloop = False
		self.homecoming = False
		
		
		# Restore:
		try:
			sun = float(self.get_state("sun.sun", attribute="elevation"))
			irr = float(self.get_state("sensor.buienradar_irradiance"))
			lux = float(self.get_state("sensor.lichtsensor_kamer_illuminance_lux"))
			
			self.lightAutoOn = False
			if sun < self.elevation_threshold or (irr*10+lux) < self.threshold or irr < self.irr_threshold or lux < self.lux_threshold:
				self.dark = True
				self.lightAutoOn = True 
		except:
			pass
			
		self.change_light()
		
	
	# Track irradiance for auto lighting
	def irradiance_changed(self, entity, attribute, old, new, kwargs):
		sun = float(self.get_state("sun.sun", attribute="elevation"))
		irr = float(self.get_state("sensor.buienradar_irradiance"))
		lux = float(self.get_state("sensor.lichtsensor_kamer_illuminance_lux"))
		
		hour = dt.datetime.now().hour
		rl = int(float(self.get_state("input_number.runlevel")))		
		
		# Automaticaly turn on the light
		if hour > 15 and self.lightAutoOn == False:
			if sun < self.elevation_threshold or (irr*10+lux) < self.threshold or irr < self.irr_threshold or lux < self.lux_threshold:
				self.lightAutoOn = True
				self.dark = True
				self.change_light()
			
		# Automaticaly turn off the light	
		elif hour < 11 and self.lightAutoOn == True:
			if sun > self.elevation_threshold and (irr*10+lux) > self.threshold and irr >= self.irr_threshold or lux >= self.lux_threshold:
				self.lightAutoOn = False
				self.dark = False
				self.change_light()
		
		# Presence simulation. Turn on some lights
		# Turns on between 19:00 - 22:00 and will turn off at 22:30
		if rl == const.rlAway and self.dark and hour >= 19 and hour < 22:
			if self.get_state(const.auto) == "on":
				self.turn_on("light.group_staande_lamp", brightness=0.9*255.0)	
				self.turn_on("light.group_eettafellamp", brightness=0.9*255.0)
				self.turn_on("light.lamp_aanrecht")
	
	def runlevel_changed(self, entity, attribute, old, new, kwargs):
		self.change_light()
		
	# Change the light setting
	def change_light(self):
		if self.get_state(const.auto) == "on":
			rl = int(float(self.get_state("input_number.runlevel")))
			
			if self.dark == False or rl == const.rlGone or rl == const.rlSleep:
				self.set_state("input_number.master_verlichting", state = 0.0)
			
			elif rl >= const.rlHome: #it is dark and we are not gone/sleeping
				# Turn on the lights
				if rl != const.rlMovie:
					self.set_state("input_number.master_verlichting", state = 0.9*255.0)
				else:
					self.set_state("input_number.master_verlichting", state = 0.2*255.0)
					
			
	def lightmaster_changed(self, entity, attribute, old, new, kwargs):
		rl = int(float(self.get_state("input_number.runlevel")))
		brightness = float(new)
		
		# Check if we change the lightmaster manually to avoid oscillation
		if rl >= const.rlHome:
			if brightness >= 1:
				self.dark = True
			else:
				self.dark = False
		
		# Magic ;)
		if self.get_state(const.auto) == "on":
			if brightness >= 1:
				# Do a special action if Kodi is playing a movie and we are under a Cinema mode threshold brightness
				kodi_state = self.get_state("media_player.kodi_kamer")
				if rl == const.rlMovie and kodi_state == "playing" and brightness <= 0.25*255.0:
					self.turn_on("light.group_eettafellamp", brightness=brightness)
					self.turn_on("light.group_staande_lamp", brightness=brightness)
					self.turn_on("light.tvledstrip", brightness=brightness)
					
					self.turn_off("light.leeslamp")
					self.turn_off("light.ikea_woonkamer_lamp_rechts")
					self.turn_off("light.ikea_woonkamer_lamp_links")
					self.turn_off("light.lamp_aanrecht")
				else:
					self.turn_on("light.group_eettafellamp", brightness=brightness)
					self.turn_on("light.group_woonkamer", brightness=brightness)
					self.turn_on("light.lamp_aanrecht")
					
			else:
				self.turn_off("light.group_eettafellamp")
				self.turn_off("light.group_woonkamer")
				self.turn_off("light.lamp_aanrecht")
				if rl != const.rlSleep:
					self.turn_off("light.group_slaapkamer")
		
	# Reset the automatic light switches
	def autoLightOn(self, kwargs):
		self.lightAutoOn = True
		
	def autoLightOff(self, kwargs):
		self.lightAutoOn = False
		
	# Disable lights presence simulation	
	def awayLightOff(self, kwargs):	
		self.log("Turning off presence simulation lights")
		self.lightAutoOn = False
		if self.get_state(const.auto) == "on":
			rl = int(float(self.get_state("input_number.runlevel")))
			if rl == const.rlAway:
				self.turn_off("light.group_staande_lamp")	
				self.turn_off("light.group_eettafellamp")
				self.turn_off("light.lamp_aanrecht")
				
				
	# Motion sensor activity		
	# FIXME Add doorbell
	def move_hal_changed(self, entity, attribute, old, new, kwargs):
		if self.get_state(const.auto) == "on" and not self.override_motion_hal:
			try:
				rl = int(float(self.get_state("input_number.runlevel")))
				brightness = float(self.get_state("input_number.master_verlichting"))
				deurbel = (self.get_state("input_boolean.deurbel"))
				
				if new == "on" or deurbel == "on":
					if rl >= const.rlHome and brightness >= 1.0:
						self.turn_on("light.group_hal", brightness=brightness)
					elif rl == const.rlSleep:
						self.turn_on("light.group_hal", brightness=0.25*255)
					else:
						self.turn_off("light.group_hal")
				else:
					self.turn_off("light.group_hal")
			except:
				self.turn_off("light.group_hal")
					
	def move_overloop_changed(self, entity, attribute, old, new, kwargs):
		if self.get_state(const.auto) == "on" and not self.override_motion_overloop:
			try:
				rl = int(float(self.get_state("input_number.runlevel")))
				brightness = float(self.get_state("input_number.master_verlichting"))
				
				if new == "on":
					if rl >= const.rlHome and brightness >= 1.0:
						self.turn_on("light.group_overloop", brightness=brightness)
					elif rl == const.rlSleep:
						self.turn_on("light.group_overloop", brightness=0.25*255)
					else:
						self.turn_off("light.group_overloop")
				else:
					self.turn_off("light.group_overloop")
			except:
				self.turn_off("light.group_overloop")
				
	
	def move_buiten_changed(self, entity, attribute, old, new, kwargs):
		if self.get_state(const.auto) == "on" and not self.override_motion_buiten:
			try:
				rl = int(float(self.get_state("input_number.runlevel")))
				brightness = float(self.get_state("input_number.master_verlichting"))
				
				if new == "on":
					if rl >= const.rlHome and brightness >= 1.0:
						self.turn_on("light.licht_buiten")
					elif rl == const.rlGone and self.homecoming and self.dark:
						self.turn_on("light.licht_buiten")
					else:
						self.turn_off("light.licht_buiten")
				else:
					self.turn_off("light.licht_buiten")
			except:
				self.turn_off("light.licht_buiten")
	
		
	def doorbel_changed(self, entity, attribute, old, new, kwargs):
		if self.get_state(const.auto) == "on":
			try:
				rl = int(float(self.get_state("input_number.runlevel")))
				brightness = float(self.get_state("input_number.master_verlichting"))
				deurbel = (self.get_state("input_boolean.deurbel"))
				motion = self.get_state("binary_sensor.beweging_onder_occupancy")
				
				if new == "on":
					if rl >= const.rlHome and brightness >= 1.0:
						self.turn_on("light.group_hal", brightness=brightness)
					else:
						self.turn_off("light.group_hal")
				elif motion == "off":
					self.turn_off("light.group_hal")
			except:
				self.turn_off("light.group_hal")
				

	# Switches
	# self.override_motion
	def schakelaar_keuken(self, entity, attribute, old, new, kwargs):
		if new == "brightness_move_up":
			self.toggle("light.lamp_aanrecht")
			
	def schakelaar_voor(self, entity, attribute, old, new, kwargs):
		if new == "on":
			self.override_motion = True
			self.override_motion_overloop = True
			self.override_motion_hal = True
			self.turn_on("light.group_hal", brightness=0.9*255)
			self.turn_on("light.group_overloop", brightness=0.9*255)
		if new == "off":
			self.override_motion = False
			self.override_motion_overloop = False
			self.override_motion_hal = False
			self.turn_off("light.group_hal")
			self.turn_off("light.group_overloop")
			
	def schakelaar_achter(self, entity, attribute, old, new, kwargs):
		if new == "on":
			self.override_motion_buiten = True
			self.turn_on("light.licht_buiten")
		if new == "off":
			self.override_motion_buiten = False
			self.turn_off("light.licht_buiten")
			
	def light_buiten_changed(self, entity, attribute, old, new, kwargs):
		motion = self.get_state("binary_sensor.beweging_buiten_occupancy")
		
		if new == "on" and old == "off" and motion == "off":
			# Manual turned on through interface, ignore motion
			self.override_motion_buiten = True
		elif new == "off":
			self.override_motion_buiten = False
			
	def light_hal_changed(self, entity, attribute, old, new, kwargs):
		motion = self.get_state("binary_sensor.beweging_onder_occupancy")
		 
		if new == "on" and old == "off" and motion == "off":
			# Manual turned on through interface, ignore motion
			self.override_motion_hal = True
		elif new == "off":
			self.override_motion_hal = False
			self.override_motion = False
			
	def light_overloop_changed(self, entity, attribute, old, new, kwargs):
		motion = self.get_state("binary_sensor.beweging_boven_occupancy")
		
		if new == "on" and old == "off" and motion == "off":
			# Manual turned on through interface, ignore motion
			self.override_motion_overloop = True
		elif new == "off":
			self.override_motion_overloop = False
			self.override_motion = False
			
					
					
	
	# Outdoor light
	def changed_gps(self, entity, attribute, old, new, kwargs):
		if old == "Campus" and new == "Omgeving":
			# Moving towards home, we have 45 minutes of light based on motion
			# This to avoid that we will be in the dark if the GPS did not trigger yet
			self.homecoming = True
			self.time_delay = self.run_in(self.turn_off_homecoming, 2700)
			
	def turn_off_homecoming(self, kwargs):
		self.homecoming = False
		