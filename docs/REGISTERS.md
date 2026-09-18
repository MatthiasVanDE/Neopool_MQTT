# Modbus-registers van de Sugar Valley Oxilife

Momentopname van **18-09-2026**, uitgelezen op het toestel zelf. Deze pagina is een
naslagwerk om te beslissen wat de integratie nog kan uitlezen of aansturen; het is
geen contract zoals [EXISTING_ENTITIES.md](EXISTING_ENTITIES.md).

## Hoe dit uitgelezen is

De NeoPool-driver (`xsns_83_neopool`) zit al in de Tasmota-build op de ESP32-S3 en
brengt `NPRead`/`NPWrite` mee. Er is dus **niets geflasht en geen Berry-script nodig**;
`neopoolcmd.be` levert alleen de hogere `NPAux`/`NPTimer`-commando's, niet de ruwe toegang.

```
curl 'http://192.168.0.183/cm?cmnd=NPRead%200x04E8%2016'
  -> {"NPRead":{"Address":1256,"Data":[1,1,5,5808,27222,20160,180,0,...]}}
```
Varianten: `NPReadL` (32-bit), `NPReadLSB`/`NPReadMSB` (byte uit een register),
`NPBit` (los bit). Maximaal 29 registers per oproep. Dezelfde commando's werken over
MQTT op `cmnd/SmartPool/NPRead`, met het antwoord op `stat/SmartPool/RESULT` — het topic
waar [coordinator.py](../coordinator.py) al op ingeschreven staat.

> **Let op de gedocumenteerde map, niet op de sweep.** Het paneel antwoordt op *elk*
> adres in 0x0000–0x06FF en geeft nooit een *illegal data address* terug. Dat een adres
> antwoordt bewijst dus niets. De 154 registers hieronder komen uit de Tasmota-driver;
> daarbuiten lazen nog 101 adressen een waarde ≠ 0, grotendeels fabriekskalibratie.

Schrijven gaat naar RAM en wordt pas actief na `NPExec`; pas `NPSave` schrijft naar
EEPROM. Spaarzaam gebruiken — EEPROM slijt.

## Wat de integratie hieruit haalt

De registers hieronder worden sinds 18-09-2026 door de integratie zelf gelezen:
`NeoPoolCoordinator` vraagt vijf blokken op met `NPRead`, elke vijf minuten, plus
de AUX-namen eenmalig bij het opstarten. Zie [EXISTING_ENTITIES.md](EXISTING_ENTITIES.md)
voor de entiteiten die eruit volgen.

### Filterspoelklep (Besgo) — geconfigureerd op het paneel, onzichtbaar in HA

| register | waarde | betekenis |
|---|---|---|
| `0x04E8` | 1 | spoelfunctie actief, modus Besgo |
| `0x04E9` | 1 | timingmodus (3 = altijd aan → spoeling forceren) |
| `0x04EA` | 5 | relais 5 (AUX2) |
| `0x04EB/EC` | 2026-07-14 11:00 | start laatste spoeling |
| `0x04ED` | 20160 | periode in minuten = 14 dagen |
| `0x04EE` | 180 | spoelduur in seconden |
| `0x04EF` | 0 | resterende spoeltijd, 0 = niet bezig |

### Pompsnelheid en de cover — gemeten 18-09-2026

De cover werd één keer geopend terwijl alle 1056 registers voor en na werden
gelezen. **Exact één discrete toestand veranderde:**

```
0x010E RELAY_STATE  0x0142 -> 0x0342   bit9 erbij
0x010D bit4 (Cover input activated)    0 -> 0   onveranderd
```
Al het andere dat bewoog waren continue waarden (spanningen, watertemperatuur,
celtellers, PWM). Het paneel verlaagt de pompsnelheid dus wél bij een gesloten
cover, maar rapporteert de covertoestand nergens. Daarom staat
`binary_sensor.neopool_cover_active` permanent op `off`.

De snelheidslijnen zijn **niet one-hot maar optellend**: bit 8 is de loop-/laaglijn,
bit 9 zet Mid erbovenop.

| cover | bits 8-10 | pomp |
|---|---|---|
| dicht | `0b001` | Low |
| open | `0b011` | Mid |

Tasmota's `NeoPoolGetFiltrationSpeed()` kent alleen 1, 2 en 4 en valt voor elke
andere combinatie terug op de ingestelde standaardsnelheid — het rapporteerde
`High` terwijl de pomp op Mid liep. De integratie decodeert de bits daarom zelf en
leidt de covertoestand af uit het verschil met `0x050F` bits 7-9.

`0x050F` = `0x00A1`: pomptype 1 (Hayward), standaardsnelheid veld 2 (High, geldt
alleen buiten een timerinterval), interval 1 veld 1 (**Mid**). Het veld is
nulgebaseerd. De cover-verlaging zelf zit in de firmware en is via Modbus niet
instelbaar — geen enkel configuratieregister bewoog mee.

