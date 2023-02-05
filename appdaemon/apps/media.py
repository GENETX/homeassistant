import appdaemon.plugins.hass.hassapi as hass
import const

import sys
import requests

import math
import time
import datetime as dt

class MediaApp(hass.Hass):
	def initialize(self):
		# Helpers / States for interrupts
		self.kodiWasPlaying = False
		self.spotifyWasPlaying = False
		self.chromecastWasPlaying = False
		self.avrWasOn = False
		self.tvWasOn = False
		
		self.interruption = False
		
		self.listen_state(self.changed_runlevel, "input_number.runlevel")
	
		self.listen_state(self.changed_kodi, "media_player.kodi_kamer")
		self.listen_state(self.changed_spotify, "media_player.spotify_ghoogsteen")
		self.listen_state(self.changed_chromecast, "media_player.chromecast_woonkamer")
		self.listen_state(self.changed_avr, "media_player.avr_kamer")
		self.listen_state(self.changed_tv, "media_player.tv")
		
		self.listen_state(self.changed_interruption, "input_boolean.deurbel")
		self.listen_state(self.changed_interruption, "sensor.smartphone_phone_state")
		
		self.listen_state(self.avr_volume_changed, "media_player.avr_kamer", attribute="volume_level")
		
		# Restore
		kodiState = self.get_state("media_player.kodi_kamer")
		if kodiState == "playing":
			self.kodiWasPlaying = True
		
		spotifyState = self.get_state("media_player.spotify_ghoogsteen")
		if spotifyState == "playing":
			self.spotifyWasPlaying = True
		
		chromecastState = self.get_state("media_player.chromecast_woonkamer")
		if chromecastState == "playing":
			self.chromecastWasPlaying = True
			
		avrState = self.get_state("media_player.avr_kamer")
		if avrState == "on":
			self.avrWasOn = True
		
		tvState = self.get_state("media_player.tv")
		if tvState == "on":
			self.tvWasOn = True
			
		# Resore avr volume_level	
		self.last_avr_volume = self.get_state("media_player.avr_kamer", attribute="volume_level")
		
		
		
	
	def changed_kodi(self, entity, attribute, old, new, kwargs):
		# Monitor the state for interruptions
		if not self.interruption:
			kodiState = self.get_state("media_player.kodi_kamer")
			if kodiState == "playing":
				self.kodiWasPlaying = True
			else:
				self.kodiWasPlaying = False
	
		if self.get_state(const.auto) == "on":
			rl = int(float(self.get_state("input_number.runlevel")))
			if rl >= const.rlHome:
				kodi_type = self.get_state("media_player.kodi_kamer", attribute="media_content_type")
				kodi_duration = self.get_state("media_player.kodi_kamer", attribute="media_duration")
			
				if new == "playing":
					if kodi_type == "movie" and int(kodi_duration) >= 4500 or rl == const.rlMovie:
						# MOVIE MODE	
						# self.turn_on("switch.subwoofer")	
						
						if old != "paused":
							self.turn_on("media_player.tv")
							self.turn_on("media_player.avr_kamer")
							self.call_service("media_player/select_source", entity_id="media_player.avr_kamer", source="Mediacenter")
							# self.call_service("media_player/volume_set", entity_id="media_player.avr_kamer", volume_level=0.54)
						
						light = float(self.get_state("input_number.master_verlichting"))
						if light > 1:
							self.set_state("input_number.master_verlichting", state = 0.2*255.0)
						
					elif kodi_type != "music" or rl == const.rlMedia:
						# SERIES MODE
						if old != "paused":
							self.turn_on("media_player.tv")
							self.turn_on("media_player.avr_kamer")
							# self.turn_off("switch.subwoofer")
							
							self.call_service("media_player/select_source", entity_id="media_player.avr_kamer", source="Mediacenter")
							# self.call_service("media_player/volume_set", entity_id="media_player.avr_kamer", volume_level=0.48)	
							
					else:
						# Other media, music?
						if old != "paused":
							self.turn_on("media_player.avr_kamer")
							# self.turn_off("switch.subwoofer")
							
							# self.call_service("media_player/volume_set", entity_id="media_player.avr_kamer", volume_level=0.38)
							self.call_service("media_player/select_source", entity_id="media_player.avr_kamer", source="Mediacenter")
				
				elif new == "paused" and rl == const.rlMovie:
					# PAUSE MODE FOR MOVIES
					light = float(self.get_state("input_number.master_verlichting"))
					if light > 1:
						self.set_state("input_number.master_verlichting", state = 0.9*255.0)
					
				elif new == "idle":	
					pass

				
	def changed_runlevel(self, entity, attribute, old, new, kwargs):
		if self.get_state(const.auto) == "on":
			rl = int(float(self.get_state("input_number.runlevel")))
			if rl == const.rlMovie:
				self.turn_on("switch.subwoofer")
				self.call_service("media_player/volume_set", entity_id="media_player.avr_kamer", volume_level=0.54)
				
				light = float(self.get_state("input_number.master_verlichting"))
				if light > 1.0:
					self.set_state("input_number.master_verlichting", state = 0.2*255.0)
					
			elif rl == const.rlMedia:
				self.turn_off("switch.subwoofer")
				self.call_service("media_player/volume_set", entity_id="media_player.avr_kamer", volume_level=0.48)
				
			else:
				self.turn_off("switch.subwoofer")
				self.call_service("media_player/volume_set", entity_id="media_player.avr_kamer", volume_level=0.38)
			
	def changed_spotify(self, entity, attribute, old, new, kwargs):
		# Monitor the state for interruptions
		if not self.interruption:
			spotifyState = self.get_state("media_player.spotify_ghoogsteen")
			if spotifyState == "playing":
				self.spotifyWasPlaying = True
			else:
				self.spotifyWasPlaying = False
		
			
	
	def changed_chromecast(self, entity, attribute, old, new, kwargs):
		# Monitor the state for interruptions
		if not self.interruption:
			chromecastState = self.get_state("media_player.chromecast_woonkamer")
			if chromecastState == "playing":
				self.chromecastWasPlaying = True
			else:
				chromecastWasPlaying = False
		
		if self.get_state(const.auto) == "on":
			rl = int(float(self.get_state("input_number.runlevel")))
			if rl >= const.rlHome:
				chromecastState = self.get_state("media_player.chromecast_woonkamer")
				if chromecastState == "playing":
					self.call_service("media_player/volume_set", entity_id="media_player.avr_kamer", volume_level=0.38)
					self.call_service("media_player/select_source", entity_id="media_player.avr_kamer", source="Chromecast")
			
			
	def changed_avr(self, entity, attribute, old, new, kwargs):
		# Monitor the state for interruptions
		if not self.interruption:
			avrState = self.get_state("media_player.avr_kamer")
			if avrState == "on":
				self.avrWasOn = True
			else:	
				self.avrWasOn = False
			
			
	def changed_tv(self, entity, attribute, old, new, kwargs):
		# Monitor the state for interruptions
		if not self.interruption:
			tvState = self.get_state("media_player.tv")
			if tvState == "on":
				self.tvWasOn = True
			else:
				self.tvWasOn = False
			
	
	
	# Handle an interruption
	def changed_interruption(self, entity, attribute, old, new, kwargs):
		if self.get_state(const.auto) == "on":
			rl = int(float(self.get_state("input_number.runlevel")))
			if rl >= const.rlHome:
				phone = self.get_state("sensor.smartphone_phone_state")
				bell = self.get_state("input_boolean.deurbel")
				
				if phone == "offhook" or bell == "on":
					# We have an interruption:
					self.interruption = True
					self.run_in(self.pause_media, 1)
				else:
					self.run_in(self.resume_media, 5)
					self.interruption = False
				
	
	def pause_media(self, kwargs):
		if self.get_state(const.auto) == "on":
			rl = int(float(self.get_state("input_number.runlevel")))	
			if rl >= const.rlHome:									
				if self.spotifyWasPlaying:
					self.call_service("media_player/media_pause", entity_id = "media_player.spotify_ghoogsteen")
				
				if self.chromecastWasPlaying:
					self.call_service("media_player/media_pause", entity_id = "media_player.chromecast_woonkamer")
					
				if self.avrWasOn:
					self.call_service("media_player/volume_mute", entity_id = "media_player.avr_kamer", is_volume_muted=True)
					
				if self.tvWasOn:
					self.call_service("media_player/volume_mute", entity_id = "media_player.tv", is_volume_muted=True)
				
				pc = self.get_state("binary_sensor.desktop")
				if pc == "on":
					self.turn_off("switch.computerspeakers")
					
				if self.kodiWasPlaying:
					self.call_service("media_player/media_pause", entity_id = "media_player.kodi_kamer")
				
			
		
	def resume_media(self, kwargs):
		if self.get_state(const.auto) == "on":
			rl = int(float(self.get_state("input_number.runlevel")))	
			if rl >= const.rlHome:
				if self.spotifyWasPlaying:
					self.call_service("media_player/media_play", entity_id = "media_player.spotify_ghoogsteen")
				
				if self.chromecastWasPlaying:
					self.call_service("media_player/media_play", entity_id = "media_player.chromecast_woonkamer")
					
				if self.avrWasOn:
					self.call_service("media_player/volume_mute", entity_id = "media_player.avr_kamer", is_volume_muted=False)
					self.call_service("media_player/volume_set", entity_id="media_player.avr_kamer", volume_level=self.last_avr_volume)	
					
				if self.tvWasOn:
					self.call_service("media_player/volume_mute", entity_id = "media_player.tv", is_volume_muted=False)
					
				pc = self.get_state("binary_sensor.desktop")
				if pc == "on":
					self.turn_on("switch.computerspeakers")
					
				if self.kodiWasPlaying:
					self.call_service("media_player/media_play", entity_id = "media_player.kodi_kamer")
								
								
	def avr_volume_changed(self, entity, attribute, old, new, kwargs):
		try:
			if float(new) > 0:
				self.last_avr_volume = float(new)
		except:
			pass