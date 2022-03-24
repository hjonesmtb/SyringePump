from datetime import datetime
import json
from typing import Type
import os
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, FigureCanvasAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

SYRINGE_DIAM = 20  # mm
FLOWRATE_CONVERSION = 1 / 1000 / 60  # 1mL/1000uL*1min/60seconds

# default values

TEST_TYPES = ["Stop-Flow", "Chronoamperometry", "Cyclic Voltametry", "Pump"]
DATE = datetime.now().strftime("%y-%m-%d_%H%M")
TEST_NAME = TEST_TYPES[0]+ "_" + DATE
PUMP_BAUD = 1200
PUMP_COM = "COM3"
PSTAT_COM = "COM4"
E_CONDITION = 0  # V
T_CONDITION = 0  # s
E_DEPOSITION = 0.8  # V
T_EQUILIBRATION = 0  # s
E_BEGIN = -0.4  # V
E_STOP = 0.4  # V
E_STEP = 0.005  # V
AMPLITUDE = 0.01  # V
FREQUENCIES = [37, 25, 7] # Hz
FLOW_RATE = 1000  # uL/min
INFUSION_VOLUME = 1  # mL
N_MEASUREMENTS = 10
N_ELECTRODES = 1
T_DEPOSITION = INFUSION_VOLUME / N_MEASUREMENTS / (FLOW_RATE * FLOWRATE_CONVERSION)
STEP_VOLUME = INFUSION_VOLUME / N_MEASUREMENTS
FIGSIZE = (20,6)
PATH = os.getcwd()


