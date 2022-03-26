#Questions: WHat is auxillary?

import serial
import numpy as np
import binascii
import time
import math
import numpy as np
from system_data import System_Data

#User inputs
technique = 2 #square wave voltammetry
cr_min = 1 # minimum current range, 0: 1nA  1: 10nA, 2: 100nA, 3: 1 uA, 4: 10uA, 5: 100uA, 6: 1mA, 7: 10mA, user input
cr_max = 5 # max current range, user input
cr = 3 #Starting current range, user input
measure_i_forward_reverse = True #user input
cell_on_post_measure = False #user input



#emstat 3 constants
dac_factor = 1.599 #DAC factor specific to emstat3
e_factor = 1.5 #Efactor specific to emstat3
v_range = 3 #specific to emstat3


class Emstat:
    def __init__(self, pstat_com, e_cond, t_cond, e_dep, t_dep, t_equil, e_begin, e_end, e_step, amplitude, frequencies, system_data):
        try:
            #self.ser = serial.Serial('COM{}'.format(pstat_com), baudrate=230400, timeout = 1)
            self.ser = serial.Serial(str(pstat_com), baudrate=230400, timeout = 1)
            if self.ser.isOpen():
                print("port opened successfully")
        except:
            try:
                self.ser = serial.Serial(pstat_com, baudrate=230400, timeout = 1)
                if self.ser.isOpen():
                    print("port opened successfully")
            except:
                print("COM port is not available")
        self.swv_params = self.format_swv_parameters(t_equil, e_begin, e_end, e_step, amplitude, frequencies, e_cond, t_cond)
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
    def deposition(self, dep_time, eDep_e1, eDep_e2, sensing_electrode):
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
            # self.emstat_ready('c')
            # self.sendData('m' + nonsensing_channel)
            # command = self.potential_to_cmd(nonsensing_dep, False)
            # command = 'D' + command
            # self.sendData(command)

            # self.sendData('m' + sensing_channel)
            self.chronoamp(sensing_dep, n_channels, dep_time)

        if n_channels == 2:
            self.sendData('m' + sensing_channel)
            self.chronoamp(sensing_dep, n_channels, dep_time)

    #Runs chronoamp measurement
    def chronoamp(self, potential, n_channels, dep_time):
        zero = self.potential_to_cmd(0) #convert 0V to bytes
        e_constant = self.potential_to_cmd(potential) #convert set potential to bytes
        if n_channels == 1:
            tInt = 1 #set tInt. Cannot be less than 0.25s if multiplexer present
        if n_channels == 2:
            tInt = 0.25 #set tInt. Cannot be less than 0.25s if multiplexer present
        nPoints = dep_time / tInt #define the number of points
        tmeas = tInt / 2 #defined p. 32 of comm protocol
        nadmean, d1, d16 = self.d1_d16_calc(tmeas)

        if n_channels > 1:
            options = 6 #if many electrodes, choose alternating multiplexer
        else:
            options = 0 #Keep the cell on after measurement
        L_command = ("technique=7\nEcond={}\ntCond={}\nEdep={}\ntDep={}\ntEquil= \
        {}\ncr_min={}\ncr_max={}\ncr={}\nEbegin={}\nEstby={}\nnPoints= \
        {}\ntInt={}\nmux_delay=0\nnmux={}\nd1={}\nd16={}\noptions={}\nnadmean={}\n*".format \
        (zero, 0, zero, 0, 0, cr_min, cr_max, \
        cr, e_constant,e_constant, nPoints, tInt, n_channels, d1, d16, options, nadmean))

        # (eCond = zero, tCond = 0, eDep = zero, tDep = 0, tEquil = 0, cr_min, cr_max, \
        # cr, e_constant,e_constant, nPoints, tInt, n_channels, d1, d16, options, nadmean))

        self.emstat_ready("L")
        self.sendData(L_command)

        starttime = time.time()
        time_log = []

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
                print(package)
                if len(package) != 8*n_channels: #Check to make sure packages are the right length
                    raise ValueError('P package not 8*n_channels characters')
                P_data.append(package)
                time_log.append(time.time()-starttime)
        else:
            potential_dep = [] #array to store potential from deposition for this run
            current_dep = [] #array to store current from deposition for this run
            overload_dep = [] #array to store overload from deposition for this run
            underload_dep = [] #array to store underload from deposition for this run
            U_data = []
            char = self.readData(1).decode()
            while char != 'U': #Write Skip bytes until first P is read
                char = self.readData(1).decode()
            while char != '*': #end condition
                package = ''
                char = self.readData(1).decode()
                while char != "U" and char != "*":
                    if char != "":
                        package = package + char
                    char = self.readData(1).decode()
                #print(package)
                if len(package) != 16: #Check to make sure packages are the right length
                    raise ValueError('U package not 16 characters')
                potential, current, current_overload, current_underload = self.process_U(package)
                potential_dep.append(potential)
                current_dep.append(current)
                overload_dep.append(current_overload)
                underload_dep.append(current_underload)
                time_log.append(time.time()-starttime)
                print(potential, current)
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
            if count > 30:
                self.sendData(key) #Try again
        return

    #Runs swv sweep, returns array with potential, current, overload and underload arrays
    def sweepSWV(self):
        self.run_swv()

    #Converts bytes to voltage, current, stage, I status and range, Aux input, for Tpackages
    def process_T(self, T_data):
        potential = []
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
    def run_swv(self):
        potential_swv = [] #array to store potential from swv for this run
        current_swv = [] #array to store current from swv for this run
        overload_swv = [] #array to store overload from swv for this run
        underload_swv = [] #array to store underload from swv for this run
        T_data = [] #string array to store T packages from measurement (during steady state)
        U_data = [] #string array to store U packages from measurement (during SWV)
        self.sendData("J") # disables idle packages
        self.ser.flush() #clears the buffer
        self.ser.read()
        self.emstat_ready("L")
        self.sendData(self.swv_params)
        try:
            skip_T = False
            n = 0
            while True:
                char = self.readData(1).decode()
                print(char)
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
                    package = ''
                    char = self.readData(1).decode()
                    while char != "T" and char != "M" and char != "U": #M is the present at the end of the last T-package
                        if char != "":
                            package = package + char
                        char = self.readData(1).decode()
                    if char == "M": #read another character if M received, should be a U
                        char = self.readData(1).decode()
                    print(package)
                    if len(package) != 20:
                        raise ValueError('T package not 20 characters')
                    T_data.append(package)

            while char != '*': #end condition
                package = ''
                char = self.readData(1).decode()
                while char != "U" and char != "*":
                    if char != "":
                        package = package + char
                    char = self.readData(1).decode()
                #print(package)
                if len(package) != 16:
                    raise ValueError('U package not 16 characters')
                potential, current, current_overload, current_underload = self.process_U(package)
                potential_swv.append(potential)
                current_swv.append(current)
                overload_swv.append(current_overload)
                underload_swv.append(current_underload)
                print("swv", potential, current)
                self.system_data.write_swv(potential_swv, current_swv, overload_swv, underload_swv)
            print("measurement complete")
        except Exception as e:
            print("Process terminated")
            print(e)
            self.ser.close()

    #Calculates all parameters for square wave voltammetry. See p. 29 of comm protocol
    def format_swv_parameters(self, t_equil, e_begin, e_end, e_step, amplitude, freq, e_cond, t_cond):
        #options
        options = 0
        if measure_i_forward_reverse: options += 1024
        if cell_on_post_measure: options += 4
        #n_points
        nPoints = int((e_end - e_begin) / e_step + 1)
        #t_meas, d1, d16, nadmean, tPulse
        t_meas = 1/(6*freq[0]) #p. 23 com protocol
        nadmean, d1, d16 = self.d1_d16_calc(t_meas)
        t_meas_actual = 2**nadmean * (0.222 + d1 * 0.0076 + d16 * 0.0005) / 1000
        tPulse = int((1 / (2 * freq[0]) - t_meas_actual) / 0.0000152)
        #potentials
        Econd = self.potential_to_cmd(e_cond)
        Edep = self.potential_to_cmd(0)
        Ebegin = self.potential_to_cmd(e_begin)
        Estep = int(e_step * 10000) 
        Epulse = int(amplitude * 10000)
        #tInt
        tInt = self.tint_calc(freq[0])
        #format ascii command
        L_command = ("technique={}\nEcond={}\ntCond={}\nEdep={}\ntDep={}\ntEquil= \
        {}\ncr_min={}\ncr_max={}\ncr={}\nEbegin={}\nEstep={}\nEpulse={}\nnPoints= \
        {}\ntInt={}\ntPulse={}\nd1={}\nd16={}\noptions={}\nnadmean={}\n*".format \
        (technique, e_cond, t_cond, 0, 0, t_equil, cr_min, cr_max, cr, Ebegin, \
        Estep, Epulse, nPoints, tInt, tPulse, d1, d16, options, nadmean))
        print(L_command)
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

    #Calculates tint from the frequency. See p. 26 of comm protocol
    def tint_calc(self, freq):
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
    def potential_to_cmd(self, potential, return_int = True):
        integer = int((potential / dac_factor + 2.048) * 16000)
        if return_int:
            return integer
        else:
            h_byte = integer / 256
            l_byte = integer - 256 * h_byte
            return str(l_byte) + str(h_byte)
