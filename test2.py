import PySimpleGUI as sg

sg.change_look_and_feel('TanBlue')

def coin_line(coin_name):
    return [sg.Text(f'{coin_name}:', size=(8,1)),
            sg.Input(size=(8,1), key=coin_name),
            sg.Text(f'{coin_name} value:', size=(12,1)),
            sg.Text(size=(6,1), key=f'{coin_name}_total')]

layout = [ coin_line('Quarters'), coin_line('Dimes'),coin_line('Nickels'), coin_line('Pennies'),
           [sg.Button('Calculate', bind_return_key=True), sg.Text(' '*15), sg.Text('Total value:', size=(12,1)), sg.Text(key='-TOTAL-', size=(6,1))]  ]

window = sg.Window('Calculator', layout)

while True:             # Event Loop
    event, values = window.read()
    if event in (None, 'Exit'):
        break
    for key in values:          # convert the inputs into floats
        try:
            values[key] = float(values[key])
        except:
            values[key] = 0.0   # if bad input, consider value to be zero
    quarters = values['Quarters']*.25
    dimes = values['Dimes']*.10
    nickels = values['Nickels']*.05
    pennies = values['Pennies']*.01
    window['Quarters_total'].update(quarters)
    window['Dimes_total'].update(dimes)
    window['Nickels_total'].update(nickels)
    window['Pennies_total'].update(pennies)
    total = quarters + dimes + nickels + pennies
    window['-TOTAL-'].update(total)

window.close()
