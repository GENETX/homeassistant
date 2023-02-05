import appdaemon.plugins.hass.hassapi as hass
import const

import math
import time
import datetime as dt

class AlarmApp(hass.Hass):
	def initialize(self):
		# Monitor the doorbell
		self.listen_state(self.signal_alarm, "binary_sensor.co_melder_washok_carbon_monoxide")
		self.listen_state(self.signal_alarm, "binary_sensor.rookmelder_smoke")

		# Track battery level
		self.listen_state(self.co_battery, "binary_sensor.co_melder_washok_battery_low")
		self.listen_state(self.rook_battery, "binary_sensor.rookmelder_battery_low")
		
		# Track movement when gone
		self.listen_state(self.movement_detected, "binary_sensor.beweging_onder_occupancy")
		self.listen_state(self.movement_detected, "binary_sensor.beweging_boven_occupancy")
		self.listen_state(self.runlevel_changed, "input_number.runlevel")
		self.listen_state(self.alarm_button_changed, "input_boolean.alarm")
		
		# Alarm for fire
		self.alarm = False
		
		# Alarm for movement
		self.alarm_movement = False
		self.alarm_pretrigger = False
	
	# Listen to changes in input
	def signal_alarm(self, entity, attribute, old, new, kwargs):
		co = self.get_state("binary_sensor.co_melder_washok_carbon_monoxide")
		smoke = self.get_state("binary_sensor.rookmelder_smoke")
		
		# Add rookmelder
		if not self.alarm:
			if co == "on" or smoke == "on":
				# Enable the alarm button to stop the alarm itself
				self.turn_on("input_boolean.alarm")
				
				# Notify always
				self.call_service("notify/mobile_app_smartphone", message="Er gaat een alarm af", title="Alarm")	
				
				# Signal doorbell
				rl = int(float(self.get_state("input_number.runlevel")))	
				if rl >= const.rlSleep:	
					# ring the doorbell sound
					self.run_in(self.turn_off_doorbell, 3)
					self.turn_on("switch.deurbel")
				
					# Signal an alarm
					self.call_service("media_player/play_media", entity_id = "media_player.gc_huiskamer", media_content_id="https://ha.gerwinhoogsteen.nl/local/alarm.mp3", media_content_type = "music")
					self.call_service("media_player/play_media", entity_id = "media_player.gc_keuken", media_content_id="https://ha.gerwinhoogsteen.nl/local/alarml.mp3", media_content_type = "music")
					self.call_service("media_player/play_media", entity_id = "media_player.gc_studeerkamer", media_content_id="https://ha.gerwinhoogsteen.nl/local/alarm.mp3", media_content_type = "music")
					self.call_service("media_player/play_media", entity_id = "media_player.gc_slaapkamer", media_content_id="https://ha.gerwinhoogsteen.nl/local/alarm.mp3", media_content_type = "music")
					
					# Lampen
					self.turn_on("light.group_hal", brightness=255)
					self.turn_on("light.group_overloop", brightness=255)
					self.turn_on("light.group_eettafellamp", brightness=255)
					self.turn_on("light.group_slaapkamer", brightness=255)
					self.turn_on("light.group_studeerkamer", brightness=255)
					self.turn_on("light.light.group_woonkamer", brightness=255)
					self.turn_on("light.lamp_aanrecht")
				

		else:
			self.alarm = False
	
	
	# Turn off doorbell	
	def turn_off_doorbell(self, kwargs):
		self.turn_off("switch.deurbel")
		
	
	def co_battery(self, entity, attribute, old, new, kwargs):
		if old == "off" and new == "on":
			self.call_service("notify/mobile_app_smartphone", message="Batterij niveau CO-melder laag", title="Batterij")
			
	def rook_battery(self, entity, attribute, old, new, kwargs):
		if old == "off" and new == "on":
			self.call_service("notify/mobile_app_smartphone", message="Batterij niveau rookmelder laag", title="Batterij")
			
			
			
# ALARM FOR MOVEMENT
# Under development!
	def movement_detected(self, entity, attribute, old, new, kwargs):
		# FIXME: FOR NOW ONLY A MESSAGE
		if new == "on" and old == "off":
			if self.get_state("input_boolean.alarm") == "on":
			
				# Check if we already had a pretrigger (so this is the second movement detected)
				if self.alarm_pretrigger and not self.alarm_movement:
					# We have an alarm
					self.alarm_movement = True
					self.call_service("notify/mobile_app_smartphone", message="Er is thuis beweging gedetecteerd! Mogelijke inbraak", title="Alarm")
					
					if self.get_state(const.auto) == "on":
						# For now we disable too much noisy things
						self.run_in(self.turn_off_doorbell, 3)
						self.turn_on("switch.deurbel")
						
						self.call_service("media_player/play_media", entity_id = "media_player.gc_huiskamer", media_content_id="https://ha.gerwinhoogsteen.nl/local/alarm.mp3", media_content_type = "music")
						self.call_service("media_player/play_media", entity_id = "media_player.gc_keuken", media_content_id="https://ha.gerwinhoogsteen.nl/local/alarml.mp3", media_content_type = "music")
						self.call_service("media_player/play_media", entity_id = "media_player.gc_studeerkamer", media_content_id="https://ha.gerwinhoogsteen.nl/local/alarm.mp3", media_content_type = "music")
						self.call_service("media_player/play_media", entity_id = "media_player.gc_slaapkamer", media_content_id="https://ha.gerwinhoogsteen.nl/local/alarm.mp3", media_content_type = "music")
			
				elif not self.alarm_movement:
					self.alarm_pretrigger = True
					self.run_in(self.reset_pretrigger, 300)
				
	def runlevel_changed(self, entity, attribute, old, new, kwargs):
		if self.get_state(const.auto) == "on":	
			rl = int(float(self.get_state("input_number.runlevel")))	
			
			# FIXME, MUST BECOME GONE!
			if rl <= const.rlGone:
				self.turn_on("input_boolean.alarm")
			else:
				self.turn_off("input_boolean.alarm")
				self.alarm_movement = False
				self.alarm_pretrigger = False
	
	
	# Ability to turn off the signal
	def alarm_button_changed(self, entity, attribute, old, new, kwargs):
		if new == "off" and old == "on" and self.alarm_movement:
			self.turn_off_alarm(None)
			
	def turn_off_alarm(self, kwargs):
		if self.alarm_movement or self.alarm:
			self.alarm_movement = False
			self.alarm_pretrigger = False
			
			# Turn off all the alarms
			self.turn_off("switch.deurbel")
			
			# Stop the playing of music
			self.call_service("media_player/media_stop", entity_id="media_player.gc_huiskamer")
			self.call_service("media_player/media_stop", entity_id="media_player.gc_keuken")
			self.call_service("media_player/media_stop", entity_id="media_player.gc_studeerkamer")
			self.call_service("media_player/media_stop", entity_id="media_player.gc_slaapkamer")
			
	# Reset pretrigger
	def reset_pretrigger(self, kwargs):
		if not self.alarm_movement:
			self.alarm_pretrigger = False