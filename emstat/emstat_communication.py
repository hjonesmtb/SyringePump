#Questions: WHat is auxillary?

import serial
import numpy as np
import binascii
import time
import math
import numpy as np
from system_data import System_Data

cell_on_post_measure = False #user input

#emstat 3 constants
dac_factor = 1.599 #DAC factor specific to emstat3
e_factor = 1.5 #Efactor specific to emstat3
v_range = 3 #specific to emstat3


class Emstat:
    def __init__(self, pstat_com, e_cond, t_cond, e_dep, t_dep, t_equil, e_begin, e_end, e_step, amplitude, frequencies, system_data):
        try:
            self.ser = serial.Serial(str(pstat_com), baudrate=230400, timeout = 1)
            if self.ser.isOpen():
                print("port opened successfully")
        except:
            self.ser = serial.Serial(pstat_com, baudrate=230400, timeout = 1)
            if self.ser.isOpen():
                print("port opened successfully")

        self.deposition_potential = e_dep
        self.system_data = system_data

    @classmethod
    def from_parameters(cls, system_data):

        return cls(system_data.pstat_com, system_data.e_cond, system_data.t_cond, system_data.e_dep, system_data.t_dep, system_data.t_equil, system_data.e_begin, system_data.e_end, system_data.e_step, system_data.amplitude, system_data.frequencies, system_data)

    def sendData(self, string):
        self.ser.write(string.encode('ascii'))

    def readData(self, bytes):
        data = self.ser.read(bytes)
        return data

    def close(self):
        self.ser.close()

    '''Runs deposition on two electrodes, returns an array with potential, current, noise, overload and underload data'''
    # Runs constant voltage measurement at potential V for time_chrono s with n multiplexer channels
    def deposition(self, dep_time, eDep_e1, eDep_e2, sensing_electrode, pump = False):
        #Sets potential on non-sensing electrode:
        if sensing_electrode == [0,1]:
            n_channels = 1
            sensing_dep = eDep_e2 #deposition potential for current reading
            nonsensing_dep = eDep_e1
            nonsensing_channel = '0200'
            sensing_channel = '0100'
        if sensing_electrode == [1,0]:
            n_channels = 1
            sensing_dep = eDep_e1 #deposition potential for current reading
            nonsensing_dep = eDep_e2
            nonsensing_channel = '0100'
            sensing_channel = '0200'
        if sensing_electrode == [1,1]:
            n_channels = 2
            sensing_channel = '0100'
            sensing_dep = eDep_e1
        n_channels = 1

        if n_channels == 1:
            self.chronoamp(sensing_dep, n_channels, dep_time, pump)

        if n_channels == 2:
            self.sendData('m' + sensing_channel)
            self.chronoamp(sensing_dep, n_channels, dep_time, pump)

    #Runs chronoamp measurement
    def chronoamp(self, potential, n_channels, dep_time, pump):
        zero = self.potential_to_cmd(0) #convert 0V to bytes
        e_constant = self.potential_to_cmd(potential) #convert set potential to bytes
        tInt = 1 / self.system_data.frequency_dep #set tInt. Cannot be less than 0.25s if multiplexer present
        if n_channels == 2 and tInt > 0.25:
            tInt = 0.25 #set tInt. Cannot be less than 0.25s if multiplexer present
        nPoints = dep_time / tInt + 1 #define the number of points
        tmeas = tInt / 2 #defined p. 32 of comm protocol
        nadmean, d1, d16 = self.d1_d16_calc(tmeas)

        tInt = self.tint_calc(tInt)

        if n_channels > 1:
            options = 6 #if many electrodes, choose alternating multiplexer
        else:
            options = 0 #Keep the cell on after measurement
        L_command = ("technique=7\nEcond={}\ntCond={}\nEdep={}\ntDep={}\ntEquil= \
        {}\ncr_min={}\ncr_max={}\ncr={}\nEbegin={}\nEstby={}\nnPoints= \
        {}\ntInt={}\nmux_delay=0\nnmux={}\nd1={}\nd16={}\noptions={}\nnadmean={}\n*".format \
        (zero, 0, zero, 0, self.system_data.t_equil_deposition, self.system_data.cr_min, self.system_data.cr_max, \
        self.system_data.cr_begin, e_constant,e_constant, nPoints, tInt, n_channels, d1, d16, options, nadmean))

        self.emstat_ready("L")
        self.sendData(L_command)

        if n_channels > 1:
            P_data = []
            char = self.readData(1).decode()
            while char != 'P': #Write Skip bytes until first P is read
                char = self.readData(1).decode()
            while char != '*': #end condition
                package = ''
                char = self.readData(1).decode()
                while char != "P" and char != "*":
                    if char != "":
                        package = package + char
                    char = self.readData(1).decode()
                if len(package) != 8*n_channels: #Check to make sure packages are the right length
                    raise ValueError('P package not 8*n_channels characters')
                P_data.append(package)
        else:
            potential_dep = [] #array to store potential from deposition for this run
            current_dep = [] #array to store current from deposition for this run
            overload_dep = [] #array to store overload from deposition for this run
            underload_dep = [] #array to store underload from deposition for this run
            time_log = []
            U_data = []
            char = self.readData(1).decode()
            while char != 'U': #Write Skip bytes until first P is read
                if char == '?':
                    print('??')
                if self.check_for_stop():
                    break
                char = self.readData(1).decode()
            if pump != False:
                pump.infuse()
            while char != '*': #end condition
                if self.check_for_stop():
                    break
                package = ''
                char = self.readData(1).decode()
                while char != "U" and char != "*":
                    if self.check_for_stop():
                        break
                    if char != "":
                        package = package + char
                    char = self.readData(1).decode()
                if len(package) != 16: #Check to make sure packages are the right length
                    print('U package not 16 characters')
                else:
                    time_log.append(time.time()-self.system_data.start_time)
                    potential, current, current_overload, current_underload = self.process_U(package)
                    potential_dep.append(potential)
                    current_dep.append(current)
                    overload_dep.append(current_overload)
                    underload_dep.append(current_underload)
                    self.system_data.write_dep(time_log, potential_dep, current_dep, overload_dep, underload_dep)
        return

    '''Sends a key(c or L) to the emstat, waits until the key is returned to make sure
    the emstat is ready to receive commands. Repeat the key if no response is heard back'''
    def emstat_ready(self, key):
        count = 0
        self.sendData(key)
        char = self.readData(1).decode()
        print(char)
        while char != key:
            char = self.readData(1).decode()
            count += 1
        return

    '''Checks if pstat needs to stop'''
    def check_for_stop(self):
        if self.system_data.stop_pstat:
            self.end_measurement()
            self.system_data.stop_pstat = False
            return True
        return False

    '''Pauses Emstat measurement if running, resumes measurement if stopped'''
    def pause_unpause_measurement(self):
        self.sendData('z')
        return

    '''Ends emstat measurement'''
    def end_measurement(self):
        self.sendData('Z')
        return

    #Converts bytes to voltage, current, stage, I status and range, Aux input, for Tpackages
    def process_T(self, T_data):
        potential_array = [] #changed from potential to potential_array - Nick
        current_array = []
        noise_array = []
        overload_array = []
        underload_array = []
        for data in T_data:
            current_overload = False
            current_underload = False
            print(T_data[2:4])
            potential = ((int(data[2:4], 16) * 256 + int(data[0:2], 16)) / 65536 * 4.096 - 2.048) * e_factor
            current_range = 10 ** int(int(data[10:12], 16) & int('0F', 16))
            if (int(data[10:12], 16) & int('20', 16) == int('20', 16)):
                current_overload = True
                print("current overload")
            if (int(data[10:12], 16) & int('40', 16) == int('40', 16)):
                current_underload = True
                print("current underload")
            current = ((int(data[6:8], 16) * 256 + int(data[4:6], 16)) / 65536 * 4.096 - 2.048) * current_range / 10**(3)
            noise = (int(data[16:18], 16) * 256 + int(data[18:20], 16)) / 65536 * 4.096
            potential_array.append(potential)
            current_array.append(current)
            noise_array.append(noise)
            overload_array.append(current_overload)
            underload_array.append(current_underload)
        return potential_array, current_array, noise_array, overload_array, underload_array

    def process_U(self, U_data):
        current_overload = False
        current_underload = False
        potential = ((int(U_data[2:4], 16) * 256 + int(U_data[0:2], 16)) / 65536 * 4.096 - 2.048) * dac_factor
        current_range = 10 ** int(int(U_data[10:12], 16) & int('0F', 16))
        current = ((int(U_data[6:8], 16) * 256 + int(U_data[4:6], 16)) / 65536 * 4.096 - 2.048) * current_range / 10**(3)
        if U_data[10:12] == '01':
            current = current + 4.096 * current
        if U_data[10:12] == 'FF':
            current = current - 4.096 * current
        if (int(U_data[10:12], 16) & int('20', 16) == int('20', 16)):
            current_overload = True
            print("current overload")
        if (int(U_data[10:12], 16) & int('40', 16) == int('40', 16)):
            current_underload = True
            print("current underload")
        return potential, current, current_overload, current_underload

    def process_P(self, P_data):
        potential1 = 0
        potential2 = 0
        current1 = 0
        current2 = 2
        return potential1, potential2, current1, current2

    #Runs measurement with defined L command parameter. L command is a string formatted as in p.26 of comm protocol
    def run_swv(self, frequency_index):
        potential_swv = [] #array to store potential from swv for this run
        current_swv = [] #array to store current from swv for this run
        overload_swv = [] #array to store overload from swv for this run
        underload_swv = [] #array to store underload from swv for this run
        time_swv = []
        T_data = [] #string array to store T packages from measurement (during steady state)
        U_data = [] #string array to store U packages from measurement (during SWV)

        swv_params = self.format_swv_parameters(self.system_data.t_equil, self.system_data.e_begin, self.system_data.e_end, self.system_data.e_step, self.system_data.amplitude, self.system_data.frequencies[frequency_index], self.system_data.e_cond, self.system_data.t_cond)

        self.sendData("J") # disables idle packages
        self.ser.flush() #clears the buffer
        self.ser.read()
        self.emstat_ready("L")
        self.sendData(swv_params)
        try:
            skip_T = False
            n = 0
            while True:
                if self.check_for_stop():
                    break
                char = self.readData(1).decode()
                # print(char)
                if n > 200:
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
                    if self.check_for_stop():
                        break
                    package = ''
                    char = self.readData(1).decode()
                    while char != "T" and char != "M" and char != "U": #M is the present at the end of the last T-package
                        if self.check_for_stop():
                            break
                        if char != "":
                            package = package + char
                        char = self.readData(1).decode()
                    if char == "M": #read another character if M received, should be a U
                        char = self.readData(1).decode()
                    # print(package)
                    if len(package) != 20:
                        print('T package not 20 characters')
                    else:
                        T_data.append(package)

            while char != '*': #end condition
                if self.check_for_stop():
                    break
                package = ''
                char = self.readData(1).decode()
                while char != "U" and char != "*":
                    if self.check_for_stop():
                        break
                    if char != "":
                        package = package + char
                    char = self.readData(1).decode()
                #print(package)
                if len(package) != 16: #Check to make sure packages are the right length
                    print('U package not 16 characters')
                else:
                    potential, current, current_overload, current_underload = self.process_U(package)
                    potential_swv.append(potential)
                    current_swv.append(current)
                    overload_swv.append(current_overload)
                    underload_swv.append(current_underload)
                    time_swv.append(time.time()- self.system_data.start_time)
                    # print("swv", potential, current)
                    self.system_data.write_swv(time_swv, potential_swv, current_swv, overload_swv, underload_swv, frequency_index)
            print("measurement complete")
        except Exception as e:
            print("Process terminated")
            print(e)
            self.ser.close()

    #Calculates all parameters for square wave voltammetry. See p. 29 of comm protocol
    def format_swv_parameters(self, t_equil, e_begin, e_end, e_step, amplitude, freq, e_cond, t_cond):
        #options
        options = 0
        if self.system_data.measure_i_forward_reverse: options += 1024
        if cell_on_post_measure: options += 4
        #n_points
        nPoints = int((e_end - e_begin) / e_step + 1)
        #t_meas, d1, d16, nadmean, tPulse
        t_meas = 1/(6*freq) #p. 23 com protocol
        nadmean, d1, d16 = self.d1_d16_calc(t_meas)
        t_meas_actual = 2**nadmean * (0.222 + d1 * 0.0076 + d16 * 0.0005) / 1000
        tPulse = int((1 / (2 * freq) - t_meas_actual) / 0.0000152)
        #potentials
        Econd = self.potential_to_cmd(e_cond)
        Edep = self.potential_to_cmd(0)
        Ebegin = self.potential_to_cmd(e_begin)
        Estep = int(e_step * 10000)
        Epulse = int(amplitude * 10000)
        #tInt
        tInt = self.tint_calc(1 / freq)
        #format ascii command
        L_command = ("technique=2\nEcond={}\ntCond={}\nEdep={}\ntDep={}\ntEquil= \
        {}\ncr_min={}\ncr_max={}\ncr={}\nEbegin={}\nEstep={}\nEpulse={}\nnPoints= \
        {}\ntInt={}\ntPulse={}\nd1={}\nd16={}\noptions={}\nnadmean={}\n*".format \
        (e_cond, t_cond, 0, 0, t_equil, self.system_data.cr_min, self.system_data.cr_max, self.system_data.cr_begin, Ebegin, \
        Estep, Epulse, nPoints, tInt, tPulse, d1, d16, options, nadmean))
        return L_command

    #Calculates d1, d16 and nadmean from tmeas. See p. 24 of comm protocol
    def d1_d16_calc(self, tmeas):
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

    #Calculates tint from the interval time in seconds. See p. 26 of comm protocol
    def tint_calc(self, tint):
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
        else:
            if tint <= 1:
                return tint * 128
            elif tint < 60:
                highbyte = 1
                return highbyte**6 + tint #Set high byte to 1


    #Calculates a Uint16 value from the set potential. See p. 11 of comm protocol
    def potential_to_cmd(self, potential, return_int = True):
        integer = int((potential / dac_factor + 2.048) * 16000)
        if return_int:
            return integer
        else:
            h_byte = integer / 256
            l_byte = integer - 256 * h_byte
            return str(l_byte) + str(h_byte)
