from datetime import datetime

SYRINGE_DIAM = 10  # mm
FLOWRATE_CONVERSION = 1 / 1000 / 60  # 1mL/1000uL*1min/60seconds

# default values
TEST_NAME = "Test_" + datetime.now().strftime("%y-%m-%d_%H%M")
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
FREQUENCY = 7  # Hz
FLOW_RATE = 100  # uL/min
INFUSION_VOLUME = 1  # mL
N_MEASUREMENTS = 10
T_DEPOSITION = INFUSION_VOLUME / N_MEASUREMENTS / (FLOW_RATE * FLOWRATE_CONVERSION)
STEP_VOLUME = INFUSION_VOLUME / N_MEASUREMENTS


class System_Data:
    def __init__(self):
        # measurment data
        self.current = []
        self.potential = []
        self.overload = []
        self.underload = []
        self.noise = []
        # system parameters
        self.pump_com = PUMP_COM
        self.pump_baud = PUMP_BAUD
        self.pstat_com = PSTAT_COM
        self.test_name = TEST_NAME
        self.flow_rate = FLOW_RATE
        self.volume = INFUSION_VOLUME
        self.e_cond = E_CONDITION
        self.e_dep = E_DEPOSITION
        self.e_begin = E_BEGIN
        self.e_end = E_STOP
        self.e_step = E_STEP
        self.t_cond = T_CONDITION
        self.t_dep = T_DEPOSITION
        self.t_equil = T_EQUILIBRATION
        self.amplitude = AMPLITUDE
        self.frequency = FREQUENCY
        self.n_measurements = N_MEASUREMENTS
        self.step_volume = STEP_VOLUME
        self.syringe_diam = SYRINGE_DIAM
        self.flowrate_conversion = FLOWRATE_CONVERSION
        self.measurements = 0

    def write_sqv(self, pot, cur, over, under):
        self.potential = pot
        self.current = cur
        self.overload = over
        self.underload = under

    def write_chrono(self, pot, cur, over, under):
        self.potential = pot
        self.current = cur
        self.overload = over
        self.underload = under
