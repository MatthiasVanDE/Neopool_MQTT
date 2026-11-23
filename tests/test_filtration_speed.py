"""Filtration speed decoded from the relay lines, and the cover inferred from it.

The register values in here were measured on the installation on 18-09-2026 by
opening and closing the pool cover while sweeping all 1056 registers; see
docs/REGISTERS.md. Only MBF_RELAY_STATE bit 9 moved.
"""
import pytest

from conftest import load_module

const = load_module("const")
coordinator_mod = load_module("coordinator")
sensor = load_module("sensor")
binary = load_module("binary_sensor")
select_mod = load_module("select")

# Measured: filtration running, interval 1 configured as Mid.
RELAY_COVER_CLOSED = 0x0142  # speed lines 0b001 -> pump runs Low
RELAY_COVER_OPEN = 0x0342    # speed lines 0b011 -> pump runs Mid
RELAY_PUMP_OFF = 0x0042      # no speed line active
CONF_INT1_MID = 0x00A1       # MBF_PAR_FILTRATION_CONF as found on the panel

# 0x0062, the undocumented input mirror. Bit 8 is the cover; bit 5 follows the pump
# speed and bit 9 the Aux4 relay, which is what made this register look unreliable.
INPUT_COVER_CLOSED = 0xBE68  # cover closed, pump Low, Aux4 on
INPUT_COVER_OPEN = 0xBF48    # cover open, pump Mid, Aux4 on
INPUT_CLOSED_PUMP_MID = 0xBC48   # cover closed, pump Mid, Aux4 off
INPUT_CLOSED_NO_SPEED = 0xFC68   # cover closed, no speed line driven


@pytest.fixture
def coord(monkeypatch):
    monkeypatch.setattr(coordinator_mod, "async_dispatcher_send", lambda *a, **k: None)
    c = coordinator_mod.NeoPoolCoordinator(
        hass=None, mqtt_topic="SmartPool", device_name="Pool", entry_id="abc"
    )
    c._available = True
    return c


def _with(coord, relay=RELAY_COVER_OPEN, conf=CONF_INT1_MID, inp=INPUT_COVER_CLOSED):
    coord.registers = {
        const.REG_RELAY_STATE: relay,
        const.REG_PAR_FILTRATION_CONF: conf,
        const.REG_INPUT_STATUS: inp,
    }
    return coord


# --- Relay line decoding --------------------------------------------------------


@pytest.mark.parametrize(
    ("relay_state", "bits", "speed"),
    [
        (RELAY_COVER_CLOSED, 1, 1),  # measured: run line only -> Low
        (RELAY_COVER_OPEN, 3, 2),    # measured: run + mid line -> Mid
        (RELAY_PUMP_OFF, 0, None),   # nothing driven -> unknown, not a guess
        (0x0242, 2, 2),              # one-hot wiring: mid
        (0x0442, 4, 3),              # one-hot wiring: high
        (0x0542, 5, 3),              # additive wiring: run + high
        (0x0742, 7, 3),
        (None, None, None),          # register never read
    ],
)
def test_speed_from_relay_lines(relay_state, bits, speed):
    assert const.filtration_speed_relay_bits(relay_state) == bits
    assert const.filtration_speed_from_relays(relay_state) == speed


def test_additive_wiring_is_not_reported_as_high():
    """Regression guard for the bug this replaces.

    Tasmota's NeoPoolGetFiltrationSpeed only recognises one-hot lines (1, 2, 4) and
    falls back to the configured default speed for anything else, so with these
    relay lines it reported High while the pump measurably ran Mid.
    """
    assert const.filtration_speed_from_relays(RELAY_COVER_OPEN) == 2


# --- Configured speed -----------------------------------------------------------


@pytest.mark.parametrize(
    ("conf", "speed"),
    [
        (CONF_INT1_MID, 2),  # measured: interval 1 field = 1, zero-based -> Mid
        (0x0021, 1),         # field 0 -> Low
        (0x0121, 3),         # field 2 -> High
        (0x01A1, None),      # field 3 is out of range, do not invent a speed
        (None, None),
    ],
)
def test_configured_interval_speed(conf, speed):
    assert const.configured_interval_speed(conf) == speed


# --- Cover, read from the input mirror -----------------------------------------


@pytest.mark.parametrize(
    ("input_status", "closed"),
    [
        (INPUT_COVER_CLOSED, True),
        (INPUT_COVER_OPEN, False),
        (INPUT_CLOSED_PUMP_MID, True),   # pump speed moved, cover did not
        (INPUT_CLOSED_NO_SPEED, True),   # filtration idle, cover still closed
        (None, None),
    ],
)
def test_cover_from_input_register(input_status, closed):
    assert const.cover_closed_from_input(input_status) is closed


def test_only_bit_8_decides_the_cover():
    """Bits 5 and 9 move with the pump and Aux4; they must not touch the cover."""
    for other_bits in (0x0020, 0x0200, 0x0008, 0x4000):
        assert const.cover_closed_from_input(0x0000 | other_bits) is True
        assert const.cover_closed_from_input(const.MASK_INPUT_COVER | other_bits) is False


# --- Coordinator ----------------------------------------------------------------


def test_coordinator_properties(coord):
    _with(coord, relay=RELAY_COVER_CLOSED, inp=INPUT_COVER_CLOSED)
    assert coord.filtration_speed == 1
    assert coord.filtration_speed_bits == 1
    assert coord.configured_speed == 2
    assert coord.cover_closed is True

    _with(coord, relay=RELAY_COVER_OPEN, inp=INPUT_COVER_OPEN)
    assert coord.cover_closed is False


