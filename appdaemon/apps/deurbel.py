import appdaemon.plugins.hass.hassapi as hass
import const

import math
import time
import datetime as dt

class DeurbelApp(hass.Hass):
	def initialize(self):
		# Monitor the doorbell
		self.listen_state(self.doorbell_changed, "sensor.deurbel_knop")
		# self.listen_state(self.doorbell_changed, "switch.deurbel_ring")
		
		self.listen_state(self.button_changed, "sensor.thuisschakelaar_voor_action")
		self.listen_state(self.input_doorbell_changed, "input_boolean.deurbel")
		
		self.active = False

	
	# Listen to changes in input
	def doorbell_changed(self, entity, attribute, old, new, kwargs):
		if self.get_state(const.auto) == "on":
			# Still experimenting with this as it doe snot always trigger on new=="1" and old=="0"....
			if new != "unknown" and old != "unknown" and not self.active:		
				# Send out the message
				rl = int(float(self.get_state("input_number.runlevel")))
				if rl <= const.rlSleep:
					self.active = True
					self.call_service("notify/mobile_app_smartphone", message="Er staat iemand bij de deur", title="Deurbel")
					self.run_in(self.doorbell_turn_off, 30)
				
				else: #if rl >= const.rlHome:	
					# Initial ring
					self.active = True
					self.turn_on("input_boolean.deurbel")

					# Notify
					self.call_service("notify/mobile_app_smartphone", message="Er staat iemand bij de deur", title="Deurbel")
					self.call_service("media_player/play_media", entity_id = "media_player.gc_huiskamer", media_content_id="https://ha.gerwinhoogsteen.nl/local/deurbel.mp3", media_content_type = "music")
					self.call_service("media_player/play_media", entity_id = "media_player.gc_keuken", media_content_id="https://ha.gerwinhoogsteen.nl/local/deurbel.mp3", media_content_type = "music")
					self.call_service("media_player/play_media", entity_id = "media_player.gc_studeerkamer", media_content_id="https://ha.gerwinhoogsteen.nl/local/deurbel.mp3", media_content_type = "music")
					
	
	# Turn off doorbell
	def button_changed(self, entity, attribute, old, new, kwargs):
		if self.get_state(const.auto) == "on":
			active = self.get_state("input_boolean.deurbel")
			
			if new == "brightness_move_down" and active == "on":
				self.run_in(self.doorbell_turn_off, 30)
				
	def input_doorbell_changed(self, entity, attribute, old, new, kwargs):
		if new == "off":
			self.active = False
	
	# Delayed action
	def doorbell_turn_off(self, kwargs):
		self.turn_off("input_boolean.deurbel")
		self.active = False
		
