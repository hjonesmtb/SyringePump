import time

import PySimpleGUI as sg
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, FigureCanvasAgg
from matplotlib.figure import Figure
import numpy as np

from syringe_pump.pump_22 import Pump

def draw_figure(canvas, figure, loc=(0, 0)):
    figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
    figure_canvas_agg.draw()
    figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
    return figure_canvas_agg

#boiler plate code for start page. Choose COM ports
def com_windows():
    layout = [
			     [sg.Text('Pump Control', size=(40, 1),
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
			     [sg.Text('Pump Control', size=(40, 1),
					justification='center', font='Helvetica 20')],

				 [sg.Text('Flow rate [uL/min]', size=(15, 1), font='Helvetica 12'), sg.InputText('1000')],
				 [sg.Text('Infusion volume [mL]', size=(15, 1), font='Helvetica 12'), sg.InputText('1')],

			     [sg.Text('SWV Settings', size=(40, 1),
					justification='center', font='Helvetica 20')],

				 [sg.Text('E condition [V]', size=(15, 1), font='Helvetica 12'), sg.InputText('0')],
				 [sg.Text('t condition [s]', size=(15, 1), font='Helvetica 12'), sg.InputText('0')],
				 [sg.Text('E deposition [V]', size=(15, 1), font='Helvetica 12'), sg.InputText('0.8')],
				 [sg.Text('t deposition [s]', size=(15, 1), font='Helvetica 12'), sg.InputText('60')],

				[sg.Text('t equilibration [s]', size=(15, 1), font='Helvetica 12'), sg.InputText('0')],
				[sg.Text('E begin [V]', size=(15, 1), font='Helvetica 12'), sg.InputText('-0.4')],
				[sg.Text('E stop [V]', size=(15, 1), font='Helvetica 12'), sg.InputText('0.4')],
				[sg.Text('E step [V]', size=(15, 1), font='Helvetica 12'), sg.InputText('0.005')],
				[sg.Text('Amplitude [V]', size=(15, 1), font='Helvetica 12'), sg.InputText('0.01')],
				[sg.Text('Frequency [Hz]', size=(15, 1), font='Helvetica 12'), sg.InputText('7')],

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

def main():

	COM_select = com_windows()
	while True:
		event, values = COM_select.read(timeout=10)

		if event in ('Submit', None):
			pump_com = int(values[0])
			pump_baud = int(values[1])
			pstat_com = int(values[2])
			break

	# TODO: connect to pstat using pstat_com 

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

		if event in ('Start', None):

			flow_rate, volume = int(values[0]), int(values[1])

			e_cond, t_cond = float(values[2]), float(values[3])
			e_dep, t_dep = float(values[4]), int(values[5])
			t_equil = float(values[6])
			e_begin, e_end, e_step = float(values[7]), float(values[8]), float(values[9])
			amplitude, frequency = float(values[10]), float(values[11])
			break

	# connect to pump
	pump = Pump(pump_com, pump_baud)

	pump.set_diameter(10) # Fixed syringe diameter
	pump.set_rate(flow_rate,'uL/min')
	pump.set_volume(volume)
	pump.reset_acc() # reset accumulated volume to zero

	# connect to emstat; the parameters could be a list or dictionary
	pstat = Emstat(pstat_com, e_cond, t_cond, e_dep, t_dep, t_equil, e_begin, e_end, e_step, amplitude, frequency)

	IV = [np.zeros(100), np.zeros(100)]

	# toggle flow on/off while measuring pstat
	while True:

		# start flow, deposit norfentynal 
		pump.infuse()
		pstat.deposition() # this takes ~10-20 secs, during which GUI is bricked

		# stop flow, run SWV sweep
		pump.stop()
		IV = pstat.sweepSWV() # this takes ~10-20 secs, during which GUI is bricked

		ax.grid() # draw the grid
		ax.plot(IV[0],IV[1]) #plot new pstat readings
		ax.set_xlabel('Voltage')
		ax.set_ylabel('Current')
		fig_agg.draw()

		# Stop program when we've pumped all the sample
		if abs(pump.check_volume() - volume) < 0.01:
			pump.stop()
			pump.close()
			break

	window.close()

if __name__ == '__main__':
	main()