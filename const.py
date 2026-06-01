"""Constants for NeoPool MQTT Controller integration."""

DOMAIN = "neopool_mqtt"
MANUFACTURER = "Sugar Valley"

CONF_MQTT_TOPIC = "mqtt_topic"
CONF_DEVICE_NAME = "device_name"

DEFAULT_MQTT_TOPIC = "SmartPool"
DEFAULT_DEVICE_NAME = "NeoPool"

TOPIC_TELE_SENSOR = "tele/{}/SENSOR"
TOPIC_TELE_LWT = "tele/{}/LWT"
TOPIC_STAT_RESULT = "stat/{}/RESULT"
TOPIC_CMND = "cmnd/{}/{}"

LWT_ONLINE = "Online"
LWT_OFFLINE = "Offline"

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
CMD_NPESCAPE = "NPEscape"
CMD_NPEXEC = "NPExec"
CMD_NPSAVE = "NPSave"
CMD_NPAUX = "NPAux"

FILTRATION_MODE_MANUAL = 0

FILTRATION_MODES = {
    0: "Manual",
    1: "Auto",
    2: "Heating",
    3: "Smart",
    4: "Intelligent",
    13: "Backwash",
}
FILTRATION_MODES_REVERSE = {v: k for k, v in FILTRATION_MODES.items()}

FILTRATION_SPEEDS = {
    1: "Low",
    2: "Mid",
    3: "High",
}
FILTRATION_SPEEDS_REVERSE = {v: k for k, v in FILTRATION_SPEEDS.items()}

BOOST_MODES = {
    0: "Off",
    1: "On",
    2: "Redox",
}
BOOST_MODES_REVERSE = {v: k for k, v in BOOST_MODES.items()}

# NPLight: 0 off, 1 on, 2 toggle, 3 auto, 4 next RGB program.
# The select exposes the stable selectable modes; toggle (2) and next-program (4)
# are actions, not states, handled by the switch / a button.
LIGHT_MODES = {
    0: "Off",
    1: "On",
    3: "Auto",
}
LIGHT_MODES_REVERSE = {v: k for k, v in LIGHT_MODES.items()}
LIGHT_TOGGLE = 2
LIGHT_NEXT_PROGRAM = 4

PH_STATES = {
    0: "No alarm",
    1: "pH too high",
    2: "pH too low",
    3: "Pump exceeded time",
    4: "pH above setpoint",
    5: "pH below setpoint",
    6: "Tank level alarm",
}

HYDROLYSIS_STATES = {
    "OFF": "Off",
    "FLOW": "Flow alarm",
    "POL1": "Polarization 1",
    "POL2": "Polarization 2",
}
