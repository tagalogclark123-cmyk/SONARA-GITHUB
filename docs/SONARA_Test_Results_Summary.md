# SONARA Test Results Summary

30 Oct 2026 · SONARA capstone team (USTP BS Data Science)

These are feasibility checks of the prototype, not field accuracy results. See Limitations.

## At a glance

The full pipeline works end to end. Through the node, the model recognises a Sick clip played from a speaker at up to 2 m, and at 10-15 m. With live birds it has not yet separated sick from healthy groups.

- **Model on the Pi = evaluated model:** identical probabilities on all full-length test clips (SmartEars accuracy 0.922, seed 42); inference median 52-100 ms.
- **Speaker playback, good speaker:** Sick clip flagged in 94% of recordings at 2 m and 80% at 1 m; Healthy clip never flagged at 1 m. At 5 m it fell to 61%; 58-78% at 10-15 m; an unattended 4 m run was excluded and will be repeated.
- **Laptop-speaker replay (19 Oct):** distress detection collapsed (3/19). Simulation traced most of it to the laptop speaker's frequency distortion, which the 30 Oct speaker checks support.
- **Live birds (5 sessions, 2 sites):** 0-4.4% of clips flagged in every session, sick or healthy. No session-level separation yet; sick birds were mostly quiet or resting.
- **Radio link:** all clips complete at 2-15 m in clear view, open air and in a paper bag; retries start near 15 m (signal about -85 dBm). A node inside a wire cage lost most of its audio (24 Oct).
- **Damaged clips must be filtered:** a partly empty clip scored p = 0.97 once. The report tool now excludes clips missing more than 5% of their packets.

## System under test

| Part | What was tested |
| --- | --- |
| Node | ESP32 DevKit V1 + INMP441 on perfboard; records 5 s at 16 kHz, 16-bit (one clip every 30 s; 20 s in test firmware) |
| Link | ESP-NOW to a bridge ESP32, USB serial (921,600 baud) to a Raspberry Pi 4; 667 packets per clip |
| Gateway | Raspberry Pi 4 rebuilds clips, runs the model, logs results |
| Model | MobileNetV3-Small B8, seed 42, TorchScript; threshold 0.535 (90%-recall operating point); zone alert at 8 of the last 20 clips |
| Power | USB power bank (no charging module; battery runtime not yet measured) |

## Model on the Pi (19 Oct)

The exported model on the Pi reproduced the evaluated model exactly on every full-length clip. This is a fidelity check, not a new performance result.

| Set | Items | Pi vs evaluation | Pi metrics at 0.535 |
| --- | --- | --- | --- |
| SmartEars locked test | 871 | identical (max diff 0.0000 on 795 full-length clips) | accuracy 0.922, distress recall 244/274, false flags 38/597, ROC-AUC 0.964 |
| PVSD external | 346 | identical on 304 full-length files; 4 of 42 short files changed flag | accuracy 0.777, ROC-AUC 0.807 |

- Short clips (under 5 s) differ because the export pads with zeros; node clips are always 5 s, so live use is unaffected.
- Inference on the Pi 4: median 52 ms, 95th percentile 127 ms (bench). In the field (22 Oct) median 100 ms, 95th percentile about 270 ms; at home (24 and 30 Oct) median 57-75 ms with no throttling (max 54 C).
- Time from end of recording to result: about 4.1-4.2 s, almost all of it the radio transfer.

## Replay test with the laptop speaker (19 Oct)

Through a laptop speaker, distress detection collapsed from 17 of 19 recordings (originals) to 3 of 19. Simulation traced most of the drop to the speaker's frequency distortion.

- Setup: 20 locked-test clips looped through the laptop speaker, node 30-50 cm away. Playback was quieter than planned (about 6 dB above room noise in the 200-4000 Hz band).
- Measured distortion: bass cut 6-10 dB below 250 Hz, a +15 dB peak at 1.2-1.5 kHz, highs cut 7-8 dB.
- Simulation on the original clips: distortion alone dropped distress flags from 15/17 to 7/17; noise alone kept 15/17 but raised false flags on non-distress clips from 2/10 to 5/10.
- Meaning: the model is sensitive to the frequency balance of the input. It was trained with volume changes only, no equaliser or noise augmentation.

