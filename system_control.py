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
            [sg.Button('Next', size=(15, 1), pad=((280, 0), 3), font='Helvetica 14')],
            ]
    return layout

#boiler plate code for entering parameters
def control_windows():
    layout = parameters_Format()
    window = sg.Window('Start Screen', layout, finalize=True, resizable=True)
    system_data.Initialize_Plots(window)
    # system_data.plot_data()
    window.Maximize()
    return window

def voltammetry_gui_format():
    layout = []
    if(system_data.test_type == 'Stop-Flow'):
        layout = swv_format()
    if(system_data.test_type == 'Chronoamperometry'):
        layout = chronoamp_format()
    if(system_data.test_type == 'Cyclic Voltammetry'):
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
    col1 =[
            [sg.Text(system_data.test_type, size=(20, 1), justification='left', font='Helvetica 20')],
            [sg.T(SYMBOL_DOWN, enable_events=True, k='-OPEN SEC1-', text_color='white'), sg.T('Parameters', enable_events=True, text_color='white', k='-OPEN SEC1-TEXT')],
            [collapse(V_parameters, '-SEC1-')],
            [sg.Button('Back', size=(15, 1), font='Helvetica 14'),
             sg.pin(sg.Button('Start', size=(15, 1), font='Helvetica 14', k = '-START-')),
             sg.pin(sg.Button('Stop', size=(15, 1), font='Helvetica 14'))],
            [sg.Text(key='-TEST_STATUS-', size=(30, 1), font='Helvetica 20')],
            [sg.Text(key='-TEST_TIME-', size=(30, 1), font='Helvetica 20')
            ],
            ]
    col2 =[
            [sg.Canvas(key='-PLOT-')],
            [sg.Text(key='-MEASUREMENT-', size=(30, 1), font='Helvetica 20')],
            [sg.Text(key='-TIME-', size=(30, 1), font='Helvetica 20')
            ],
            ]
    layout = [[sg.Column(col1, element_justification='l' ), sg.Column(col2, element_justification='c')]]
    return layout

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

    #GUI Window is created
    window = control_windows()

    # Enter measurement parameters and start pumping
    while True:
        event, values = window.read(10)
        if event == sg.WIN_CLOSED:
            new_parameters = True
            break
        if event == 'Back':
            new_parameters = True
            window.close()
            break
        window['-TEST_STATUS-'].update('Press Start to Start Pumping')

        if event.startswith('-OPEN SEC1-'):
            is_expanded = not is_expanded
            window['-OPEN SEC1-'].update(SYMBOL_DOWN if is_expanded else SYMBOL_UP)
            window['-SEC1-'].update(visible=is_expanded)

        if event in ('-START-', None):
            system_data.start_time = time.time()
            if system_data.test_type == 'Stop-Flow':
                print(event, values)
                system_data.test_name = values['-TestName-']
                system_data.n_measurements = float(values['-NMeasurements-'])
                system_data.step_volume = float(values['-StepVolume-'])/1000
                system_data.flow_rate = float(values['-FlowRate-'])
                system_data.e_cond, system_data.t_cond = float(values['-E_cond-']), float(values['-T_cond-'])
                system_data.e_dep = float(values['-E_dep-'])
                system_data.t_equil = float(values['-T_equil-'])
                system_data.e_begin, system_data.e_end, system_data.e_step = float(values['-E_begin-']), float(values['-E_end-']), float(values['-E_step-'])
                system_data.amplitude = float(values['-Amp-'])
                system_data.frequencies =  [float(values['-Freq_1-']), float(values['-Freq_2-']), float(values['-Freq_3-'])]
                system_data.t_dep = float(system_data.step_volume) / (float(system_data.flow_rate)*system_data.flowrate_conversion) #s/measurement
                new_parameters = False
                break

            if system_data.test_type == 'Chronoamperometry':
                print(event, values)
                system_data.test_name = values['-TestName-']
                system_data.flow_rate = values['-FlowRate-']
                system_data.t_equil = float(values['-T_equil-'])
                system_data.e_dep = float(values['-E_dep-'])
                system_data.t_dep = float(values['-T_dep-']) #s/measurement
                new_parameters = False
                break

    return window, new_parameters

def connect_to_pump():
    # connect to pump
    pump = Pump.from_parameters(system_data)
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

def conduct_measurements(pstat, pump, window):
    if system_data.test_type == 'Stop-Flow':
        stop_flow_measurements(pstat, pump, window)
    elif system_data.test_type == 'Cyclic voltammetry':
        cyclic_measurements(pstat, pump, window)
    elif system_data.test_type == 'Pump':
        pump_fluid(pump, window)
    elif system_data.test_type == 'Chronoamperometry':
        chrono_measurements(pstat, pump, window)

