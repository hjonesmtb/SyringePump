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
"""
    Helper function that creates a Column that can be later made hidden, thus appearing "collapsed"
    :param layout: The layout for the section
    :param key: Key used to make this seciton visible / invisible
    :return: A pinned column that can be placed directly into your layout
    :rtype: sg.pin
    """

#boiler plate code for USB port selection page.
def com_window():

    #creates a list of the names of all current usb devices.
    usbs = list_ports.comports()
    port_name = []
    for usb in usbs:
        port_name.append(usb.name)

    layout = usb_gui_format(usbs, port_name)

    # create the form and show it without the plot
    window = sg.Window('Select USB Ports', layout, finalize=True, resizable=True)
    return window

def usb_gui_format(usbs, port_name):
    layout =[
            [sg.Text('Pump Control', size=(40, 1), justification='center', font='Helvetica 20')],
            [sg.Text('Syringe Pump Port', size=(20, 1), font='Helvetica 12'), sg.Combo(port_name, size=(10,1),key=('-PumpPort-'))],
            [sg.Text('Pstat Port', size=(20, 1), font='Helvetica 12'), sg.Combo(port_name, size=(10,1),key=("-PStatPort-"))],
            [sg.Text('List of Detected Ports', size=(20, 1), font='Helvetica 12'), sg.Combo(usbs, key=("-usbs-"))],
            [sg.Canvas(key='controls_cv')],
            [sg.Canvas(size=(650, 30), key='-CANVAS-')],
            [sg.Button('Submit', size=(10, 1), pad=((280, 0), 3), font='Helvetica 14')],
            ]
    return layout

#boiler plate code for entering parameters
def control_windows():
    SWV_parameters = voltammetry_gui_format()
    layout = Test_GUI_Format(SWV_parameters)
    window = sg.Window('Start Screen', layout, finalize=True, resizable=True)
    ax, fig_agg = Plot_GUI_Format(window)

    return window, ax, fig_agg

def voltammetry_gui_format():
    swv_parameters = [
            [sg.Text('Square Wave Voltammetry Settings', size=(40, 1), justification='center', font='Helvetica 20')],
            [sg.Text('E condition [V]', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.e_cond)],
            [sg.Text('t condition [s]', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.t_cond)],
            [sg.Text('E deposition [V]', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.e_dep)],
            [sg.Text('t equilibration [s]', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.t_equil)],
            [sg.Text('E begin [V]', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.e_begin)],
            [sg.Text('E stop [V]', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.e_end)],
            [sg.Text('E step [V]', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.e_end)],
            [sg.Text('Amplitude [V]', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.amplitude)],
            [sg.Text('Frequency [Hz]', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.frequency)]
            ]
    return swv_parameters

def Test_GUI_Format(SWV_parameters):
    layout =[
            [sg.Text('Test Name', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.test_name)],
            [sg.Text('Pump Settings', size=(40, 1),justification='center', font='Helvetica 20')],
            [sg.Text('Syringe Diammeter [mm]', size=(15,1), font='Helvetica 12'), sg.InputText(system_data.syringe_diam)],
            [sg.Text('Flow rate [uL/min]', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.flow_rate)],
            [sg.Text('Infusion volume [mL]', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.volume)],
            [sg.Text('# Measurements', size=(15, 1), font='Helvetica 12'), sg.InputText(system_data.n_measurements)],
            [sg.T(SYMBOL_DOWN, enable_events=True, k='-OPEN SEC1-', text_color='white'), sg.T('SWV parameters', enable_events=True, text_color='white', k='-OPEN SEC1-TEXT')],
            [collapse(SWV_parameters, '-SEC1-')],
            [sg.Button('Start', size=(10, 1), pad=((280, 0), 3), font='Helvetica 14')],
            [sg.Canvas(key='controls_cv')],
            [sg.Canvas(size=(650, 30), key='-CANVAS-')],
            [sg.Button('Exit', size=(10, 1), pad=((280, 0), 3), font='Helvetica 14')]
            ]
    return layout

def Plot_GUI_Format(window):
    canvas_elem = window['-CANVAS-']
    canvas = canvas_elem.TKCanvas

    #draw the initial plot in the window
    fig = plt.figure(1)
    ax = fig.add_subplot(111)
    ax.set_xlabel('Potential (V)')
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
def com_window_process():
    COM_select = com_window()
    while True:
        event, values = COM_select.read(timeout=10)

        if event in ('Submit', None):
            system_data.pump_com = values['-PumpPort-']
            system_data.pstat_com = values['-PStatPort-']
            break

    COM_select.close()

