import appdaemon.plugins.hass.hassapi as hass
import const

import math
import time
import datetime
from dateutil import parser
from datetime import timedelta
from datetime import timezone

class VaatwasserApp(hass.Hass): 
	def initialize(self):	
		# MQTT
		self.mqtt = self.get_plugin_api("MQTT")	
		
		# Config
		self.devname = "vaatwasser"
		self.powerthreshold = 1.0
		self.delay = 300

		# Add time restrictions to devices
		self.allowedStartHour = None
		self.allowedEndHour = None 	# Including, so 22 means 22:59 is also allowed!
	
		self.timestep = 900 
		
		# Profiles in Watts
		# Vaatwasser = 1.3kWh
		self.profile = [200, 1704, 1139, 66, 44, 1592, 462, 4, 5]
	
		# State
		self.running = False
		self.waiting = False
		self.smartstarttimer = None
		
		self.energy = 0
		self.costs = 0
		self.co2 = 0
		
		self.delaytimer = None
		self.finishtimer = None

		# Listeners
		self.listen_state(self.changed_power, "sensor.stopcontact_"+self.devname+"_power")
		self.listen_state(self.changed_energy, "sensor.stopcontact_"+self.devname+"_energy")
		
		self.listen_state(self.changed_powerswitch, "switch.stopcontact_"+self.devname, old="off", new="on")
		self.listen_state(self.changed_datetime, "input_datetime."+self.devname+"_starttijd")
		
		self.listen_state(self.click_button_price, "input_button."+self.devname+"_goedkoop")
		self.listen_state(self.click_button_co2, "input_button."+self.devname+"_co2")
		self.listen_state(self.click_button_clever, "input_button."+self.devname+"_clever")

		# Initial state
		self.set_state("sensor."+self.devname+"_plan_status", state="Inactief") 
		if float(self.get_state("sensor.stopcontact_"+self.devname+"_power")) >= self.powerthreshold:
			self.running = True
			self.set_state("sensor."+self.devname+"_plan_status", state="Actief")

		# Optimal scheduling
		self.run_in(self.calculate, 10)
		
		
		# Restore
		if float(self.get_state("sensor.stopcontact_"+self.devname+"_power")) >= self.powerthreshold:
			self.running = True
			self.set_state("sensor."+self.devname+"_plan_status", state="Actief")

	def changed_power(self, entity, attribute, old, new, kwargs):
		# First check the smart start and disable the device if needed
		smartstart = self.get_state("input_boolean."+self.devname+"_smartstart") == "on"
		smarttime = int(self.get_state("input_datetime."+self.devname+"_starttijd", attribute="timestamp"))
		thistime = int(time.time())
		
		# Check if we should delay the start
		if smartstart and not thistime >= smarttime-10 and not self.waiting and self.get_state(const.auto) == "on":
			# We should turn off the device if it is consuming
			if float(new) >= self.powerthreshold:
				# This is the only way to turn off with smart start due to the initial power peak when setting a mode
				# This will be triggered after 15 seconds. Hence, we have 15 seconds to set to turn on the dishwasher, set the mode, and press start
				self.run_in(self.smart_turn_off, 15)
				
			
		# Else, we should be running and this code should do the accounting + notification trigger
		else:
			# Device is running
			if float(new) >= self.powerthreshold:
				# Make sure we don't get false notifications
				if self.finishtimer is not None:
					try:	
						self.cancel_timer(self.finishtimer)
						self.finishtimer = None
					except:
						pass
					
				# Reset accounting triggers
				if not self.running:
					# Reset the defaults
					self.running = True
					self.waiting = False
					self.energy = 0
					self.costs = 0
					self.co2 = 0
					
					# Calculate the end time:
					et = datetime.datetime.fromtimestamp(int(time.time())+len(self.profile)*self.timestep)
					
					s = "Actief - Klaar rond "+et.strftime('%H:%M')
					self.set_state("sensor."+self.devname+"_plan_status", state=s)
			
			# Device seems to be idle
			# Activate the delay if needed
			else:
				if self.running and self.finishtimer is None:
					self.finishtimer = self.run_in(self.timer_finish, self.delay)
				

	# This is the only way to turn off with smart start due to the initial power peak when setting a mode
	# This will be triggered after 30 seconds. Hence, we have 30 seconds to set to turn on the dishwasher, set the mode, and press start
	def smart_turn_off(self, kwargs):
		# First check the smart start and disable the device if needed
		smartstart = self.get_state("input_boolean."+self.devname+"_smartstart") == "on"
		smarttime = int(self.get_state("input_datetime."+self.devname+"_starttijd", attribute="timestamp"))
		thistime = int(time.time())
		
		# Check if we should delay the start
		if smartstart and not thistime >= smarttime and not self.waiting and self.get_state(const.auto) == "on":
			# Set the waiting state
			self.waiting = True
			self.running = False
			self.turn_off("switch.stopcontact_"+self.devname)
					
			# Set a message in the interface:
			s = "Uitgesteld met Smart Start"
			self.set_state("sensor."+self.devname+"_plan_status", state=s)
			
			# Set the timer for the smart start
			st = self.get_state("input_datetime."+self.devname+"_starttijd")
			self.smartstarttimer = self.run_at(self.delayed_start, st)
	
	
	
	# Activate after delayed start
	def delayed_start(self, kwargs):
		smartstart = self.get_state("input_boolean."+self.devname+"_smartstart") == "on"
		smarttime = int(self.get_state("input_datetime."+self.devname+"_starttijd", attribute="timestamp"))
		thistime = int(time.time())
		
		# Check if we should start
		if smartstart and self.get_state(const.auto) == "on":
			self.waiting = False
			self.smartstarttimer = None
			
			# Start the device
			self.turn_on("switch.stopcontact_"+self.devname)
			
			# And push a notification
			self.call_service("notify/mobile_app_smartphone", message="De "+self.devname+" start nu door middel van Smart Start", title="Witgoed")
			
	# Cleanup if we decide to flick the switch now		
	def changed_powerswitch(self, entity, attribute, old, new, kwargs):
		try:
			self.waiting = False
			if self.smartstarttimer is not None:
				self.cancel_timer(self.smartstarttimer)
				self.smartstarttimer = None
		except:
			pass
			
	# Monitor changes in datetime when the device is waiting		
	def changed_datetime(self, entity, attribute, old, new, kwargs):
		smartstart = self.get_state("input_boolean."+self.devname+"_smartstart") == "on"
		smarttime = int(self.get_state("input_datetime."+self.devname+"_starttijd", attribute="timestamp"))
		thistime = int(time.time())
		
		# Sanity check, if the datetime is in history we do no nothing
		if smartstart and self.waiting and self.smartstarttimer is not None and self.get_state(const.auto) == "on":
			if thistime < smarttime:
				try:
					if self.smartstarttimer is not None:
						self.cancel_timer(self.smartstarttimer)
						self.smartstarttimer = None
				except:
					pass
					
				# Change the timer
				st = self.get_state("input_datetime."+self.devname+"_starttijd")
				self.smartstarttimer = self.run_at(self.delayed_start, st)
				
	
	
	
	# Monitor the energy usage of this run
	def changed_energy(self, entity, attribute, old, new, kwargs):
		if self.running:
			price = float(self.get_state("sensor.zonneplan_current_electricity_tariff"))
			co2 = float(self.get_state("sensor.zonneplan_current_co2"))
			
			diff = float(new)-float(old)
			self.energy += diff
			self.costs += diff*price
			self.co2 += diff*co2
			


	# Finish notification
	def timer_finish(self, kwargs):
		if self.running and float(self.get_state("sensor.stopcontact_"+self.devname+"_power")) < self.powerthreshold:
			self.running = False
			
			# Set the stats
			s = "{:.2f} kWh".format(self.energy)
			s = s.replace(".", ",")
			a = "??? {:.2f} en {:d} gCO2".format(self.costs, int(round(self.co2)))
			a = a.replace(".", ",")
			
			self.mqtt.mqtt_publish("homeassistant/sensor/"+self.devname+"/last_run", s, retain=True)
			self.mqtt.mqtt_publish("homeassistant/sensor/"+self.devname+"/last_run/info", a, retain=True)
		
			# Create the message
			msg = "De "+self.devname+" is klaar! Statistieken: {:.2f} kWh verbruikt voor in totaal ??? {:.2f} met {:d} gCO2 uitstoot.".format(self.energy, self.costs, int(round(self.co2)))
			
			# Send out the message
			rl = int(float(self.get_state("input_number.runlevel")))	
			self.call_service("notify/mobile_app_smartphone", message=msg, title="Witgoed")
			if rl >= const.rlHome:	
				self.call_service("tts/google_translate_say", entity_id = "media_player.gc_huiskamer", message="De "+self.devname+" is klaar!")
				self.call_service("tts/google_translate_say", entity_id = "media_player.gc_keuken", message="De "+self.devname+" is klaar!")
				self.call_service("tts/google_translate_say", entity_id = "media_player.gc_studeerkamer", message="De "+self.devname+" is klaar!")
			
			# Set the state
			self.set_state("sensor."+self.devname+"_plan_status", state="Klaar")
			self.finishtimer = self.run_in(self.timer_idle, 7200)
			
			# Reset
			self.energy = 0
			self.costs = 0
			self.co2 = 0

	# Timer to reset the device description to idle again
	def timer_idle(self, kwargs):
		if not self.running:
			self.set_state("sensor."+self.devname+"_plan_status", state="Inactief")




	# Helpers to set the time
	def click_button_price(self, entity, attribute, old, new, kwargs):
		dt = self.get_state("sensor."+self.devname+"_plan_price_timestamp")
		self.call_service("input_datetime/set_datetime", entity_id="input_datetime."+self.devname+"_starttijd", timestamp=dt)
		
	def click_button_co2(self, entity, attribute, old, new, kwargs):
		dt = self.get_state("sensor."+self.devname+"_plan_co2_timestamp")
		self.call_service("input_datetime/set_datetime", entity_id="input_datetime."+self.devname+"_starttijd", timestamp=dt)
		
	def click_button_clever(self, entity, attribute, old, new, kwargs):
		dt = self.get_state("sensor."+self.devname+"_plan_clever_timestamp")
		self.call_service("input_datetime/set_datetime", entity_id="input_datetime."+self.devname+"_starttijd", timestamp=dt)

	







	
	# Calculate the costs
	def calculate(self, kwargs):
		# Always good to have a backup if things fail
		try:
	#### Preparation
			# Obtaining data
			zp = self.get_state("sensor.zonneplan_current_electricity_tariff", attribute="all")
			ts = int(time.time())
			
			# Prepopulate the result attributes dict
			result = {'forecast': []}
			
			# Now round to the next full self.timestep.
			ts = ts + (self.timestep - (ts%self.timestep))
			
			# Prepare the result vectors
			energy_prices = []
			energy_co2 = []
			timestamp = ts
			
			# Prepare the optimal soluation storage variables
			best_costs 			= 100000000
			best_co2 			= 100000000
			best_clever 		= 100000000
			
			best_cost_co2 		= 100000000
			best_co2_costs 		= 100000000
			best_clever_costs 	= 100000000
			best_clever_co2 	= 100000000
			
			best_cost_time 		= ts
			best_co2_time 		= ts
			best_clever_time	= ts
		

		
			
	#### Data processing
			# Process the data
			for element in zp['attributes']['forecast']:
				timeElement = int(parser.parse(element['datetime']).timestamp())
				for i in range(0, int(3600/self.timestep)):
				
					# Check if time is in this slot:
					if timeElement <= timestamp < timeElement+3600:
						# Add all the elements
						try:
							energy_prices.append(element['electricity_price']/10000000)
						except:
							energy_prices.append(0.0)
							
						try:	
							energy_co2.append(element['carbon_footprint_in_grams']/10)
						except:
							energy_co2.append(0.0)
						
						# Increment time
						timestamp += self.timestep
						
			
			
	#### Find Optimal solutions		
			# Loop through all options
			for i in range(0, len(energy_co2)-len(self.profile)+1):
				co2 = 0
				costs = 0
				clever = 0
				timestamp = ts + i*self.timestep
				
				for j in range(0, len(self.profile)):
					#Calculate the costs
					costs += self.profile[j] * energy_prices[i+j] * (self.timestep/3600.0) / 1000
					co2 += self.profile[j] * energy_co2[i+j] * (self.timestep/3600.0) / 1000
					
					# Perform normalization, ensure that divisions by 0 do not occur
					try:
						# Price normalization
						p = (energy_prices[i+j]-min(energy_prices)) / (max(energy_prices)-min(energy_prices))
					except:
						p = 0
					
					try:
						# CO2 normalization
						c = (energy_co2[i+j]-min(energy_co2)) / (max(energy_co2)-min(energy_co2))
					except:
						c = 0
					
					# Give a score, note that I weigh CO2 emissions with a factor of 2
					clever += self.profile[j] * (c*2+p) * (self.timestep/3600.0) / 1000
					

				
				# Select the best options
				
				# First verify if this is a valid option given time constraints
				allowed_option = True
				if self.allowedStartHour is not None and self.allowedEndHour is not None:
					allowed_option = False
					start = datetime.datetime.fromtimestamp(timestamp).hour
					end = datetime.datetime.fromtimestamp(int(timestamp+len(self.profile)*self.timestep-1)).hour
					if self.allowedStartHour <= start <= self.allowedEndHour and self.allowedStartHour <= end <= self.allowedEndHour:
						allowed_option = True
						
				# If it is ivalid, see if it is better than the previous obtained value		
				if allowed_option:
					if costs < best_costs:
						best_costs = costs
						best_cost_time = timestamp
						best_cost_co2 = co2
					if co2 < best_co2:
						best_co2 = co2
						best_co2_time = timestamp
						best_co2_costs = costs
					if clever < best_clever:
						best_clever = clever
						best_clever_time = timestamp
						best_clever_costs = costs	
						best_clever_co2 = co2
					
					
	#### Set the sensors for graphing		
				# Add this result	
				dt = datetime.datetime.fromtimestamp(timestamp).astimezone(tz=timezone.utc)
				r = {	
						'datetime': dt.isoformat(timespec='microseconds')[:-6]+'Z', 
						'costs': costs, 
						'co2': co2 
					}	
				result['forecast'].append(r)


			# Now set the sensors:
			self.set_state("sensor."+self.devname+"_plan", state="on", attributes=result)
			
			
	#### Price Optimum			
			# Indicate the best moment for price:
			dt = datetime.datetime.fromtimestamp(best_cost_time)
			et = datetime.datetime.fromtimestamp(best_cost_time+len(self.profile)*self.timestep)
			
			s = ""
			
			if datetime.datetime.now().strftime('%d-%m-%Y') != dt.strftime('%d-%m-%Y'):
				s+= "Morgen "
			s += dt.strftime('%H:%M')
			s += " ( +"+str(int(round(best_cost_time - int(time.time()))/3600))+"h )"
			
			a = "??? {:.2f} en {:d} gCO2".format(best_costs, int(round(best_cost_co2)))
			a = a.replace(".", ",")
			a += " - Klaar rond "
			a += et.strftime('%H:%M')
			
			self.set_state("sensor."+self.devname+"_plan_price", state=s, attributes={'info': a})		
			self.set_state("sensor."+self.devname+"_plan_price_timestamp", state=best_cost_time)
			
			
			
			
	#### CO2 Optimum		
			# Indicate the best moment for CO2:
			dt = datetime.datetime.fromtimestamp(best_co2_time)
			et = datetime.datetime.fromtimestamp(best_co2_time+len(self.profile)*self.timestep)
			
			s = ""
			if datetime.datetime.now().strftime('%d-%m-%Y') != dt.strftime('%d-%m-%Y'):
				s+= "Morgen "
			s += dt.strftime('%H:%M')
			s += " ( +"+str(int(round(best_co2_time - int(time.time()))/3600))+"h )"
			
			a = "??? {:.2f} en {:d} gCO2".format(best_co2_costs, int(round(best_co2)))
			a = a.replace(".", ",")
			a += " - Klaar rond "
			a += et.strftime('%H:%M')
			
			self.set_state("sensor."+self.devname+"_plan_co2", state=s, attributes={'info': a})		
			self.set_state("sensor."+self.devname+"_plan_co2_timestamp", state=best_co2_time)		
			

			
	#### Verstandigste Keuze		
			# Indicate the best moment for Clever:
			dt = datetime.datetime.fromtimestamp(best_clever_time)
			et = datetime.datetime.fromtimestamp(best_clever_time+len(self.profile)*self.timestep)
			
			s = ""
			if datetime.datetime.now().strftime('%d-%m-%Y') != dt.strftime('%d-%m-%Y'):
				s+= "Morgen "
			s += dt.strftime('%H:%M')
			s += " ( +"+str(int(round(best_clever_time - int(time.time()))/3600))+"h )"
			
			a = "??? {:.2f} en {:d} gCO2".format(best_clever_costs, int(round(best_clever_co2)))
			a = a.replace(".", ",")
			a += " - Klaar rond "
			a += et.strftime('%H:%M')
			
			self.set_state("sensor."+self.devname+"_plan_clever", state=s, attributes={'info': a})		
			self.set_state("sensor."+self.devname+"_plan_clever_timestamp", state=best_clever_time)		
			
			
		except:
			self.log("Internal error in optimization class")
			
		# Set the next runtime of this function
		nt = int(self.timestep - (int(time.time())%self.timestep))
		if nt <= 5:
			nt = 900
		self.run_in(self.calculate, nt)