def test_coordinator_without_registers(coord):
    assert coord.filtration_speed is None
    assert coord.filtration_speed_bits is None
    assert coord.cover_closed is None


@pytest.mark.asyncio
async def test_fast_block_is_polled_separately(coord, monkeypatch):
    sent = []

    async def collect(cmd, payload=""):
        sent.append((cmd, payload))

    monkeypatch.setattr(coord, "async_send_command", collect)
    await coord._async_poll_registers_fast()
    assert sent == [
        (const.CMD_NPREAD, f"0x{addr:04X} {count}")
        for addr, count in const.REGISTER_BLOCKS_FAST
    ]
    assert (const.CMD_NPREAD, "0x0062 1") in sent


def test_fast_block_covers_the_live_registers():
    covered = {
        addr + offset
        for addr, count in const.REGISTER_BLOCKS_FAST
        for offset in range(count)
    }
    assert const.REG_RELAY_STATE in covered
    assert const.REG_INPUT_STATUS in covered


def test_filtration_conf_is_polled():
    covered = {
        addr + offset
        for addr, count in const.REGISTER_BLOCKS
        for offset in range(count)
    }
    assert const.REG_PAR_FILTRATION_CONF in covered


# --- Entities -------------------------------------------------------------------


def _sensor(key):
    for desc in sensor.SENSORS:
        if desc.key == key:
            return desc
    raise AssertionError(key)


def test_speed_sensor_prefers_the_relay_lines(coord):
    _with(coord, relay=RELAY_COVER_OPEN)
    desc = _sensor("filtration_speed_sensor")
    # Tasmota would say High here; the relay lines say Mid.
    coord.data = {"Filtration": {"Speed": 3}}
    assert desc.coordinator_value_fn(coord) == "Mid"
    assert desc.value_fn(coord.data) == "High"


def test_speed_select_reports_the_real_speed(coord):
    _with(coord, relay=RELAY_COVER_OPEN)
    coord.data = {"Filtration": {"Speed": 3}}
    entity = select_mod.NeoPoolFiltrationSpeedSelect(coord)
    assert entity.current_option == "Mid"


def test_speed_select_falls_back_before_the_first_register_read(coord):
    coord.data = {"Filtration": {"Speed": 2}}
    entity = select_mod.NeoPoolFiltrationSpeedSelect(coord)
    assert entity.current_option == "Mid"


def test_speed_select_is_blank_when_no_speed_line_is_driven(coord):
    _with(coord, relay=RELAY_PUMP_OFF)
    coord.data = {"Filtration": {"Speed": 3}}
    entity = select_mod.NeoPoolFiltrationSpeedSelect(coord)
    assert entity.current_option is None


def test_cover_binary_sensor(coord):
    desc = next(d for d in binary.REGISTER_BINARY_SENSORS if d.key == "cover_closed")
    _with(coord, inp=INPUT_COVER_CLOSED)
    assert desc.is_on_fn(coord) is True
    _with(coord, inp=INPUT_COVER_OPEN)
    assert desc.is_on_fn(coord) is False


def test_cover_is_readable_while_the_pump_is_off(coord):
    """The old speed-based inference went blind here; the register does not."""
    desc = next(d for d in binary.REGISTER_BINARY_SENSORS if d.key == "cover_closed")
    _with(coord, relay=RELAY_PUMP_OFF, inp=INPUT_CLOSED_NO_SPEED)
    assert desc.is_on_fn(coord) is True


# --- Interval speed select ------------------------------------------------------


def test_interval_select_shows_the_configured_speed(coord):
    _with(coord, conf=CONF_INT1_MID)
    entity = select_mod.NeoPoolIntervalSpeedSelect(coord)
    assert entity.current_option == "Mid"


@pytest.mark.asyncio
async def test_interval_select_writes_only_the_speed_bits(coord, monkeypatch):
    """Measured: 0x0001 + Mid must become 0x0081, leaving pump type and default be."""
    _with(coord, conf=0x0001)
    sent = []

    async def collect(cmd, payload=""):
        sent.append((cmd, payload))

    monkeypatch.setattr(coord, "async_send_command", collect)
    entity = select_mod.NeoPoolIntervalSpeedSelect(coord)
    await entity.async_select_option("Mid")

    assert sent[0] == ("NPWrite", "0x050F 129")
    assert sent[1] == ("NPExec", "")


@pytest.mark.asyncio
async def test_interval_select_low(coord, monkeypatch):
    _with(coord, conf=0x0081)
    sent = []

    async def collect(cmd, payload=""):
        sent.append((cmd, payload))

    monkeypatch.setattr(coord, "async_send_command", collect)
    entity = select_mod.NeoPoolIntervalSpeedSelect(coord)
    await entity.async_select_option("Low")
    assert sent[0] == ("NPWrite", "0x050F 1")


@pytest.mark.asyncio
async def test_interval_select_does_nothing_before_the_register_is_read(
    coord, monkeypatch
):
    sent = []

    async def collect(cmd, payload=""):
        sent.append((cmd, payload))

    monkeypatch.setattr(coord, "async_send_command", collect)
    entity = select_mod.NeoPoolIntervalSpeedSelect(coord)
    await entity.async_select_option("Mid")
    assert sent == []


def test_speed_bits_diagnostic_sensor(coord):
    desc = next(
        d for d in sensor.REGISTER_SENSORS if d.key == "filtration_speed_bits"
    )
    _with(coord, relay=RELAY_COVER_OPEN)
    assert desc.value_fn(coord) == 3
