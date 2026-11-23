"""Raw Modbus register support: NPRead caching, polling, decoding and writes.

The register fixture is a real reading of a Sugar Valley Oxilife (18-09-2026); see
docs/REGISTERS.md. Using measured values rather than invented ones means a decoding
mistake shows up as a wrong pool setting, not as a passing test.
"""
from types import SimpleNamespace

import pytest

from conftest import load_fixture, load_module

coordinator_mod = load_module("coordinator")
const = load_module("const")
sensor = load_module("sensor")
binary = load_module("binary_sensor")
number = load_module("number")


def _msg(payload):
    return SimpleNamespace(payload=payload)


@pytest.fixture
def coord(monkeypatch):
    monkeypatch.setattr(coordinator_mod, "async_dispatcher_send", lambda *a, **k: None)
    return coordinator_mod.NeoPoolCoordinator(
        hass=None, mqtt_topic="SmartPool", device_name="Pool", entry_id="abc"
    )


@pytest.fixture
def loaded(coord):
    """A coordinator preloaded with the measured register values."""
    coord.registers = {int(k): v for k, v in load_fixture("registers").items()}
    coord._available = True
    return coord


# --- NPRead result parsing ------------------------------------------------------


def test_npread_list_is_cached_per_address(coord):
    coord._on_result_message(_msg('{"NPRead": {"Address": 1256, "Data": [1, 1, 5]}}'))
    assert coord.register(0x04E8) == 1
    assert coord.register(0x04E9) == 1
    assert coord.register(0x04EA) == 5


def test_npread_scalar_data(coord):
    coord._on_result_message(_msg('{"NPRead": {"Address": 1263, "Data": 42}}'))
    assert coord.register(0x04EF) == 42


def test_npread_marks_available(coord):
    assert coord.available is False
    coord._on_result_message(_msg('{"NPRead": {"Address": 271, "Data": [24200]}}'))
    assert coord.available is True


def test_npread_unchanged_values_report_no_change(coord):
    payload = '{"NPRead": {"Address": 271, "Data": [24200]}}'
    coord._on_result_message(_msg(payload))
    assert coord._apply_result("NPRead", {"Address": 271, "Data": [24200]}) is False


def test_npread_garbage_is_ignored(coord):
    for value in ("nonsense", {"Address": "x", "Data": [1]}, {"Address": 1}, {}):
        assert coord._apply_result("NPRead", value) is False
    assert coord.registers == {}


def test_npread_skips_non_integer_items(coord):
    coord._apply_result("NPRead", {"Address": 100, "Data": [1, "x", 3]})
    assert coord.registers == {100: 1, 102: 3}


# --- Decoding helpers -----------------------------------------------------------


def test_register_long_is_low_word_first(loaded):
    # 0x04EB/EC hold the last backwash start.
    assert loaded.register_long(const.REG_PAR_FILTVALVE_START) == 5808 | (27222 << 16)


def test_register_long_needs_both_words(coord):
    coord.registers = {0x04EB: 5808}
    assert coord.register_long(0x04EB) is None


def test_register_string_reads_aux_name(loaded):
    name = loaded.register_string(const.REG_PAR_UICFG_MACH_NAME_AUX[3], 5)
    assert name == "Warmtepomp"


def test_register_string_empty_is_none(loaded):
    assert loaded.register_string(const.REG_PAR_UICFG_MACH_NAME_AUX[0], 5) is None


def test_register_string_missing_is_none(coord):
    assert coord.register_string(0x0610, 5) is None


@pytest.mark.parametrize(
    ("raw", "seconds"),
    [
        (None, None),
        (0, 0),
        (30, 30),          # 1..180 is seconds
        (180, 180),
        (200, 23 * 60),    # documented example: (200 - 180 + 3) minutes
        (187, 10 * 60),    # measured: dosing pump on time
        (237, 60 * 60),    # measured: dosing pump off time
        (0x803C, 60),      # repetitive bit 0x8000 must be masked off
    ],
)
def test_decode_pump_time(raw, seconds):
    assert const.decode_pump_time(raw) == seconds


# --- Polling and writing --------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_reads_every_block(coord, monkeypatch):
    sent = []

    async def collect(cmd, payload=""):
        sent.append((cmd, payload))

    monkeypatch.setattr(coord, "async_send_command", collect)
    await coord.async_refresh_registers()

    assert sent == [
        (const.CMD_NPREAD, f"0x{addr:04X} {count}")
        for addr, count in const.REGISTER_BLOCKS
    ]