### Timerblok vanaf `0x0434` (12 timers × 15 registers)

Offsets per timer: 0 modus, 1 start (32-bit), 5 periode, 7 duur, 9 countdown, 11 functie,
13 looptijd. De Berry-`NPAux` schrijft niets anders dan de modus (3 = altijd aan,
4 = altijd uit) van de betrokken AUX-timer.

| timer | addr | modus | start | periode | duur | functie |
|---|---|---|---|---|---|---|
| FILT_INT1 | `0x0434` | enabled | 08:00 | 24 u | 10.00 u | filtratie |
| FILT_INT2 | `0x0443` | enabled | 00:00 | 24 u | 0.00 u | filtratie |
| FILT_INT3 | `0x0452` | enabled | 00:00 | 24 u | 0.00 u | filtratie |
| AUX1_INT2 | `0x0461` | disabled | 00:00 | 0 u | 0.00 u | — |
| LIGHT_INT | `0x0470` | always off | 07:00 | 72 u | 1.00 u | verlichting |
| AUX2_INT2 | `0x047F` | disabled | 00:00 | 0 u | 0.00 u | — |
| AUX3_INT2 | `0x048E` | disabled | 00:00 | 0 u | 0.00 u | — |
| AUX4_INT2 | `0x049D` | disabled | 00:00 | 0 u | 0.00 u | — |
| AUX1_INT1 | `0x04AC` | always off | 00:00 | 0 u | 0.00 u | relais 4 (AUX1) |
| AUX2_INT1 | `0x04BB` | always off | 00:00 | 0 u | 0.00 u | — |
| AUX3_INT1 | `0x04CA` | always on | 00:00 | 0 u | 0.00 u | — |
| AUX4_INT1 | `0x04D9` | always on | 00:00 | 0 u | 0.00 u | relais 7 (AUX4) |

Filtratietimer 2 en 3 hebben duur 0: een tweede filtratieblok per dag is vrij.

### AUX-namen zoals op het paneel (ASCIIZ, 5 registers per AUX)

| addr | naam |
|---|---|
| `0x0610` | AUX1: (leeg) |
| `0x0615` | AUX2: (leeg) |
| `0x061A` | AUX3: (leeg) |
| `0x061F` | AUX4: Warmtepomp |

### Verder de moeite waard

- `0x010F` = 24200 — PWM-opening van de hydrolysecel; fijnere modulatie dan de 0/100 %-productie.
- `0x0408/09` — paneelklok, stond op 2026-09-18 15:29 en liep gelijk met HA.
- `0x0418`/`0x0419` = 28/23 °C — Smart-modus boven- en ondergrens, `0x041A` antivries.
- `0x041C`/`0x041D` = 23 °C / 540 min — Intelligent-modus.
- `0x0405`–`0x0407` = 360/360/1 min — polarisatietijden van de cel.
- `0x042C`/`0x042D` = 0/8 — reductie van de hydrolyse bij afdekking en uitschakeltemperatuur.
- `0x042E`–`0x0433` — doseerpomp: aan/uit-tijden, max. looptijd 400 s, gedrag bij overschrijding.

## Waarschuwingen

**`0x0416` bevat hier geen temperatuur.** Het leest 6423 (0x1917), terwijl
`0x0414 HEATING_MODE` = 0 en `0x0415 HEATING_GPIO` = 0: de verwarmingsfunctie
van het paneel is niet geconfigureerd — de warmtepomp hangt aan AUX4. De experimentele
`heating_setpoint` in [number.py](../number.py) schrijft dus naar een register waarvan de
betekenis op dit toestel onbewezen is. Niet inschakelen zonder dat eerst aan te tonen.

**De FL1-vergrendeling van AUX4 is niet teruggevonden.** `0x051B FUNCTION_DEPENDENCY` = 0 en documenteert alleen een afhankelijkheid voor *heating*. `0x0403` = 0x0001 zegt dat FL1-controle systeembreed aanstaat. De paneelinstelling zit
vermoedelijk ongedocumenteerd rond `0x051D` (= 0x6400) of `0x0516` (= 0x1000).
Een volledige baseline van alle 1056 adressen is gemaakt; de instelling één keer omzetten
op het paneel en opnieuw sweepen wijst het register met een diff aan.

**Page 0x03xx niet schrijven.** `0x0330`–`0x0346` zijn ijkpunten van de pH- en redoxsondes.

## Volledige map

`HA` = `x` als er een entiteit voor bestaat, `cache` als de integratie het register
wel ophaalt maar niet toont. `poll` = Tasmota zet het uit zichzelf in de SENSOR-JSON;
registers zonder `poll` haalt de integratie op met een expliciete `NPRead`.


### Meet- en voedingswaarden (0x00xx)

Spanningen en de 4-20 mA-lijn. De rest van deze page is ongedocumenteerd.

