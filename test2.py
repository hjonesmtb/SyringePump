## Paste your code here

import PySimpleGUI as sg

layout = [  [sg.Text('Some text on Row 1')] ]
window = sg.Window('Window Title', layout, resizable = True, finalize = True, Maximize = True)
# window.Maximize()
while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED or event == 'Cancel':
        break
window.close()

if __name__ == '__main__':
	main()
