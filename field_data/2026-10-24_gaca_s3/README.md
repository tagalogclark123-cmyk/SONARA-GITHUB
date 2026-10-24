# Session 2026-10-24_gaca_s3: 17 birds, one sick (first run of the day)

| | |
|---|---|
| Date and time | 24 Oct 2026, 11:24:09 to 11:46:05 (Asia/Manila), about 22 min; ended when the node lost its connection |
| Site | Gaca residence |
| Pen label used in reports | Cage (node 1) |
| Birds | 17, about 4 weeks old |
| Health status | all healthy except **one sick bird** (owner report, no veterinary examination). Signs of the sick bird not recorded |
| Mic position | node **inside** the cage |
| Node power | USB-C (source not recorded) |
| Distance node to bridge/Pi | not recorded |
| Observer | Karl Michael Gaca |
| Related session | [`2026-10-24_gaca_s4`](../2026-10-24_gaca_s4/): same cage and birds, restarted 7 min later |

## Data

- `audio/`: 50 clips, exactly as received. One stray clip from before the session (`node1_clip00017_20261024-112359.wav`) is excluded.
- `report/clips.csv` has a `usable` column: 1 = at most 33 of the 667 radio packets lost (at most 5% of the audio missing), 0 = damaged.
- `report/`: `summary.txt`, `report.html`, `clips.csv`. Regenerated after the session with the updated `tools/sonara_field_report.py` (same model; probabilities identical to the Pi's to 5 decimals), so the speed line in the summary is not the Pi's.
- `review/`: blind listening set (1 flagged + 15 not flagged, shuffled), key in `review/review_key_OPEN_AFTER_LISTENING.csv`.
- No `predictions_live.csv`: the live log of this run was not kept.

## Radio link

16 of 50 clips are damaged (11:28 to 11:36; 62 to 656 of 667 packets lost), then the link recovered until 11:46 and the node disconnected. Damaged clips contain long runs of zeros and are left out of all numbers below.

## Model output (threshold 0.535, usable clips only)

- **1 of 34 usable clips flagged (2.9%)**: p = 0.632 at 11:28:09 (borderline). Median probability 0.082; no other clip above 0.53. No zone alert.
- Energy below 250 Hz: about 81% (SmartEars 74 to 95%).

## Limitations

- Only one bird in 17 reported sick; most clips may contain no sound from that bird.
- Node inside the cage: birds can peck, bump or stand on it.
- Short session (34 usable clips); owner report, not a veterinary check; signs not recorded.