| addr | HA | poll | waarde | register | betekenis |
|---|---|---|---|---|---|
| `0x0002` |  |  | 1280 | `MBF_POWER_MODULE_VERSION` | ! Power module version (MSB=Major, LSB=Minor) |
| `0x0004` |  |  | 94 | `MBF_POWER_MODULE_NODEID` | ! Power module Node ID (6 register 0x0004 - 0x0009) |
| `0x000C` |  |  | 24 | `MBF_POWER_MODULE_REGISTER` | ! Writing an address in this register causes the power module register address to be read out into MBF_POWER_MODULE_DATA, see MBF_POWER_MODULE_REG_* |
| `0x000D` |  |  | 12338 | `MBF_POWER_MODULE_DATA` | ! power module data as requested in MBF_POWER_MODULE_REGISTER |
| `0x0022` | x | * | 26959 | `MBF_VOLT_24_36` | ! Current 24-36V line in mV |
| `0x0023` | x | * | 13975 | `MBF_VOLT_12` | ! Current 12V line in mV |
| `0x006A` | x | * | 3091 | `MBF_VOLT_5` | ! 5V line in mV / 0,62069 |
| `0x0072` | x | * | 10 | `MBF_AMP_4_20_MICRO` | ! 2-40mA line in µA * 10 (1=0,01mA) |

### MEASURE (0x01xx)

Actuele meetwaarden en modulestatus. Vrijwel volledig in de Tasmota-JSON.

| addr | HA | poll | waarde | register | betekenis |
|---|---|---|---|---|---|
| `0x0100` | x | * | 0 | `MBF_ION_CURRENT` | Ionization level measured |
| `0x0101` | x | * | 1000 | `MBF_HIDRO_CURRENT` | Hydrolysis intensity level |
| `0x0102` | x | * | 719 | `MBF_MEASURE_PH` | ph     pH level measured in 1/100 (700 = 7.00) |
| `0x0103` | x | * | 521 | `MBF_MEASURE_RX` | mV     Redox level measured in mV |
| `0x0104` | x | * | 0 | `MBF_MEASURE_CL` | ppm    Chlorine level measured in 1/100 ppm (100 = 1.00 ppm) |
| `0x0105` | x | * | 0 | `MBF_MEASURE_CONDUCTIVITY` | %      Conductivity level measured in % |
| `0x0106` | x | * | 268 | `MBF_MEASURE_TEMPERATURE` | °C     Temperature sensor measured in 1/10° C (100 = 10.0°C) |
| `0x0107` | x | * | 58624 | `MBF_PH_STATUS` | mask   Status of the pH-module |
| `0x0108` | x | * | 58752 | `MBF_RX_STATUS` | mask   Status of the Rx-module |
| `0x0109` |  | * | 1280 | `MBF_CL_STATUS` | mask   Status of the Chlorine-module |
| `0x010A` |  | * | 1280 | `MBF_CD_STATUS` | mask   Status of the Conductivity-module |
| `0x010C` |  | * | 8256 | `MBF_ION_STATUS` | mask   Status of the Ionization-module |
| `0x010D` | x | * | 8938 | `MBF_HIDRO_STATUS` | mask   Status of the Hydrolysis-module |
| `0x010E` | x | * | 322 | `MBF_RELAY_STATE` | mask   Status of each configurable relay |
| `0x010F` | x | * | 24200 | `MBF_HIDRO_SWITCH_VALUE` | INTERNAL - contains the opening of the hydrolysis PWM. |
| `0x0110` | cache | * | 25 | `MBF_NOTIFICATION` | mask   Bit field that informs whether a property page has changed since the last time it was queried. (see MBMSK_NOTIF_*). This register makes it … |
| `0x0111` | x |  | 0 | `MBF_HIDRO_VOLTAGE` | The voltage applied to the hydrolysis cell. This register, together with that of MBF_HIDRO_CURRENT allows extrapolation of water salinity. |

### GLOBAL (0x02xx)

Celtellers en de actieregisters (EXEC, SAVE, ESCAPE).

