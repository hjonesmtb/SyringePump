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
	class PumpError(Exception):
		pass

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
		self.port.flushInput()
		self.port.flushOutput()

	def close(self):
		self.write("KEY")
		self.port.close()

	def print_state(self, response):
		try:
			state = Pump.prompts[response]
			print(state)
		except KeyError:
			raise PumpError("Pump response invalid")

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

		response = self.port.read(3).decode("utf-8") # Isolate prompt from CR LF

		return response.strip()	

	""" 
		Basic query operation to the pump.
		cmd: string with the desired pump command. Must be
			 a valid command from page 23 of the data sheet.

		value: The return value from the syringe pum
		prompt: The return prompt from the syringe pump
	"""
	def query(self, cmd):
		print("query: {}".format(cmd))
		command = "{}\r".format(cmd)
		self.port.write(command.encode())

		value = self.port.read(10).decode("utf-8") # Isolate value from CR LF
		prompt = self.port.read(3).decode("utf-8") # Isolate prompt from CR LF

		return value.strip(), prompt.strip()			

	# Start infusion
	def infuse(self):
		response = self.write("RUN")
		self.print_state(response)

	# Pause infusion
	def stop(self):
		response = self.write("STP")
		self.print_state(response)

	# Set the flow rate
	def set_rate(self, rate, unit):

		units = { 'uL/min' : 'ULM', 
				  'mL/min' : 'MLM', 
				  'uL/hr'  : 'ULH', 
				  'mL/hr'  : 'MLH'}

		try:
			unit_code = units[unit]
		except KeyError:
			raise PumpError("Invalid unit")		

		response = self.write(units[unit] + str(rate))

		self.print_state(response)

	# Set the syringe diameter
	def set_diameter(self, diameter):
		response = self.write("MMD{}".format(diameter))
		self.print_state(response)

	# Set the target infusion volume
	def set_volume(self, volume):
		response = self.write("MLT{}".format(volume))
		self.print_state(response)

	# Reset the volume accumulator
	def reset_acc(self):
		response = self.write("CLV")
		self.print_state(response)

	# Query the pump for the current accumulated volume	
	def check_volume(self):
		value, prompt = self.query("VOL")
		self.print_state(prompt)

		return float(value)