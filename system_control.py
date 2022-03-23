"""
Main controler for the Fentanyl Quantification System.
To use the application the following libraries will need to be installed:
    pandas
    matplotlib
    PySimpleGUI
    serial.tools


References:

Serial library
https://pyserial.readthedocs.io/en/latest/tools.html

"""
import sys
import time
import PySimpleGUI as sg
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, FigureCanvasAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np
import os
from datetime import datetime
import pandas as pd
from serial.tools import list_ports
import threading, queue

from syringe_pump.pump_22 import Pump
from emstat.emstat_communication import Emstat
from system_data import System_Data


SYMBOL_UP =    '▲'
SYMBOL_DOWN =  '▼'

#System_Data class is initialized with default values.
#This class will hold the data read from the potentiostat for generating plots and saving to a .csv
system_data = System_Data()
#can be loaded from a custom config file.
#system_data = System_Data.load_system_data_from_json("pathtoconfig/config.json")
"""
    Helper function that creates a Column that can be later made hidden, thus appearing "collapsed"
    :param layout: The layout for the section
    :param key: Key used to make this seciton visible / invisible
    :return: A pinned column that can be placed directly into your layout
    :rtype: sg.pin
    """

#boiler plate code for USB port selection page.
def test_settings_window():

    #creates a list of the names of all current usb devices.
    usbs = list_ports.comports()
    port_name = []
    for usb in usbs:
        port_name.append(usb.name)

    layout = test_settings_gui_format(usbs, port_name)

    # create the form and show it without the plot
    window = sg.Window('Test Settings', layout, finalize=True, resizable=True)
    return window

def test_settings_gui_format(usbs, port_name):
    layout =[
            [sg.Text('Test Settings', size=(40, 1),justification='left', font='Helvetica 20')],
            # [sg.Text('Test Name', size=(20, 1), font='Helvetica 12'), sg.InputText(system_data.test_name, key=('-TestName-'))],
            [sg.Text('Test Type', size=(20, 1), font='Helvetica 12'), sg.Combo(system_data.test_types, size=(20,1),default_value=system_data.test_type,key=('-TestType-'))],
            [sg.Text('# Electrodes', size=(20, 1), font='Helvetica 12'), sg.InputText(system_data.n_electrodes, key=('-NElectrodes-'))],
            # [sg.Text('# Measurements', size=(20, 1), font='Helvetica 12'), sg.InputText(system_data.n_measurements, key=('-NMeasurements-'))],
            # [sg.Text('Measurement Volume [uL]', size=(20, 1), font='Helvetica 12'), sg.InputText(system_data.step_volume*1000, key=('-StepVolume-'))], 
            # [sg.Text('Flow rate [uL/min]', size=(20, 1), font='Helvetica 12'), sg.InputText(system_data.flow_rate, key=('-FlowRate-'))],
            [sg.Text('Syringe Diameter [mm]', size=(20,1), font='Helvetica 12'), sg.InputText(system_data.syringe_diam, key=('-SyringeDiam-'))],
            [sg.Text('Syringe Pump Port', size=(20, 1), font='Helvetica 12'), sg.Combo(port_name, size=(20,1),key=('-PumpPort-'))],
            [sg.Text('Pstat Port', size=(20, 1), font='Helvetica 12'), sg.Combo(port_name, size=(20,1),key=("-PStatPort-"))],
            [sg.Text('List of Detected Ports', size=(20, 1), font='Helvetica 12'), sg.Listbox(usbs, size=(20, len(usbs)), key=("-usbs-"))],
            [sg.Canvas(key='-controls_cv-')],
            [sg.Button('Next', size=(10, 1), pad=((280, 0), 3), font='Helvetica 14')],
            ]
    return layout

#boiler plate code for entering parameters
def control_windows():
    
    layout = parameters_Format()
    window = sg.Window('Start Screen', layout, finalize=True, resizable=True)
    ax, fig_agg = Plot_GUI_Format(window)

    return window, ax, fig_agg

def voltammetry_gui_format():
    layout = []
    if(system_data.test_type == 'Stop-Flow'):
        layout = swv_format()
    if(system_data.test_type == 'Chronoamperometry'):
        layout = chronoamp_format()
    if(system_data.test_type == 'Cyclic Voltametry'):
        layout = cyclic_format()
    if(system_data.test_type == 'Pump'):
        layout = pump_format()
       #print("Failed to pick test name")
    return layout
   

