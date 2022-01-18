#Questions: WHat is auxillary?

import serial
import numpy as np
import binascii
import time
import math
import numpy as np
import pandas as pd

#User inputs
technique = 2 #square wave voltammetry
e_cond = 0 #conditioning potential, V, user input
tCond = 0 #conditioning time, s, user input
e_dep = 0.8 #deposition potential, V, user input
tDep = 0 #depostion time, s, user input 60
tEquil = 2 #equilibration time, s, user input 5
cr_min = 1 # minimum current range, 0: 1nA  1: 10nA, 2: 100nA, 3: 1 uA, 4: 10uA, 5: 10uA, 6: 1mA, 7: 10mA, user input
cr_max = 4 # max current range, user input
cr = 3 #Starting current range, user input
Estby = 0.8 #V, user input
t_stby = 1 #s, user input
measure_i_forward_reverse = True #user input
cell_on_post_measure = False #user input

#emstat 3 constants
dac_factor = 1.599 #DAC factor specific to emstat3
e_factor = 1.5 #Efactor specific to emstat3
v_range = 3 #specific to emstat3

class Emstat:
    def __init__(self, pstat_com, e_cond, t_cond, e_dep, t_dep, t_equil, e_begin, e_end, e_step, amplitude, frequency):
        try:
            self.ser = serial.Serial('COM{}'.format(pstat_com), baudrate=230400, timeout = 1)
            if self.ser.isOpen():
                print("port opened successfully")
        except:
            try:
                self.ser = serial.Serial('COM{}'.format(pstat_com), baudrate=230400, timeout = 1)
                if self.ser.isOpen():
                    print("port opened successfully")
            except:
                print("COM port is not available")
        self.swv_params = format_parameters(t_equil, e_begin, e_end, e_step, amplitude, frequency)
        self.deposition_potential = e_dep

    def sendData(self, string):
        self.ser.write(string.encode('ascii'))

    def readData(self, bytes):
        data = self.ser.read(bytes)
        return data

	def close(self):
		self.ser.close()

    '''Runs deposition, returns T_packages'''
    def depostion(self, dep_time):
        self.ser.sendData("j") #enables idle packages
        T_packages = []
        command = potential_to_cmd(self.deposition_potential, False)
        command = 'D' + command
        self.ser.sendData(command)
        starttime = time.time()
        while char != "T":
            if time.time() - starttime < dep_time:
                break
            self.ser.readData(1).decode()

        while time.time() - starttime < dep_time::
            package = ''
            char = self.ser.readData(1).decode()
            while char != "T":
                if char != '':
                    package = package + char
                char = self.ser.readData(1).decode()
            T_packages.append(package)
        potential_T, current_T, noise_T, overload_T, underload_T = process_T(T_packages)
        return [potential_T, current_T, noise_T, overload_T, underload_T]

    '''Runs swv sweep, returns array with potential, current, overload and underload arrays '''
    def sweepSWV():
        T_data, U_data = run_swv()
        potential_T, current_T, noise_T, overload_T, underload_T = process_T(T_data)
        potential_U, current_U, overload_U, underload_U = process_U(U_data)
        data_array = [potential_U, current_U, overload_U, underload_U]
        return data_array

    #Converts bytes to voltage, current, stage, I status and range, Aux input, for Tpackages
    def process_T(T_data):
        potential_array = []
        current_array = []
        noise_array = []
        overload_array = []
        underload_array = []
        for data in T_data:
            current_overload = False
            current_underload = False
            print(T_data[2:4])
            potential = ((int(data[2:4], 16) * 256 + int(data[0:2], 16)) / 65536 * 4.096 - 2.048) * e_factor
            current_range = 10 ^ (int(data[10:12] and '0F', 16))
            if (data[10:12] and '20' == '20'):
                current_overload = True
                print("current overload")
            if (data[10:12] and '40' == '40'):
                current_underload = True
                print("current underload")
            current = ((int(data[6:8], 16) * 256 + int(data[4:6], 16)) / 65536 * 4.096 - 2.048) * current_range
            noise = (int(data[16:18], 16) * 256 + int(data[18:20], 16)) / 65536 * 4.096
            potential_array.append(potential)
            current_array.append(current)
            noise_array.append(noise)
            overload_array.append(current_overload)
            underload_array.append(current_underload)
        return potential_array, current_array, noise_array, overload_array, underload_array

    def process_U(U_data):
        potential_array = []
        current_array = []
        overload_array = []
        underload_array = []
        for data in U_data:
            current_overload = False
            current_underload = False
            potential = ((int(data[2:4], 16) * 256 + int(data[0:2], 16)) / 65536 * 4.096 - 2.048) * dac_factor
            current_range = 10 ** (int(data[10:12] and '0F', 16))
            current = ((int(data[6:8], 16) * 256 + int(data[4:6], 16)) / 65536 * 4.096 - 2.048) * current_range
            if data[10:12] == '01':
                current = current + 4.096 * current
            if data[10:12] == 'FF':
                current = current - 4.096 * current
            if ((data[10:12] and '20') == '20'):
                current_overload = True
                print("current overload")
            if ((data[10:12] and '40') == '40'):
                current_underload = True
                print("current underload")
            potential_array.append(potential)
            current_array.append(current)
            overload_array.append(current_overload)
            underload_array.append(current_underload)
        return potential_array, current_array, overload_array, underload_array

    #Runs measurement with defined L command parameter. L command is a string formatted as in p.26 of comm protocol
    def run_swv(self):
        T_data = [] #string array to store T packages from measurement (during steady state)
        U_data = [] #string array to store U packages from measurement (during SWV)
        self.ser.sendData("J") # disables idle packages
        self.ser.flush() #clears
        self.ser.read()
        self.ser.sendData("L") #
        time.sleep(0.1)
        ser.sendData(self.swv_params)
        try:
            skip_T = False
            n = 0
            while True:
                char = self.ser.readData(1).decode()
                if n > 20:
                    raise ValueError('Reading wrong, no T found in first 20 characters')
                if char == "T":
                    break
                if char == "U":
                    skip_T = True #If deposition time is 0, skip T package reading
                    break
                if char != "":
                    n += 1

            if not skip_T:
                while char != 'U': #Write T poackages as long as no U is read
                    package = ''
                    char = self.ser.readData(1).decode()
                    while char != "T" and char != "M" and char != "U": #M is the present at the end of the last T-package
                        if char != "":
                            package = package + char
                        char = self.ser.readData(1).decode()
                    if char == "M": #read another character if M received, should be a U
                        char = self.ser.readData(1).decode()
                    print(package)
                    if len(package) != 20:
                        raise ValueError('T package not 20 characters')
                    T_data.append(package)

            while char != '*': #end condition
                package = ''
                char = self.ser.readData(1).decode()
                while char != "U" and char != "*":
                    if char != "":
                        package = package + char
                    char = self.ser.readData(1).decode()
                print(package)
                if len(package) != 16:
                    raise ValueError('U package not 16 characters')
                U_data.append(package)
            print("measurement complete")
            return T_data, U_data
        except Exception as e:
            print("Process terminated")
            print(e)
            return T_data, U_data
            ser.close()

    #Calculates all parameters for square wave voltammetry. See p. 29 of comm protocol
    def format_parameters(t_equil, e_begin, e_end, e_step, amplitude, freq):
        #options
        options = 0
        if measure_i_forward_reverse: options += 1024
        if cell_on_post_measure: options += 4
        #n_points
        nPoints = int((e_end - e_begin) / e_step + 1)
        #t_meas, d1, d16, nadmean, tPulse
        t_meas = 1/(6*freq) #p. 23 com protocol
        nadmean, d1, d16 = d1_d16_calc(t_meas)
        t_meas_actual = 2**nadmean * (0.222 + d1 * 0.0076 + d16 * 0.0005) / 1000
        tPulse = int((1 / (2 * freq) - t_meas_actual) / 0.0000152)
        #potentials
        Econd = potential_to_cmd(e_cond)
        Edep = potential_to_cmd(0)
        Ebegin = potential_to_cmd(e_begin)
        Estep = int(e_step * 10000) #not sure why
        Epulse = int(amplitude * 10000) #not sure why
        #tInt
        tInt = tint_calc(freq)
        #format ascii command
        L_command = "technique={}\nEcond={}\ntCond={}\nEdep={}\ntDep={}\ntEquil={}\ncr_min={}\ncr_max={}\ncr={}\nEbegin={}\nEstep={}\nEpulse={}\nnPoints={}\ntInt={}\ntPulse={}\nd1={}\nd16={}\noptions={}\nnadmean={}\n*".format(technique, Econd, tCond, Edep, tDep, tEquil, cr_min, cr_max, cr, Ebegin, Estep, Epulse, nPoints, tInt, tPulse, d1, d16, options, nadmean)
        print(L_command)
        return L_command

    #Calculates d1, d16 and nadmean from tmeas. See p. 24 of comm protocol
    def d1_d16_calc(tmeas):
        ADT16ad = 0.0002604
        d1 = 5
        d16 = 1

        if tmeas < 1/60:
            ADT16ad = 0.000222
            d1 = 0
            d16 = 0
        ncycles = int(tmeas / ADT16ad)
        if ncycles < 1:
            ncycles = 1
        nadmean = int(np.log(ncycles) / np.log(2))
        if nadmean < 0: nadmean = 0
        if nadmean > 11: nadmean = 11
        return int(nadmean), int(d1), int(d16)

    #Calculates tint from the frequency. See p. 26 of comm protocol
    def tint_calc(freq):
        tint = 1 / freq
        if tint < 0.98:
            t2value = tint * 16.7772e6
            t2m = math.ceil(t2value / 65536 + 1)
            if t2m > 255:
                t2m = 255
            if t2m < 1:
                t2m = 1
            t2hl = math.ceil(65536 - t2value / t2m)
            value = 4 << 24
            value += t2m * 65536
            value += t2hl
            return value

    #Calculates a Uint16 value from the set potential. See p. 11 of comm protocol
    def potential_to_cmd(potential, return_int = True):
        integer = int((potential / dac_factor + 2.048) * 16000)
        if return_int:
            return integer
        else:
            h_byte = int / 256
            l_byte = int - 256 * h_byte
            return str(l_byte) + str(high_byte)
