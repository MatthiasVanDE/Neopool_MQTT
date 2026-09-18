# Device profile (Fase 0.2)

Vastgelegde antwoorden van de gebruiker (2026-06-01). Bepalen welke taken wel/niet
en hoe worden uitgevoerd.

| Vraag | Antwoord | Gevolg voor implementatie |
|-------|----------|---------------------------|
| Berry-script `neopoolcmd.be` geladen? | **Nee / onbekend** — ⚠️ achterhaald, zie "Nameting" onderaan | NPAux/NPAntiFreeze/NPTimer/NPBackup zijn NIET gegarandeerd aanwezig. Aux-switches worden conditioneel: nieuwe config-optie "Berry NeoPool-commando's geïnstalleerd" (default uit) + OptionsFlow om dit achteraf te wijzigen. Aux-switches worden alleen aangemaakt als de optie aanstaat. Bestaande `aux1..aux4` keys blijven ongewijzigd. (Fase 1.5) |
| Modules fysiek aanwezig? | **OxiLife** (controllermodel, geen exacte modulelijst) | OxiLife is een Sugar Valley zout-/hydrolyse-controller. Exacte modules onbekend → alle lees-entities blijven defensief met `available_fn` (verschijnen alleen als de subkey in de SENSOR-JSON staat). Geen harde module-gating (Fase 3 wordt overgeslagen). |
| Variabele filtratiepomp (snelheid 1..3)? | **Onbekend** (model genoemd i.p.v. ja/nee) | NPFiltration twee-parametervorm (`"1 2"`) wordt backward-compatible toegevoegd; bestaande `filtration` switch en `filtration_speed` select blijven ongewijzigd. (Fase 1.4) |
| Tasmota `Topic` / SetOption157 | Niet opgegeven | Geen code-impact; topic komt uit config_flow. NodeID wordt sowieso niet meer geëxposeerd (Fase 1.2). |

## Beslissing over fases

- **Fase 1** (betrouwbaarheid/correctheid): volledig uitvoeren.
- **Fase 2** (lees-entities): volledig, defensief (`available_fn`), geen harde module-gating.
- **Fase 3** (module-aware creatie): **OVERGESLAGEN** op expliciet verzoek van de
  gebruiker (risico voor bestaande automatiseringen, REGEL 0).
- **Fase 4** (Berry-only besturing): alleen het veilige/diagnostische deel
  (NPVersion-sensor). NPAntiFreeze/NPTimer/NPBackup overgeslagen omdat de Berry-driver
  niet (zeker) geladen is. **Die aanname klopt niet meer voor het referentietoestel —
  zie "Nameting". De beslissing zelf is niet herzien.**
- **Fase 5** (tests/docs/translations): volledig uitvoeren.

## Aandachtspunt heating (Fase 2.4)

Verwarmings-setpoint vereist een geverifieerd register (MBF_PAR_HEATING_TEMP = 0x0416)
en schrijven via NPWrite+NPExec — risicovol. Wordt alleen aangemaakt als
`Relay.Heating` in de SENSOR-JSON aanwezig is (`available_fn`), default disabled, met
expliciete waarschuwing. Geen automatische NPSave.

## Nameting op het referentietoestel (2026-09-18)

De tabel hierboven staat op antwoorden van 2026-06-01. Twee ervan zijn intussen
gemeten in plaats van gevraagd, rechtstreeks op het toestel.

**Het Berry-script is wél geladen.** Alle drie de commando's antwoorden, en Tasmota
rapporteert een Berry-heap:

```
cmnd/SmartPool/NPVersion   -> {"NPVersion":["V5.00","May 12 2022","10:43:02"]}
cmnd/SmartPool/NPTimer11   -> {"NPTimer11":{"Mode":"Manual","State":"ON","Allocation":"Aux4"}}
Status 11                  -> "Berry":{"HeapUsed":30,"Objects":423}
```

**Het toestel.** Sugar Valley **Oxilife**, Tasmota 15.3.0.1 (tasmota32) op een
ESP32-S3, hostnaam `SmartPool-3064`, `192.168.0.183`, MQTT-topic `SmartPool`.
Modules volgens de SENSOR-JSON: `pH: 1, Redox: 1, Hydrolysis: 1`, en
`Chlorine: 0, Conductivity: 0, Ionization: 0`. De vraag "modules fysiek aanwezig?"
uit de tabel is daarmee ook beantwoord — al blijft `available_fn` de juiste aanpak
voor andermans toestellen.

**Filtratie.** `Filtration: {"State":1,"Speed":1,"Mode":1}` — modus `Auto`, en
`NPTimer1` staat op `Filtration 08:00–18:00, 1d`. Speed 1 van een toestel dat
snelheden kent, dus de tweeparametervorm van `NPFiltration` heeft hier zin.

### Wat dit betekent voor de code

Niets breekt, en er is niets gewijzigd naar aanleiding van deze meting:

- `berry_enabled()` geeft voor de bestaande config entry `True` terug via het
  backward-compat-pad (de entry heeft geen `berry_enabled`-sleutel), dus de
  `aux1..aux4`-switches bestaan en werken. Dat is aantoonbaar: Home Assistant
  schakelt `switch.neopool_aux_4` en het relais volgt.
- `DEFAULT_BERRY_ENABLED = False` voor **nieuwe** entries blijft verdedigbaar: dat
  gaat over andermans toestellen, niet over dit toestel.
- **Te heroverwegen:** het overslaan van `NPAntiFreeze`/`NPTimer`/`NPBackup` in
  fase 4 berustte op "Berry niet zeker aanwezig". Die grond is voor dit toestel
  weg. Een `NPTimer`-lezing per relais zou bijvoorbeeld zichtbaar maken of een
  hulprelais aan de filtratie gekoppeld is — precies wat je moet weten als je een
  warmtepomp op een AUX hangt en de flowswitch op de Neopool zit en niet op de
  warmtepomp.