@pytest.mark.asyncio
async def test_refresh_static_blocks_are_opt_in(coord, monkeypatch):
    sent = []

    async def collect(cmd, payload=""):
        sent.append((cmd, payload))

    monkeypatch.setattr(coord, "async_send_command", collect)
    await coord.async_refresh_registers(include_static=True)

    assert (const.CMD_NPREAD, "0x0610 20") in sent
    assert len(sent) == len(const.REGISTER_BLOCKS) + len(const.REGISTER_BLOCKS_STATIC)


@pytest.mark.asyncio
async def test_write_register_writes_executes_and_reads_back(coord, monkeypatch):
    sent = []

    async def collect(cmd, payload=""):
        sent.append((cmd, payload))

    monkeypatch.setattr(coord, "async_send_command", collect)
    await coord.async_write_register(const.REG_PAR_SMART_TEMP_HIGH, 27)

    assert sent == [
        ("NPWrite", "0x0418 27"),
        ("NPExec", ""),
        ("NPRead", "0x0418 1"),
    ]


@pytest.mark.asyncio
async def test_write_register_never_saves_to_eeprom(coord, monkeypatch):
    sent = []

    async def collect(cmd, payload=""):
        sent.append(cmd)

    monkeypatch.setattr(coord, "async_send_command", collect)
    await coord.async_write_register(const.REG_PAR_FILTVALVE_INTERVAL, 180)
    assert "NPSave" not in sent


# --- Sensors --------------------------------------------------------------------


def _sensor(key):
    for desc in sensor.REGISTER_SENSORS:
        if desc.key == key:
            return desc
    raise AssertionError(f"no register sensor {key}")


def test_backwash_values_match_the_panel(loaded):
    assert _sensor("backwash_remaining").value_fn(loaded) == 0
    assert _sensor("backwash_relay").value_fn(loaded) == 5

    last = _sensor("backwash_last_start").value_fn(loaded)
    assert (last.year, last.month, last.day, last.hour) == (2026, 7, 14, 11)

    # 0x04ED holds 20160 minutes = 14 days.
    nxt = _sensor("backwash_next_start").value_fn(loaded)
    assert (nxt - last).days == 14


def test_backwash_next_start_without_period(loaded):
    loaded.registers[const.REG_PAR_FILTVALVE_PERIOD_MINUTES] = 0
    assert _sensor("backwash_next_start").value_fn(loaded) is None


def test_cover_reduction_splits_the_register(loaded):
    # 0x042D = 0x0008: LSB is the reduction %, MSB the shutdown temperature.
    assert _sensor("cover_reduction_percent").value_fn(loaded) == 8
    assert _sensor("cover_shutdown_temp").value_fn(loaded) == 0


def test_dosing_pump_times_are_decoded_to_seconds(loaded):
    assert _sensor("dosing_pump_time_on").value_fn(loaded) == 600
    assert _sensor("dosing_pump_time_off").value_fn(loaded) == 3600


def test_polarization_times(loaded):
    assert _sensor("cell_pol_positive_time").value_fn(loaded) == 360
    assert _sensor("cell_pol_negative_time").value_fn(loaded) == 360
    assert _sensor("cell_pol_dead_time").value_fn(loaded) == 1


def test_cell_pwm(loaded):
    assert _sensor("cell_pwm").value_fn(loaded) == 24200


def test_aux_names(loaded):
    assert _sensor("aux4_name").value_fn(loaded) == "Warmtepomp"
    assert _sensor("aux1_name").value_fn(loaded) is None


def test_panel_clock_drift_is_zero_for_the_current_time(loaded, monkeypatch):
    import datetime as dt

    panel = _sensor("panel_time").value_fn(loaded)
    monkeypatch.setattr(sensor.dt_util, "now", lambda: panel + dt.timedelta(seconds=3))
    assert _sensor("panel_clock_drift").value_fn(loaded) == -3


def test_register_sensors_are_none_before_any_read(coord):
    for desc in sensor.REGISTER_SENSORS:
        assert desc.value_fn(coord) is None, desc.key


# --- Binary sensors -------------------------------------------------------------


def _binary(key):
    for desc in binary.REGISTER_BINARY_SENSORS:
        if desc.key == key:
            return desc
    raise AssertionError(f"no register binary sensor {key}")


