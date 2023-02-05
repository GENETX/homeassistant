import appdaemon.plugins.hass.hassapi as hass
import time
import datetime
from datetime import timedelta

class GoogleAliveApp(hass.Hass):
	# Hack to keep the google homes alive :P
	def initialize(self):
		self.run_every(self.activate_gh, "now", 2 * 60)

	def activate_gh(self, kwargs):
		s = self.get_state("media_player.gc_slaapkamer")
		if s != "playing":
			self.call_service("media_player/play_media", entity_id = "media_player.gc_slaapkamer", media_content_id="https://ha.gerwinhoogsteen.nl/local/silence.mp3", media_content_type = "music")