def stop_flow_measurements(pstat, pump, window):
    #start pump, output current
    pump.infuse()
    window['-TEST_STATUS-'].update('Initial flow-through phase. When system is ready (~60s), hit load sample to start the 5 second timer to load sample.')
    window['-START-'].update('Load Sample')

    #Step 1:Start pumping fluid until the user chooses to turn the valve
    window.perform_long_operation(lambda :
                                          pstat.deposition(self.initial_pump_time, system_data.e_dep, system_data.e_dep, [0,1]),
                                          '-INITIAL_DONE-') #Depose for 4 minutes and plot data. Wait until user hits load sample.
    while True: #Loop to start pumping and get user to turn valve
        window['-TEST_TIME-'].update('Pumping time: {}'.format(round(time.time()-system_data.start_time)))
        system_data.plot_data()
        if event in ('-START-', None):
            system_data.stop_pstat = True #Send flag to pstat to stop measurement

            #counts down for user to turn valve
            countdown_start = time.time()
            while time.time() - countdown_start < 5:
                window['-TEST_STATUS-'].update('Load Sample in {} seconds'.format(5 - round(time.time() - countdown_start)))
                window.read(10)
            window['-TEST_STATUS-'].update('Turn Sample Valve')
            window.read(10)
            system_data.inject_time = time.time() - start_time
            system_data.valve_turned = True
            break
        if event in ('INITIAL_DONE'):
            window['-TEST_STATUS-'].update('Pump flowed for {} minutes, please restart'.format(system_data.initial_pump_time / 60))
            window.read(10)
            restart(pstat, pump, window)
        check_for_stop(pstat, pump, window)
        window.read(10)

    system_data.stop_pstat = False #Unsend flag to pstat to stop measurement

    #Step 2: Once valve is turned, cycle through deposition and swv measurements
    while True:
        system_data.measurements += 1
        window['-TEST_STATUS-'].update('Squarewave Measurement Running')

        #Step 2a: Deposition
        pump.infuse()
        system_data.measurement_time = time.time()
        window.perform_long_operation(lambda :
                                              pstat.deposition(system_data.t_dep, system_data.e_dep, system_data.e_dep, [0,1]),
                                              '-DEPOSITION_DONE-') #Deposition.
        while True: #Loop for deposition
            system_data.plot_data()
            window['-TEST_TIME-'].update('Test time since valve turned: {}'.format(round(time.time()-system_data.inject_time)))
            window['-MEASUREMENT-'].update('Deposition, measurement #{}'.format(system_data.measurements))
            window['-TIME-'].update('Measurement Time: {}'.format(round(time.time()-system_data.measurement_time)))
            if event in ('-DEPOSITION_DONE-', None):
                pump.stop()
                break
            check_for_stop(pstat, pump, window)
            window.read(10)

        #Step 2b: SWV
        window.perform_long_operation(lambda :
                                              pstat.sweepSWV(),
                                              '-SWV_DONE-') #SWV.
        while True: #Loop for swv
            system_data.plot_data()
            window['-TEST_TIME-'].update('Test time since valve turned: {}'.format(round(time.time()-system_data.inject_time)))
            window['-MEASUREMENT-'].update('SWV, measurement #{}'.format(system_data.measurements))
            window['-TIME-'].update('Measurement Time: {}'.format(round(time.time()-system_data.measurement_time)))

            if event in ('-SWV_DONE-', None):
                break
            check_for_stop(pstat, pump, window)
            window.read(10)

        check_for_stop(pstat, pump, window)
        window.read(10)

        # Once measurements are complete, keep pumping
        if system_data.measurements >= system_data.n_measurements:
            system_data.time_end = time.time()
            break
    #TODOStep 3: Once measurement is complete, keep pummping
    # window['-TEST_STATUS-'].update('Pump ')
    restart(pstat, pump, window)

def cyclic_measurements(pstat, pump, window):
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

'''Checks if the Stop button has been pressed. If so, returns to main GUI window'''
def check_for_stop(pstat, pump, window):
    if event in ('Stop', none):
        system_data.stop_pstat = True
        pump.stop()
        restart(pstat, pump, window)
    return

'''Starts another measurement once user has stopped'''
def restart(pstat, pump, window):
    new_parameters = True:
    while new_parameters:
        #Step 2: System Parameters are set by user input.
        window, new_parameters = parameter_window_process()
        if new_parameters:
            test_setting_process()
    conduct_measurements(pstat, pump, window)


"""Main process for GUI windows. Process occurs in the following steps:

1). The USB port selection window appears allowing the user to select the correct usb connections
    for the potentiostat and the syringe pump.
2). The parameter setting window appears allowing for a test to be named
    and measurement parameters to be selected.
3). The syringe pump is connected via serial.
4). The potentiostat is connected via serial.
5). The square wave voltammetry is conducted and data is saved to csv file.

"""
def main():
    #Step 1: USB ports are selected by user input.
    new_parameters = True
    while new_parameters == True:
        test_setting_process()
        #Step 2: System Parameters are set by user input.
        window, new_parameters = parameter_window_process()
    #Step 3:
    pump = connect_to_pump()
    #Step 4:
    pstat = connect_to_pstat()
    #Step 5:
    conduct_measurements(pstat, pump, window)

   #Keeps measurement window open until closed
    while True:
        event, values = window.read(timeout=10)
        if event == sg.WIN_CLOSED:
            pump.stop()
            pump.close()
            pstat.close()
            break

if __name__ == '__main__':
	main()
