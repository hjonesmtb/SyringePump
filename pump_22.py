"""
	Github Links: 
		https://github.com/tomwphillips/pumpy/blob/master/pumpy.py
		https://github.com/bgamari/harvard-syringe-pump/blob/master/harvardpump/pump.py

	Manuals:
		https://www.harvardapparatus.com/media/harvard/pdf/552222_Pump_22_Manual.pdf
		https://www.harvardapparatus.com/media/harvard/pdf/702208_Pump_11_Plus_Manual.pdf
	"""
import serial

import time

class Pump():

	""" When a command is sent to the pump, it returns a 3 byte response
	    CR LF prompt (CR = \r, LF = \n, prompt = one of the symbols below)
	    knowing the status of the pump helps detect errors
	"""
	prompts = {
	    ':': 'stopped',
	    '>': 'running',
	    '<': 'reverse',
	    '*': 'stalled' }

	def __init__(self, port, baudrate):
		self.port = serial.Serial(port = 'COM{}'.format(port), stopbits = 2, baudrate = baudrate, parity = 'N', timeout = 2)
		self.port.flushOutput()
		self.port.flushInput()

	""" 
		Basic write operation to the pump.
		cmd: string with the desired pump command. Must be
			 a valid command from page 23 of the data sheet.

		prompt: The return prompt from the syringe pump
	"""
	def write(self, cmd):
		print("write: {}".format(cmd))
		command = "{}\r".format(cmd)
		self.port.write(command.encode())

		response = self.port.read(3).decode("utf-8") # get return, remove CR and LF to isolate prompt

		return response.strip()	

	def infuse(self):
		response = self.write("RUN")
		try:
			state = Pump.prompts[response]
			print(response)
		except KeyError:
			raise PumpError("Pump response invalid")

	def stop(self):
		response = self.write("STP")
		try:
			state = Pump.prompts[response]
			print(response)
		except KeyError:
			raise PumpError("Pump response invalid")

	def set_rate(self, rate, unit):

		units = { 'uL/min' : 'ULM', 
				  'mL/min' : 'MLM', 
				  'uL/hr'  : 'ULH', 
				  'mL/hr'  : 'MLH'}
		try:
			response = self.write(units[unit] + str(rate))
			print(response)
		except KeyError:
			raise PumpError("Invalid unit")		

		try:
			state = Pump.prompts[response]
			print(response)
		except KeyError:
			raise PumpError("Pump response invalid")

	def set_diameter(self, diameter):
		response = self.write("MMD{}".format(diameter))
		try:
			state = Pump.prompts[response]
			print(response)
		except KeyError:
			raise PumpError("Pump response invalid")

	def set_volume(self, volume):
		response = self.write("MLT{}".format(volume))
		try:
			state = Pump.prompts[response]
			print(response)
		except KeyError:
			raise PumpError("Pump response invalid")


	def check_volume(self):
		value, prompt = self.query("VOL")

		print('value: ',value)
		print('prompt: ', prompt)
		try:
			state = Pump.prompts[prompt]
			print(state)
		except KeyError:
			raise PumpError("Pump response invalid")

		return value

class PumpError(Exception):
	pass

if __name__ == '__main__':
	pump = Pump(11, 1200)

	pump.set_diameter(10)
	pump.set_rate(1,'mL/min')
	pump.set_volume(1)

	pump.infuse()

	#time.sleep(5)
	#pump.stop()


