"""Constants for NeoPool MQTT Controller integration."""

DOMAIN = "neopool_mqtt"
MANUFACTURER = "Sugar Valley"

# Config keys
CONF_MQTT_TOPIC = "mqtt_topic"
CONF_DEVICE_NAME = "device_name"

# Default values
DEFAULT_MQTT_TOPIC = "SmartPool"
DEFAULT_DEVICE_NAME = "NeoPool"

# MQTT Topics
TOPIC_TELE_SENSOR = "tele/{}/SENSOR"
TOPIC_STAT_RESULT = "stat/{}/RESULT"
TOPIC_CMND = "cmnd/{}/{}"

# NeoPool Commands
CMD_NPFILTRATION = "NPFiltration"
CMD_NPFILTRATIONMODE = "NPFiltrationmode"
CMD_NPFILTRATIONSPEED = "NPFiltrationspeed"
CMD_NPLIGHT = "NPLight"
CMD_NPBOOST = "NPBoost"
CMD_NPPHMIN = "NPpHMin"
CMD_NPPHMAX = "NPpHMax"
CMD_NPREDOX = "NPRedox"
CMD_NPHYDROLYSIS = "NPHydrolysis"
CMD_NPIONIZATION = "NPIonization"
CMD_NPCHLORINE = "NPChlorine"
CMD_NPTIME = "NPTime"
CMD_NPTELEPERIOD = "NPTelePeriod"
CMD_NPONERROR = "NPOnError"
CMD_NPCONTROL = "NPControl"
CMD_NPESCAPE = "NPEscape"
CMD_NPEXEC = "NPExec"
CMD_NPSAVE = "NPSave"
CMD_NPREAD = "NPRead"
CMD_NPWRITE = "NPWrite"
CMD_NPWRITEL = "NPWriteL"
CMD_NPBIT = "NPBit"
CMD_NPAUX = "NPAux"

# Filtration modes
FILTRATION_MODES = {
    0: "Manual",
    1: "Auto",
    2: "Heating",
    3: "Smart",
    4: "Intelligent",
    13: "Backwash",
}

FILTRATION_MODES_REVERSE = {v: k for k, v in FILTRATION_MODES.items()}

# Filtration speeds
FILTRATION_SPEEDS = {
    1: "Low",
    2: "Mid",
    3: "High",
}

FILTRATION_SPEEDS_REVERSE = {v: k for k, v in FILTRATION_SPEEDS.items()}

# Boost modes
BOOST_MODES = {
    0: "Off",
    1: "On",
    2: "Redox",
}

BOOST_MODES_REVERSE = {v: k for k, v in BOOST_MODES.items()}

# pH States
PH_STATES = {
    0: "No alarm",
    1: "pH too high",
    2: "pH too low",
    3: "Pump exceeded time",
    4: "pH above setpoint",
    5: "pH below setpoint",
    6: "Tank level alarm",
}

# Hydrolysis States
HYDROLYSIS_STATES = {
    "OFF": "Off",
    "FLOW": "Flow alarm",
    "POL1": "Polarization 1",
    "POL2": "Polarization 2",
}

# NeoPool device types
DEVICE_TYPES = [
    "Hidrolife", "Aquascenic", "Oxilife", "Bionet",
    "Hidroniser", "UVScenic", "Station", "Brilix",
    "Generic", "Bayrol", "Hay", "NeoPool",
]

# Modbus registers for timer blocks (filtration intervals)
MBF_PAR_TIMER_BLOCK_FILT_INT1 = 0x0434
MBF_PAR_TIMER_BLOCK_FILT_INT2 = 0x0443
MBF_PAR_TIMER_BLOCK_FILT_INT3 = 0x0452

# Timer offsets
MBV_TIMER_OFFMB_TIMER_ENABLE = 0
MBV_TIMER_OFFMB_TIMER_ON = 1
MBV_TIMER_OFFMB_TIMER_OFF = 3
MBV_TIMER_OFFMB_TIMER_PERIOD = 5
MBV_TIMER_OFFMB_TIMER_INTERVAL = 7

# Aux timer blocks
MBF_PAR_TIMER_BLOCK_AUX1_INT1 = 0x04A2
MBF_PAR_TIMER_BLOCK_AUX2_INT1 = 0x04B1
MBF_PAR_TIMER_BLOCK_AUX3_INT1 = 0x04C0
MBF_PAR_TIMER_BLOCK_AUX4_INT1 = 0x04D9

# Timer enable values
MBV_PAR_CTIMER_ALWAYS_ON = 3
MBV_PAR_CTIMER_ALWAYS_OFF = 4

# Heating register
MBF_PAR_HEATING_TEMP = 0x0416
