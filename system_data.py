from cProfile import label
from datetime import datetime
import json
from typing import Type
import os
import pandas as pd
import PySimpleGUI as sg
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, FigureCanvasAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import ListedColormap, LinearSegmentedColormap

SYRINGE_DIAM = 20  # mm
FLOWRATE_CONVERSION = 1 / 1000 / 60  # 1mL/1000uL*1min/60seconds

# default values

TEST_TYPES = ["Stop-Flow", "Chronoamperometry"]
DATE = datetime.now().strftime("%y-%m-%d_%H%M")
TEST_NAME = TEST_TYPES[0]+ "_" + DATE
PUMP_BAUD = 1200
PUMP_COM = "COM7"
PSTAT_COM = "COM6"
E_CONDITION = 0  # V
T_CONDITION = 0  # s
E_DEPOSITION = 0.8  # V
T_EQUILIBRATION = 0  # s
E_BEGIN = -0.4  # V
E_STOP = 0.4  # V
E_STEP = 0.005  # V
AMPLITUDE = 0.01  # V
FREQUENCY_DEP = 10 #Hz
FREQUENCIES = [37, 25, 7] # Hz
FLOW_RATE = 1000  # uL/min
INFUSION_VOLUME = 1  # mL
N_MEASUREMENTS = 10
N_ELECTRODES = 1
T_DEPOSITION = INFUSION_VOLUME / N_MEASUREMENTS / (FLOW_RATE * FLOWRATE_CONVERSION)
STEP_VOLUME = INFUSION_VOLUME / N_MEASUREMENTS
FIGSIZE = (20,12)
PATH = os.getcwd()
PUMP_SCALE = 20 #cuts off first few points of the first deposition during stop flow.
MAX_PLOTS = 5
INITIAL_PUMP_TIME = 240