def swv_format():
    swv_parameters = [
            [sg.Text('Test Name', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.test_name, key=('-TestName-'))],
            [sg.Text('Stop', size=(15, 1), font='Helvetica 14')],
            [sg.Text('# Measurements', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.n_measurements, key=('-NMeasurements-'))],
            [sg.Text('Measurement Volume [uL]', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.step_volume*1000, key=('-StepVolume-'))], 
            [sg.Text('Flow rate [uL/min]', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.flow_rate, key=('-FlowRate-'))],
            [sg.Text('E deposition [V]', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.e_dep, key='-E_dep-')],
            [sg.Text('Flow', size=(15, 1), font='Helvetica 14')],
            [sg.Text('E condition [V]', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.e_cond, key='-E_cond-')],
            [sg.Text('t condition [s]', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.t_cond, key='-T_cond-')],
            [sg.Text('t equilibration [s]', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.t_equil, key='-T_equil-')],
            [sg.Text('E begin [V]', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.e_begin, key='-E_begin-')],
            [sg.Text('E stop [V]', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.e_end, key='-E_end-')],
            [sg.Text('E step [V]', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.e_step, key='-E_step-')],
            [sg.Text('Amplitude [V]', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.amplitude, key='-Amp-')],
            [sg.Text('Frequency 1 [Hz]', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.frequencies[0], key='-Freq_1-')],
            [sg.Text('Frequency 2 [Hz]', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.frequencies[1], key='-Freq_2-')],
            [sg.Text('Frequency 3 [Hz]', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.frequencies[2], key='-Freq_3-')],
            ]
    return swv_parameters

def cyclic_format():
    print("Not supported")
    return []

def pump_format():
    pump_parameters = [
            [sg.Text('Flow rate [uL/min]', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.flow_rate, key=('-FlowRate-'))],
           
            [sg.Text('Time [s]', size=(15, 1), font='Helvetica 12'), sg.InputText(120, key='-T_dep-')],
            ]
    return pump_parameters
    

def chronoamp_format():
    chrono_parameters = [
            [sg.Text('Test Name', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.test_name, key=('-TestName-'))],
            [sg.Text('Flow rate [uL/min]', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.flow_rate, key=('-FlowRate-'))],
           
            [sg.Text('E deposition [V]', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.e_dep, key='-E_dep-')],
            [sg.Text('t equilibration [s]', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.t_equil, key='-T_equil-')],
            [sg.Text('t deposition [s]', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.t_dep, key='-T_dep-')],
            ]
    return chrono_parameters

def parameters_Format():
    V_parameters = voltammetry_gui_format()
    layout =[
            [sg.Text(system_data.test_type, size=(40, 1), justification='left', font='Helvetica 20')],
            [sg.T(SYMBOL_DOWN, enable_events=True, k='-OPEN SEC1-', text_color='white'), sg.T('Parameters', enable_events=True, text_color='white', k='-OPEN SEC1-TEXT')],
            [collapse(V_parameters, '-SEC1-')],
            [sg.Canvas(key='-CANVAS-')],
            [sg.Button('Back', size=(10, 1), font='Helvetica 14'), 
             sg.pin(sg.Button('Start', size=(10, 1), font='Helvetica 14')),
             sg.pin(sg.Button('Exit', size=(10, 1), font='Helvetica 14'))
            ],
            ]
    return layout

def Plot_GUI_Format(window):
    canvas_elem = window['-CANVAS-']
    canvas = canvas_elem.TKCanvas

    #draw the initial plot in the window
    fig = plt.figure(1)
    ax = fig.add_subplot(111)
    ax.set_xlabel('Voltage (V)')
    # plt.xlim([0,200])
    ax.set_ylabel('Current (uA)')
    fig_agg = draw_figure(canvas, fig)

    return ax, fig_agg

def draw_figure(canvas, figure, loc=(0, 0)):
    figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
    figure_canvas_agg.draw()
    figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
    return figure_canvas_agg

#allows section of GUI to be collapsed
def collapse(layout, key):
    return sg.pin(sg.Column(layout, key=key))