def test_binary_sensors_match_the_panel(loaded):
    assert _binary("backwash_enabled").is_on_fn(loaded) is True
    assert _binary("backwash_active").is_on_fn(loaded) is False
    assert _binary("fl1_interlock").is_on_fn(loaded) is True
    assert _binary("cover_reduction_enabled").is_on_fn(loaded) is False
    assert _binary("temperature_shutdown_enabled").is_on_fn(loaded) is False
    assert _binary("smart_antifreeze").is_on_fn(loaded) is False
    assert _binary("heating_active").is_on_fn(loaded) is False


def test_backwash_active_when_counting_down(loaded):
    loaded.registers[const.REG_PAR_FILTVALVE_REMAINING] = 42
    assert _binary("backwash_active").is_on_fn(loaded) is True


def test_register_binary_sensors_are_none_before_any_read(coord):
    for desc in binary.REGISTER_BINARY_SENSORS:
        assert desc.is_on_fn(coord) is None, desc.key


# --- Numbers --------------------------------------------------------------------


def _number(key):
    for desc in number.REGISTER_NUMBERS:
        if desc.key == key:
            return desc
    raise AssertionError(f"no register number {key}")


def test_number_registers_read_the_measured_values(loaded):
    assert loaded.register(_number("smart_temp_high").register) == 28
    assert loaded.register(_number("smart_temp_low").register) == 23
    assert loaded.register(_number("intelligent_temp").register) == 23
    assert loaded.register(_number("intelligent_filt_min_time").register) == 540
    assert loaded.register(_number("backwash_period").register) == 20160
    assert loaded.register(_number("backwash_duration").register) == 180
    assert loaded.register(_number("dosing_pump_max_time").register) == 400


def test_every_number_register_is_polled():
    """A writable register that is never read would show up as unavailable."""
    polled = {
        addr + offset
        for addr, count in const.REGISTER_BLOCKS
        for offset in range(count)
    }
    for desc in number.REGISTER_NUMBERS:
        assert desc.register in polled, desc.key


def test_every_sensor_register_block_is_contiguous():
    """Blocks must not overlap, or a single NPRead would fetch the same twice."""
    seen: set[int] = set()
    for addr, count in const.REGISTER_BLOCKS + const.REGISTER_BLOCKS_STATIC:
        block = set(range(addr, addr + count))
        assert not (block & seen), f"overlapping block at 0x{addr:04X}"
        seen |= block


# --- Startup resilience ---------------------------------------------------------


class _FakeHass:
    """Just enough hass to capture async_create_task without running a loop."""

    def __init__(self):
        self.tasks = []

    def async_create_task(self, coro):
        self.tasks.append(coro)
        coro.close()  # never awaited in this test


def test_sensor_message_re_requests_registers_when_none_arrived(coord):
    """At startup the integration can be set up before MQTT is connected.

    Telemetry flowing while the register cache is still empty means those first
    reads went nowhere, so ask again instead of waiting out the slow poll.
    """
    coord.hass = _FakeHass()
    coord._on_sensor_message(_msg('{"NeoPool": {"Type": "Oxilife"}}'))
    assert len(coord.hass.tasks) == 1


def test_register_re_request_happens_only_once(coord):
    coord.hass = _FakeHass()
    for _ in range(3):
        coord._on_sensor_message(_msg('{"NeoPool": {"Type": "Oxilife"}}'))
    assert len(coord.hass.tasks) == 1


def test_no_re_request_once_registers_are_known(coord):
    coord.hass = _FakeHass()
    coord.registers = {0x0062: 0xBE68}
    coord._on_sensor_message(_msg('{"NeoPool": {"Type": "Oxilife"}}'))
    assert coord.hass.tasks == []


@pytest.mark.asyncio
async def test_refresh_all_covers_every_block(coord, monkeypatch):
    """The self-heal must not forget the fast blocks: the cover lives there."""
    sent = []

    async def collect(cmd, payload=""):
        sent.append(payload)

    monkeypatch.setattr(coord, "async_send_command", collect)
    await coord.async_refresh_all_registers()

    alle = (
        const.REGISTER_BLOCKS + const.REGISTER_BLOCKS_STATIC + const.REGISTER_BLOCKS_FAST
    )
    assert sorted(sent) == sorted(f"0x{a:04X} {n}" for a, n in alle)
    assert f"0x{const.REG_INPUT_STATUS:04X} 1" in sent