class System_Data:
    def __init__(self, data_dict = None):
        #loads default values
        self.initial_pump_time = INITIAL_PUMP_TIME #initial pumping time
        self.start_time = 0 #Time user first hits start button
        self.time_end = 0 #Time the measurement ends
        self.stop_pstat = False
        self.inject_time = 0 #Time user turns valve
        self.valve_turned = False
        self.measurement_time = 0
        # measurment data
        self.current_swv = [[0], [0], [0]]
        self.potential_swv =  [[0], [0], [0]]
        self.overload_swv = []
        self.underload_swv = []
        self.current_dep = []
        self.potential_dep = []
        self.overload_dep = []
        self.underload_dep = []
        self.total_potential = []
        self.total_current = []
        self.noise = []
        self.time = []
        self.time_dep = []
        self.measurements = 0
        # test type
        self.test_types = TEST_TYPES
        # communication
        self.pump_com = PUMP_COM
        self.pump_baud = PUMP_BAUD
        self.pstat_com = PSTAT_COM
        self.flowrate_conversion = FLOWRATE_CONVERSION

        #plot axes
        self.figsize = FIGSIZE
        self.ax_dep = []
        self.ax_swv = [0, 0, 0]
        self.ax_cyclic = []
        self.ax_chrono = []
        self.line_dep = []
        self.line_swv = []

        self.fig_agg = None
        self.fig = None
        self.canvas = None


        if data_dict == None:
            print("No JSON file found, loading in default values...")
            # test type
            self.test_type = self.test_types[0]
            # system parameters
            self.test_name = TEST_NAME
            self.flow_rate = FLOW_RATE
            self.infusion_volume = INFUSION_VOLUME
            self.e_cond = E_CONDITION
            self.e_dep = E_DEPOSITION
            self.e_begin = E_BEGIN
            self.e_end = E_STOP
            self.e_step = E_STEP
            self.t_cond = T_CONDITION
            self.t_dep = T_DEPOSITION
            self.t_equil = T_EQUILIBRATION
            self.amplitude = AMPLITUDE
            self.frequencies = FREQUENCIES
            self.frequency_dep = FREQUENCY_DEP
            self.n_measurements = N_MEASUREMENTS
            self.step_volume = STEP_VOLUME
            self.syringe_diam = SYRINGE_DIAM
            self.n_electrodes = N_ELECTRODES
        #loads config files
        else:
            # test types
            self.test_type = data_dict["test_type"]
            # system parameters
            self.test_name = data_dict["test_name"]
            self.flow_rate = data_dict["flow_rate"]
            self.infusion_volume = data_dict["infusion_volume"]
            self.e_cond = data_dict["e_cond"]
            self.e_dep = data_dict["e_dep"]
            self.e_begin = data_dict["e_begin"]
            self.e_end = data_dict["e_end"]
            self.e_step = data_dict["e_step"]
            self.t_cond = data_dict["t_cond"]
            self.t_dep = data_dict["t_dep"]
            self.t_equil = data_dict["t_equil"]
            self.amplitude = data_dict["amplitude"]
            self.frequencies = data_dict["frequencies"]
            self.frequency_dep = data_dict["frequency_dep"]
            self.n_measurements = data_dict["n_measurements"]
            self.step_volume = data_dict["step_volume"]
            self.syringe_diam = data_dict["syringe_diam"]
            self.n_electrodes = data_dict["n_electrodes"]

        self.path = PATH + '\data'
        self.data_folder = os.path.join(self.path, self.test_name)
        return

    def write_swv(self,time, pot, cur, over, under, freq_index):
        self.time.append(time[-1])
        self.potential_swv[freq_index] = pot
        self.current_swv[freq_index] = cur
        self.overload_swv = over
        self.underload_swv = under
        self.total_potential.append(pot[-1])
        self.total_current.append(cur[-1])

    def write_dep(self, time, pot, cur, over, under):
        self.time_dep = time
        self.time.append(time[-1])#get last element to stop duplicate values in data
        self.potential_dep = pot
        self.current_dep = cur
        self.overload_dep = over
        self.underload_dep = under
        self.total_potential.append(pot[-1])
        self.total_current.append(cur[-1])

    def save_data(self):
        #create directory if one does not already exist.
        #this will always happen when the test is started.
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
            os.makedirs(os.path.join(self.data_folder, 'csv'))
        #save the test configuration
        jsonFile = self.data_folder + '/config.json'
        with open(jsonFile, "w") as write_file:
            json.dump(self.encode_system_data(), write_file)

        #save the csv
        total_data = {'Time':self.time, 'Potential':self.total_potential,'Current':self.total_current,}
        total_data = pad_dict_list(total_data, 0)
        data_dict = {'Potential_dep':self.potential_dep, 'Current_dep':self.current_dep,'Potential_'+str(self.frequencies[0]):self.potential_swv[0], 'Current_'+str(self.frequencies[0]):self.current_swv[0],'Potential_'+str(self.frequencies[1]):self.potential_swv[1], 'Current_'+str(self.frequencies[1]):self.current_swv[1],'Potential_'+str(self.frequencies[2]):self.potential_swv[2], 'Current_'+str(self.frequencies[2]):self.current_swv[2],}
        data_dict = pad_dict_list(data_dict, 0)
        df = pd.DataFrame(data_dict)
        df.to_csv(self.data_folder + '/csv/' + str(self.measurements) + '.csv', index=False)
        df_t = pd.DataFrame(total_data)
        df_t.to_csv(self.data_folder + '/csv/' + str(self.inject_time) + '_total.csv', index=False)
        return

    #creates dictionary from system parameters to be JSON serialized.
    def encode_system_data(self):
        if isinstance(self, System_Data):
            data_dict = {
            "__System_Data__": True,
            "test_name" : self.test_name,
            "test_type" : self.test_type,
            "Inject_time": self.inject_time,
            "flow_rate" : self.flow_rate,
            "infusion_volume" : self.infusion_volume,
            "e_cond" : self.e_cond,
            "e_dep": self.e_dep,
            "e_begin": self.e_begin,
            "e_end" : self.e_end,
            "e_step" : self.e_step,
            "t_cond" : self.t_cond,
            "t_dep" : self.t_dep,
            "t_equil": self.t_equil,
            "amplitude" : self.amplitude,
            "frequencies" : self.frequencies,
            "frequency_dep" : self.frequency_dep,
            "n_measurements" : self.n_measurements,
            "step_volume": self.step_volume,
            "syringe_diam" : self.syringe_diam,
            "n_electrodes" : self.n_electrodes
            }
            return data_dict
        else:
            type_name = self.__class__.__name__
            raise TypeError(f"Object of type '{type_name}' is not JSON serializable")

    def decode_system_config(data_dict):
        if "__System_Data__" in data_dict:
            return System_Data(data_dict)
        return data_dict

    def load_system_data_from_json(json_file: str):
        with open(json_file) as json_data:
            data = json_data.read()
            system_data = json.loads(data, object_hook=System_Data.decode_system_config)
        return system_data

    def plot_data(self):
        cmap = cm.get_cmap('gist_rainbow', int(10))
        colour = cmap((self.measurements % self.n_measurements) / 10)
        if self.test_type == 'Stop-Flow':
            self.ax_swv[0].set_title('Square Wave Current at ' + str(self.frequencies[0])+ 'Hz')
            self.ax_swv[1].set_title('Square Wave Current at ' + str(self.frequencies[1])+ 'Hz')
            self.ax_swv[2].set_title('Square Wave Current at ' + str(self.frequencies[2])+ 'Hz')
            length = get_min_length(self.time_dep, self.current_dep)
            if(self.measurements == 1):
                self.ax_dep.cla()
                self.ax_dep.set_xlabel('Time(s)')
                self.ax_dep.set_ylabel('Current (uA)')
                self.ax_dep.set_title('Deposition Current at ' + str(self.e_dep) + 'V')
            if(length >1):
                self.ax_dep.plot(self.time_dep[0:length-1],self.current_dep[0:length-1], color = colour)
            if(length > PUMP_SCALE and not self.valve_turned):
                self.ax_dep.cla()
                self.ax_dep.set_xlabel('Time(s)')
                self.ax_dep.set_ylabel('Current (uA)')
                self.ax_dep.set_title('Deposition Current at ' + str(self.e_dep) + 'V')
                self.ax_dep.plot(self.time_dep[PUMP_SCALE-1:length-1],self.current_dep[PUMP_SCALE-1:length-1], color = colour)
                #self.ax_dep.set_xlim(self.time_dep[0], self.time_dep[-1])
            length = get_min_length(self.potential_swv[0], self.current_swv[0])
            if(length >1):
                self.ax_swv[0].plot(self.potential_swv[0][0:length-1],self.current_swv[0][0:length-1], color = colour, label=str(self.measurements+1))
            length = get_min_length(self.potential_swv[1], self.current_swv[1])
            if(length >1):
                self.ax_swv[1].plot(self.potential_swv[1][0:length-1],self.current_swv[1][0:length-1], color = colour, label=str(self.measurements+1))
            length = get_min_length(self.potential_swv[2], self.current_swv[2])
            if(length >1):
                self.ax_swv[2].plot(self.potential_swv[2][0:length-1],self.current_swv[2][0:length-1], color = colour, label=str(self.measurements+1))

            legend_without_duplicate_labels(self.ax_swv[0])

            self.fig_agg.draw()


        elif self.test_type == 'Cyclic voltammetry':
            length = get_min_length(self.potential_dep, self.current_dep)
            if(length >1):
                self.ax_cyclic.plot(self.potential_dep[0:length-1],self.current_dep[0:length-1], color = colour)
            self.fig_agg.draw()
        elif self.test_type == 'Chronoamperometry':
            length = get_min_length(self.time_dep, self.current_dep)
            if(length >1):
                self.ax_chrono.plot(self.time_dep[0:length-1],self.current_dep[0:length-1], color = colour)

            self.fig_agg.draw()
        return

    def update_test_name(self):
        self.test_name = self.test_type + "_" + datetime.now().strftime("%y-%m-%d_%H%M")
        self.data_folder = os.path.join(self.path, self.test_name)

    def draw_figure(self):
        figure_canvas_agg = FigureCanvasTkAgg(self.fig, self.canvas)
        figure_canvas_agg.draw()
        figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
        self.fig_agg = figure_canvas_agg

    #draw the initial plot in the window
    def Initialize_Plots(self, window):
        canvas_elem = window['-PLOT-']
        self.canvas = canvas_elem.TKCanvas

        if self.test_type == 'Stop-Flow':
            self.fig = plt.figure(1, figsize = self.figsize)
            self.fig.clf()
            self.ax_dep = self.fig.add_subplot(221)
            self.ax_dep.set_xlabel('Time(s)')
            self.ax_dep.set_ylabel('Current (uA) at ' + str(self.e_dep) + 'V')
            self.ax_dep.set_title('Deposition Current')

            self.ax_swv[0] = self.fig.add_subplot(222)
            self.ax_swv[0].set_xlabel('Potential (V)')
            self.ax_swv[0].set_ylabel('Current (uA)')
            self.ax_swv[0].set_title('Square Wave Current at ' + str(self.frequencies[0])+ 'Hz')

            self.ax_swv[1] = self.fig.add_subplot(223)
            self.ax_swv[1].set_xlabel('Potential (V)')
            self.ax_swv[1].set_ylabel('Current (uA)')
            self.ax_swv[1].set_title('Square Wave Current at '+ str(self.frequencies[1])+ 'Hz')

            self.ax_swv[2] = self.fig.add_subplot(224)
            self.ax_swv[2].set_xlabel('Potential (V)')
            self.ax_swv[2].set_ylabel('Current (uA)')
            self.ax_swv[2].set_title('Square Wave Current at '+ str(self.frequencies[2])+ 'Hz')


        elif self.test_type == 'Chronoamperometry':
            self.fig = plt.figure(1, figsize = self.figsize)
            self.fig.clf()
            self.ax_chrono = self.fig.add_subplot(111)
            self.ax_chrono.set_xlabel('Time(s)')
            self.ax_chrono.set_ylabel('Current (uA)')

        elif self.test_type == 'Cyclic Voltammetry':
            self.fig = plt.figure(1, figsize = self.figsize)
            self.fig.clf()
            self.ax_cyclic = self.fig.add_subplot(111)
            self.ax_cyclic.set_xlabel('Potential (V)')
            self.ax_cyclic.set_ylabel('Current (uA)')
        else:
            print("No Plot Initialized")
        self.draw_figure()

    def reset_measurement_arrays(self):
        self.current_swv =  [[0], [0], [0]]
        self.potential_swv =  [[0], [0], [0]]
        self.overload_swv = []
        self.underload_swv = []
        self.current_dep = []
        self.potential_dep = []
        self.overload_dep = []
        self.underload_dep = []
        self.time_dep = []

'''
Private helper functions for System data class.
'''
def pad_dict_list(dict_list, pad_val):
    lmax = 0
    for lname in dict_list.keys():
        lmax = max(lmax, len(dict_list[lname]))
    for lname in dict_list.keys():
        ll = len(dict_list[lname])
        if  ll < lmax:
            dict_list[lname] += [pad_val] * (lmax - ll)
    return dict_list

def get_min_length(array1, array2):
    return min(len(array1), len(array2))

def legend_without_duplicate_labels(ax):
    handles, labels = ax.get_legend_handles_labels()
    unique = [(h, l) for i, (h, l) in enumerate(zip(handles, labels)) if l not in labels[:i]]
    ax.legend(*zip(*unique))