#Opens usb selection window
#returns pump port, pump baud rate, and potentiostat port.
def test_setting_process():
    test_setting_select = test_settings_window()
    while True:
        event, values = test_setting_select.read(timeout=10)

        if event in ('Next', None):
            system_data.pump_com = values['-PumpPort-']
            system_data.pstat_com = values['-PStatPort-']
            system_data.n_electrodes = values['-NElectrodes-']
            system_data.test_type = values['-TestType-']
            system_data.update_test_name()
            system_data.syringe_diam = values['-SyringeDiam-']
            break

    test_setting_select.close()

def parameter_window_process():
    #value for tracking the state of the collapsable window being expanded or not.
    is_expanded = True
    #boolean value allows for test to be changed.
    new_parameters = True
    window, ax, fig_agg = control_windows()
    data_folder = ""

    # Enter measurement parameters and start pumping
    while True:
        event, values = window.read(timeout=10)
        if event == sg.WIN_CLOSED or event == 'Exit':
            new_parameters = False
            break
        if event == 'Back':
            new_parameters = True
            window.close()
            break
            
        if event.startswith('-OPEN SEC1-'):
            is_expanded = not is_expanded
            window['-OPEN SEC1-'].update(SYMBOL_DOWN if is_expanded else SYMBOL_UP)
            window['-SEC1-'].update(visible=is_expanded)

        if event in ('Start', None) and system_data.test_type == 'Stop_Flow':
            print(event, values)
            system_data.test_name = values['-TestName-']
            system_data.n_measurements = values['-NMeasurements-']
            system_data.step_volume = float(values['-StepVolume-'])/1000
            system_data.flow_rate = values['-FlowRate-']
            system_data.e_cond, system_data.t_cond = float(values['-E_cond-']), float(values['-T_cond-'])
            system_data.e_dep = float(values['-E_dep-'])
            system_data.t_equil = float(values['-T_equil-'])
            system_data.e_begin, system_data.e_end, system_data.e_step = float(values['-E_begin-']), float(values['-E_end-']), float(values['-E_stop-'])
            system_data.amplitude = float(values['-Amp-'])
            system_data.frequencies =  [float(values['-Freq_1-']), float(values['-Freq_2-']), float(values['-Freq_3-'])]
            system_data.t_dep = system_data.step_volume / (system_data.flow_rate*system_data.flowrate_conversion) #s/measurement
            new_parameters = False
            break

        if event in ('Start', None) and system_data.test_type == 'Chronoamperometry':
            print(event, values)
            system_data.test_name = values['-TestName-']
            system_data.n_measurements = values['-NMeasurements-']
            system_data.step_volume = float(values['-StepVolume-'])/1000
            system_data.flow_rate = values['-FlowRate-']
            system_data.t_equil = float(values['-T_equil-'])
            system_data.e_dep = float(values['-E_dep-'])
            system_data.t_dep = float(values['-T_dep-']) #s/measurement
            new_parameters = False
            break

    if not new_parameters:
        path = os.getcwd() + '\data'
        new_folder = system_data.test_name
        data_folder = os.path.join(path, new_folder)
        if not os.path.exists(data_folder):
            os.makedirs(data_folder)
            os.makedirs(os.path.join(data_folder, 'plots'))
            os.makedirs(os.path.join(data_folder, 'csv'))
    return window, ax, fig_agg, data_folder, new_parameters

def connect_to_pump():
    # connect to pump
    pump = Pump.from_parameters(system_data)
    #pump = Pump(system_data.["pump_com"], system_data.["pump_baud"])
    pump.set_diameter(system_data.syringe_diam) # Fixed syringe diameter
    pump.set_rate(system_data.flow_rate,'uL/min')
    system_data.infusion_volume = system_data.step_volume*system_data.n_measurements
    pump.set_volume(system_data.infusion_volume)
    pump.reset_acc() # reset accumulated volume to zero
    return pump

def connect_to_pstat():
   
    #connect to emstat
    return Emstat.from_parameters(system_data)
    #return Emstat(system_data.["pstat_com"], system_data.["e_cond"], system_data.["t_cond"], system_data.["e_dep"], system_data.["t_dep"], system_data.["t_equil"], system_data.["e_begin"], system_data.["e_end"], system_data.["e_step"], system_data.["amplitude"], system_data.["frequency"])