## Field sessions with live birds (22 and 24 Oct)

In all five sessions the model flagged 0-4.4% of usable clips, whether the birds were reported healthy or sick, and no zone alert fired.

| Session | Birds | Health (source) | Usable clips | Flagged | Strongest flag |
| --- | --- | --- | --- | --- | --- |
| s5, 24 Oct, Palitoc | same sick birds as s2 | respiratory illness (caretaker) | 61 of 68 | 0 | 0.47 |
| s4, 24 Oct, Gaca residence | 17, about 4 weeks | one sick bird (owner) | 19 of 108 | 0 | 0.40 |
| s3, 24 Oct, Gaca residence | 17, about 4 weeks | one sick bird (owner) | 34 of 50 | 1 (2.9%) | 0.63 |
| s2, 22 Oct, Palitoc | 4, 3 months | respiratory illness (caretaker) | 114 of 114 | 5 (4.4%) | 0.92 |
| s1, 22 Oct, Palitoc | 4 chicks, 3 weeks | healthy (caretaker) | 123 of 123 | 5 (4.1%) | 0.66 |

- The sick birds in s2 were mostly sleeping; quiet birds give the mic nothing to hear.
- s3 and s4 lost most of their audio to radio failures with the node inside a wire cage.
- Health labels are caretaker or owner reports for the whole pen, not veterinary checks; a pen label is not a clip label.
- All sessions are in `field_data/` with audio, reports and blind listening sets (listening not yet done).

## Radio link range (24 Oct, home, clear line of sight)

Every clip arrived complete from 2 to 15 m, in open air and inside a paper bag; the link was approaching its limit at 15 m.

| Distance | Signal, open air (median / weakest) | Signal, paper bag (median / weakest) | Complete clips (open / bag) | Retries per clip (open) |
| --- | --- | --- | --- | --- |
| 2 m | -63 / -65 dBm | -70 / -74 dBm | 7/7, 6/6 | 0 |
| 5 m | -74 / -83 dBm | -73 / -85 dBm | 7/7, 6/6 | 0 |
| 10 m | -84 / -94 dBm | -84 / -91 dBm | 6/6, 6/6 | 0 |
| 15 m | -82 / -87 dBm | -80 / -84 dBm | 6/6, 6/6 | 2 (max 3) |

- Raw delivery without retries was 100% at every spot; send time 4.0-4.1 s per clip (about 40 kB/s).
- The paper bag made no measurable difference to the radio.
- On 30 Oct, about one clip per run lost 384-508 packets even with a strong signal (-46 dBm), 100% raw delivery and no retries. The loss is between the bridge and the Pi (USB cable or serial buffer). The damaged-clip filter keeps these out of the results, but it must be fixed before deployment.
- Not yet tested: 20 m and beyond, walls, a wire cage, and the farm itself.

## Speaker checks with a Sick clip (30 Oct, good speaker)

Through the node, the model flagged the Sick clip in 94% of recordings at 2 m and 61% at 5 m; the Healthy clip was never flagged at 1 m. It was flagged in 7 of 9 recordings at 10 m and 7 of 12 at 15 m, and background noise alone was never flagged.

| Distance | Clip | Place | Recordings while playing | Flagged | Median p |
| --- | --- | --- | --- | --- | --- |
| 1 m | Healthy | indoors, home | 9 | 0 | 0.066 |
| 1 m | Sick | indoors, home | 10 | 8 (80%) | 0.981 |
| 2 m | Sick | indoors, home | 18 | 17 (94%) | 0.948 |
| 5 m | Sick | indoors, home | 31 | 19 (61%) | 0.655 |
| 10 m | Sick | home, second location | 9 | 7 (78%) | 0.813 |
| 15 m | Sick | home, second location | 12 | 7 (58%) | 0.639 |
| none | background | home, second location | 12 | 0 | 0.012 |

