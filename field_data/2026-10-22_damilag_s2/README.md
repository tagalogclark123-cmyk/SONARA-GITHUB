# Session 2026-10-22_damilag_s2: caretaker-reported respiratory illness

| | |
|---|---|
| Date and time | 22 Oct 2026, 13:37:52 to 14:34:22 (Asia/Manila), about 1 h |
| Site | Palitoc compound, Damilag |
| Pen label used in reports | Distress pen (node 1) |
| Birds | older than session 1; number, age and breed **not recorded** |
| Health status | respiratory illness, **caretaker report** (no veterinary examination). Specific signs, number of affected birds, duration and medication **not recorded** |
| Behaviour during recording | birds mostly sleeping/lethargic (observer note, 14:33) |
| Mic position | not recorded |
| Observer | Karl Michael Gaca |

## Data

- `audio/`: 114 clips (`node1_clip00000` to `node1_clip00113`), 114 of 114 expected; 3 clips with lost packets; 12 very quiet clips (< -60 dBFS in 200-4000 Hz).
- `predictions_live.csv`: model output written live during the session.
- `report/`: `summary.txt`, `report.html`, `clips.csv`.
- `review/`: blind listening set (5 flagged + 15 not flagged, shuffled) and `review_sheet.csv`. The key is `review/review_key_OPEN_AFTER_LISTENING.csv`.

## Model output (threshold 0.535)

- Flagged: **5 of 114 (4.4%)**. Median probability 0.064. No zone alert.
- Strongest flags: 0.922 (14:00:52), 0.849 (14:04:22), 0.733 (13:47:51), 0.659 (14:04:52), 0.632 (14:15:22). All quiet clips (-49 to -60 dBFS). 4 of the 5 flags fell between 14:00 and 14:15.
- Energy below 250 Hz: 88.0%.
- Inference on the Pi: median 99 ms, 95th percentile 273 ms.

## Comparison with session 1

Same flag rate (4.1% vs 4.4%) and same median probability (0.065 vs 0.064). At the session level the model did not separate this pen from the healthy chick pen. This session did produce the only strong flags (above 0.70). Whether those clips contain respiratory sounds has not been checked by listening.

## Limitations

- Birds were mostly resting, so there may have been few or no distress sounds to record.
- Missing details (bird count, age, signs, mic distance) limit interpretation; add them here if the caretaker can still provide them.
- Caretaker report, not a veterinary check. One pen, one hour.
