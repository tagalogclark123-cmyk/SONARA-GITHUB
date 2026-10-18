# C3 check: EfficientNet-B0 with the same loudness augmentation as B8

Run on 18 October 2026, Google Colab, **T4 GPU**. Notebook: `SONARA_C3_EfficientNet_Gain_Check.ipynb`. The executed copy is identical to the version on `main` except for one added `!nvidia-smi` cell that only prints the GPU. The C3 run files (JSON, history, validation predictions) were received as a zip of `MyDrive/SONARA/c3_efficientnet_gain_check/`. The B5, B8 and C2 rows are the stored second-pass runs, loaded from `MyDrive/SONARA/run2_second_pass/runs/`. Their values match `results/run2_second_pass/FINDINGS.md` exactly.

**Every number here is a validation result.** The locked test set (871 clips, id `bf636617`) and PVSD were not used. C3 was not evaluated on the test set, and the system model (B8) does not change.

Files: `SONARA_C3_EfficientNet_Gain_Check_executed.ipynb`, `notebook_text_outputs.txt`, `c3_validation_summary.csv`, `c3_comparisons.csv`, `c3_level_check.csv`, `c3_all_runs.csv`, `model_size_and_cpu_time.csv`, and `runs/` (C3 JSON, training history and validation predictions per seed).

## Why this check was run

B8 (MobileNetV3-Small) was trained with a random loudness change of up to ±12 dB on every clip. The runner-up C2 (EfficientNet-B0) was trained with ±6 dB on 20% of clips. So the final comparison was between two trained setups, not two architectures trained the same way. Without the strong augmentation, EfficientNet-B0 was ahead on validation (C2 0.970 against B5 0.964). C3 is C2 with B8's augmentation and nothing else changed. The notebook checks this before training: C3 differs from C2 only in `gain_prob` (0.2 → 1.0) and `gain_db` (6 → 12).

## Checks done on the received files

- **ROC-AUC:** recomputed from each seed's saved validation predictions. It matches the JSON on all 3 seeds (0.9706, 0.9758, 0.9676).
- **Labels:** the validation labels match the files' folders (Sick = Distress) on all 3 seeds.
- **No leakage:** 0 validation clips and 0 validation source recordings are in the locked test set, on all 3 seeds. The locked test set id was recomputed as `bf636617`.

## Table C1. Validation results (mean ± SD over seeds 7, 21, 42)

| Setup | Model | Loudness augmentation | ROC-AUC | ROC-AUC per seed (7 / 21 / 42) | Accuracy @0.5 | Distress F1 @0.5 | False alarms @0.90 recall | …on Normal | …on Noise | Best epoch |
| :- | :- | :- | :- | :- | :- | :- | :- | :- | :- | :- |
| B5 | MobileNetV3-Small | ±6 dB on 20% | 0.9642 ± 0.0079 | 0.9556 / 0.9711 / 0.9659 | 0.917 ± 0.008 | 0.881 ± 0.012 | 0.073 ± 0.017 | 0.111 | 0.031 | 21.3 ± 12.1 |
| **B8 (system model)** | MobileNetV3-Small | ±12 dB on every clip | 0.9698 ± 0.0023 | 0.9678 / 0.9723 / 0.9694 | 0.918 ± 0.004 | 0.883 ± 0.006 | 0.072 ± 0.011 | 0.106 | 0.034 | 25.7 ± 5.9 |
| C2 (runner-up) | EfficientNet-B0 | ±6 dB on 20% | 0.9699 ± 0.0031 | 0.9691 / 0.9733 / 0.9674 | 0.931 ± 0.006 | 0.901 ± 0.007 | 0.061 ± 0.023 | 0.092 | 0.027 | 22.0 ± 8.0 |
| **C3 (check)** | EfficientNet-B0 | ±12 dB on every clip | 0.9713 ± 0.0042 | 0.9706 / 0.9758 / 0.9676 | 0.936 ± 0.005 | 0.907 ± 0.009 | 0.048 ± 0.015 | 0.070 | 0.023 | 34.3 ± 5.7 |

## Table C2. Seed-by-seed comparisons (same seed = same split)

| Comparison | ROC-AUC change | Seeds better | Accuracy change | Seeds better | False-alarm change @0.90 | Seeds better |
| :- | :- | :- | :- | :- | :- | :- |
| ±12 dB augmentation on EfficientNet-B0 (C3 vs C2) | +0.0014 | 3 of 3 | +0.0048 | 3 of 3 | −0.0130 | 3 of 3 |
| ±12 dB augmentation on MobileNetV3-Small (B8 vs B5) | +0.0056 | 3 of 3 | +0.0014 | 2 of 3 | −0.0005 | 1 of 3 |
| **EfficientNet-B0 vs MobileNetV3-Small, same training (C3 vs B8)** | **+0.0015** | **2 of 3** | +0.0173 | 3 of 3 | −0.0243 | 3 of 3 |

