"""Constants for NeoPool MQTT Controller integration."""

DOMAIN = "neopool_mqtt"
MANUFACTURER = "Sugar Valley"

CONF_MQTT_TOPIC = "mqtt_topic"
CONF_DEVICE_NAME = "device_name"
# Whether the Berry script neopoolcmd.be is loaded on the ESP32. It provides the
# NPAux/NPAntiFreeze/NPTimer/NPBackup commands. Aux switches are only created when
# this is enabled.
CONF_BERRY_ENABLED = "berry_enabled"

DEFAULT_MQTT_TOPIC = "SmartPool"
DEFAULT_DEVICE_NAME = "NeoPool"
# Default for NEW config entries (config flow). Most devices have no Berry script.
DEFAULT_BERRY_ENABLED = False

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
CMD_NPWRITE = "NPWrite"
CMD_NPVERSION = "NPVersion"

CMD_NPREAD = "NPRead"

# Modbus register for the heating setpoint (MBF_PAR_HEATING_TEMP), per Tasmota NeoPool
# docs. Used only by the experimental heating_setpoint number (Fase 2.4). Writing it
# uses NPWrite + NPExec (RAM only). Verify the register/scaling for your model before
# enabling this entity. Whole degrees Celsius are assumed.
REG_HEATING_TEMP = "0x0416"

# --- Raw Modbus registers ----------------------------------------------------
# Tasmota publishes only ~46 registers in its SENSOR JSON. Everything below is read
# explicitly with NPRead and cached in NeoPoolCoordinator.registers. Addresses and
# semantics come from the Tasmota NeoPool driver (xsns_83_neopool); see
# docs/REGISTERS.md for the values measured on a Sugar Valley Oxilife.

REG_INPUT_STATUS = 0x0062                # undocumented; mirrors inputs and outputs
REG_HIDRO_STATUS = 0x010D                # mask: hydrolysis module status
REG_RELAY_STATE = 0x010E                 # mask: relay outputs, incl. the speed lines
REG_HIDRO_SWITCH_VALUE = 0x010F          # PWM opening of the hydrolysis cell (raw)
REG_NOTIFICATION = 0x0110                # bitmask: which property page changed
REG_HIDRO_VOLTAGE = 0x0111               # cell voltage; 0 on models that do not report it

REG_PAR_HIDRO_ION_CAUDAL = 0x0403        # mask: flow/interlock control bits
REG_PAR_HIDRO_POL0 = 0x0405              # minutes in positive polarization
REG_PAR_HIDRO_POL1 = 0x0406              # minutes in negative polarization
REG_PAR_HIDRO_POL2 = 0x0407              # minutes of dead time between polarizations
REG_PAR_TIME = 0x0408                    # 32-bit panel clock (low word first)

REG_PAR_HEATING_MODE = 0x0414
REG_PAR_SMART_TEMP_HIGH = 0x0418         # °C
REG_PAR_SMART_TEMP_LOW = 0x0419          # °C
REG_PAR_SMART_ANTI_FREEZE = 0x041A
REG_PAR_SMART_INTERVAL_REDUCTION = 0x041B  # %, read-only
REG_PAR_INTELLIGENT_TEMP = 0x041C        # °C
REG_PAR_INTELLIGENT_FILT_MIN_TIME = 0x041D  # minutes
REG_PAR_INTELLIGENT_BONUS_TIME = 0x041E  # minutes
REG_PAR_INTELLIGENT_TT_NEXT_INTERVAL = 0x041F  # minutes
REG_PAR_INTELLIGENT_INTERVALS = 0x0420   # count, wraps at 12

REG_PAR_HIDRO_COVER_ENABLE = 0x042C      # mask: cover reduction / temperature shutdown
REG_PAR_HIDRO_COVER_REDUCTION = 0x042D   # LSB = reduction %, MSB = shutdown °C
REG_PAR_PUMP_RELAY_TIME_OFF = 0x042E     # dosing pumps except pH, coded time
REG_PAR_PUMP_RELAY_TIME_ON = 0x042F      # dosing pumps except pH, coded time
REG_PAR_RELAY_MAX_TIME = 0x0431          # seconds a dosing pump may run before alarm

