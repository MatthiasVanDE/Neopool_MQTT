# Device profile (Fase 0.2)

Vastgelegde antwoorden van de gebruiker (2026-06-01). Bepalen welke taken wel/niet
en hoe worden uitgevoerd.

| Vraag | Antwoord | Gevolg voor implementatie |
|-------|----------|---------------------------|
| Berry-script `neopoolcmd.be` geladen? | **Nee / onbekend** | NPAux/NPAntiFreeze/NPTimer/NPBackup zijn NIET gegarandeerd aanwezig. Aux-switches worden conditioneel: nieuwe config-optie "Berry NeoPool-commando's geïnstalleerd" (default uit) + OptionsFlow om dit achteraf te wijzigen. Aux-switches worden alleen aangemaakt als de optie aanstaat. Bestaande `aux1..aux4` keys blijven ongewijzigd. (Fase 1.5) |
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
  niet (zeker) geladen is.
- **Fase 5** (tests/docs/translations): volledig uitvoeren.

## Aandachtspunt heating (Fase 2.4)

Verwarmings-setpoint vereist een geverifieerd register (MBF_PAR_HEATING_TEMP = 0x0416)
en schrijven via NPWrite+NPExec — risicovol. Wordt alleen aangemaakt als
`Relay.Heating` in de SENSOR-JSON aanwezig is (`available_fn`), default disabled, met
expliciete waarschuwing. Geen automatische NPSave.
