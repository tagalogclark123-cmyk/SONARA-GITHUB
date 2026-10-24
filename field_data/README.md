# SONARA field recordings

Audio recorded by a SONARA sensing node in real poultry pens, with the model's output for every clip.
These recordings are **not** part of the training, validation or locked test data, and nothing in the
model or its threshold was changed because of them.

## Sessions

| Session | Date / time | Birds | Health status (source) | Clips | Flagged (p >= 0.535) | Max p | Zone alert |
|---|---|---|---|---|---|---|---|
| [`2026-10-22_damilag_s1`](2026-10-22_damilag_s1/) | 22 Oct 2026, 12:15-13:16 | 4 chicks, 3 weeks old | healthy (caretaker report) | 123 | 5 (4.1%) | 0.659 | none |
| [`2026-10-22_damilag_s2`](2026-10-22_damilag_s2/) | 22 Oct 2026, 13:37-14:34 | 4 birds, 3 months old | respiratory illness (caretaker report) | 114 | 5 (4.4%) | 0.922 | none |
| [`2026-10-24_gaca_s3`](2026-10-24_gaca_s3/) | 24 Oct 2026, 11:24-11:46 | 17 birds, about 4 weeks old | all healthy except one sick bird (owner report) | 50 (34 usable) | 1 of 34 (2.9%) | 0.632 | none |
| [`2026-10-24_gaca_s4`](2026-10-24_gaca_s4/) | 24 Oct 2026, 11:53-12:43 | same birds as s3 | same as s3 | 108 (**19 usable**) | 0 of 19 | 0.400 | none |
| [`2026-10-24_palitoc_s5`](2026-10-24_palitoc_s5/) | 24 Oct 2026, 14:48-15:21 | same sick birds as s2 | respiratory illness (caretaker report) | 68 (61 usable) | 0 of 61 | 0.469 | none |

Flag counts use usable clips only (see "Damaged clips" below). Machine-readable version: [`sessions.csv`](sessions.csv). Each session folder has its own README with full details.

## How the audio was recorded

| | |
|---|---|
| Node | ESP32 dev board + INMP441 MEMS microphone (I2S), soldered on perfboard, LoRa module removed |
| Link | ESP-NOW to a bridge ESP32, USB serial (921600 baud) to a Raspberry Pi 4 (`sonara_receiver.py`) |
| Duty cycle | one 5-s clip every 30 s (the node does not listen for the other 25 s) |
| Format | WAV, 16 kHz, 16-bit, mono, 80,000 samples (5.0 s) per clip |
| File name | `node{N}_clip{#####}_{YYYYmmdd-HHMMSS}.wav`; the time is when the Pi finished receiving the clip, about 9 s after the recording started. The Pi has no battery clock; session times agree with the observer's notes (12:17-13:17 for session 1) |
| Lost packets | a lost ESP-NOW packet is stored as 120 zero samples; the reports count these per clip (`lost_packets_est`) |
| Damaged clips | a clip missing more than 33 of its 667 packets (more than 5% of the audio) is marked `usable = 0` in `report/clips.csv` and left out of all statistics. The audio files are kept |
| Processing | none. Files are exactly as written by the receiver |

## How the clips were classified

- Model: system model B8 (MobileNetV3-Small, log-mel input), seed 42, TorchScript export `sonara_system_model.pt`, run on the Raspberry Pi 4 CPU.
- Operating point: 90%-recall threshold **0.535** (from `deployment_config.json`, chosen on validation data during the final evaluation).
- Zone alert rule: at least 8 of the last 20 clips from one node flagged.
- `predictions_live.csv`: written live during the session by `sonara_classify.py --watch`.
- `report/`: written after the session by [`tools/sonara_field_report.py`](../tools/sonara_field_report.py) (classification, audio-quality checks, band-energy comparison with SmartEars, summary, timeline chart).

## Labels: what they mean and what they do not

- The only health information is the **caretaker's report for the whole pen**. There was no veterinary examination and no laboratory test. Treat it as a weak, pen-level label.
- A pen label is **not** a clip label. Most 5-s clips from a pen with sick birds contain no distress sound at all (birds can be quiet, asleep or far from the mic).
- Clip-level labels can only come from listening. Each session has a blind listening set in `review/`; listeners fill in `review_sheet.csv` before opening the key.
- "Flagged" means the model found acoustic patterns similar to the respiratory-distress clips it was trained on. It is a screening signal, not a diagnosis.

## How to use this data correctly

- Unit of analysis for any comparison between pens is the **session/pen**, not the clip. Consecutive clips share the same birds, room and noise, so they are not independent.
- If these clips are ever used for training or fine-tuning, split by **session** (never by clip), and keep at least one session completely unseen for testing.
- With two sessions from one site on one day, results are descriptive only. They are not a field accuracy, recall or false-alarm rate.

## Main observations so far

- Both pens had almost the same flag rate (4.1% vs 4.4%) and the same median probability (0.065 vs 0.064). The model did **not** separate the reported-sick pen from the reported-healthy pen at the session level.
- The sick pen produced the only strong flags (0.92, 0.85, 0.73); all flags in the healthy pen were borderline (0.59 to 0.66). Whether those clips contain distress sounds has not been checked by listening yet.
- The sick birds were mostly sleeping/lethargic, so there may have been little to hear. An acoustic system can only detect distress that makes a sound.
- The frequency balance of the field audio (about 86 to 88% of energy below 250 Hz) is close to the SmartEars training clips (74 to 95%), unlike the laptop-speaker replay test.
- Inference on the Pi in the field (22 Oct): median about 100 ms, 95th percentile about 270 ms (bench: 52 / 127 ms). Possible thermal or power throttling; not yet checked.
- 24 Oct (sessions 3 and 4): the ESP-NOW link failed for long stretches (105 of 158 clips damaged, 80 almost empty). An empty clip gets probability 0.355 and partly empty clips can cross the threshold: the 3 live flags in session 4 came from damaged clips. Damaged clips must be filtered before any analysis.
- In the usable 24 Oct clips (17 birds, one reported sick), 1 of 53 clips was flagged (borderline, 0.632).
- Session 5 re-recorded the sick birds from session 2: 0 of 61 usable clips flagged (session 2: 5 of 114, three strong). One damaged clip in session 5 scored 0.969, confirming that damaged clips must be filtered.
- Across all sessions so far, the model has not separated reported-sick from reported-healthy birds at the session level.

## Consent and privacy

Recorded on site; the caretaker provided the information about the birds. Audio may contain human voices from people near the pens.
Before this data is shared further, confirm the farm owner's consent to publish the recordings and the site name.