C3 minus B8 per seed (7 / 21 / 42):
- **ROC-AUC:** +0.0028 / +0.0035 / −0.0018
- **False alarms @0.90 recall:** −0.0201 / −0.0373 / −0.0153

## Table C3. Loudness check (threshold fixed at its 0 dB value; mean over 3 seeds)

| Setup | Recall −20 dB | −10 dB | 0 dB | +10 dB | +20 dB | False alarms −20 / 0 / +20 dB | ROC-AUC −20 / 0 / +20 dB | Largest recall change ±10 / ±20 dB | Largest false-alarm change ±10 / ±20 dB |
| :- | :- | :- | :- | :- | :- | :- | :- | :- | :- |
| B5 | 0.720 | 0.867 | 0.901 | 0.882 | 0.841 | 0.078 / 0.073 / 0.139 | 0.923 / 0.964 / 0.930 | 0.034 / 0.181 | 0.021 / 0.066 |
| **B8** | 0.850 | 0.894 | 0.901 | 0.899 | 0.888 | 0.057 / 0.072 / 0.077 | 0.959 / 0.970 / 0.964 | 0.007 / 0.051 | 0.006 / 0.015 |
| C2 | 0.655 | 0.863 | 0.901 | 0.893 | 0.793 | 0.033 / 0.061 / 0.082 | 0.930 / 0.970 / 0.942 | 0.038 / 0.246 | 0.013 / 0.028 |
| **C3** | 0.858 | 0.894 | 0.901 | 0.892 | 0.860 | 0.041 / 0.048 / 0.047 | 0.964 / 0.971 / 0.958 | 0.009 / 0.043 | 0.003 / 0.007 |

## Size and CPU timing (Colab CPU, 1 thread; a proxy, not the Raspberry Pi 4)

| Model | Parameters | Size (MB, float32) | CPU ms per clip |
| :- | -: | -: | -: |
| MobileNetV3-Small | 1,519,906 | 6.08 | 8.8 |
| EfficientNet-B0 | 4,010,110 | 16.04 | 26.1 |

The ratio is 3.0× here, against 3.7× in the second pass (11.7 vs 43.8 ms). Colab CPU sessions differ between runs, so only the Pi benchmark gives the deployment number.

## What the results show

1. **On the selection metric, the two architectures are not clearly different under the same training.** C3 − B8 validation ROC-AUC is +0.0015 on average. It is higher on 2 of 3 seeds and within the run-to-run noise of about 0.004 measured in tuning (identical trials 3 and 23). The reading fixed in Part 0 of the notebook gives **"no clear difference"**.
2. **The selection of B8 holds.** If C3 had been in the second pass, the pre-declared rule (highest ROC-AUC among level-robust setups, smaller and faster model when not clearly different) would still have chosen B8.
3. **The loudness robustness comes from the augmentation, not the architecture.** With the same ±12 dB augmentation, EfficientNet-B0 is as flat as MobileNetV3-Small (largest recall change 0.009 vs 0.007 at ±10 dB, 0.043 vs 0.051 at ±20 dB). B8's advantage over C2 in the final evaluation's loudness check should therefore be credited to the augmentation. It is not a reason to prefer MobileNetV3-Small.
4. **EfficientNet-B0 has fewer false alarms on every seed.** Under the same training, C3 flags 4.8% of non-distress clips at 90% recall against 7.2% for B8 (−2.4 points, 3 of 3 seeds), and has higher accuracy (0.936 vs 0.918, 3 of 3). This matches the test-set gap between C2 and B8 (−2.1 points FPR). It is the cost of choosing the smaller model.
5. **The augmentation helps EfficientNet-B0 too.** C3 beats C2 on all three seeds for ROC-AUC, accuracy and false alarms.
6. **C3 trained longer:** best epoch 34.3 against 25.7 for B8, and seed 21 peaked at epoch 39 of 40. It might gain slightly more with a higher epoch cap. This was not tested.

## How to report it

- In Section 3.2.5, as a supplementary validation check on the model selection (Table 3.2 in `SONARA_Paper_Revisions_ModelChoice_PVSD.md` in the claude.ai Project). Never as a test result.
- B8 stays the system model. Switching after the test set was opened would mean choosing by test results; C3 was never tested.
- The trade-off to state: about 2 to 3 more false alarms per 100 non-distress clips in exchange for a model 2.6× smaller and about 3× faster. The Pi benchmark (`test/pi_latency_benchmark.py`) supplies the deployment speed ratio.
- Future work: EfficientNet-B0 with strong loudness augmentation, compared with B8 on new field recordings.
