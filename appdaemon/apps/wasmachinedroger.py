import appdaemon.plugins.hass.hassapi as hass
import const

import math
import time
import datetime
from dateutil import parser
from datetime import timedelta
from datetime import timezone

class WasmachineDrogerApp(hass.Hass):
	def initialize(self):	
		# MQTT
		self.mqtt = self.get_plugin_api("MQTT")	
		
		# Config
		self.devname = "wasmachine_droger"

		# Add time restrictions to devices
		self.allowedStartHour = 7
		self.allowedEndHour = 22 	# Including, so 22 means 22:59 is also allowed!

		self.timestep = 900 
		
		# Profiles in Watts
		# Wasmachine+Droger
		self.profile = [48, 1060, 1165, 89, 82, 80, 68, 63, 66, 64, 63, 70, 63, 204, 0, 252, 557, 646, 753, 397, 39, 37]

	
		# Optimal scheduling
		self.run_in(self.calculate, 10)
		
	

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
			for element in zp['attributes']['forcast']:
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
			
			a = "€ {:.2f} en {:d} gCO2".format(best_costs, int(round(best_cost_co2)))
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
			
			a = "€ {:.2f} en {:d} gCO2".format(best_co2_costs, int(round(best_co2)))
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
			
			a = "€ {:.2f} en {:d} gCO2".format(best_clever_costs, int(round(best_clever_co2)))
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