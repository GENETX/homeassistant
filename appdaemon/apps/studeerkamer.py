import appdaemon.plugins.hass.hassapi as hass
import const

import math
import time
import datetime as dt

class StudeerkamerApp(hass.Hass):
	def initialize(self):
		self.listen_state(self.changed_light, "input_number.master_verlichting")
		self.listen_state(self.changed_desktop, "binary_sensor.desktop")
		
	def changed_desktop(self, entity, attribute, old, new, kwargs):
		if self.get_state(const.auto) == "on":
			rl = int(float(self.get_state("input_number.runlevel")))
			if rl >= const.rlHome:
				pc = self.get_state("binary_sensor.desktop")
				temp = float(self.get_state("sensor.temperatuur_kantoor_temperature"))
				heater = self.get_state("climate.smart_infrared_panel_heater")
				
				# Turn on devices at the computer
				if pc == "on":
					self.turn_on("switch.computerspeakers")
					
					if temp < 19.0 and heater=="off":
						self.turn_on("climate.smart_infrared_panel_heater")
						self.call_service("climate/set_temperature", entity_id = "climate.smart_infrared_panel_heater", temperature=22.0)
					elif temp >= 19.0 and heater=="heat":
						self.turn_off("climate.smart_infrared_panel_heater")
					
				# And turn off when the PC is shut down	
				else:
					self.turn_off("switch.computerspeakers")
					if heater=="heat":
						self.turn_off("climate.smart_infrared_panel_heater")
				
				# Update light
				# self.run_in(self.delayed_light, 1)
				self.delayed_light(None)

	
	def changed_light(self, entity, attribute, old, new, kwargs):
		if self.get_state(const.auto) == "on":
			rl = int(float(self.get_state("input_number.runlevel")))
			if rl >= const.rlHome:
				# self.run_in(self.delayed_light, 1)
				self.delayed_light(None)
						
						
	# Zigbee overloading prevention:
	def delayed_light(self, kwargs):
		pc = self.get_state("binary_sensor.desktop")
		brightness = float(self.get_state("input_number.master_verlichting"))
		
		if pc == "on":
			if brightness >= 1:
				self.turn_on("light.group_studeerkamer", brightness=255.0)	
			else:
				self.turn_off("light.group_studeerkamer")
				
		else:
			self.turn_off("light.computerlamp")
			self.turn_off("light.studeerkamer")