class System_Data:
    def __init__(self, data_dict = None):
        #loads default values
        self.initial_pump_time = 240 #initial pumping time
        self.start_time = 0
        #creates directory for system data
        if data_dict == None:
            print("No JSON file found, loading in default values...")
            # measurment data
            self.current_swv = []
            self.potential_swv = []
            self.overload_swv = []
            self.underload_swv = []
            self.current_dep = []
            self.potential_dep = []
            self.overload_dep = []
            self.underload_dep = []
            self.noise = []
            self.time = []
            # test types
            self.test_types = TEST_TYPES
            self.test_type = self.test_types[0]
            # system parameters
            self.pump_com = PUMP_COM
            self.pump_baud = PUMP_BAUD
            self.pstat_com = PSTAT_COM
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
            self.n_measurements = N_MEASUREMENTS
            self.step_volume = STEP_VOLUME
            self.syringe_diam = SYRINGE_DIAM
            self.flowrate_conversion = FLOWRATE_CONVERSION
            self.n_electrodes = N_ELECTRODES
            self.measurements = 0
            #plot axes
            self.figsize = FIGSIZE
            self.ax_dep = []
            self.ax_swv = []
            self.ax_cyclic = []
            self.ax_chrono = []
        #loads config files
        else:
            # measurment data
            self.current_swv = []
            self.potential_swv = []
            self.overload_swv = []
            self.underload_swv = []
            self.current_dep = []
            self.potential_dep = []
            self.overload_dep = []
            self.underload_dep = []
            self.noise = []
            self.time = []
            # test types
            self.test_types = []
            self.test_types.append("Stop-Flow")
            self.test_types.append("Chronoamperometry")
            self.test_types.append("Cyclic Voltametry")
            self.test_type = data_dict["test_type"]
            # system parameters
            self.pump_com = PUMP_COM
            self.pump_baud = PUMP_BAUD
            self.pstat_com = PSTAT_COM
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
            self.n_measurements = data_dict["n_measurements"]
            self.step_volume = data_dict["step_volume"]
            self.syringe_diam = data_dict["syringe_diam"]
            self.flowrate_conversion = FLOWRATE_CONVERSION
            self.n_electrodes = data_dict["n_electrodes"]
            self.measurements = 0
            #plot axes
            self.figsize = FIGSIZE
            self.ax_dep = []
            self.ax_swv = []
            self.ax_cyclic = []
            self.ax_chrono = []

        self.path = PATH + '\data'
        #fix naming of folder
        self.data_folder = os.path.join(self.path, self.test_name)
        self.fig_agg = []
        self.fig = []
        return

    def write_swv(self, pot, cur, over, under):
        self.potential_swv = pot
        self.current_swv = cur
        self.overload_swv = over
        self.underload_swv = under

    def write_dep(self, pot, cur, over, under):
        self.potential_dep = pot
        self.current_dep = cur
        self.overload_dep = over
        self.underload_dep = under

    def save_data(self):
        #save the test configuration
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
            os.makedirs(os.path.join(self.data_folder, 'plots'))
            os.makedirs(os.path.join(self.data_folder, 'csv'))
        
        jsonFile = self.data_folder + '/config.json'
        with open(jsonFile, "w") as write_file:
            json.dump(self.encode_system_data(), write_file)
        #save the csv
        df = pd.DataFrame({'Potential_dep':self.potential_dep, 'Current_dep':self.current_dep,'Potential_SWV':self.potential_swv, 'Current_SWV':self.current_swv,})
        df.to_csv(self.data_folder + '/csv/' + str(self.measurements) + '.csv')
        #save the plots
        plt.figure(2)
        plt.clf()
        plt.plot(self.potential_swv,self.current_swv)
        plt.xlabel('Potential (V)')
        plt.ylabel('Current (uA)')
        plt.savefig(self.data_folder + '/plots/' + str(self.measurements) + '.png')

        # self.fig.savefig(self.data_folder + '/plots/' + str(self.measurements) + '.png')
        return

    #creates dictionary to be JSON serialized from all the given data
    def encode_system_data(self):
        if isinstance(self, System_Data):
            data_dict = {
            "__System_Data__": True,
            "test_name" : self.test_name,
            "test_type" : self.test_type,
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
        if self.test_type == 'Stop-Flow':
            self.ax_dep.plot(self.potential_dep,self.time)
            self.ax_swv.plot(self.potential_swv,self.current_swv)
            self.fig_agg.draw()
        elif self.test_type == 'Cyclic voltammetry':
            self.ax_cyclic.plot(self.potential_dep,self.current_dep)
            self.fig_agg.draw()
            return
        elif self.test_type == 'Pump':
            return
        elif self.test_type == 'Chronoamperometry':
            self.ax_chrono.plot(self.potential_dep,self.time)
            self.fig_agg.draw()

        return

    def update_test_name(self):
        self.test_name = self.test_type + "_" + datetime.now().strftime("%y-%m-%d_%H%M")
        self.data_folder = os.path.join(self.path, self.test_name)

    def draw_figure(self, canvas, figure, loc=(50, 0)):
        figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
        figure_canvas_agg.draw()
        figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
        self.fig_agg =  figure_canvas_agg

    def Initialize_Plots(self, window):
        canvas_elem = window['-PLOT-']
        canvas = canvas_elem.TKCanvas

        if self.test_type == 'Stop-Flow':
            #draw the initial plot in the window
            fig = plt.figure(1, figsize = self.figsize)
            fig.clf()
            self.ax_dep = fig.add_subplot(121)
            self.ax_dep.set_xlabel('time(s)')
            self.ax_dep.set_ylabel('Current (uA)')
            self.ax_dep.set_title('Deposition Current')

            self.ax_swv = fig.add_subplot(122)
            self.ax_swv.set_xlabel('Potential (V)')
            self.ax_swv.set_ylabel('Current (uA)')
            self.ax_swv.set_title('Squarewave Current')
            
        if self.test_type == 'Chronoamperometry':
            #draw the initial plot in the window
            fig = plt.figure(1, figsize = self.figsize)
            fig.clf()
            self.ax_chrono = fig.add_subplot(111)
            self.ax_chrono.set_xlabel('time(s)')
            self.ax_chrono.set_ylabel('Current (uA)')
            
        if self.test_type == 'Cyclic Voltammetry':
            #draw the initial plot in the window
            fig = plt.figure(1, figsize = self.figsize)
            fig.clf()
            self.ax_cyclic = fig.add_subplot(111)
            self.ax_cyclic.set_xlabel('Potential (V)')
            self.ax_cyclic.set_ylabel('Current (uA)')
        self.plot = fig
        self.draw_figure(canvas, fig)


    