| addr | HA | poll | waarde | register | betekenis |
|---|---|---|---|---|---|
| `0x0206` | x | * | 924 | `MBF_CELL_RUNTIME_LOW` | ! Cell runtime (32 bit value - low word) |
| `0x0207` | x | * | 243 | `MBF_CELL_RUNTIME_HIGH` | ! Cell runtime (32 bit value - high word) |
| `0x0208` | x | * | 924 | `MBF_CELL_RUNTIME_PART_LOW` | ! Cell part runtime (32 bit value - low word) |
| `0x0209` | x | * | 243 | `MBF_CELL_RUNTIME_PART_HIGH` | ! Cell part runtime (32 bit value - high word) |
| `0x020C` | x | * | 0 | `MBF_CELL_BOOST` | mask   ! Boost control (see MBMSK_CELL_BOOST_*) |
| `0x0214` | x | * | 26714 | `MBF_CELL_RUNTIME_POLA_LOW` | ! Cell runtime polarity 1 (32 bit value - low word) |
| `0x0215` | x | * | 121 | `MBF_CELL_RUNTIME_POLA_HIGH` | ! Cell runtime polarity 1 (32 bit value - high word) |
| `0x0216` | x | * | 39747 | `MBF_CELL_RUNTIME_POLB_LOW` | ! Cell runtime polarity 2 (32 bit value - low word) |
| `0x0217` | x | * | 121 | `MBF_CELL_RUNTIME_POLB_HIGH` | ! Cell runtime polarity 2 (32 bit value - high word) |
| `0x0218` | x | * | 794 | `MBF_CELL_RUNTIME_POL_CHANGES_LOW` | ! Cell runtime polarity change count (32 bit value - low word) |
| `0x0219` | x | * | 0 | `MBF_CELL_RUNTIME_POL_CHANGES_HIGH` | ! Cell runtime polarity change count (32 bit value - high word) |
| `0x0280` |  |  | 266 | `MBF_HIDRO_MODULE_VERSION` | ! Hydrolysis module version |
| `0x0281` |  |  | 10000 | `MBF_HIDRO_MODULE_CONNECTIVITY` | ! Hydrolysis module connection quality (in myriad: 0..10000) |
| `0x0287` |  |  | 0 | `MBF_SET_COUNTDOWN_KEY_AUX_OFF` | mask   ! switch AUX1-4 OFF - only for AUX which is assigned as AUX and set to MBV_PAR_CTIMER_COUNTDOWN_KEY_* mode  - see … |
| `0x0288` |  |  | 0 | `MBF_SET_COUNTDOWN_KEY_AUX_ON` | mask   ! switch AUX1-4 ON  - only for AUX which is assigned as AUX and set to MBV_PAR_CTIMER_COUNTDOWN_KEY_* mode - see … |
| `0x0289` |  |  | 0 | `MBF_SET_MANUAL_CTRL` | ! write a 1 before manual control MBF_RELAY_STATE, after done write 0 and do MBF_EXEC |
| `0x0297` | x |  | 0 | `MBF_ESCAPE` | ! A write operation to this register is the same as using the ESC button on main screen - clears error |
| `0x02F0` | x |  | 0 | `MBF_SAVE_TO_EEPROM` | A write operation to this register immediately starts a EEPROM storage operation. During the EEPROM storage procedure, the system may be unresponsive … |
| `0x02F5` | x |  | 0 | `MBF_EXEC` | ! A write operation to this register immediately take over settings of the previous written data |

### FACTORY (0x03xx)

Fabrieksinstellingen en kalibratie. **Niet schrijven.**

| addr | HA | poll | waarde | register | betekenis |
|---|---|---|---|---|---|
| `0x0300` | x | * | 2055 | `MBF_PAR_VERSION` | Software version of the PowerBox |
| `0x0301` | x | * | 2 | `MBF_PAR_MODEL` | mask   System model options |
| `0x0302` |  | * | 0 | `MBF_PAR_SERNUM` | Serial number of the PowerBox |
| `0x0303` |  | * | 0 | `MBF_PAR_ION_NOM` | Ionization maximum production level (DO NOT WRITE!) |
| `0x0306` |  | * | 1000 | `MBF_PAR_HIDRO_NOM` | Hydrolysis maximum production level. (DO NOT WRITE!) If the hydrolysis is set to work in percent mode, this value will be 100. If the hydrolysis … |
| `0x030A` |  |  | 2600 | `MBF_PAR_SAL_AMPS` | Current command in regulation for which we are going to measure voltage |
| `0x030B` |  |  | 2 | `MBF_PAR_SAL_CELLK` | Specifies the relationship between the resistance obtained in the measurement process and its equivalence in g / l (grams per liter) |
| `0x030C` |  |  | 1792 | `MBF_PAR_SAL_TCOMP` | Specifies the deviation in temperature from the conductivity. |
| `0x0322` |  |  | 100 | `MBF_PAR_HIDRO_MAX_VOLTAGE` | Allows setting the maximum voltage value that can be reached with the hydrolysis current regulation. The value is specified in tenths of a volt. The … |
| `0x0323` |  |  | 3 | `MBF_PAR_HIDRO_FLOW_SIGNAL` | Allows to select the operation of the flow detection signal associated with the operation of the hydrolysis (see MBV_PAR_HIDRO_FLOW_SIGNAL*). The … |
| `0x0324` |  |  | 100 | `MBF_PAR_HIDRO_MAX_PWM_STEP_UP` | This register sets the PWM ramp up of the hydrolysis in pulses per duty cycle. This register makes it possible to adjust the rate at which the power … |
| `0x0325` |  |  | 100 | `MBF_PAR_HIDRO_MAX_PWM_STEP_DOWN` | This register sets the PWM down ramp of the hydrolysis in pulses per duty cycle. This register allows adjusting the rate at which the power delivered … |

