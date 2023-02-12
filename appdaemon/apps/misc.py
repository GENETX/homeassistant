import appdaemon.plugins.hass.hassapi as hass
import mqttapi as mqtt
import const

import math
import time
import datetime
from datetime import timedelta
from dateutil import parser


class MiscApp(hass.Hass):
	def initialize(self):
		# MQTT instance
		self.mqtt = self.get_plugin_api("MQTT")		
	
		# Notifications
		self.listen_state(self.send_message, "input_text.melding")
	
		# Monitor the CO2 emissions
		self.listen_state(self.changed_electricity, "sensor.elektriciteit" )
		self.listen_state(self.changed_power, "sensor.meter_power_consumption")
	
		# Turn on Fridge and Freezer to avoid long term being unpoweed (in case of some weird error or PEBCAK):
		runtime = datetime.time(0, 0, 0)
		self.run_hourly(self.power_fridges, runtime)
	
		# Zonneplan fixes
		self.listen_state(self.changed_zonneplan, "sensor.zonneplan_current_electricity_tariff")	
		self.update_zonneplan() 
		
	# Notifications
	def send_message(self, entity, attribute, old, new, kwargs):
		if new != "" and new != " " and new != "unknown":
			try:
				self.call_service("notify/mobile_app_smartphone", message=new, title="Bericht")
				self.set_value("input_text.melding", value="")
			except:
				self.set_value("input_text.melding", value="")
	
	
	# Monitor emissions in gCO2
	def changed_electricity(self, entity, attribute, old, new, kwargs):
		# How much has been consumed?
		delta = float(new) - float(old)
		
		# get the CO2 emissions
		current_co2 = float(self.get_state("sensor.zonneplan_current_co2"))
		co2 = float(self.get_state("sensor.co2_total_emissions"))
		
		# Calculate the new CO2 emission level
		co2 = co2 + delta * current_co2
		
		# and set the new sensor value
		self.mqtt.mqtt_publish("homeassistant/sensor/energy/co2_total", float(co2), retain=True)
		
	# Monitor momentary emissions in gCO2/h
	def changed_power(self, entity, attribute, old, new, kwargs):
		# Calculate the momentary CO2 emission level
		current_co2 = float(self.get_state("sensor.zonneplan_current_co2"))
		co2 = float(new) * current_co2
		
		# and set the new sensor value
		self.mqtt.mqtt_publish("homeassistant/sensor/energy/co2_current", float(co2), retain=True)	
		
		
	# Force Fridge and freezer on
	def power_fridges(self, kwargs):
		self.turn_on("switch.stopcontact_vriezer")
		self.turn_on("switch.stopcontact_koelkast")
		
	# Zonneplan fixes
	def changed_zonneplan(self, entity, attribute, old, new, kwargs):
		self.update_zonneplan()
			
			
	def update_zonneplan(self):
		# First go through the gas prices
		try:
			zp = self.get_state("sensor.zonneplan_current_electricity_tariff", attribute="all")
				
			# Get the gas price
			gp = self.get_state("sensor.current_hourly_gas_price_zonneplan")
			try:
				gp = float(gp)
			except:
				gp = 0.0
				
			ts = int(time.time())
			
			for element in zp['attributes']['forecast']:
				if 'gas_price' in element:
					if int(parser.parse(element['datetime']).timestamp()) <= ts:
						gp = element['gas_price']/10000000
					if int(parser.parse(element['datetime']).timestamp()) > ts+3600:
						break
			
			# self.set_state("sensor.current_hourly_gas_price_zonneplan", state=gp)
			self.mqtt.mqtt_publish("homeassistant/sensor/zonneplan/gas_price", float(gp), retain=True)
		except:
			pass
			
		# Then try to get the carbon emissions	
		try:
			zp = self.get_state("sensor.zonneplan_current_electricity_tariff", attribute="all")
				
			# Get the co2 level
			co2 = self.get_state("sensor.zonneplan_current_co2")
			try:
				co2 = float(co2)
			except:
				co2 = 0.0
				
			ts = int(time.time())
			
			for element in zp['attributes']['forecast']:
				if 'carbon_footprint_in_grams' in element:
					if int(parser.parse(element['datetime']).timestamp()) <= ts:
						co2 = element['carbon_footprint_in_grams']/10
					if int(parser.parse(element['datetime']).timestamp()) > ts+3600:
						break
						
			# self.set_state("sensor.zonneplan_current_co2", state=float(co2))
			self.mqtt.mqtt_publish("homeassistant/sensor/zonneplan/co2", float(co2), retain=True)
		except:
			pass
			
		# And then get to know also the averages for today:
		try:
			zp = self.get_state("sensor.zonneplan_current_electricity_tariff", attribute="all")
				
			# Get the gas price
			co2 = []
			prices = []
			
			for element in zp['attributes']['forecast']:
				# check if we are an element of today
				d = parser.parse(element['datetime']).strftime("%d-%m-%Y")
				t = datetime.datetime.now().strftime("%d-%m-%Y")
				
				if d == t:				
					if 'carbon_footprint_in_grams' in element:
						co2.append(float(element['carbon_footprint_in_grams']/10))
					if 'electricity_price' in element:
						prices.append(float(element['electricity_price']/10000000))
			
			try:
				priceavg = sum(prices)/len(prices)
				self.set_state("sensor.zonneplan_average_daily_price", state=priceavg)
				
				priceavgs = "{:.2f}".format(priceavg).replace(".",",")
				self.set_state("sensor.zonneplan_average_daily_price_str", state=priceavgs)

			except:
				pass
				
			try:
				co2avg = sum(co2)/len(co2)
				self.set_state("sensor.zonneplan_average_daily_co2", state=co2avg)
				
				co2avgs = "{:d}".format(int(round(co2avg))).replace(".",",")
				self.set_state("sensor.zonneplan_average_daily_co2_str", state=co2avgs)
			except:
				pass
			
			
		except:
			pass	