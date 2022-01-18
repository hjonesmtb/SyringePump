import time

import PySimpleGUI as sg
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, FigureCanvasAgg
from matplotlib.figure import Figure
import numpy as np

from syringe_pump.pump_22 import Pump
from emstat.emstat_communication import Emstat




def draw_figure(canvas, figure, loc=(0, 0)):
    figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
    figure_canvas_agg.draw()
    figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
    return figure_canvas_agg

#boiler plate code for start page. Choose COM ports
#TODO: define new variable emstat_com
def com_windows():
    layout = [
			     [sg.Text('Valve Control', size=(40, 1),
					justification='center', font='Helvetica 20')],
       			 [sg.Text('Syringe Pump COM', size=(15, 1), font='Helvetica 12'), sg.InputText('12')],
       			 [sg.Text('Syringe Pump Baudrate', size=(15, 1), font='Helvetica 12'), sg.InputText('1200')],
       			 [sg.Text('PStat COM', size=(15, 1), font='Helvetica 12'), sg.InputText('6')],

		         [sg.Canvas(key='controls_cv')],
                 [sg.Canvas(size=(650, 30), key='-CANVAS-')],

		        [sg.Button('Submit', size=(10, 1), pad=((280, 0), 3), font='Helvetica 14')]
		        ]

    # create the form and show it without the plot
    window = sg.Window('Start Screen',
                layout, finalize=True)

    canvas_elem = window['-CANVAS-']
    canvas = canvas_elem.TKCanvas

    return window

#boiler plate code for entering parameters
def control_windows():
    layout = [
			     [sg.Text('Valve Control', size=(40, 1),
					justification='center', font='Helvetica 20')],

				 [sg.Text('Flow rate [uL/min]', size=(15, 1), font='Helvetica 12'), sg.InputText('1000')],
				 [sg.Text('Infusion volume [mL]', size=(15, 1), font='Helvetica 12'), sg.InputText('1')],
				 [sg.Text('pulse period [ms]', size=(15, 1), font='Helvetica 12'), sg.InputText('2000')],

				 [sg.Button('Start', size=(10, 1), pad=((280, 0), 3), font='Helvetica 14')],

		         [sg.Canvas(key='controls_cv')],
                 [sg.Canvas(size=(650, 30), key='-CANVAS-')],

		        [sg.Button('Exit', size=(10, 1), pad=((280, 0), 3), font='Helvetica 14')]
		      ]

    window = sg.Window('Start Screen',
                layout, finalize=True)

    canvas_elem = window['-CANVAS-']
    canvas = canvas_elem.TKCanvas

       # draw the initial plot in the window
    fig = Figure()
    ax = fig.add_subplot(111)
    fig_agg = draw_figure(canvas, fig)

    return window, ax, fig_agg

def read_pstat(emstat, parameters):
	swv_data = emstat.run_swv()
	return swv_data

def pstat_deposition(emstat, deposition_potential):
    emstat.set_potential(deposition_potential)

def main():

	COM_select = com_windows()
	while True:
		event, values = COM_select.read(timeout=10)

		if event in ('Submit', None):
			pump_com = int(values[0])
			pump_baud = int(values[1])
			pstat_com = int(values[2])
			break

	pump = Pump(pump_com, pump_baud)
    emstat = Emstat(emstat_com)

	# TODO: connect to pstat using pstat_com

	COM_select.close()

	window, ax, fig_agg = control_windows()
	flow_rate, volume, period = 0,0,0
	# Enter measurement parameters and start pumping
	while True:
		event, values = window.read(timeout=10)

		if event in ('Start', None):

			flow_rate = int(values[0])
			volume = int(values[1])
			period = int(values[2])

			pump.set_diameter(10) # Fixed syringe diameter
			pump.set_rate(flow_rate,'uL/min')
			pump.set_volume(volume)

			pump.reset_acc() # reset accumulated volume to zero

			break

	pump_on = True  #True when pumping, False when stopped
	counter = 0

	IV = [np.zeros(100), np.zeros(100)]

	# toggle flow on/off at a fixed period
	while True:

		if pump_on:
            pstat_deposition(deposition_potential) #TODO define a user inputted value called deposition_potential
			pump.infuse()	# Run flow for 5s between DPV sweeps. Fentanyl --> Norfentanyl
			window.read(period)
		else:
			pump.stop() 	# While flow is stopped, store pstat data in csv
			IV = read_pstat(emstat, parameters) #TODO make an array called parameters [t equilibration, e begin, e end, e step, amplitude]

		pump_on = not pump_on

		ax.grid() # draw the grid
		ax.plot(IV[0],IV[1]) #plot new pstat readings
		ax.set_xlabel('Voltage')
		ax.set_ylabel('Current')
		fig_agg.draw()

		# Stop program when we've pumped all the sample
		if abs(pump.check_volume() - volume) < 0.01:
			pump.stop()
			pump.close()
            emstat.close()
			break

	window.close()

if __name__ == '__main__':
	main()