### INSTALLER (0x04xx)

Installateursparameters: relaistoewijzing, bedrijfsmodi, timerblok, spoelklep.

| addr | HA | poll | waarde | register | betekenis |
|---|---|---|---|---|---|
| `0x0400` |  |  | 0 | `MBF_PAR_ION_POL0` | Time in minutes that the equipment must remain working in positive polarization in the copper-silver ionization. |
| `0x0401` |  |  | 0 | `MBF_PAR_ION_POL1` | Time in minutes that the equipment must remain working in negative polarization in the copper-silver ionization. |
| `0x0402` |  |  | 0 | `MBF_PAR_ION_POL2` | Time in minutes that the equipment must remain working in dead time (without delivering power) in the copper-silver ionization. |
| `0x0403` | x |  | 1 | `MBF_PAR_HIDRO_ION_CAUDAL` | mask   Bitmask register regulates the external control mode of ionization, hydrolysis and pumps (see MBMSK_HIDRO_ION_CAUDAL_*) |
| `0x0404` | cache |  | 1 | `MBF_PAR_HIDRO_MODE` | Regulates the external control mode of hydrolysis from the modules of measure. 0 = no control, 1 = standard control (on / off), 2 = with timed pump |
| `0x0405` | x |  | 360 | `MBF_PAR_HIDRO_POL0` | Time in minutes that the equipment must remain in positive polarization during hydrolysis/electrolysis. |
| `0x0406` | x |  | 360 | `MBF_PAR_HIDRO_POL1` | Time in minutes that the equipment must remain in negative polarization during hydrolysis/electrolysis. |
| `0x0407` | x |  | 1 | `MBF_PAR_HIDRO_POL2` | Time in minutes that the equipment must remain working in dead time (without delivering power) in the hydrolysis/electrolysis. |
| `0x0408` | x | * | 22735 | `MBF_PAR_TIME_LOW` | System timestamp as unix timestamp (32 bit value - low word). |
| `0x0409` | cache | * | 27309 | `MBF_PAR_TIME_HIGH` | System timestamp as unix timestsmp (32 bit value - high word). |
| `0x040A` | x | * | 1 | `MBF_PAR_PH_ACID_RELAY_GPIO` | Relay number assigned to the acid pump function (only with pH module). |
| `0x040B` | x | * | 0 | `MBF_PAR_PH_BASE_RELAY_GPIO` | Relay number assigned to the base pump function (only with pH module). |
| `0x040C` | x | * | 0 | `MBF_PAR_RX_RELAY_GPIO` | Relay number assigned to the Redox level regulation function. If the value is 0, there is no relay assigned, and therefore there is no pump function … |
| `0x040D` | x | * | 0 | `MBF_PAR_CL_RELAY_GPIO` | Relay number assigned to the chlorine pump function (only with free chlorine measuring modules). |
| `0x040E` | x | * | 0 | `MBF_PAR_CD_RELAY_GPIO` | Relay number assigned to the conductivity (brine) pump function (only with conductivity measurement modules). |
| `0x040F` |  | * | 1 | `MBF_PAR_TEMPERATURE_ACTIVE` | Indicates whether the equipment has a temperature measurement or not. |
| `0x0410` | x | * | 0 | `MBF_PAR_LIGHTING_GPIO` | Relay number assigned to the lighting function. 0: inactive. |
| `0x0411` | x | * | 1 | `MBF_PAR_FILT_MODE` | Filtration mode (see MBV_PAR_FILT_*) |
| `0x0412` | x | * | 2 | `MBF_PAR_FILT_GPIO` | Relay selected to perform the filtering function (by default it is relay 2). When this value is at zero, there is no relay assigned and therefore it … |
| `0x0413` |  |  | 0 | `MBF_PAR_FILT_MANUAL_STATE` | Filtration status in manual mode (on = 1; off = 0) |
| `0x0414` | x |  | 0 | `MBF_PAR_HEATING_MODE` | Heating mode: 0 = the equipment is not heated. 1 = the equipment is heating. |
| `0x0415` | x |  | 0 | `MBF_PAR_HEATING_GPIO` | Relay number assigned to perform the heating function (by default it is relay 7). When this value is at zero, there is no relay assigned and … |
| `0x0416` | x |  | 6423 | `MBF_PAR_HEATING_TEMP` | Heating mode: Heating setpoint temperature |
| `0x0417` | cache |  | 0 | `MBF_PAR_CLIMA_ONOFF` | Activation of the climate mode (0 = inactive, 1 = active). |
| `0x0418` | x |  | 28 | `MBF_PAR_SMART_TEMP_HIGH` | Smart mode: Upper temperature |
| `0x0419` | x |  | 23 | `MBF_PAR_SMART_TEMP_LOW` | Smart mode: Lower temperature |
| `0x041A` | x |  | 0 | `MBF_PAR_SMART_ANTI_FREEZE` | Smart mode: Antifreeze mode activated (1) or not (0). |
| `0x041B` | x |  | 0 | `MBF_PAR_SMART_INTERVAL_REDUCTION` | Smart mode: This register is read-only and reports to the outside what percentage (0 to 100%) is being applied to the nominal filtration time. 100% … |
| `0x041C` | x |  | 23 | `MBF_PAR_INTELLIGENT_TEMP` | Intelligent mode: Setpoint temperature |
| `0x041D` | x |  | 540 | `MBF_PAR_INTELLIGENT_FILT_MIN_TIME` | Intelligent mode: Minimum filtration time in minutes |
| `0x041E` | x |  | 0 | `MBF_PAR_INTELLIGENT_BONUS_TIME` | Intelligent mode: Bonus time for the current set of intervals |
| `0x041F` | x |  | 0 | `MBF_PAR_INTELLIGENT_TT_NEXT_INTERVAL` | Intelligent mode: Time to next filtration interval. When it reaches 0 an interval is started and the number of seconds is reloaded for the next … |
| `0x0420` | x |  | 0 | `MBF_PAR_INTELLIGENT_INTERVALS` | Intelligent mode: Number of started intervals. When it reaches 12 it is reset to 0 and the bonus time is reloaded with the value of … |
| `0x0421` | x |  | 1 | `MBF_PAR_FILTRATION_STATE` | Filtration state: 0 is off and 1 is on. The filtration state is regulated according to the MBF_PAR_FILT_MANUAL_STATE register if the filtration mode … |
| `0x0422` | cache |  | 60 | `MBF_PAR_HEATING_DELAY_TIME` | Timer in seconds that counts up when the heating is to be enabled. Once this counter reaches 60 seconds, the heating is then enabled. This counter is … |
| `0x0423` |  |  | 0 | `MBF_PAR_FILTERING_TIME_LOW` | Internal timer for the intelligent filtering mode (32-bit value - low word). It counts the filtering time done during a given day. This register is … |
| `0x0424` |  |  | 0 | `MBF_PAR_FILTERING_TIME_HIGH` | Internal timer for the intelligent filtering mode (32-bit value - high word) |
| `0x0425` |  |  | 0 | `MBF_PAR_INTELLIGENT_INTERVAL_TIME_LOW` | Internal timer that counts the filtration interval assigned to the the intelligent mode (32-bit value - low word). This register is only for internal … |
| `0x0426` |  |  | 0 | `MBF_PAR_INTELLIGENT_INTERVAL_TIME_HIGH` | Internal timer that counts the filtration interval assigned to the the intelligent mode (32-bit value - high word) |
| `0x0427` |  |  | 0 | `MBF_PAR_UV_MODE` | UV mode active or not - see MBV_PAR_UV_MODE*. To enable UV support for a given device, add the mask MBMSK_MODEL_UV to the MBF_PAR_MODEL register. |
| `0x0428` |  |  | 0 | `MBF_PAR_UV_HIDE_WARN` | mask   Suppression for warning messages in the UV mode (see MBMSK_UV_HIDE_WARN_*) |
| `0x0429` |  |  | 0 | `MBF_PAR_UV_RELAY_GPIO` | Relay number assigned to the UV function. |
| `0x042A` |  |  | 32828 | `MBF_PAR_PH_PUMP_REP_TIME_ON` | mask   Time that the pH pump will be turn on in the repetitive mode (see MBMSK_PH_PUMP_*). Contains a special time format, see desc for … |
| `0x042B` |  |  | 187 | `MBF_PAR_PH_PUMP_REP_TIME_OFF` | mask   Time that the pH pump will be turn off in the repetitive mode. Contains a special time format, see desc for MBMSK_PH_PUMP_TIME, has no upper … |
| `0x042C` | x |  | 0 | `MBF_PAR_HIDRO_COVER_ENABLE` | mask   Options for the hydrolysis/electrolysis module (see MBMSK_HIDRO_*) |
| `0x042D` | x |  | 8 | `MBF_PAR_HIDRO_COVER_REDUCTION` | Configured levels for the cover reduction and the hydrolysis shutdown temperature options: LSB = Percentage for the cover reduction, MSB = … |
| `0x042E` | x |  | 237 | `MBF_PAR_PUMP_RELAY_TIME_OFF` | Time level in minutes or seconds that the dosing pump must remain off when the temporized pump mode is selected. This time level register applies to … |
| `0x042F` | x |  | 187 | `MBF_PAR_PUMP_RELAY_TIME_ON` | Time level in minutes or seconds that the dosing pump must remain on when the temporized pump mode is selected. This time level register applies to … |
| `0x0430` | cache |  | 1 | `MBF_PAR_RELAY_PH` | Determine what pH regulation configuration the equipment has (see MBV_PAR_RELAY_PH_*) |
| `0x0431` | x |  | 400 | `MBF_PAR_RELAY_MAX_TIME` | Maximum amount of time in seconds, that a dosing pump can operate before rising an alarm signal. The behavior of the system when the dosing time is … |
| `0x0432` |  |  | 2 | `MBF_PAR_RELAY_MODE` | Behavior of the system when the dosing time is exceeded (see MBMSK_PAR_RELAY_MODE_* and MBV_PAR_RELAY_MODE_*) |
| `0x0433` |  |  | 0 | `MBF_PAR_RELAY_ACTIVATION_DELAY` | Delay time in seconds for the pH pump when the measured pH value is outside the allowable pH setpoints. The system internally adds an extra time of … |
| `0x0434` |  |  | 1 | `MBF_PAR_TIMER_BLOCK_BASE` | Block of 180 registers containing the configuration of the 12 timers with 15 registers each (see MBV_TIMER_OFFMB_*). The system has a set of 12 fully … |
| `0x0434` |  |  | 1 | `MBF_PAR_TIMER_BLOCK_FILT_INT1` | Filtration timer 1 |
| `0x0443` |  |  | 1 | `MBF_PAR_TIMER_BLOCK_FILT_INT2` | Filtration tiemr 2 |
| `0x0452` |  |  | 1 | `MBF_PAR_TIMER_BLOCK_FILT_INT3` | Filtration timer 3 |
| `0x0461` |  |  | 0 | `MBF_PAR_TIMER_BLOCK_AUX1_INT2` | Aux1 timer 2 |
| `0x0470` |  |  | 4 | `MBF_PAR_TIMER_BLOCK_LIGHT_INT` | Lighting timer |
| `0x047F` |  |  | 0 | `MBF_PAR_TIMER_BLOCK_AUX2_INT2` | Aux2 timer 2 |
| `0x048E` |  |  | 0 | `MBF_PAR_TIMER_BLOCK_AUX3_INT2` | Aux3 timer 2 |
| `0x049D` |  |  | 0 | `MBF_PAR_TIMER_BLOCK_AUX4_INT2` | Aux4 timer 2 |
| `0x04AC` |  |  | 4 | `MBF_PAR_TIMER_BLOCK_AUX1_INT1` | Aux1 timer 1 |
| `0x04BB` |  |  | 4 | `MBF_PAR_TIMER_BLOCK_AUX2_INT1` | Aux2 timer 1 |
| `0x04CA` |  |  | 3 | `MBF_PAR_TIMER_BLOCK_AUX3_INT1` | Aux3 timer 1 |
| `0x04D9` |  |  | 3 | `MBF_PAR_TIMER_BLOCK_AUX4_INT1` | Aux4 timer 1 |
| `0x04E8` | x |  | 1 | `MBF_PAR_FILTVALVE_ENABLE` | Filter cleaning functionality mode (0 = off, 1 = Besgo) |
| `0x04E9` | cache |  | 1 | `MBF_PAR_FILTVALVE_MODE` | Filter cleaning valve timing mode, possible modes: MBV_PAR_CTIMER_ENABLED, MBV_PAR_CTIMER_ALWAYS_ON, MBV_PAR_CTIMER_ALWAYS_OFF |
| `0x04EA` | x |  | 5 | `MBF_PAR_FILTVALVE_GPIO` | Relay associated with the filter cleaning function. default AUX2 (value 5) |
| `0x04EB` | x |  | 5808 | `MBF_PAR_FILTVALVE_START_LOW` | Start timestamp of filter cleaning (32-bit value - low word) |
| `0x04EC` | cache |  | 27222 | `MBF_PAR_FILTVALVE_START_HIGH` | Start timestamp of filter cleaning (32-bit value - high word) |
| `0x04ED` | x |  | 20160 | `MBF_PAR_FILTVALVE_PERIOD_MINUTES` | Period in minutes between cleaning actions. For example, if a value of 60 is stored in this registry, a cleanup action will occur every hour. |
| `0x04EE` | x |  | 180 | `MBF_PAR_FILTVALVE_INTERVAL` | Cleaning action duration in seconds. |
| `0x04EF` | x |  | 0 | `MBF_PAR_FILTVALVE_REMAINING` | Time remaining for the current cleaning action in seconds. If this register is 0, it means that there is no cleaning function running. When a cleanup … |
| `0x04F0` |  |  | 0 | `MBF_ACTION_COPY_TO_RTC` | A write (any value) forces the writing of the RTC time registers MBF_PAR_TIME_LOW (0x0408) and MBF_PAR_TIME_HIGH (0x0409) into the RTC internal … |

