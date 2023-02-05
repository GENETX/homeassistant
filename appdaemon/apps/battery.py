import appdaemon.plugins.hass.hassapi as hass
import const

import math
import time
import datetime
from datetime import timedelta

class BatteryApp(hass.Hass):
	def initialize(self):
		self.devicelist = [ "sensor.aqara_tvoc_battery",
							"sensor.beweging_boven_battery",
							"sensor.beweging_buiten_battery",
							"sensor.beweging_onder_battery",
							"sensor.co_melder_washok_battery",
							"sensor.lichtsensor_kamer_battery",
							"sensor.schakelaar_bed_battery",
							"sensor.schakelaar_keuken_battery",
							"sensor.temperatuur_badkamer_battery",
							"sensor.temperatuur_kamer_battery",
							"sensor.temperatuur_kantoor_battery",
							"sensor.temperatuur_keuken_battery",
							"sensor.temperatuur_slaapkamer_battery",
							"sensor.thuisschakelaar_achter_battery",
							"sensor.thuisschakelaar_voor_battery",
							"sensor.rookmelder_battery",
							"sensor.remote_battery",
							"sensor.schakelaar_eettafel_battery",
							"sensor.schakelaar_slaapkamer_battery",
							"sensor.schakelaar_woonkamer_battery",
							"sensor.schakelaar_slaapkamer_battery"
						]
						
		self.threshold = 20
		
		# run every day
		nt = datetime.time(20, 0, 0)
		self.run_daily(self.check_battery, nt)
		self.run_in(self.check_battery, 1)

	# Listen to changes in input
	def check_battery(self, kwargs):
		if self.get_state(const.auto) == "on":
			for d in self.devicelist:
				try:
					s = self.get_state(d)
					if s != "unknown":
						b = int(s)
						if b <= self.threshold:
							n = d
							try:
								n = self.get_state(d, attribute="friendly_name")
							except:
								pass
							self.call_service("notify/mobile_app_smartphone", message="Batterij niveau laag van "+n, title="Batterij")
				except:
					pass
		