REG_PAR_FILTVALVE_ENABLE = 0x04E8        # 0 = off, 1 = Besgo backwash valve
REG_PAR_FILTVALVE_MODE = 0x04E9
REG_PAR_FILTVALVE_GPIO = 0x04EA          # relay driving the valve
REG_PAR_FILTVALVE_START = 0x04EB         # 32-bit timestamp of the last cleaning
REG_PAR_FILTVALVE_PERIOD_MINUTES = 0x04ED
REG_PAR_FILTVALVE_INTERVAL = 0x04EE      # cleaning duration in seconds
REG_PAR_FILTVALVE_REMAINING = 0x04EF     # seconds left, 0 = not cleaning

REG_PAR_FILTRATION_CONF = 0x050F         # mask: pump type and speed per timer interval
REG_PAR_FILTRATION_SPEED_FUNC = 0x0513   # undocumented; read but not interpreted

REG_PAR_UICFG_MACH_NAME_AUX = (0x0610, 0x0615, 0x061A, 0x061F)  # 5 registers each
REG_AUX_NAME_LENGTH = 5

# Bit masks
MASK_INPUT_COVER = 0x0100                # 0x0062 bit 8: pool cover open
MASK_RELAY_FILTSPEED = 0x0700            # relay bits 8-10 drive the pump speed
SHIFT_RELAY_FILTSPEED = 8
MASK_FILTRATION_CONF_INT1_SPEED = 0x0380  # configured speed for timer interval 1
SHIFT_FILTRATION_CONF_INT1_SPEED = 7
MASK_CAUDAL_FL1 = 0x0001                 # FL1 disables the system when inactive
MASK_HIDRO_COVER_ENABLE = 0x0001
MASK_HIDRO_TEMPERATURE_SHUTDOWN = 0x0002
MASK_HIDRO_COVER_REDUCTION = 0x00FF
MASK_PH_PUMP_TIME = 0x7FFF

# Blocks read on every poll: (start address, register count). Contiguous blocks keep
# the number of Modbus transactions down — one NPRead per block, not per register.
REGISTER_BLOCKS: tuple[tuple[int, int], ...] = (
    (0x010F, 3),   # 0x010F-0x0111 cell PWM, notification, cell voltage
    (0x050F, 5),   # 0x050F-0x0513 filtration type and per-interval speeds
    (0x0403, 7),   # 0x0403-0x0409 flow interlock, polarization times, panel clock
    (0x0414, 15),  # 0x0414-0x0422 heating, smart and intelligent mode
    (0x042C, 6),   # 0x042C-0x0431 cover reduction and dosing pump limits
    (0x04E8, 8),   # 0x04E8-0x04EF backwash valve
)

# Live state, polled far more often than the configuration blocks: the speed the panel
# is actually driving. Tasmota does not publish these bits in its SENSOR JSON.
REGISTER_BLOCKS_FAST: tuple[tuple[int, int], ...] = (
    (0x0062, 1),   # 0x0062       input mirror, holds the pool cover bit
    (0x010D, 2),   # 0x010D-0x010E hydrolysis status and relay state
)

REGISTER_POLL_FAST_SECONDS = 30

# Read once at setup: configuration that cannot change while the panel runs.
REGISTER_BLOCKS_STATIC: tuple[tuple[int, int], ...] = (
    (0x0610, 20),  # 0x0610-0x0623 Aux1..Aux4 names as configured on the panel
)

# These registers are configuration, not measurements; five minutes is frequent
# enough to notice a change made on the panel without adding Modbus load.
REGISTER_POLL_INTERVAL_MINUTES = 5


def decode_pump_time(value: int | None) -> int | None:
    """Decode the Sugar Valley coded pump time (MBMSK_PH_PUMP_TIME) to seconds.

    1..180 is a value in seconds; above that the panel switches to minutes, where
    180 means 3 minutes — so 200 is (200 - 180 + 3) = 23 minutes.
    """
    if value is None:
        return None
    time_level = value & MASK_PH_PUMP_TIME
    if time_level <= 180:
        return time_level
    return (time_level - 177) * 60

