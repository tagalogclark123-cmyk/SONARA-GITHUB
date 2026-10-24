# Session 2026-10-24_gaca_s4: 17 birds, one sick (second run of the day)

| | |
|---|---|
| Date and time | 24 Oct 2026, 11:53:35 to 12:43:53 (Asia/Manila), about 50 min |
| Site | Gaca residence |
| Pen label used in reports | Cage (node 1) |
| Birds | 17, about 4 weeks old (same birds as session 3) |
| Health status | all healthy except **one sick bird** (owner report, no veterinary examination). Signs not recorded |
| Mic position | node **inside** the cage |
| Node power | USB-C (source not recorded) |
| Distance node to bridge/Pi | not recorded |
| Observer | Karl Michael Gaca |
| Related session | [`2026-10-24_gaca_s3`](../2026-10-24_gaca_s3/): same cage and birds, 7 min earlier |

## Data

- `audio/`: 108 clips, exactly as received (includes damaged and empty clips, kept on purpose as a record of the link failure).
- `predictions_live.csv`: model output written live on the Pi (includes the damaged clips).
- `report/`: regenerated with the updated `tools/sonara_field_report.py`; `clips.csv` has a `usable` column (see session 3).
- `review/`: blind listening set (0 flagged + 15 not flagged), key in `review/review_key_OPEN_AFTER_LISTENING.csv`.

## Radio link: mostly failed

**89 of 108 clips are damaged**, 80 of them almost completely empty (666 of 667 packets lost) from 12:07 to the end. Packet loss grew gradually from about 12:01, which points to the radio link (distance, obstacles, or power), not the microphone. Some clips were split into two files (the same clip number twice) because packets arrived too slowly.

Why this matters: the model gives an empty (all-zero) clip a probability of 0.355, and partly empty clips can cross the threshold. The 3 clips flagged live on the Pi (12:02 to 12:03) were all damaged (10 to 24% of the audio missing) and are not counted.

## Model output (threshold 0.535, usable clips only)

- **0 of 19 usable clips flagged.** Highest probability 0.40; median 0.078. No zone alert.
- Usable clips are only from 11:53 to 12:07.

## Limitations

- Only 19 usable clips (about 13 minutes): too few for any conclusion on its own.
- Same limitations as session 3 (one sick bird in 17, node inside the cage, owner report).
