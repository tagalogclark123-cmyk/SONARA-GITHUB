# Hyperparameter tuning of the system model (B8): results

Results received 16 October 2026. Notebook: `SONARA_Hyperparameter_Tuning.ipynb` (code identical to the version on `main` after PR #6), Google Colab, run over several sessions between 14 and 16 October; most sessions had a T4 GPU, some ran on CPU (see "How the run went").

**Every number here is a validation result.** The locked test set (871 clips, id `bf636617`) and PVSD were not used.

Files in this folder, all saved by the notebook unless noted:

| File | Contents |
| :- | :- |
| `SONARA_Hyperparameter_Tuning_executed.ipynb`, `notebook_text_outputs.txt` | The notebook as it ran and all its text output |
| `search_trials.csv` | Every search trial: settings, score, state, minutes |
| `optuna_study.db` | The Optuna study itself (SQLite), including start and end times |
| `setting_importance.csv`, `figures/figure_setting_importance.png` | Importance of each setting (fANOVA) |
| `figures/figure_setting_vs_score.png` | Each setting plotted against the score |
| `confirm/*.json`, `confirmation_results.csv` | Confirmation runs, one file per settings and seed |
| `chosen_system_model_config.json` | The decision the final evaluation reads |

## What was searched

22 training settings of B8 (MobileNetV3-Small, ImageNet weights, no normalization): optimizer (AdamW, Adam, SGD), learning rate, weight decay, batch size (8 to 128), class weights, schedule (cosine, constant, plateau), warm-up, maximum epochs (20 to 100), patience, dropout, label smoothing, mixup, loudness change and its share, time shift and its share, and the probability, width and number of time and frequency masks. Ranges and reasons are in the notebook.

## Stage 1: the search

- Budget reached: 20.3 hours of training. **71 trials**: 30 completed, 37 stopped early by the pruner, 4 interrupted by Colab disconnects (trials 20, 28, 36 and 69, left "running" in the database).
- Search split (seed 1), validation ROC-AUC. **Run 2 settings (trial 0): 0.9684, 12th of the 30 completed trials.** 21 completed trials scored above 0.96 and 7 above 0.97; the median was 0.965.
- One completed trial (9: Adam, learning rate 0.0062) collapsed to 0.5, which is chance; that learning rate was too high.
- Best completed trials:

| Trial | ROC-AUC | Main features |
| :- | :- | :- |
| 3 | 0.9733 | Adam, lr 2.0e-4, batch 32, constant schedule, 60 epochs, label smoothing 0.19, mixup 0.6, ±24 dB loudness on 25% of clips, 3 time + 3 frequency masks (frequency masks up to 32.5% of bands) |
| 47 | 0.9724 | Adam, lr 5.0e-4, batch 64, constant, 70 epochs, label smoothing 0.17, mixup 0.6, ±21 dB on 25%, 3 + 3 masks |
| 38 | 0.9720 | Adam, lr 1.2e-3, batch 64, constant, 80 epochs, label smoothing 0.16, mixup 0.5, ±24 dB on 25%, 3 + 3 masks |
| 27 | 0.9717 | Adam, lr 2.8e-4, batch 32, constant, 60 epochs, label smoothing 0.20, mixup 0.5, ±24 dB on 25%, 3 + 3 masks |

- The search converged on one region: Adam, a constant learning rate, strong label smoothing (0.15 to 0.20), strong mixup (0.4 to 0.8), large but infrequent loudness changes, and three masks of each kind.
- After the 25 random start trials, 32 of the 46 later trials were Adam with a constant learning rate; most were stopped early, but those that finished averaged 0.970 against 0.907 for the random start trials.
- **Trials 3 and 23 used identical settings and scored 0.9733 and 0.9692.** Training the same settings twice on the same split moved the score by 0.004, which is about the gap between the best trial and the Run 2 settings (0.005). Differences of that size between trials are within training noise.
- Importance of each setting for the score (fANOVA, from the 30 completed trials; rough, because the search concentrated in one region): loudness share 0.16, mixup 0.12, warm-up 0.10, loudness size 0.07, time-mask probability 0.06, time shift 0.06; optimizer, schedule and class weights each 0.006 or less. Augmentation settings matter most; optimizer and schedule choices matter least.

## Stage 2: confirmation on the three Run 2 splits

The 3 best search settings and the Run 2 settings were each retrained on seeds 7, 21 and 42.

| Settings | ROC-AUC | Accuracy @0.5 | Distress F1 @0.5 | False alarms @0.90 recall | False alarms @0.95 recall | ROC-AUC vs Run 2 | Seeds better | Loudness condition |
| :- | :- | :- | :- | :- | :- | :- | :- | :- |
| **Run 2 settings** | **0.9704 ± 0.0017** | 0.9197 ± 0.0048 | 0.8867 ± 0.0088 | 0.0688 ± 0.0098 | **0.1344 ± 0.0010** | — | — | met |
| Trial 3 | 0.9657 ± 0.0011 | 0.9216 ± 0.0064 | 0.8898 ± 0.0043 | 0.0627 ± 0.0048 | 0.1462 ± 0.0209 | −0.0047 | 0 of 3 | met |
| Trial 47 | 0.9673 ± 0.0022 | 0.9149 ± 0.0015 | 0.8807 ± 0.0043 | 0.0734 ± 0.0067 | 0.1497 ± 0.0255 | −0.0031 | 0 of 3 | met |
| Trial 38 | 0.9627 ± 0.0066 | 0.9119 ± 0.0131 | 0.8748 ± 0.0148 | 0.0829 ± 0.0121 | 0.1920 ± 0.0434 | −0.0077 | 0 of 3 | met |

Per seed (validation ROC-AUC):

| Settings | Seed 7 | Seed 21 | Seed 42 |
| :- | :- | :- | :- |
| **Run 2 settings** | **0.9698** | **0.9723** | **0.9692** |
| Trial 3 | 0.9647 | 0.9668 | 0.9657 |
| Trial 47 | 0.9683 | 0.9689 | 0.9648 |
| Trial 38 | 0.9616 | 0.9698 | 0.9566 |

The Run 2 settings reproduced their second-pass result (0.9704 here against 0.9698 then; seed 21 identical at 0.9723). All candidates changed recall and false alarms by at most 0.034 at ±10 dB.

Trial 3 reached its best checkpoint at or near its last allowed epoch on every seed (epochs 60, 53 and 59 of 60), so it may have been cut short by its own 60-epoch limit. That limit was part of its settings, and it was still 0.005 below the Run 2 settings, so a longer run is unlikely to change the decision.

## How the run went

Two problems in the run are worth stating; neither changes the decision.

1. **Some sessions had no GPU.** Five search trials took 2 to 3.5 hours each (trials 23, 27, 32, 33 and 34) instead of the usual 4 to 10 minutes, and three confirmation runs on seed 7 took 1 to 3 hours. Those ran on a CPU. The training is the same on CPU, so the scores are valid, but the five slow trials used about 12.5 of the 20 search hours. **The search therefore tried about 70 settings instead of the roughly 150 to 200 a GPU-only run would have reached.**
2. **Five trials repeated earlier ones.** Trials 21 to 25 used exactly the same settings as trials 1 to 5. The search's random generator is seeded with a fixed number, so after a disconnect the restarted session drew the same random start settings again. Five of the 71 trials were therefore repeats. The one useful side effect is trial 23, which completed and measured the run-to-run noise above. If the notebook is used again, the generator should be seeded differently in each session.

Neither problem affects the validity of the comparison: the decision rests on the confirmation stage, which retrained the best settings and the Run 2 settings on three independent splits.

## Decision

By the rule fixed before the search, **no tuned setting replaces the Run 2 settings**: every candidate had a lower mean validation ROC-AUC and was lower on all 3 splits. `chosen_system_model_config.json` therefore contains the Run 2 settings (AdamW, learning rate 3e-4, weight decay 0.01, batch size 16, cosine schedule with 2 warm-up epochs, 40 epochs, patience 10, dropout 0.2, label smoothing 0.02, mixup 0.2, ±12 dB loudness change on every clip, time shift up to 0.5 s on half the clips, one time mask and one frequency mask of up to 12.5%, class weights balanced). The final evaluation reads this file.

## What this shows

1. **The Run 2 settings are no longer a convention; they are supported by a search.** Among 71 trials (66 distinct settings) across 22 parameters, none did better when checked on independent splits.
2. **The best search scores were partly luck on one split** (the "winner's curse"): they were selected because they scored highest on the search split, and on three fresh splits all three fell below the Run 2 settings.
3. **Performance is flat near the top.** Very different recipes (Run 2's cosine schedule with mild augmentation, and the search's constant learning rate with heavy augmentation) reach about the same ROC-AUC, around 0.97. The result does not hinge on a fragile choice of settings.
4. **The Run 2 settings also have the lowest false alarms at 95% recall** (13.4% against 14.6% to 19.2%), the operating point the team considered. Trial 3 had slightly fewer false alarms at 90% recall (6.3% against 6.9%), but not on ROC-AUC.
5. **All candidates passed the loudness condition** at both operating points.

## For the paper

Suggested wording: "Training settings of the selected model were examined with a guided search (Optuna, Tree-structured Parzen Estimator) over 22 parameters within a 20-hour budget (71 trials, 66 distinct settings). The three best settings from the search split were retrained on three independent validation splits and compared with the settings used in model selection. None improved validation ROC-AUC on any of the three splits, so the original settings were retained. Random seeds were not tuned."

If the panel asks how thorough the search was, the honest answer is that part of the budget ran on CPU sessions, so fewer settings were tried than planned, and the top of the search was flat (21 of the 30 completed trials scored between 0.96 and 0.973).

## Caution

These are validation results. 71 trials plus the confirmation runs have now used the development data, so validation scores are optimistic; the honest estimate comes from the final evaluation on the locked test set and PVSD.
