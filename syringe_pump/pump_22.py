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
		def __init__(self, *args: object) -> None:
			super().__init__(*args)
		def __str__(self) -> str:
			return super().__str__()
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

	def __init__(self, ser, baudrate):
		#self.port = serial.Serial(port = 'COM{}', stopbits = 2, baudrate = baudrate, parity = 'N', timeout = 2)
		try:
			self.ser = serial.Serial(port = ser, stopbits = 2, baudrate = baudrate, parity = 'N', timeout = 2)
			if self.ser.isOpen():
				print("pump port opened successfully")
		except:
			print("COM port is not available")
		self.ser.flushInput()
		self.ser.flushOutput()
	
	@classmethod
	def from_parameters(cls, system_data):
		return cls(system_data.pump_com, system_data.pump_baud)

	def close(self):
		self.write("KEY")
		self.ser.close()

	def print_state(self, response):
		try:
			state = Pump.prompts[response]
			print(state)
		except KeyError:
			raise PumpError

	""" 
		Basic write operation to the pump.
		cmd: string with the desired pump command. Must be
			 a valid command from page 23 of the data sheet.

		prompt: The return prompt from the syringe pump
	"""
	def write(self, cmd):
		print("write: {}".format(cmd))
		command = "{}\r".format(cmd)
		self.ser.write(command.encode())

		response = self.ser.read(3).decode("utf-8") # Isolate prompt from CR LF

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
		self.ser.write(command.encode())

		value = self.ser.read(10).decode("utf-8") # Isolate value from CR LF
		prompt = self.ser.read(3).decode("utf-8") # Isolate prompt from CR LF

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