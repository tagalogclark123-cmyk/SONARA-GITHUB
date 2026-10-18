# Final evaluation: results for the paper

Run on 17 October 2026 (UTC), Google Colab, **T4 GPU**. Notebook: `SONARA_Final_Evaluation.ipynb` (code identical to the version on `main`). The locked test set and PVSD were opened **once** (log entry #1, 17 Oct 2026 18:22 UTC, model fingerprint `2dbc43ca6501`).

These are the numbers for the paper. Everything before this (Run 2, tuning) was chosen on validation data only.

Files in this folder: `SONARA_Final_Evaluation_executed.ipynb`, `notebook_text_outputs.txt`, `figures/figure_loudness_check.png`, `figures/figure_test_roc_and_confusion.png`. The CSV tables, trained weights, predictions and the exported gateway model are in the team Drive under `MyDrive/SONARA/final_evaluation/` (tables, `runs/`, `test_predictions/`, `export/`).

**Note on the saved notebook.** Four cells (main table, target comparison, paired comparison, export) ran but their printed output was not saved in the notebook copy. Their results were written to CSV files in Drive at the same time; the tables below come from those files (`table_test_main.csv`, `table_test_confidence_intervals.csv`, `table_test_paired_comparison.csv`, `table_test_target_recall_comparison.csv`, `table_test_seed_average.csv`, `export/deployment_config.json`).

## Setup

- **Models:** B8, MobileNetV3-Small with ImageNet weights (system model, declared before the test set was opened; settings confirmed by the tuning notebook); C2, EfficientNet-B0 (runner-up); A0, the CNN–BiLSTM with the Run 1 settings (baseline). C2 and A0 kept their Run 2 settings and were not tuned.
- **Training:** 5 seeds (7, 21, 42, 77, 99), development data only (85% of SmartEars), grouped by source recording.
- **Thresholds:** each run chose two thresholds on its own validation clips: the highest reaching 90% distress recall (primary) and 95%.
- **Locked test set:** 871 SmartEars clips, 597 Non-distress and 274 Distress (id `bf636617`). Always predicting Non-distress scores 0.685.
- **PVSD:** 346 files, external test, never used for training or choosing anything.

## Table F1. Locked test set (mean ± SD over 5 seeds)

**90% recall operating point (primary)**

| Model | Parameters | Threshold | Accuracy | Distress recall | Distress precision | Distress F1 | FPR | ROC-AUC | PR-AUC |
| :- | -: | :- | :- | :- | :- | :- | :- | :- | :- |
| Majority class | 0 | — | 0.685 | 0.000 | — | 0.000 | 0.000 | 0.500 | — |
| **MobileNetV3-Small (B8)** | 1,519,906 | 0.462 ± 0.103 | **0.913 ± 0.007** | **0.873 ± 0.016** | 0.853 ± 0.013 | 0.863 ± 0.012 | **0.069 ± 0.007** | **0.962 ± 0.006** | 0.917 ± 0.018 |
| EfficientNet-B0 (C2) | 4,010,110 | 0.591 ± 0.083 | 0.928 ± 0.006 | 0.876 ± 0.031 | 0.894 ± 0.020 | 0.884 ± 0.011 | 0.048 ± 0.012 | 0.969 ± 0.002 | 0.933 ± 0.005 |
| CNN–BiLSTM, Run 1 settings (A0) | 1,221,186 | 0.412 ± 0.054 | 0.867 ± 0.014 | 0.872 ± 0.008 | 0.748 ± 0.028 | 0.805 ± 0.017 | 0.136 ± 0.020 | 0.934 ± 0.007 | 0.870 ± 0.017 |

**95% recall operating point**

| Model | Threshold | Accuracy | Distress recall | Distress precision | Distress F1 | FPR |
| :- | :- | :- | :- | :- | :- | :- |
| **MobileNetV3-Small (B8)** | 0.198 ± 0.055 | 0.891 ± 0.020 | 0.942 ± 0.012 | 0.766 ± 0.033 | 0.845 ± 0.025 | 0.132 ± 0.023 |
| EfficientNet-B0 (C2) | 0.190 ± 0.072 | 0.906 ± 0.023 | 0.941 ± 0.021 | 0.801 ± 0.057 | 0.864 ± 0.027 | 0.110 ± 0.041 |
| CNN–BiLSTM (A0) | 0.210 ± 0.031 | 0.816 ± 0.028 | 0.924 ± 0.009 | 0.647 ± 0.042 | 0.760 ± 0.029 | 0.234 ± 0.041 |

**At threshold 0.5,** B8: accuracy 0.911 ± 0.007, distress recall 0.866, precision 0.854, distress F1 0.860, FPR 0.068. C2: 0.930, 0.893, 0.886, 0.889, 0.053. A0: 0.880, 0.846, 0.788, 0.816, 0.105.

## Table F2. 95% confidence intervals (1,000 resamples of test recordings, seed-averaged)

| Operating point | Model | Accuracy | Distress recall | FPR | ROC-AUC |
| :- | :- | :- | :- | :- | :- |
| 90% | **B8** | 0.897 – 0.929 | 0.835 – 0.908 | 0.052 – 0.087 | 0.948 – 0.973 |
| 90% | C2 | 0.912 – 0.943 | 0.839 – 0.911 | 0.034 – 0.064 | 0.959 – 0.979 |
| 90% | A0 | 0.842 – 0.889 | 0.825 – 0.912 | 0.111 – 0.164 | 0.910 – 0.954 |
| 95% | **B8** | 0.874 – 0.909 | 0.917 – 0.963 | 0.110 – 0.156 | 0.948 – 0.973 |
| 95% | C2 | 0.889 – 0.921 | 0.916 – 0.963 | 0.091 – 0.132 | 0.959 – 0.979 |
| 95% | A0 | 0.790 – 0.841 | 0.888 – 0.956 | 0.204 – 0.267 | 0.910 – 0.954 |

## Table F3. Seed-by-seed comparison (system model minus the other model; "better" for FPR means lower)

| Operating point | Compared with | ROC-AUC | Accuracy | Distress F1 | FPR | Distress recall |
| :- | :- | :- | :- | :- | :- | :- |
| 90% | C2 | −0.008 (0 of 5 better) | −0.015 (0 of 5) | −0.022 (0 of 5) | +0.021 (0 of 5) | −0.003 (2 of 5) |
| 90% | A0 | +0.028 (5 of 5) | +0.046 (5 of 5) | +0.058 (5 of 5) | −0.066 (5 of 5) | +0.002 (3 of 5) |
| 95% | C2 | — | −0.015 (2 of 5) | −0.019 (2 of 5) | +0.022 (2 of 5) | +0.001 (2 of 5) |
| 95% | A0 | — | +0.075 (4 of 5) | +0.085 (4 of 5) | −0.102 (4 of 5) | +0.018 (4 of 5) |

## Table F4. B8 at 90% vs 95% recall (mean over seeds)

| | 90% | 95% | Change |
| :- | :- | :- | :- |
| Threshold | 0.462 | 0.198 | −0.264 |
| Distress recall | 0.873 | 0.942 | +0.069 |
| Missed distress | 12.7% | 5.8% | −6.9 points |
| False-positive rate | 6.9% | 13.2% | +6.3 points |
| Healthy calls flagged | 10.2% | 19.7% | +9.5 points |
| Noise flagged | 3.8% | 7.0% | +3.2 points |
| Distress precision | 0.853 | 0.766 | −0.086 |
| Accuracy | 0.913 | 0.891 | −0.022 |

Confusion matrices for B8, seed 42: at 90%, 244 of 274 Distress clips caught, 38 of 597 Non-distress flagged; at 95%, 259 caught, 75 flagged.

## Table F5. Loudness check on the locked test set (90% threshold held fixed; mean over seeds)

| Model | Recall −20 dB | −10 dB | 0 dB | +10 dB | +20 dB | FPR −20 / 0 / +20 dB | ROC-AUC −20 / 0 / +20 dB |
| :- | :- | :- | :- | :- | :- | :- | :- |
| **B8** | **0.836** | 0.867 | 0.873 | 0.884 | **0.882** | 0.061 / 0.069 / 0.087 | 0.956 / 0.962 / 0.959 |
| C2 | 0.649 | 0.820 | 0.876 | 0.857 | 0.661 | 0.026 / 0.048 / 0.051 | 0.935 / 0.969 / 0.928 |
| A0 | 0.199 | 0.679 | 0.872 | 0.795 | 0.525 | 0.017 / 0.136 / 0.203 | 0.757 / 0.934 / 0.775 |

## Table F6. PVSD external test (per file; mean ± SD over seeds)

346 files (225 Non-distress, 121 Distress); always predicting Non-distress scores 0.650.

| Operating point | Model | Accuracy | Distress recall | FPR | ROC-AUC | PR-AUC |
| :- | :- | :- | :- | :- | :- | :- |
| 90% | **B8** | **0.758 ± 0.031** | 0.759 ± 0.072 | 0.243 ± 0.036 | 0.825 ± 0.065 | 0.753 ± 0.077 |
| 90% | C2 | 0.791 ± 0.034 | 0.549 ± 0.098 | 0.079 ± 0.053 | 0.833 ± 0.022 | 0.769 ± 0.043 |
| 90% | A0 | 0.549 ± 0.031 | 0.960 ± 0.066 | 0.672 ± 0.028 | 0.788 ± 0.048 | 0.662 ± 0.120 |
| 95% | B8 | 0.580 ± 0.065 | 0.884 ± 0.091 | 0.584 ± 0.102 | — | — |
| 95% | C2 | 0.643 ± 0.076 | 0.879 ± 0.085 | 0.484 ± 0.158 | — | — |
| 95% | A0 | 0.448 ± 0.030 | 0.992 ± 0.018 | 0.844 ± 0.050 | — | — |

B8, seed 42, 90% threshold: 16.5% of Healthy, 27.9% of Noise and 73.6% of Unhealthy PVSD files flagged. Files shorter than 5 s were flagged 28.6% of the time against 40.8% for longer files.

## Table F7. Zone alerts (simulation on locked-test predictions)

Rule chosen on validation predictions (shortest median time to alert at outbreak share 0.3 with at most 1 false alert-hour per healthy zone per week). One clip per zone every 30 s.

| Operating point | Rule | False alert-hours per healthy zone per week | Outbreak share | Detected within 24 h | Median minutes to alert |
| :- | :- | :- | :- | :- | :- |
| 90% | 8 of the last 20 clips (10 min) | 0.26 | 0.1 | 98.0% | 324 |
| | | | 0.2 | 100% | 40 |
| | | | 0.3 | 100% | 16 |
| | | | 0.5 | 100% | 7 |
| 95% | 10 of the last 20 clips (10 min) | 0.60 | 0.1 | 89.5% | 401 |
| | | | 0.2 | 100% | 49 |
| | | | 0.3 | 100% | 18 |
| | | | 0.5 | 100% | 8 |

Clips are drawn independently in the simulation; real false-alert rates are likely higher because consecutive clips in a poultry house are related.

## Gateway export

`export/sonara_system_model.pt` (6.6 MB TorchScript, B8 seed 42, feature extraction included), plain weights `mobilenetv3_small_seed42.pt`, and `deployment_config.json`: 90% threshold 0.535 with rule 8 of 20 clips; 95% threshold 0.24 with rule 10 of 20 clips; input 16 kHz mono, 5 s, values −1 to 1.

## What the results show

1. **B8 meets the project's needs on unseen data.** At the primary operating point it catches 87.3% of distress clips (95% CI 83.5% to 90.8%) while flagging 6.9% of non-distress clips, with ROC-AUC 0.962 and accuracy 0.913.
2. **Recall landed slightly below the 90% target** (0.873), as expected when a threshold set on validation data is applied to new data. The 95% setting reached 0.942.
3. **B8 clearly beats the original CNN–BiLSTM** on every seed at the primary point: +4.6 points accuracy, half the false-positive rate (6.9% vs 13.6%), +0.028 ROC-AUC.
4. **EfficientNet-B0 scored higher than B8 on the test set** at the 90% point (accuracy 0.928 vs 0.913, FPR 4.8% vs 6.9%, ROC-AUC 0.969 vs 0.962), on all 5 seeds; the confidence intervals overlap. At 95% the two are not clearly different (B8 better on 2 of 5 seeds). B8 was declared the system model before the test set was opened, on a validation tie, because it is 2.6 times smaller, about 4 times faster on a CPU and steadier across recording levels. **Switching to C2 now would mean choosing a model by its test score, so it stays as reported.**
5. **B8 is by far the most robust to recording level.** From −20 to +20 dB its recall stays between 0.84 and 0.88 and its ROC-AUC between 0.956 and 0.962. EfficientNet-B0's recall falls to 0.65 at both extremes, and the CNN–BiLSTM's to 0.20 at −20 dB. This matters because the INMP441 nodes will not record at the SmartEars level.
6. **Healthy calls remain the main source of false alarms:** 10.2% of healthy calls vs 3.8% of noise clips flagged at 90%.
7. **Moving from 90% to 95% recall** halves missed distress (12.7% to 5.8%) but nearly doubles false alarms (6.9% to 13.2%, healthy calls 10.2% to 19.7%).
8. **PVSD transfer improved greatly over Run 1.** B8 now beats the 0.650 majority accuracy on recordings from different equipment and birds (0.758 at 90%), with ROC-AUC 0.825. In Run 1 every model was below that floor. The 95% threshold does not transfer well (0.580). EfficientNet-B0 has slightly higher PVSD accuracy, but by missing almost half of the Unhealthy files (recall 0.549).
9. **Zone alerts look practical in simulation:** a zone where a third of the clips contain distress is alerted in about 16 minutes, with about one false alert-hour per healthy zone every four weeks at the 90% setting.
10. **The test set was opened once,** with the frozen models; the log shows a single opening.

## Compared with earlier figures

The old manuscript reported 0.890 accuracy for the CNN–BiLSTM under a looser protocol (pooled datasets, random split, accuracy-tuned threshold). Under the strict protocol, the system model reaches 0.911 accuracy at threshold 0.5 and 0.913 at the 90% operating point, and the same CNN–BiLSTM reaches 0.880 at 0.5. The old figures should not be cited.

## Limitations to state in the paper

- C2 and A0 were not tuned; only B8 was.
- Test-set distress recall at the 90% point was 0.873, below the target set on validation.
- PVSD labels describe treated versus untreated groups, not individual clips.
- Zone results are a simulation with independent clips.
- Timing on the Raspberry Pi 4 has not yet been measured; Colab CPU timing is a proxy.
- End-to-end performance with the INMP441 sensing nodes (playback and field tests) is not covered by this evaluation.
