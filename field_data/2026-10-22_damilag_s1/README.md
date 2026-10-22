# Session 2026-10-22_damilag_s1: caretaker-reported healthy chicks

| | |
|---|---|
| Date and time | 22 Oct 2026, 12:15:40 to 13:16:41 (Asia/Manila), about 1 h |
| Site | Palitoc compound, Damilag |
| Pen label used in reports | Chick pen (node 1) |
| Birds | 4 chicks, 3 weeks old |
| Health status | healthy, **caretaker report** (no veterinary examination) |
| Mic position | node on top of the cage, touching it; less than 1 m from the birds |
| Observer | Karl Michael Gaca |
| Recorded first | yes (before the sick pen, to avoid carrying infection to healthy birds) |

## Data

- `audio/`: 123 clips (`node1_clip00082` to `node1_clip00204`), 123 of 123 expected; 4 clips with lost packets; 17 very quiet clips (< -60 dBFS in 200-4000 Hz).
- `predictions_live.csv`: model output written live during the session.
- `report/`: `summary.txt`, `report.html` (timeline chart), `clips.csv` (per-clip probability, flag, level, peak, clipping, lost packets, band-energy shares).
- `review/`: blind listening set (5 flagged + 15 not flagged, shuffled) and `review_sheet.csv`. The key is `review/review_key_OPEN_AFTER_LISTENING.csv`.

## Model output (threshold 0.535)

- Flagged: **5 of 123 (4.1%)**, all borderline (0.590 to 0.659). Median probability 0.065. No zone alert.
- Two flags were one minute apart (12:22:10 and 12:23:10, loud clips): possibly the same event.
- Two flags were very quiet clips (-56 and -61 dBFS); possible cage vibration because the node touched the cage (not checked).
- Energy below 250 Hz: 85.7% (SmartEars Healthy 73.6%, Sick 94.9%, None 82.8%).
- Inference on the Pi: median 100 ms, 95th percentile 268 ms.

## Limitations

- 3-week-old chicks are probably younger than the birds in the SmartEars training data, so this is an out-of-domain check.
- Only 4 birds; one pen; one hour.
- Mic touched the cage, so bumps from the birds may be in the audio.
- Caretaker report, not a veterinary check.

Notes not recorded during the session: noise sources and times, exact mic height.
