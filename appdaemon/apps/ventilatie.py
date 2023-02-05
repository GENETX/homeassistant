import appdaemon.plugins.hass.hassapi as hass
import const

import math
import time
import datetime as dt

class VentilatieApp(hass.Hass):
	def initialize(self):
		# Monitor the ventilation system
		self.listen_state(self.mode_changed, "input_select.ventilatie")
		
		self.listen_state(self.changed_co2, "sensor.awair_carbon_dioxide")
		self.listen_state(self.changed_humidiy, "sensor.temperatuur_badkamer_humidity")
		self.listen_state(self.changed_runlevel, "input_number.runlevel")
		
		# Initialize the state
		self.turn_off("switch.ventilatie_switch_medium")
		self.turn_off("switch.ventilatie_switch_high")
		self.run_in(self.set_fan_mode, 1) 
		
		# States
		self.notifyCO2 = False
	
	# Listen to changes in input
	def mode_changed(self, entity, attribute, old, new, kwargs):
		self.turn_off("switch.ventilatie_switch_medium")
		self.turn_off("switch.ventilatie_switch_high")
		self.run_in(self.set_fan_mode, 1) 
		
	
	# Set the actual state (making sure the both switches were off first)
	def set_fan_mode(self, kwargs):
		mode = self.get_state("input_select.ventilatie")
		
		# Switch the state, ensuring as good as possible that we do not cause problems
		try:
			if mode == "Medium":
				self.turn_off("switch.ventilatie_switch_high")
				self.turn_on("switch.ventilatie_switch_medium")
			elif mode == "High":
				self.turn_off("switch.ventilatie_switch_medium")
				self.turn_on("switch.ventilatie_switch_high")
			else:
				self.turn_off("switch.ventilatie_switch_medium")
				self.turn_off("switch.ventilatie_switch_high")
		except:
			self.turn_off("switch.ventilatie_switch_medium")
			self.turn_off("switch.ventilatie_switch_high")

	def auto_level(self):
		if self.get_state("input_boolean.ventilator_auto") == "on":
			try:
				if self.get_state(const.auto) == "on":
					living_co2 = float(self.get_state("sensor.awair_carbon_dioxide"))
					bath_hum = float(self.get_state("sensor.temperatuur_badkamer_humidity"))
					
					rl = int(float(self.get_state("input_number.runlevel")))
					
					if rl >= const.rlHome:
						if living_co2 > 1200 or bath_hum > 70:
							self.select_option("input_select.ventilatie", "High")			
						elif living_co2 > 1000 or bath_hum > 60:
							self.select_option("input_select.ventilatie", "Medium")
						else:
							self.select_option("input_select.ventilatie", "Low")
							
					elif rl == const.rlGone:		
						if bath_hum > 65:
							self.select_option("input_select.ventilatie", "Medium")
						else:
							self.select_option("input_select.ventilatie", "Low")
							
					else:
						self.select_option("input_select.ventilatie", "Low")
			except:
				pass
			
		

	# Track living room CO2
	def changed_co2(self, entity, attribute, old, new, kwargs):
		self.auto_level()
		
		try:
			rl = int(float(self.get_state("input_number.runlevel")))
			if float(new) > 1000 and rl >= const.rlHome and not self.notifyCO2:
				self.notifyCO2 = True
				# Notify that it might be wise to open ventilation vents
				self.call_service("notify/mobile_app_smartphone", message="Hoge concentratie CO2, open de ventilatieroosters", title="Ventilatie")
				self.call_service("tts/google_translate_say", entity_id = "media_player.gc_huiskamer", message="Hoge concentratie CO2, open de ventilatieroosters")
				self.call_service("tts/google_translate_say", entity_id = "media_player.gc_keuken", message="Hoge concentratie CO2, open de ventilatieroosters")
				self.call_service("tts/google_translate_say", entity_id = "media_player.gc_studeerkamer", message="Hoge concentratie CO2, open de ventilatieroosters")
			
			elif self.notifyCO2 and float(new) < 800:
				# Disable notifcation for next time
				self.notifyCO2 = False
				
		except:
			pass
			# communication error

	# Track bathroom humidity
	def changed_humidiy(self, entity, attribute, old, new, kwargs):
		self.auto_level()
		
	# Track runlevel
	# Track bathroom humidity
	def changed_runlevel(self, entity, attribute, old, new, kwargs):
		self.auto_level()
		