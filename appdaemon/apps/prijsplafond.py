import appdaemon.plugins.hass.hassapi as hass

import time
import math
import datetime

from pytz import timezone


class PrijsplafondApp(hass.Hass):
	def initialize(self):
		self.mqtt = self.get_plugin_api("MQTT")	
	
		# At which date should we monitor the ceiling? Nothing will be monitored before this date
		timeZone = timezone('Europe/Amsterdam')
		self.startTime = int(timeZone.localize(datetime.datetime(2023, 1, 1)).timestamp())
		
		# set the entities:
		# Electricity
		self.electricity_meter 		= "sensor.elektriciteit" 								# Energy meter, It is recommended to make a helper sensor that adds T1 and T2 values
		self.electricity_price 		= "sensor.zonneplan_current_electricity_tariff"			# Dyanmic tariffs
		self.electricity_utility 	= "sensor.electricity_year"								# Utility with the yearly energy consumption
		self.electricity_costs 		= "sensor.elektriciteitskosten"							# Sensor monitoring the tarriff
		self.electricity_ceiling 	= "sensor.incrementing_electricity_ceiling"				# Sensor that will show ceiling up to and including today
		
		self.electricity_discount	= "homeassistant/sensor/plafond/electricity_discount"	# MQTT Sensor that will show the profit from ceiling (negative means ceiling is not used, your prices are lower)			
		self.electricity_costs_mqtt = "homeassistant/sensor/plafond/electricity_costs"		# MQTT topic to store electricity data
		
		# Monitor Electricity meter changes
		self.listen_state(self.changed_electricity, self.electricity_meter)
		
		self.enable_gas 	= True
		self.gas_meter 		= "sensor.meter_gas_consumption" 								# Energy meter, It is recommended to make a helper sensor that adds T1 and T2 values
		self.gas_price 		= "sensor.current_hourly_gas_price_zonneplan"					# Dyanmic tariffs
		self.gas_costs 		= "sensor.gaskosten"											# Sensor monitoring the tarriff
		self.gas_ceiling 	= "sensor.incrementing_gas_ceiling"								# Sensor that will show ceiling up to and including today
		self.gas_utility 	= "sensor.gas_year"												# Utility with the yearly energy consumption
		
		self.gas_discount	= "homeassistant/sensor/plafond/gas_discount"			# MQTT Sensor that will show the profit from ceiling (negative means ceiling is not used, your prices are lower)
		self.gas_costs_mqtt = "homeassistant/sensor/plafond/gas_costs"						# MQTT topic to store gas data
		
		# Monitor Gas meter changes
		if self.enable_gas:
			self.listen_state(self.changed_gas, self.gas_meter)
		
		# Static stuff		
		# Ceiling values:
		self.ceilingStart = int(timeZone.localize(datetime.datetime(2023, 1, 1)).timestamp())
		self.ceiling_electricity = [11.321629,11.151776,10.814767,10.933145,10.867808,10.874362,11.547017,11.609251,10.888195,10.611738,10.735336,10.606315,10.791567,11.522976,11.617777,10.779735,10.637142,10.592714,10.389801,10.798875,11.48632,11.563054,10.815985,10.70622,10.710802,10.4052,10.616436,11.463526,11.448301,10.702218,10.489358,10.519083,10.186772,10.316489,11.261048,11.521497,10.646596,10.330003,10.29848,10.120275,10.289374,11.059556,11.251913,10.304251,9.688175,9.761052,9.708185,9.723468,10.125843,10.088172,9.582209,8.822438,8.864227,9.131549,9.083699,9.615443,9.930615,9.216896,8.564686,8.708265,9.024655,9.018188,9.7324,10.161049,9.085961,8.573009,8.853497,8.859065,8.870694,9.608599,9.751627,8.779924,8.480499,8.699217,8.663344,8.598471,9.250565,9.211821,8.555725,8.33257,8.130034,8.214511,8.031173,8.647481,8.287736,7.73401,7.08122,7.418751,7.404657,7.592983,8.079777,8.137023,7.342858,7.053496,7.270503,7.100186,7.303998,8.019138,7.758457,7.375831,6.963016,6.94666,6.647699,6.722635,7.416199,7.035284,6.676003,6.303382,6.223864,6.255561,6.188339,6.830834,6.592309,6.253589,5.979423,5.981221,6.702422,6.401808,6.810389,6.827731,6.166821,6.178508,6.143911,6.187933,6.03635,6.55603,6.468827,5.9044,5.740086,5.777525,5.736345,5.710448,6.294566,6.310052,5.791474,5.659698,5.555124,6.252197,5.74345,6.010424,6.210669,5.667035,5.615705,5.445388,5.442662,5.23247,5.494804,5.647953,5.558662,5.280407,5.31802,5.484219,5.4114,5.606483,5.504026,5.190855,5.09965,5.29888,5.243867,5.315439,5.692874,5.64195,5.178588,5.132014,5.33687,5.312017,5.316715,5.416562,5.570407,5.263152,5.109655,5.205181,5.316106,5.246912,5.461193,5.54683,5.214664,5.081525,5.078016,5.044724,4.979039,5.47317,5.538594,5.164639,5.032834,5.093415,4.982142,5.011577,5.448897,5.570842,5.207762,5.109191,5.084367,5.072796,5.032689,5.281741,5.399974,5.038344,5.097707,5.103014,5.219623,5.110496,5.461193,5.346353,5.002442,5.04281,5.069432,5.106929,5.106378,5.467834,5.2345,5.060123,4.921909,4.963466,4.914862,5.144426,5.631655,5.556835,5.541059,5.222088,5.34441,5.44475,5.549585,6.045949,6.098149,5.945986,5.629161,5.649983,5.856521,5.718307,5.928731,6.148522,5.805626,5.728486,5.762648,5.773088,5.849561,6.018544,6.443539,5.891756,5.898165,5.994822,5.90005,6.012773,6.251588,6.672581,6.026577,5.964198,6.189528,6.090348,6.062131,6.542835,6.75091,6.260375,6.254894,6.372083,6.197474,6.280965,6.633402,6.928622,6.566325,6.467754,6.480543,6.609709,6.773907,6.947704,7.66876,7.094647,6.921198,7.165233,7.453464,7.584921,8.006233,8.710585,7.898498,7.675604,7.971578,7.941447,8.099091,8.63011,8.975906,8.259316,7.985527,8.30473,8.107472,8.213815,8.712876,8.94331,8.423601,8.183307,8.450194,8.339704,8.52455,9.096604,9.086367,8.854802,8.468058,8.560278,8.584232,8.684978,9.453217,10.471784,9.402728,9.401597,9.646096,9.569797,9.587922,10.243293,10.320897,9.67933,9.629682,9.88349,9.789588,9.861653,10.469841,10.541239,10.243699,9.943868,9.968721,10.023995,10.036958,10.65808,10.694127,10.378491,10.118564,10.049747,10.191905,10.309007,11.059527,11.120137,10.704857,10.257068,10.483674,10.752272,11.036646,11.445082,11.656811,11.281957,10.826454,11.113902,11.253595,11.481912,11.785281,11.994342,11.304954,11.10178,11.210878,11.079653,11.247969,11.8697,12.150942,11.457755,11.439601,11.488553,11.511898,11.269458,11.667715,12.176143,12.185655,12.185974,11.798592,11.880111,11.375627,11.427334,10.623773]
		self.ceiling_gas = [7.17361783,7.29365989,7.50814813,7.46678924,7.40948305,7.12583471,7.06297627,6.90513601,6.93128915,6.9051776,6.94681715,6.92379916,6.69227866,6.74976235,6.72370085,6.90239464,6.96068977,7.08851374,7.00058675,6.98597455,7.12991528,7.19546986,7.43678302,7.35814823,7.49728597,7.56062596,7.31163871,7.23298964,7.10172329,7.19504536,7.37483185,7.39434818,7.16656154,6.79139149,6.76650941,6.53328173,6.69376133,6.97538503,7.14112236,7.22550605,7.18161464,6.99223027,6.8513672,7.05662366,7.02768284,6.75782404,6.56174147,6.48236336,6.51979424,6.62183914,6.62736338,6.68609065,6.69458268,6.53537825,6.25175401,6.08763773,5.98658881,6.18420619,6.21955242,6.33414223,6.3920358,6.38074567,6.1333713,5.81858212,5.87373527,5.63116308,5.49814379,5.41436083,5.35144112,5.4200091,5.14192746,5.34588974,5.30233717,5.05722134,4.85703858,4.86955706,4.9993197,4.96335972,5.06943626,5.06784216,4.96086198,4.84258328,4.53696997,4.37508967,4.55934398,4.49977616,4.55496799,4.19289924,3.69225967,3.47473025,3.37406227,3.13616214,3.42950266,3.8634897,4.17129634,4.0048733,3.5640263,3.47990668,3.10103989,3.12204805,3.29015648,3.43146997,3.68846788,3.3293311,3.06104812,2.81264011,2.9624469,2.93833466,2.89785233,2.51750236,2.172746,2.00642815,1.86792547,1.83656459,1.86647537,1.95518306,1.91831654,2.09209433,2.0167141,1.81858578,1.60206209,1.61957664,1.60384111,1.69101241,1.6423665,1.57653253,1.32181553,1.35462656,1.15338499,1.12296589,1.18614508,1.26037852,1.12140696,1.21073387,1.2450091,1.1967596,1.18517618,1.02318482,0.96128749,0.8158073,0.88714532,0.90468481,0.8695861,0.85710858,0.83091895,0.84871555,0.79069552,0.81712562,0.77404646,0.71923118,0.69844573,0.67137725,0.65331774,0.65264522,0.69033146,0.68549868,0.68327159,0.67334834,0.6671072,0.68183083,0.62803514,0.64351399,0.62778155,0.62322211,0.60647658,0.59900252,0.62671348,0.56840167,0.63051601,0.60524975,0.6038147,0.5848005,0.60646592,0.63832346,0.61693966,0.62504214,0.57042036,0.56796326,0.56537989,0.57959834,0.5622769,0.55953127,0.58038446,0.5661326,0.55614494,0.54503117,0.54999786,0.54674671,0.55009128,0.59383794,0.55603008,0.56114256,0.57363995,0.56241896,0.57818165,0.54429919,0.56796701,0.54732128,0.5481287,0.54021942,0.54267691,0.53977651,0.5384846,0.56499448,0.547195,0.54254719,0.54281489,0.54540694,0.5328153,0.53998415,0.56067566,0.54111043,0.53567102,0.53514,0.53514,0.5253,0.53374975,0.54899698,0.54093034,0.5422708,0.54683204,0.54717354,0.54480494,0.54031513,0.56252779,0.55014626,0.54058578,0.53738905,0.55425887,0.54794138,0.54873619,0.56150334,0.54844692,0.55896661,0.56550066,0.5682563,0.57024144,0.56373832,0.60008246,0.58213879,0.62706535,0.62469466,0.61423171,0.58928904,0.55941635,0.63402464,0.65885335,0.65388412,0.65097845,0.65822159,0.65170182,0.61614016,0.68267237,0.67214809,0.67865315,0.74551014,0.84495514,0.8573852,0.80558136,0.89469236,0.90856757,0.9047651,0.89446666,0.83622768,0.83826014,0.81265447,0.94133995,0.95566073,0.9663058,0.96224534,1.02139183,1.11909116,1.24319872,1.57043478,1.76777894,1.81455061,1.90907052,1.99894022,2.11086835,2.07794884,1.90463772,2.04317806,2.10946619,2.21119639,2.32430322,2.31905846,2.36815397,2.29131431,2.61299417,2.75403059,2.94665803,2.89336418,2.95666906,3.07442792,2.90511974,3.05840303,3.1672682,3.18810383,3.11528614,3.2798946,3.41381906,3.48598024,3.56958755,3.62275514,3.76247078,3.79335062,3.67880611,3.63490626,3.78758707,3.97212916,4.17706524,4.24792609,4.39175154,4.41613518,4.59637202,4.63698242,4.7195774,4.78600768,4.81466141,4.96622921,5.05569503,5.23945098,5.34327938,5.68601556,5.74850358,5.61756916,5.43609485,5.55160963,5.61753797,5.5794874,5.70469898,5.77639088,5.93504257,6.04070029,6.09285304,6.15886988,6.18658619,6.38676769,6.39470252,6.37163657,6.46708343,6.57854221,6.7170259,6.71854288,6.64992443,6.51386155,6.5689296,6.72261404,6.80619704,6.7838974,6.58253207,6.49862754,6.51519817,6.80140727,7.02736985,6.77435087,6.690633,6.4199535,6.63312469,6.89685004,7.14043776,7.24106764,7.19102346,7.14543568,6.88440509]
		self.ceiling_price_electricity = 0.4
		self.ceiling_price_gas = 1.45
		self.ceiling_electricity_max = 2900
		self.ceiling_gas_max = 1200
		
		# Intialize hourly ceiling calculation
		self.run_hourly(self.calculate_ceiling_electricity, datetime.time(0, 0, 0))
		self.run_hourly(self.calculate_ceiling_gas, datetime.time(0, 0, 0))
		
		self.calculate_ceiling_electricity(None)	# Kickoff once 
		self.calculate_ceiling_gas(None)			# Kickoff once 
		
		
	# Calcualte costs when electricity changes
	def changed_electricity(self, entity, attribute, old, new, kwargs):
		try:
			# Update the costs
			delta = float(new) - float(old)
			price = float(self.get_state(self.electricity_price))
			oldcosts = float(self.get_state(self.electricity_costs))
			
			# Increment the costs:
			costs = oldcosts + price * delta
	
			# Stop cost accounting before the ceiling starts
			if int(time.time())<=self.startTime:
				costs = 0.0
			
			self.mqtt.mqtt_publish(self.electricity_costs_mqtt, float(costs), retain=True)
			
			# Now calculate the ceiling
			ceiling = float(self.calculate_ceiling_electricity(None))		
			energy = float(self.get_state(self.electricity_utility))
			try:
				average = costs / energy
			except:
				average = 0
			
			# Now determine the ceiling discount
			discount = 0
			if average <= self.ceiling_price_electricity:
				# Negative value, you pay less than the ceiling
				discount = float(self.ceiling_price_electricity - average) * energy
			elif ceiling >= energy:
				# You consume less than the ceiling, no profit compared to ceiling
				discount = 0
			else:
				# You use more than the ceiling at a higher price, you pay more than the ceiling
				discount = float(self.ceiling_price_electricity - average) * (energy - ceiling)		

			if int(time.time()) <= self.startTime:
				discount = 0.0
			# self.set_state(self.electricity_discount, state=float("{:.2f}".format(discount)))	
			self.mqtt.mqtt_publish(self.electricity_discount, float("{:.2f}".format(discount)), retain=True)
				
		except:
			self.log("Error with electricity cost calculation")
			
		
	# Calculate costs when gas changes	
	def changed_gas(self, entity, attribute, old, new, kwargs):
		try:
			# Update the costs
			delta = float(new) - float(old)
			price = float(self.get_state(self.gas_price))
			oldcosts = float(self.get_state(self.gas_costs))
			
			# Increment the costs:
			costs = oldcosts + price * delta
	
			# Stop cost accounting before the ceiling starts
			if int(time.time())<=self.startTime:
				costs = 0.0

			self.mqtt.mqtt_publish(self.gas_costs_mqtt, float(costs), retain=True)
			
			# Now calculate the ceiling
			ceiling = float(self.calculate_ceiling_gas(None))
			energy = float(self.get_state(self.gas_utility))
			try:
				average = costs / energy
			except:
				average = 0
			
			# Now determine the ceiling discount
			discount = 0
			if average <= self.ceiling_price_gas:
				# Negative value, you pay less than the ceiling
				discount = float(self.ceiling_price_gas - average) * energy
			elif ceiling >= energy:
				# You consume less than the ceiling, no profit compared to ceiling
				discount = 0
			else:
				# You use more than the ceilign at a higher price, you pay more than the ceiling
				discount = float(self.ceiling_price_gas - average) * (energy - ceiling)		
				
			if int(time.time()) <= self.startTime:
				discount = 0.0
			# self.set_state(self.gas_discount, state=float("{:.2f}".format(discount)))		
			self.mqtt.mqtt_publish(self.gas_discount, float("{:.2f}".format(discount)), retain=True)
				
		except:
			self.log("Error with gas cost calculation")
		
	# Calculate the current ceiling
	def calculate_ceiling_electricity(self, kwargs):	
		try:
			# Calcualte the electricity ceiling
			start_day = max(0,int(math.floor( (self.startTime - self.ceilingStart) / (3600*24))))
			num_days = int(math.floor( (int(time.time()) - self.ceilingStart) / (3600*24)))
			num_days = max(1, min(len(self.ceiling_electricity), num_days+1)) - start_day
			
			ceiling = 0
			for i in range(start_day, start_day+num_days):
				ceiling += self.ceiling_electricity[i]
		
			self.set_state(self.electricity_ceiling, state=float(min(ceiling, self.ceiling_electricity_max)))
			return ceiling
			
		except:
			self.log("Error with ceiling calculation")
			
			
	def calculate_ceiling_gas(self, kwargs):	
		try:
			# Calcualte the electricity ceiling
			start_day = max(0,int(math.floor( (self.startTime - self.ceilingStart) / (3600*24))))
			num_days = int(math.floor( (int(time.time()) - self.ceilingStart) / (3600*24)))
			num_days = max(1, min(len(self.ceiling_electricity), num_days+1)) - start_day
			
			ceiling = 0
			
			# Calculate the gas ceiling
			if self.enable_gas:
				ceiling = 0
				for i in range(0, num_days):
					ceiling += self.ceiling_gas[i]
			
				self.set_state(self.gas_ceiling , state=float(min(ceiling, self.ceiling_gas_max)))
			return ceiling
			
		except:
			self.log("Error with ceiling calculation")
		