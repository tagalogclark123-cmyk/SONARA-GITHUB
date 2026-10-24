# Session 2026-10-24_palitoc_s5: caretaker-reported sick birds (second recording of the same birds as session 2)

| | |
|---|---|
| Date and time | 24 Oct 2026, 14:48:08 to 15:21:09 (Asia/Manila), about 33 min |
| Site | Palitoc compound, Damilag |
| Pen label used in reports | Sick pen (node 1) |
| Birds | the same sick birds as [`2026-10-22_damilag_s2`](../2026-10-22_damilag_s2/) (4 birds, 3 months old on 22 Oct), per the observer |
| Health status | respiratory illness, **caretaker report** (no veterinary examination). Specific signs, number of affected birds and any treatment since 22 Oct not recorded |
| Mic position | not recorded |
| Node power | not recorded |
| Observer | Karl Michael Gaca |

## Data

- `audio/`: 68 clips, exactly as received. One stray clip from before the session (`node1_clip00017_20261024-144733.wav`, received before the node restarted at clip 0) is excluded, as in session 3.
- `predictions_live.csv`: model output written live on the Pi (includes the stray clip).
- `report/`: `summary.txt`, `report.html`, `clips.csv` (with the `usable` column). Regenerated without the stray clip using `tools/sonara_field_report.py` (same model as on the Pi).
- `review/`: blind listening set (0 flagged + 15 not flagged), key in `review/review_key_OPEN_AFTER_LISTENING.csv`.

## Radio link

7 of 68 clips damaged (14:58 to 15:14), 1 almost empty; much better than sessions 3 and 4. One damaged clip (14:58:28, 150 of 667 packets lost) scored **p = 0.969**: without the damaged-clip filter it would have been counted as a strong flag. This is direct evidence that partly empty clips can produce false flags.

## Model output (threshold 0.535, usable clips only)

- **0 of 61 usable clips flagged.** Highest probability 0.469; median 0.041. No zone alert.
- Energy below 250 Hz: about 67% (lower than the other sessions; SmartEars 74 to 95%).

## Comparison with session 2 (same birds, 22 Oct)

Session 2: 5 of 114 flagged (4.4%), median 0.064, three strong flags (0.73 to 0.92). Session 5: 0 of 61, median 0.041. The model did not flag these reported-sick birds in this session. Possible reasons, none checked: few or no audible respiratory sounds during the recording (birds resting, recovering or treated), mic position, or the model missing them.

## Limitations

- Bird condition on 24 Oct, signs, mic position and power not recorded.
- 33 minutes; 4 birds; caretaker report, not a veterinary check.