def berry_enabled(entry) -> bool:
    """Resolve whether Berry (neopoolcmd.be) commands are enabled for an entry.

    Backward compat (REGEL 0): when the key is absent — i.e. the entry was created
    before this option existed — default to True so the existing aux1..aux4 switches
    are NOT silently removed. New entries always carry an explicit value from the
    config flow, and the OptionsFlow can change it afterwards.
    """
    if CONF_BERRY_ENABLED in entry.options:
        return bool(entry.options[CONF_BERRY_ENABLED])
    return bool(entry.data.get(CONF_BERRY_ENABLED, True))


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


# --- Filtration speed --------------------------------------------------------
# The panel drives three relay lines for pump speed (MBF_RELAY_STATE bits 8-10).
# Tasmota assumes they are one-hot (1, 2, 4) and falls back to the *configured
# default* speed for any other combination — so on a pump wired additively it
# reports a speed the pump is not running. Measured on a Sugar Valley Oxilife with
# a Hayward variable-speed pump (18-09-2026): bits 0b001 = Low, 0b011 = Mid, where
# bit 8 is the run line and bit 9 adds the middle speed.
#
# Both wirings are covered below; values are on the 1..3 scale of FILTRATION_SPEEDS.
FILTRATION_SPEED_BY_RELAY_BITS = {
    1: 1,  # 0b001 run line only
    2: 2,  # 0b010 one-hot mid
    3: 2,  # 0b011 run + mid            (measured on this installation)
    4: 3,  # 0b100 one-hot high
    5: 3,  # 0b101 run + high
    6: 3,  # 0b110 mid + high
    7: 3,  # 0b111 all lines
}


def filtration_speed_relay_bits(relay_state: int | None) -> int | None:
    """The raw speed lines (0..7) from MBF_RELAY_STATE, or None if not read yet."""
    if relay_state is None:
        return None
    return (relay_state & MASK_RELAY_FILTSPEED) >> SHIFT_RELAY_FILTSPEED


def filtration_speed_from_relays(relay_state: int | None) -> int | None:
    """Speed (1..3) the panel is really driving.

    None means either "not read yet" or "no speed line active" — in both cases we
    genuinely do not know what the pump is doing, and saying so beats guessing.
    """
    bits = filtration_speed_relay_bits(relay_state)
    if not bits:
        return None
    return FILTRATION_SPEED_BY_RELAY_BITS.get(bits)


def configured_interval_speed(filtration_conf: int | None) -> int | None:
    """Configured speed (1..3) for filtration timer interval 1.

    The field is zero-based (0 = Low), unlike the reported speed, hence the +1.
    """
    if filtration_conf is None:
        return None
    field = (
        filtration_conf & MASK_FILTRATION_CONF_INT1_SPEED
    ) >> SHIFT_FILTRATION_CONF_INT1_SPEED
    if field > 2:
        return None
    return field + 1


def cover_closed_from_input(input_status: int | None) -> bool | None:
    """Pool cover, read from bit 8 of the undocumented register 0x0062.

    The panel exposes the cover in none of the documented registers: sweeping all
    1056 addresses with the cover open and then closed showed MBF_HIDRO_STATUS bit 4
    ("cover input activated") stuck at 0 throughout. 0x0062 is an undocumented mirror
    of inputs and outputs, and its bit 8 was the one bit that tracked the cover.

    Measured on 18-09-2026: bit 8 was set only while the cover was open, and clear in
    every reading with it closed - across pump speed changes and across the Aux4
    relay dropping out, which move bits 5 and 9 of the same register. Bit 3 toggles
    on its own and means something else again.

    This rests on a single open-cover observation, so keep the default-disabled
    "Input Status Register" diagnostic sensor in mind if the cover ever reads wrong.
    """
    if input_status is None:
        return None
    return not bool(input_status & MASK_INPUT_COVER)
