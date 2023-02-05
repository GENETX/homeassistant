import appdaemon.plugins.hass.hassapi as hass
import const

import math
import time
import datetime
from datetime import timedelta

class AfvalApp(hass.Hass):
	def initialize(self):	
		self.oranje = False
		self.groen = False
		self.blauw = False
		
		nt = datetime.time(20, 0, 0)
		self.run_in(self.storeAfval, 1)
		self.run_daily(self.storeAfval, nt)

	def notifyAfval(self):
		rl = int(float(self.get_state("input_number.runlevel")))	
		if rl >= const.rlGone:	
			try:
				if self.groen:
					self.call_service("notify/mobile_app_smartphone", message="De groene container wordt morgen geleegd", title="Afval")
					if rl >= const.rlHome:	
						self.call_service("tts/google_translate_say", entity_id = "media_player.gc_huiskamer", message="De groene container wordt morgen geleegd")
						self.call_service("tts/google_translate_say", entity_id = "media_player.gc_keuken", message="De groene container wordt morgen geleegd")
						self.call_service("tts/google_translate_say", entity_id = "media_player.gc_studeerkamer", message="De groene container wordt morgen geleegd")
			except:
				pass
				
			try:	
				if self.blauw:
					self.call_service("notify/mobile_app_smartphone", message="Papier wordt morgen opgehaald", title="Afval")
					if rl >= const.rlHome:	
						self.call_service("tts/google_translate_say", entity_id = "media_player.gc_huiskamer", message="Papier wordt morgen opgehaald")
						self.call_service("tts/google_translate_say", entity_id = "media_player.gc_keuken", message="Papier wordt morgen opgehaald")
						self.call_service("tts/google_translate_say", entity_id = "media_player.gc_studeerkamer", message="Papier wordt morgen opgehaald")
			except:
				pass
				
			try:	
				if self.oranje:
					self.call_service("notify/mobile_app_smartphone", message="De plastic container wordt morgen geleegd", title="Afval")
					if rl >= const.rlHome:	
						self.call_service("tts/google_translate_say", entity_id = "media_player.gc_huiskamer", message="De plastic container wordt morgen geleegd")
						self.call_service("tts/google_translate_say", entity_id = "media_player.gc_keuken", message="De plastic container wordt morgen geleegd")
						self.call_service("tts/google_translate_say", entity_id = "media_player.gc_studeerkamer", message="De plastic container wordt morgen geleegd")
			except:
				pass
				
	def storeAfval(self, kwargs):
		self.groen = False
		self.blauw = False
		self.oranje= False
		
		today = datetime.datetime.now().date()
		today += datetime.timedelta(days=1)
	
		try:
			groen = self.get_state("sensor.twentemilieu_organic_waste_pickup")
			groent = datetime.datetime.strptime(groen, '%Y-%m-%d').date()
			if groent == today:
				self.groen = True
		except:
			pass
			
		try:	
			blauw = self.get_state("sensor.twentemilieu_paper_waste_pickup")	
			blauwt = datetime.datetime.strptime(blauw, '%Y-%m-%d').date()
			if blauwt == today:
				self.blauw = True
		except:
			pass
			
		try:	
			oranje = self.get_state("sensor.twentemilieu_plastic_waste_pickup")	
			oranjet = datetime.datetime.strptime(oranje, '%Y-%m-%d').date()
			if oranjet == today:
				self.oranje = True
		except:
			pass
		
		self.notifyAfval()

