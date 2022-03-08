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

from syringe_pump.pump_22 import Pump
from emstat.emstat_communication import Emstat


SYMBOL_UP =    '▲'
SYMBOL_DOWN =  '▼'

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
            [sg.Text('Syringe Pump Port', size=(20, 1), font='Helvetica 12')],
            [sg.Combo(usbs, key=("-usbs-"))],
            [sg.Combo(port_name, key=('-PumpPort-'))],
            [sg.Text('Syringe Pump Baudrate', size=(20, 1), font='Helvetica 12'), sg.InputText('1200', key='-baud-')],
            [sg.Text('Pstat Port', size=(20, 1), font='Helvetica 12')],
            [sg.Combo(port_name, key=("-PStatPort-"))],
            [sg.Canvas(key='controls_cv')],
            [sg.Canvas(size=(650, 30), key='-CANVAS-')],
            [sg.Button('Submit', size=(10, 1), pad=((280, 0), 3), font='Helvetica 14')]
            ]
    return layout

#boiler plate code for entering parameters
def control_windows():
    SWV_parameters = voltammetry_gui_format()
    layout = Test_GUI_Format(SWV_parameters)
    window = sg.Window('Start Screen',layout, finalize=True, resizable=True)
    ax, fig_agg = Plot_GUI_Format(window)
   
    return window, ax, fig_agg

def voltammetry_gui_format():
    swv_parameters = [
            [sg.Text('SWV Settings', size=(40, 1), justification='center', font='Helvetica 20')],
            [sg.Text('E condition [V]', size=(15, 1), font='Helvetica 12'), sg.InputText('0')],
            [sg.Text('t condition [s]', size=(15, 1), font='Helvetica 12'), sg.InputText('0')],
            [sg.Text('E deposition [V]', size=(15, 1), font='Helvetica 12'), sg.InputText('0.8')],
            [sg.Text('t equilibration [s]', size=(15, 1), font='Helvetica 12'), sg.InputText('0')],
            [sg.Text('E begin [V]', size=(15, 1), font='Helvetica 12'), sg.InputText('-0.4')],
            [sg.Text('E stop [V]', size=(15, 1), font='Helvetica 12'), sg.InputText('0.4')],
            [sg.Text('E step [V]', size=(15, 1), font='Helvetica 12'), sg.InputText('0.005')],
            [sg.Text('Amplitude [V]', size=(15, 1), font='Helvetica 12'), sg.InputText('0.01')],
            [sg.Text('Frequency [Hz]', size=(15, 1), font='Helvetica 12'), sg.InputText('7')]
            ]
    return swv_parameters

def Test_GUI_Format(SWV_parameters):
    dt = datetime.now().replace(second=0, microsecond=0)
    layout =[
            [sg.Text('Test Name', size=(15, 1), font='Helvetica 12'), sg.InputText('Test_'+dt)],
            [sg.Text('Pump Settings', size=(40, 1),justification='center', font='Helvetica 20')],
            [sg.Text('Flow rate [uL/min]', size=(15, 1), font='Helvetica 12'), sg.InputText('1000')],
            [sg.Text('Infusion volume [mL]', size=(15, 1), font='Helvetica 12'), sg.InputText('1')],
            [sg.Text('# Measurements', size=(15, 1), font='Helvetica 12'), sg.InputText('1')],
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
def main():
    opened1 = True
    COM_select = com_window()
    while True:
        event, values = COM_select.read(timeout=10)

        if event in ('Submit', None):
            pump_com = values['-PumpPort-']
            pump_baud = int(values['-baud-'])
            pstat_com = values['-PStatPort-']
            break

    COM_select.close()

    window, ax, fig_agg = control_windows()

    # Measurement parameters
    flow_rate, volume = 0,0
    e_cond, e_dep, e_begin, e_end, e_step = 0,0,0,0,0
    t_cond, t_dep, t_equil = 0,0,0
    amplitude, frequency = 0, 0

    # Enter measurement parameters and start pumping
    while True:
        event, values = window.read(timeout=10)
        if event == sg.WIN_CLOSED or event == 'Exit':
            break

        if event.startswith('-OPEN SEC1-'):
            opened1 = not opened1
            window['-OPEN SEC1-'].update(SYMBOL_DOWN if opened1 else SYMBOL_UP)
            window['-SEC1-'].update(visible=opened1)

        if event in ('Start', None):
            print(event, values)
            test_name = values[0]
            flow_rate, volume, nmeasurements = int(values[1]), int(values[2]), int(values[3])
            e_cond, t_cond = float(values[4]), float(values[5])
            e_dep = float(values[6])
            t_equil = float(values[7])
            e_begin, e_end, e_step = float(values[8]), float(values[9]), float(values[10])
            amplitude, frequency = float(values[11]), float(values[12])
            break

    path = os.getcwd() + '\data'
    new_folder = test_name + '_' + datetime.now().strftime("%Y_%m_%d_%I_%M_%S_%p")
    data_folder = os.path.join(path, new_folder)
    if not os.path.exists(data_folder):
        os.makedirs(data_folder)
        os.makedirs(os.path.join(data_folder, 'plots'))
        os.makedirs(os.path.join(data_folder, 'csv'))
    # connect to pump
    pump = Pump(pump_com, pump_baud)

    pump.set_diameter(10) # Fixed syringe diameter
    pump.set_rate(flow_rate,'uL/min')
    pump.set_volume(volume)
    pump.reset_acc() # reset accumulated volume to zero

    IV = [np.zeros(100), np.zeros(100)]
    step_volume = volume / nmeasurements
    t_dep = step_volume / (flow_rate / 1000 / 60)
    # connect to emstat; the parameters could be a list or dictionary
    pstat = Emstat(pstat_com, e_cond, t_cond, e_dep, t_dep, t_equil, e_begin, e_end, e_step, amplitude, frequency)
    measurement = 0

	# toggle flow on/off while measuring pstat

    while True:
        # start flow, deposit norfentynal
        pump.infuse()
        pstat.deposition(t_dep) # this takes ~10-20 secs, during which GUI is bricked
        #
        # #stop flow, run SWV sweep
        pump.stop()
        IV = pstat.sweepSWV() # this takes ~10-20 secs, during which GUI is bricked
        measurement += 1 #keeps track of measurement number
        plt.figure(1)
        ax.grid() # draw the grid
        ax.plot(IV[0],IV[1]) #plot new pstat readings

        df = pd.DataFrame({'Potential':IV[0], 'Current':IV[1]})
        df.to_csv(data_folder + '/csv/' + str(measurement) + '.csv')
        ax.set_xlabel('Potential (V)')
        ax.set_ylabel('Current (uA)')
        fig_agg.draw()
        fig2 = plt.figure(2)
        plt.clf()
        plt.plot(IV[0],IV[1])
        plt.xlabel('Potential (V)')
        plt.ylabel('Current (uA)')
        plt.savefig(data_folder + '/plots/' + str(measurement) + '.png')

        window.read(10)

        # Stop program when we've completed all measurements
        if measurement >= nmeasurements:
            pump.stop()
            pump.close()
            pstat.close()
            break


    while True: #Keeps window open until closed
        event, values = window.read(timeout=10)
        if event == sg.WIN_CLOSED or event == 'Exit':
            break

if __name__ == '__main__':
	main()
