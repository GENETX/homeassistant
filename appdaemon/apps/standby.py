import appdaemon.plugins.hass.hassapi as hass
import const

import math
import time
import datetime as dt

class StandbyApp(hass.Hass):
	def initialize(self):
		self.listen_state(self.changed_runlevel, "input_number.runlevel")
			
	def changed_runlevel(self, entity, attribute, old, new, kwargs):
		if self.get_state(const.auto) == "on":
			rl = int(float(self.get_state("input_number.runlevel")))
			if rl >= const.rlHome:
				# Stuff could be turned on if needed
				pass
				
			else:
				# Stuff should be turned off
				# Living
				self.turn_off("media_player.avr_kamer")
				self.turn_off("media_player.tv")
				self.turn_off("switch.subwoofer")
				
				# Home Office
				self.turn_off("switch.computerspeakers")
				heater = self.get_state("climate.smart_infrared_panel_heater")
				if heater=="heat":
					self.turn_off("climate.smart_infrared_panel_heater")
				
				# Stop media playback
				self.call_service("media_player/media_stop", entity_id = "media_player.kodi_kamer")