- Clips: SmartEars `Sick/rpi0104-20240323131600-3` (original p 0.997) and `Healthy/rpi0105-20240119201100-0` (original p 0.038), each looped through a Bluetooth/desktop speaker at one fixed volume.
- Indoor runs: recordings during silence and four with loud interruptions were excluded; silent recordings were never flagged (max p 0.18). The recorded level fell only about 3 dB from 2 to 5 m (indoor echo), yet p dropped strongly: consistent with the model's sensitivity to sound character.
- A 4 m run was excluded: the tester stepped away during it, so it is not known what was playing or where the speaker was (it ran about 16 minutes against a 3-minute loop). Its result was 11 of 43 recordings flagged. It will be repeated with someone present.
- The good speaker restored detection compared with the laptop replay, supporting the distortion diagnosis.
- 10 and 15 m (30 Oct afternoon, during rain, other conditions held the same): a first spot was abandoned because it was too noisy (the clip was only about 2 dB above the background; 0 of 13 flagged). At the spot used, rain noise rose and fell (-40.8 to -49.8 dBFS), so levels cannot be compared between runs.
- A check that does not use the model confirmed every flagged recording contains the Sick clip: each recording was matched against the original clip (correlation 0.32-0.42 when the clip is clear, against at most 0.08 for a reversed copy of the clip). Counting only recordings where the clip was clearly present: 10 m 7 of 8 flagged, 15 m 6 of 7. Five early 15 m recordings held the clip only faintly (correlation about 0.2) and one was flagged; one 10 m recording was drowned out by a loud burst of noise and held no detectable clip (not flagged).
- Takeaway: at 10-15 m, whether the clip stood out from the background mattered more than distance.

## Speaker checks: Sick and Healthy clips by distance

Same speaker setup as above, with the Healthy clip now played at every distance. Across all distances the Sick clip was flagged in 58 of 80 recordings and the Healthy clip in 4 of 90.

| Distance | Sick: flagged / recordings | Healthy: flagged / recordings | Median pBackground | Indoor / outdoor recordings |
| --- | --- | --- | --- | --- |
| 1 m | 8 / 10 | 0 / 12 | 0.06 | 12 / 0 |
| 2 m | 17 / 18 | 0 / 20 | 0.09 | 20 / 0 |
| 5 m | 19 / 31 | 1 / 28 | 0.18 | 28 / 0 |
| 10 m | 7 / 9 | 1 / 14 | 0.15 | 14 / 12 |
| 15 m | 7 / 12 | 2 / 16 | 0.25 | 16 / 0 |

## Limitations

None of these tests gives a field accuracy or recall for detecting sick birds.

- **Speaker is not a chicken:** detection distances depend on the playback volume, which was not measured in dB.
- **Very few clips:** the distance checks used one Sick and one Healthy clip; repeated recordings of the same sound are not independent.
- **Weather:** the 10-15 m checks ran during rain; one rainy afternoon does not show robustness to rain.
- **Weak ground truth:** bird health came from caretaker or owner reports per pen; no veterinary examination; "Sick" clips are the dataset's own labels.
- **Small field sample:** 5 sessions, 2 sites, a few birds each, mostly young or resting birds.
- **Duty cycle:** the node listens 5 s in every 30 s, so most short sounds (a sneeze) are missed.
- **Home conditions:** range and speaker tests ran at home with Wi-Fi nearby; a poultry house may behave differently.
- **Not yet measured:** battery runtime, range beyond 15 m, walls, the farm's radio environment.

## Recommendations and next steps

For deployment now: keep birds within about 2 m of each mic and nodes within about 10 m of the bridge, in clear view and never inside a wire cage.

- [ ] Repeat 4 m with someone present the whole time; repeat 10-15 m once in dry weather
- [ ] Full mic range test: 8 clips at 0.5-5 m (`sonara_micrange_playback.wav`), volume noted with a sound-meter app
- [ ] Fix the packet loss between the bridge and the Pi (try another USB cable; check the serial buffer)
- [ ] Radio: 20 m and beyond, one and two walls, a wire cage, then a short check on site at the farm
- [ ] Blind listening of the review sets in `field_data/` before opening the keys
- [ ] Power bank runtime: run one node until it stops and log the hours
- [ ] Discuss with the adviser whether to retrain with equaliser, echo and noise augmentation (a model change after final evaluation)
- [ ] Paper: update LoRa to ESP-NOW, the deployed model, and these results as feasibility checks
