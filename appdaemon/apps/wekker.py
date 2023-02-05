import appdaemon.plugins.hass.hassapi as hass
import const

import time
import datetime
from datetime import timedelta

class WekkerApp(hass.Hass):
	def initialize(self):
		self.listen_state(self.changed_alarmtime, "sensor.smartphone_next_alarm")
		self.alarm = None
		
		self.brightness = 0
		self.alarm_active = False
		
		self.call_service("media_player/media_stop", entity_id = "media_player.gc_slaapkamer")
		self.call_service("media_player/volume_set", entity_id="media_player.gc_slaapkamer", volume_level=0.25)
		
		self.turn_on("light.bedlamp_links", color_temp=454.0, brightness=0.0) # add delay
		self.turn_on("light.bedlamp_rechts", color_temp=454.0, brightness=0.0) # add delay
		self.turn_on("light.slaapkamer", color_temp=454.0, brightness=0.0) # add delay
		
		# Monitor change in the input field
		self.listen_state(self.changed_runlevel, "input_number.runlevel")
		
		self.listen_state(self.turn_off_sleep, "light.bedlamp_links", old="on", new="off")
		
		self.listen_state(self.button_action, "sensor.schakelaar_bed_action")

		try:
			s = self.get_state("sensor.smartphone_next_alarm", attribute="Time in Milliseconds")
			t = datetime.datetime.fromtimestamp((int(s)/1000)-1800)
			if self.alarm is not None:
				self.cancel_timer(self.alarm)
				self.alarm = None
			
			self.alarm = self.run_at(self.kickoff_alarm, t)
		except:
			pass 
 
	def changed_alarmtime(self, entity, attribute, old, new, kwargs):
		try:
			s = self.get_state("sensor.smartphone_next_alarm", attribute="Time in Milliseconds")
			t = datetime.datetime.fromtimestamp((int(s)/1000)-1800)
			try:
				if self.alarm is not None:
					self.cancel_timer(self.alarm)
					self.alarm = None
			except:
				pass
			self.alarm = self.run_at(self.kickoff_alarm, t)

		except:
			if self.alarm is not None:
				try:
					self.cancel_timer(self.alarm)
					self.alarm = None
				except:
					pass
		

	def kickoff_alarm(self, kwargs):
		if self.get_state(const.auto) == "on":
			rl = int(float(self.get_state("input_number.runlevel")))
			if not self.alarm_active and rl == const.rlSleep:
				self.brightness = 0
				self.alarm_active = True
				self.call_service("media_player/volume_set", entity_id = "media_player.gc_slaapkamer", volume_level=0.33)
				self.call_service("media_player/play_media", entity_id = "media_player.gc_slaapkamer", media_content_id="https://ha.gerwinhoogsteen.nl/local/birds.mp3", media_content_type = "music")
				self.run_in(self.wakeuplight, 10)
				self.run_in(self.stop_all, 1900) 

	def wakeuplight(self, kwargs):
		if self.brightness < 250.0:
			self.brightness += 13.0
			# self.turn_on("light.bedlamp_links", color_temp=454.0-self.brightness, brightness=self.brightness) # add delay
			# self.turn_on("light.bedlamp_rechts", color_temp=454.0-self.brightness, brightness=self.brightness) # add delay
			# self.turn_on("light.slaapkamer", color_temp=454.0-self.brightness, brightness=self.brightness) # add delay
			self.turn_on("light.group_slaapkamer", color_temp=454.0-self.brightness, brightness=self.brightness) # add delay
			self.run_in(self.wakeuplight, 80)
		else:
			self.brightness = 255.0
			# self.turn_on("light.bedlamp_links", color_temp=454.0-self.brightness, brightness=255.0) # add delay
			# self.turn_on("light.bedlamp_rechts", color_temp=454.0-self.brightness, brightness=255.0) # add 
			# self.turn_on("light.slaapkamer", color_temp=454.0-self.brightness, brightness=255.0) # add delay
			self.turn_on("light.group_slaapkamer", color_temp=454.0-self.brightness, brightness=255.0) # add delay
			
			# Already prepare the receiver
			self.call_service("media_player/select_source", entity_id="media_player.avr_kamer", source="KPN")


	def stop_all(self, kwargs):
		self.alarm_active = False
		self.brightness = 0.0
		
		self.call_service("media_player/media_stop", entity_id="media_player.gc_slaapkamer")
		self.call_service("media_player/volume_set", entity_id="media_player.gc_slaapkamer", volume_level=0.33)


	def changed_runlevel(self, entity, attribute, old, new, kwargs):	
		if self.get_state(const.auto) == "on":
			new = int(float(new))
			old = int(float(old))
			
			if new == const.rlSleep and old == const.rlHome:
				self.call_service("tts/google_translate_say", entity_id = "media_player.gc_slaapkamer", message="Welterusten Gerwin!")
			elif new == const.rlHome and old == const.rlSleep:
				self.call_service("media_player/media_stop", entity_id="media_player.gc_slaapkamer")
				self.call_service("media_player/volume_set", entity_id="media_player.gc_slaapkamer", volume_level=0.33)
				self.call_service("tts/google_translate_say", entity_id = "media_player.gc_slaapkamer", message="Goedemorgen Gerwin!")

	def turn_off_sleep(self, entity, attribute, old, new, kwargs):
		if not self.alarm_active:
			self.turn_off("light.slaapkamer")		
			
			
	# Button to set sleep/home mode:
	def button_action(self, entity, attribute, old, new, kwargs):
		if self.get_state(const.auto) == "on":
			rl = int(float(self.get_state("input_number.runlevel")))
			# Setting runlevel to away
			if new == "brightness_move_down" and rl >= const.rlHome:
				self.set_value("input_number.runlevel", int(const.rlSleep))
				
			# Setting runlevel to home
			if new == "brightness_move_up" and rl < const.rlHome:
				self.set_value("input_number.runlevel", int(const.rlHome))