# Evidence and rule bank for consumer-wearable wellness coaching

Last grounded from live sources: 2026-08-05. Recheck official pages before relying on version-specific terminology.

## Authoritative source bank

### Google Health / Fitbit vitals

- [Track your vitals in the Google Health app](https://support.google.com/googlehealth/answer/14236917?hl=en)
- Current terminology: Vitals (formerly Health Metrics) includes breathing rate, HRV, skin-temperature variation, oxygen saturation, and resting heart rate where supported.
- Google describes these as wellbeing insights, advises professional consultation for health concerns, and emergency services for emergencies.
- Design implication: prefer Google’s personal range and do not reinterpret it as a clinical reference range.

### Activity

- [WHO physical activity fact sheet](https://www.who.int/news-room/fact-sheets/detail/physical-activity), updated 2024-06-26 when reviewed.
- Adult target: 150–300 minutes of moderate or 75–150 minutes of vigorous aerobic activity per week, or an equivalent combination; muscle strengthening on two or more days where appropriate. Limit sedentary time and replace it with movement of any intensity.
- [Google Health Active Zone Minutes](https://support.google.com/googlehealth/answer/14236509?hl=en-AU)
- Google states that about 22 Active Zone Minutes per day on average reaches the 150-minute weekly recommendation, while the goal remains customizable.
- Design implication: pace against a weekly target; do not punish a missed day.

### Sleep

- [CDC About Sleep](https://www.cdc.gov/sleep/about/index.html), reviewed 2024-05-15 when checked.
- Duration reference: ages 18–60, at least 7 hours; ages 61–64, 7–9; 65+, 7–8. Use the appropriate age band.
- Lee et al. 2024, [Fitbit Charge 4, Garmin Vivosmart 4, and WHOOP versus polysomnography](https://doi.org/10.2196/52192): devices produced useful estimates but only moderate or variable accuracy for specific sleep stages; literature was limited.
- Design implication: coach from duration/regularity and multi-night trend; do not infer recovery or a disorder from stage minutes.

### Wearable accuracy

- Fuller et al. 2024, [living umbrella review](https://doi.org/10.1007/s40279-024-02077-2), PMID 39080098.
- Included 24 systematic reviews, 249 non-duplicate validation studies, and 430,465 participants.
- Approximately 11% of commercially available wearables had validation for at least one biometric outcome; only about 3.5% of the validations needed for complete outcome coverage had been conducted.
- Reported summaries included heart-rate mean bias around ±3%; activity-intensity mean absolute errors of 29–80%; SpO2 mean absolute differences up to 2 percentage points; and a tendency to overestimate total sleep time, often by more than 10% MAPE. Methods and outcomes were highly heterogeneous.
- Design implication: never imply false precision; a valid result for one device/outcome does not validate all metrics or newer models.

### Pulse oximetry safety

- [FDA Pulse Oximeter Basics](https://www.fda.gov/consumers/consumer-updates/pulse-oximeter-basics)
- FDA advises interpreting readings alongside symptoms and how the person feels. Measurement quality can be affected by movement, hand temperature, positioning, and other factors; altitude also changes expected saturation.
- Serious signs listed include blue coloration, worsening breathing difficulty, chest pain/tightness, restlessness/discomfort, and fast/racing pulse.
- Design implication: no wellness-app diagnostic threshold. Recheck quality for an isolated reading; persistent alerts or symptoms lead to professional/urgent evaluation, not a diagnosis.

### Diet and weight

- [WHO healthy diet](https://www.who.int/news-room/fact-sheets/detail/healthy-diet), updated 2026-01-26 when checked: adequacy, balance, moderation, diversity, and a foundation of varied minimally processed/unprocessed foods low in unhealthy fats, free sugars, and sodium.
- [CDC Steps for Losing Weight](https://www.cdc.gov/healthy-weight-growth/losing-weight/index.html), reviewed 2025-01-17 when checked: healthy weight management includes food pattern, activity, sleep, and stress management; gradual loss around 1–2 lb (about 0.45–0.9 kg) per week is more likely to be maintained.
- Design implication: the CDC range is guidance for an explicit weight-loss context, not a universal target or a diagnostic red flag. Never react to a daily scale change.

## Conservative product heuristics

These numbers are implementation defaults, **not medically validated cutoffs**:

| Purpose | Conservative default |
|---|---|
| Baseline for nocturnal vitals | 21 valid nights in previous 28 |
| Isolated outlier | Quality/context check only |
| Confirmed personal-range drift | Outside range on 2 of 3 valid nights |
| Persistent drift | 3 consecutive or 5 of 7 valid nights |
| Sleep trend | At least 3 valid nights; 7–14 preferred |
| Weekly activity coverage | At least 5 of 7 days |
| Nutrition/hydration evaluation | At least 4 plausibly complete days of 7 |
| Weight trend | Weekly median from at least 3 comparable weigh-ins, evaluated over several weeks |
| Sedentary reminder | Roughly 60 continuous minutes, then suggest 2–5 minutes movement |

Label these defaults in product documentation and expose them to tuning/validation. Prefer vendor confidence flags and personal ranges where available.

## Reusable decision matrix

| Input pattern | Allowed coaching | Prohibited inference |
|---|---|---|
| One unusual HRV/RHR/respiration/temperature/SpO2 value | Check fit, sync, context; observe | Illness, dehydration, stress, apnea, overtraining |
| RHR above and HRV below personal range on 2 of 3 nights, person feels well | Optional lighter day, usual fluids/meals, earlier sleep routine | A named cause or requirement to cancel all activity |
| Weekly activity below goal, recovery stable | Add a small achievable bout; plan across remaining week | “Unhealthy” or “failed day” |
| Activity spike plus multi-signal recovery drift | Consider easy session/rest and reassess | Overtraining diagnosis |
| Sleep duration repeatedly below age guidance/personal pattern | Regular schedule, modest earlier wind-down, late-caffeine reduction | Insomnia/apnea diagnosis |
| Isolated SpO2 reading without symptoms | Repeat only after quality check; mention uncertainty | Clinical saturation diagnosis or oxygen advice |
| Persistent vendor alert or ongoing symptoms | Consult a professional; urgent services for severe symptoms | Disease explanation |
| Partial food/fluid log | State insufficient data; offer a generic additive habit only | Deficiency, excess, dehydration |
| Daily weight change | No interpretation | Fat gain/loss or compensation |
| Persistent unintentional weight trend | Professional consultation | Cause speculation |

## Brief template

> **Data confidence: [high/medium/low].** [Signal(s)] [were stable/moved outside] your recent pattern over [window]. This does not determine a cause. **Today:** [one optional, achievable action]. [If warranted: persistence/symptom escalation sentence.]

Use no more than two actions. Avoid burying the recommendation under disclaimers; place uncertainty in one plain sentence.