def conduct_measurements(pstat, pump, window, ax, fig_agg, data_folder):
    #data_queue = queue.Queue()
    #thread = threading.Thread(target=take_measurement(data_queue, pump, pstat))
    #thread.start()
    # for measure in range(system_data.n_measurements):
    #     data_queue.put(system_data)
    #system_data.write_swv(np.zeros(100), np.zeros(100),np.zeros(100),np.zeros(100))
    # toggle flow on/off while measuring pstat

    if system_data.test_type == 'Stop-Flow':
            #TODO Fill in proper proto 
        stop_flow_measurements(pstat, pump, window, ax, fig_agg, data_folder)     
    elif system_data.test_type == 'Cyclic Voltametry':
        cyclic_measurements(pstat, pump, window, ax, fig_agg, data_folder)

    elif system_data.test_type == 'Pump':
        pump_fluid(pump, window)
    elif system_data.test_type == 'Chronoamperometry':
        chrono_measurements(pstat, pump, window, ax, fig_agg, data_folder)
             

def cyclic_measurements(pstat, pump, window, ax, fig_agg, data_folder):
        pump.infuse()
        pstat.deposition(system_data.t_dep, system_data.e_dep, system_data.e_dep, [0,1])
        pump.stop()
        return

def pump_fluid(pump, window):
        pump.infuse()
        pump.stop()
        return

def chrono_measurements(pstat, pump, window, ax, fig_agg, data_folder):
        return
        
def stop_flow_measurements(pstat, pump, window, ax, fig_agg, data_folder):
      while True:
        # start flow, deposit norfentynal
        pump.infuse()
        pstat.deposition(system_data.t_dep, system_data.e_dep, system_data.e_dep, [0,1])
        pump.stop()
        pstat.sweepSWV()
        system_data.measurements += 1
        plt.figure(1)
        ax.grid() # draw the grid
        ax.plot(system_data.potential_swv,system_data.current_swv) #plot new pstat readings

        df = pd.DataFrame({'Potential':system_data.potential_swv, 'Current':system_data.current_swv})
        df.to_csv(data_folder + '/csv/' + str(system_data.measurements) + '.csv')
        ax.set_xlabel('Potential (V)')
        ax.set_ylabel('Current (uA)')
        fig_agg.draw()
        fig2 = plt.figure(2)
        plt.clf()
        plt.plot(system_data.potential_swv,system_data.current_swv)
        plt.xlabel('Potential (V)')
        plt.ylabel('Current (uA)')
        plt.savefig(data_folder + '/plots/' + str(system_data.measurements) + '.png')

        window.read(10)

        # Stop program when we've completed all measurements
        if system_data.measurements >= system_data.n_measurements:
            #thread.join()
            pump.stop()
            pump.close()
            pstat.close()
            break

#threded function attempt
def take_measurement(data_queue, pump, pstat):
    while True:
        data = data_queue.get()
        #do something
        pump.infuse()
        pstat.deposition(data.t_dep)
        pump.stop()
        data.write_IV(pstat.sweepSWV())
        data.measurements += 1
        data_queue.task_done()

"""Main process for GUI windows. Process occurs in the following steps:

1). The USB port selection window appears allowing the user to select the correct usb connections
    for the potentiostat and the syringe pump.
2). The parameter setting window appears allowing for a test to be named
    and measurement parameters to be selected.
3). The syringe pump is connected via serial.
4). The potentiostat is connected via serial.
5). The square wave voltametry is conducted and data is saved to csv file.

"""
def main():
    #Step 1: USB ports are selected by user input.
    new_parameters = True
    while new_parameters == True:
        test_setting_process()
    #Step 2: System Parameters are set by user input.
        window, ax, fig_agg, data_folder, new_parameters = parameter_window_process()
    #Step 3:
    pump = connect_to_pump()
    #Step 4:
    pstat = connect_to_pstat()
    #Step 5:
    conduct_measurements(pstat, pump, window, ax, fig_agg, data_folder)

   #Keeps measurement window open until closed
    while True:
        event, values = window.read(timeout=10)
        if event == sg.WIN_CLOSED or event == 'Exit':
            pump.stop()
            pump.close()
            pstat.close()
            break

if __name__ == '__main__':
	main()
