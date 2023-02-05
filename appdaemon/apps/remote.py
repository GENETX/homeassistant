import appdaemon.plugins.hass.hassapi as hass
import const

import time
import datetime
from datetime import timedelta

class RemoteApp(hass.Hass):
	def initialize(self):
		self.listen_state(self.button_action, "sensor.remote_action")
		
 
	# Implementation of a remote
	def button_action(self, entity, attribute, old, new, kwargs):
		# Magic remote
		
		# Kodi Play/pause or turn on tv+avr or set home if we are away
		if new == "toggle":
			rl = int(float(self.get_state("input_number.runlevel")))
			kodi = self.get_state("media_player.kodi_kamer")
			spotify = self.get_state("media_player.spotify_ghoogsteen")
			doorbell = self.get_state("binary_sensor.deurbel_input") == "on"
			
			# First check if we need to set the system to home as a sort of override
			if rl < const.rlHome:
				self.select_option("input_select.status", "Thuis")
				self.turn_off("input_boolean.auto_runlevel")
				self.call_service("tts/google_translate_say", entity_id = "media_player.gc_huiskamer", message="Automatische runlevel bepaling uitgeschakeld.")
				
			# or toggle doorbell
			elif doorbell:
				self.turn_off("binary_sensor.deurbel_input")
			
			# Otherwise we use it for smart media
			elif kodi == "playing" or kodi == "paused":
				# toggle play/pause
				self.call_service("media_player/media_play_pause", entity_id = "media_player.kodi_kamer")
				
			elif spotify == "playing":
				# Select next song
				self.call_service("media_player/media_next_track", entity_id = "media_player.spotify_ghoogsteen")
				
			elif kodi == "idle":
				# check if we need to turn on or off:
				tv = self.get_state("media_player.tv")
				avr = self.get_state("media_player.avr_kamer")
				
				if tv == "on" or avr == "on":
					# turn off TV + AVR
					self.turn_off("media_player.tv")
					self.turn_off("media_player.avr_kamer")
				
				else:
					# turn on TV + AVR
					self.turn_on("media_player.tv")
					self.turn_on("media_player.avr_kamer")
					self.call_service("media_player/select_source", entity_id="media_player.avr_kamer", source="Mediacenter")
			
				
		# Lighting options (Master light)
		elif new == "brightness_up_click":
			brightness = float(self.get_state("input_number.master_verlichting"))
			brightness = min(1*255, brightness+0.05*255)
			self.set_state("input_number.master_verlichting", state = brightness)
		
		elif new == "brightness_down_click":
			brightness = float(self.get_state("input_number.master_verlichting"))
			brightness = max(0, brightness-0.05*255)
			self.set_state("input_number.master_verlichting", state = brightness)
		
		elif new == "brightness_up_hold":
			self.set_state("input_number.master_verlichting", state = 0.9*255.0)
		
		elif new == "brightness_down_hold":
			self.set_state("input_number.master_verlichting", state = 0)
		
		# AVR Volume
		elif new == "arrow_right_click":
			volume = self.get_state("media_player.avr_kamer", attribute="volume_level")
			volume = min(1, volume + 0.02)
			self.call_service("media_player/volume_set", entity_id="media_player.avr_kamer", volume_level=volume)

		
		elif new == "arrow_left_click":
			volume = self.get_state("media_player.avr_kamer", attribute="volume_level")
			volume = max(0, volume - 0.02)
			self.call_service("media_player/volume_set", entity_id="media_player.avr_kamer", volume_level=volume)
		
		#Thermostaat		
		elif new == "arrow_right_hold":
			setpoint = int(float(self.get_state("climate.nefit_nefit", attribute="temperature")))
			setpoint = min(float(setpoint)+1.0, 22)
			self.call_service("climate/set_temperature", entity_id = "climate.nefit_nefit", temperature=setpoint)
			self.call_service("tts/google_translate_say", entity_id = "media_player.gc_huiskamer", message="Thermostaat ingesteld op "+str(int(setpoint))+" graden.")
		
		elif new == "arrow_left_hold":
			setpoint = int(float(self.get_state("climate.nefit_nefit", attribute="temperature")))
			setpoint = max(float(setpoint)-1.0, 15)
			self.call_service("climate/set_temperature", entity_id = "climate.nefit_nefit", temperature=setpoint)
			self.call_service("tts/google_translate_say", entity_id = "media_player.gc_huiskamer", message="Thermostaat ingesteld op "+str(int(setpoint))+" graden.")