### USER (0x05xx)

Setpoints en gebruikersinstellingen.

| addr | HA | poll | waarde | register | betekenis |
|---|---|---|---|---|---|
| `0x0500` | x | * | 10 | `MBF_PAR_ION` | Ionization target production level. The value adjusted in this register must not exceed the value set in the MBF_PAR_ION_NOM factory register. |
| `0x0501` |  | * | 30 | `MBF_PAR_ION_PR` | Amount of time in minutes that the ionization must be activated each time that the filtration starts. |
| `0x0502` | x | * | 1000 | `MBF_PAR_HIDRO` | Hydrolisis target production level. When the hydrolysis production is to be set in percent values, this value will contain the percent of production. … |
| `0x0504` | x | * | 720 | `MBF_PAR_PH1` | Higher limit of the pH regulation system. The value set in this register is multiplied by 100. This means that if we want to set a value of 7.5, the … |
| `0x0505` | x | * | 700 | `MBF_PAR_PH2` | Lower limit of the pH regulation system. The value set in this register is multiplied by 100. This means that if we want to set a value of 7.0, the … |
| `0x0508` | x | * | 650 | `MBF_PAR_RX1` | Set point for the redox regulation system. This value must be in the range of 0 to 1000. |
| `0x050A` | x | * | 100 | `MBF_PAR_CL1` | Set point for the chlorine regulation system. The value stored in this register is multiplied by 100. This mean that if we want to set a value of 1.5 … |
| `0x050F` | x | * | 161 | `MBF_PAR_FILTRATION_CONF` | mask   ! filtration type and speed, see MBMSK_PAR_FILTRATION_CONF_* |
| `0x0513` | cache |  | 515 | `MBF_PAR_FILTRATION_SPEED_FUNC` | ! filtration speed function control |
| `0x051B` |  |  | 0 | `MBF_PAR_FUNCTION_DEPENDENCY` | mask   Specification for the dependency of different functions, such as heating, from external events like FL1 (see … |

### MISC / UI (0x06xx)

Schermconfiguratie en de AUX-namen.

| addr | HA | poll | waarde | register | betekenis |
|---|---|---|---|---|---|
| `0x0600` | x | * | 3 | `MBF_PAR_UICFG_MACHINE` | Machine type (see MBV_PAR_MACH_* and  kNeoPoolMachineNames[]) |
| `0x0601` |  | * | 8 | `MBF_PAR_UICFG_LANGUAGE` | Selected language (see MBV_PAR_LANG_*) |
| `0x0602` |  | * | 25604 | `MBF_PAR_UICFG_BACKLIGHT` | Display backlight brightness (in %, upper part (8-bit MSB)=0-100) and function (lower part 8-bit LSB, see MBV_PAR_BACKLIGHT_*) |
| `0x0603` |  | * | 5 | `MBF_PAR_UICFG_SOUND` | mask   Audible alerts (see MBMSK_PAR_SOUND_*) |
| `0x0604` |  | * | 0 | `MBF_PAR_UICFG_PASSWORD` | System password encoded in BCD |
| `0x0605` |  | * | 2112 | `MBF_PAR_UICFG_VISUAL_OPTIONS` | mask   Stores the different display options for the user interface menus (bitmask). Some bits allow you to hide options that are normally visible … |
| `0x0606` |  | * | 553 | `MBF_PAR_UICFG_VISUAL_OPTIONS_EXT` | mask   This register stores additional display options for the user interface menus (see MBMSK_VOE_*) |
| `0x0607` |  | * | 0 | `MBF_PAR_UICFG_MACH_VISUAL_STYLE` | mask   This register is an expansion of register MBF_PAR_UICFG_MACHINE and MBF_PAR_UICFG_VISUAL_OPTIONS. If MBF_PAR_UICFG_MACHINE is … |
| `0x0608` |  |  | 0 | `MBF_PAR_UICFG_MACH_NAME_BOLD` | Machine name bold part title displayed during startup if MBF_PAR_UICFG_MACHINE is MBV_PAR_MACH_GENERIC. Note: Only lowercase letters (a-z) can be … |
| `0x060C` |  |  | 0 | `MBF_PAR_UICFG_MACH_NAME_LIGHT` | Machine name normal intensity part title displayed during startup if MBF_PAR_UICFG_MACHINE is MBV_PAR_MACH_GENERIC. Note: Only lowercase letters … |
| `0x0610` | x |  | 0 | `MBF_PAR_UICFG_MACH_NAME_AUX1` | Aux1 relay name: 5 register ASCIIZ string with up to 10 characters |
| `0x0615` | x |  | 0 | `MBF_PAR_UICFG_MACH_NAME_AUX2` | Aux2 relay name: 5 register ASCIIZ string with up to 10 characters |
| `0x061A` | x |  | 0 | `MBF_PAR_UICFG_MACH_NAME_AUX3` | Aux3 relay name: 5 register ASCIIZ string with up to 10 characters |
| `0x061F` | x |  | 22369 | `MBF_PAR_UICFG_MACH_NAME_AUX4` | Aux4 relay name: 5 register ASCIIZ string with up to 10 characters |