def parameter_window_process():
    #value for tracking the state of the collapsable window being expanded or not.
    is_expanded = True
    window, ax, fig_agg = control_windows()

    # Enter measurement parameters and start pumping
    while True:
        event, values = window.read(timeout=10)
        if event == sg.WIN_CLOSED or event == 'Exit':
            break

        if event.startswith('-OPEN SEC1-'):
            is_expanded = not is_expanded
            window['-OPEN SEC1-'].update(SYMBOL_DOWN if is_expanded else SYMBOL_UP)
            window['-SEC1-'].update(visible=is_expanded)

        if event in ('Start', None):
            print(event, values)
            system_data.test_name = values[0]
            system_data.flow_rate,system_data.syringe_diam, system_data.volume, system_data.n_measurements = float(values[1]), float(values[2]), float(values[3]), float(values[4])
            system_data.e_cond, system_data.t_cond = float(values[5]), float(values[6])
            system_data.e_dep = float(values[7])
            system_data.t_equil = float(values[8])
            system_data.e_begin, system_data.e_end, system_data.e_step = float(values[9]), float(values[10]), float(values[11])
            system_data.amplitude, system_data.frequency = float(values[12]), float(values[13])
            break

    path = os.getcwd() + '\data'
    new_folder = system_data.test_name
    data_folder = os.path.join(path, new_folder)
    if not os.path.exists(data_folder):
        os.makedirs(data_folder)
        os.makedirs(os.path.join(data_folder, 'plots'))
        os.makedirs(os.path.join(data_folder, 'csv'))
    return window, ax, fig_agg, data_folder

def connect_to_pump():
    # connect to pump
    pump = Pump.from_parameters(system_data)
    #pump = Pump(system_data.["pump_com"], system_data.["pump_baud"])

    pump.set_diameter(system_data.syringe_diam) # Fixed syringe diameter
    pump.set_rate(system_data.flow_rate,'uL/min')
    pump.set_volume(system_data.volume)
    pump.reset_acc() # reset accumulated volume to zero
    return pump
def connect_to_pstat():
   
   #need to compute deposition time from inputted values.
    system_data.step_volume = system_data.volume / system_data.n_measurements
    system_data.t_dep = system_data.step_volume / (system_data.flow_rate*system_data.flowrate_conversion) #s/measurement
    #connect to emstat
    return Emstat.from_parameters(system_data)
    #return Emstat(system_data.["pstat_com"], system_data.["e_cond"], system_data.["t_cond"], system_data.["e_dep"], system_data.["t_dep"], system_data.["t_equil"], system_data.["e_begin"], system_data.["e_end"], system_data.["e_step"], system_data.["amplitude"], system_data.["frequency"])

def conduct_measurements(pstat, pump, window, ax, fig_agg, data_folder):
    #data_queue = queue.Queue()
    #thread = threading.Thread(target=take_measurement(data_queue, pump, pstat))
    #thread.start()
    # for measure in range(system_data.n_measurements):
    #     data_queue.put(system_data)
    system_data.write_IV(np.zeros(100), np.zeros(100),np.zeros(100),np.zeros(100))
    # toggle flow on/off while measuring pstat
    while True:
        # start flow, deposit norfentynal
        
        pump.infuse()
        pstat.deposition(system_data.t_dep)
        pump.stop()
        system_data.write_IV(pstat.sweepSWV())
        system_data.measurements += 1
        plt.figure(1)
        ax.grid() # draw the grid
        ax.plot(system_data.potential,system_data.current) #plot new pstat readings

        df = pd.DataFrame({'Potential':system_data.potential, 'Current':system_data.current})
        df.to_csv(data_folder + '/csv/' + str(system_data.measurements) + '.csv')
        ax.set_xlabel('Potential (V)')
        ax.set_ylabel('Current (uA)')
        fig_agg.draw()
        fig2 = plt.figure(2)
        plt.clf()
        plt.plot(system_data.potential,system_data.current)
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
    com_window_process()
    #Step 2: System Parameters are set by user input.
    window, ax, fig_agg, data_folder = parameter_window_process()
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
            break

if __name__ == '__main__':
	main()
