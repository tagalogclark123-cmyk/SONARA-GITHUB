# Run 2, second pass: validation results and the model choice

Results received 14 October 2026. Notebook: `SONARA_Run2_SecondPass.ipynb` (identical to the version in the repo). All 18 runs finished (6 setups × 3 seeds). The seed-42 runs of C2, B6, B7 and B8 were trained on a Colab CPU session instead of a GPU; the code and settings were the same.

**Every number here is a validation result.** The locked test set (871 clips, id `bf636617`) and PVSD were not used.

Files: `SONARA_Run2_SecondPass_executed.ipynb` and `notebook_text_outputs.txt`. The CSV files are in Google Drive under `MyDrive/SONARA/run2_second_pass`.

## Table S1. Validation results (mean ± SD over 3 seeds), with first-pass reference rows

| Setup | Model | Settings | ROC-AUC | Accuracy @0.5 | False alarms @0.90 recall | …on Normal | …on Noise |
| :- | :- | :- | :- | :- | :- | :- | :- |
| A0 (first pass) | CNN–BiLSTM | Run 1 settings | 0.944 ± 0.005 | 0.882 ± 0.005 | 0.141 ± 0.013 | 0.201 | 0.073 |
| A2 (first pass) | CNN–BiLSTM | normalization + recipe | 0.946 ± 0.003 | 0.885 ± 0.007 | 0.133 ± 0.019 | 0.195 | 0.065 |
| A3 | CNN–BiLSTM | recipe, no normalization | 0.953 ± 0.004 | 0.895 ± 0.007 | 0.115 ± 0.014 | 0.159 | 0.066 |
| B4 (first pass) | MobileNetV3-Small | normalization + ImageNet + recipe | 0.961 ± 0.006 | 0.913 ± 0.010 | 0.086 ± 0.024 | 0.115 | 0.054 |
| B5 | MobileNetV3-Small | ImageNet + recipe, no normalization | 0.964 ± 0.008 | 0.917 ± 0.008 | 0.073 ± 0.017 | 0.111 | 0.031 |
| B6 | MobileNetV3-Small | B4 + three classes | 0.962 ± 0.001 | 0.910 ± 0.007 | 0.086 ± 0.004 | 0.131 | 0.037 |
| B7 | MobileNetV3-Small | B5 + three classes | 0.969 ± 0.001 | 0.927 ± 0.006 | 0.064 ± 0.008 | 0.095 | 0.030 |
| B8 | MobileNetV3-Small | B5 + ±12 dB loudness change on every training clip | 0.970 ± 0.002 | 0.918 ± 0.004 | 0.072 ± 0.011 | 0.106 | 0.034 |
| C1 (first pass) | EfficientNet-B0 | normalization + ImageNet + recipe | 0.964 ± 0.002 | 0.919 ± 0.005 | 0.074 ± 0.004 | 0.107 | 0.037 |
| C2 | EfficientNet-B0 | ImageNet + recipe, no normalization | 0.970 ± 0.003 | 0.931 ± 0.006 | 0.061 ± 0.023 | 0.092 | 0.027 |

## Table S2. Effect of each change, against its parent on the same seeds

| Change | On | ROC-AUC change | Seeds better | False-alarm change | Seeds better |
| :- | :- | :- | :- | :- | :- |
| Remove normalization | CNN–BiLSTM (A3 vs A2) | +0.006 | 3 of 3 | −0.018 | 1 of 3 |
| Remove normalization | MobileNetV3-Small (B5 vs B4) | +0.003 | 3 of 3 | −0.014 | 3 of 3 |
| Remove normalization | EfficientNet-B0 (C2 vs C1) | +0.006 | 3 of 3 | −0.013 | 2 of 3 |
| Three classes, with normalization | MobileNetV3-Small (B6 vs B4) | +0.001 | 1 of 3 | +0.000 | 1 of 3 |
| Three classes, without normalization | MobileNetV3-Small (B7 vs B5) | +0.004 | 2 of 3 | −0.009 | 3 of 3 |
| ±12 dB loudness augmentation | MobileNetV3-Small (B8 vs B5) | +0.006 | 3 of 3 | −0.001 | 1 of 3 |

## Table S3. Loudness check (threshold fixed at its 0 dB value; mean over 3 seeds)

| Setup | Recall −20 dB | Recall −10 dB | Recall 0 dB | Recall +10 dB | Recall +20 dB | False alarms −10 / 0 / +10 dB | ROC-AUC −20 / 0 / +20 dB |
| :- | :- | :- | :- | :- | :- | :- | :- |
| A3 CNN–BiLSTM | 0.388 | 0.801 | 0.901 | 0.863 | 0.616 | 0.098 / 0.115 / 0.138 | 0.872 / 0.953 / 0.835 |
| B5 MobileNetV3-Small | 0.720 | 0.867 | 0.901 | 0.882 | 0.841 | 0.081 / 0.073 / 0.094 | 0.923 / 0.964 / 0.930 |
| C2 EfficientNet-B0 | 0.655 | 0.863 | 0.901 | 0.893 | 0.793 | 0.048 / 0.061 / 0.073 | 0.930 / 0.970 / 0.942 |
| B6 (normalized) | 0.901 | 0.901 | 0.901 | 0.901 | 0.901 | 0.086 / 0.086 / 0.086 | 0.962 / 0.962 / 0.962 |
| B7 MobileNetV3-Small, 3 classes | 0.763 | 0.881 | 0.901 | 0.876 | 0.821 | 0.084 / 0.064 / 0.073 | 0.921 / 0.969 / 0.934 |
| B8 MobileNetV3-Small, ±12 dB augmentation | 0.850 | 0.894 | 0.901 | 0.899 | 0.888 | 0.066 / 0.072 / 0.070 | 0.959 / 0.970 / 0.964 |

All six setups pass the selection rule's loudness condition (recall and false-alarm rate within 0.10 at ±10 dB). The CNN–BiLSTM is exactly at the limit (0.100).

## Table S4. The two leading setups, seed by seed

| Seed | ROC-AUC C2 / B8 | Accuracy @0.5 C2 / B8 | False alarms @0.90 recall C2 / B8 |
| :- | :- | :- | :- |
| 7 | 0.9691 / 0.9678 | 0.930 / 0.914 | 0.086 / 0.084 |
| 21 | 0.9733 / 0.9723 | 0.937 / 0.917 | 0.041 / 0.071 |
| 42 | 0.9674 / 0.9694 | 0.925 / 0.923 | 0.056 / 0.062 |
| Mean | 0.9699 / 0.9698 | 0.931 / 0.918 | 0.061 / 0.072 |

| | C2 EfficientNet-B0 | B8 MobileNetV3-Small |
| :- | :- | :- |
| Parameters | 4,010,110 | 1,519,906 |
| Size (32-bit) | 16.0 MB | 6.1 MB |
| Colab CPU, one thread | 43.8 ms per clip | 11.7 ms per clip |

## Findings

1. **Removing normalization helps every model**, on all 3 seeds for ROC-AUC. This confirms the first-pass result.
2. **Without normalization the models depend on recording level.** A recording 20 dB quieter drops the CNN–BiLSTM's recall from 0.90 to 0.39 and EfficientNet-B0's to 0.66.
3. **Loudness augmentation of ±12 dB removes most of that dependence without costing accuracy.** B8 keeps recall between 0.85 and 0.90 from −20 to +20 dB and raises ROC-AUC over B5 on all 3 seeds.
4. **Three-class training has a small effect.** Without normalization it lowers false alarms on all 3 seeds (−0.009) and raises ROC-AUC on 2 of 3. With normalization it shows no clear effect. It was not tested together with loudness augmentation.
5. **The CNN–BiLSTM remains behind.** Its best version (A3) reaches 0.953 ROC-AUC and 11.5% false alarms against 0.964 to 0.970 and 6% to 7% for the pretrained models, is the most sensitive to level, and is the slowest on a CPU.
6. **EfficientNet-B0 (C2) and MobileNetV3-Small with loudness augmentation (B8) are tied on ROC-AUC** (0.9699 against 0.9698; C2 ahead on 2 of 3 seeds). C2 has higher accuracy at 0.5 on all 3 seeds (+0.013) and fewer false alarms on 2 of 3. B8 is 2.6 times smaller, about 4 times faster on a CPU, and much steadier across recording levels.

## Decision

By the selection rule fixed before this run (highest validation ROC-AUC among Pi-deployable, level-robust setups; the smaller model when two are not clearly different), **B8 is selected: MobileNetV3-Small with ImageNet weights, the training recipe, no normalization, and ±12 dB loudness augmentation.** C2 is the runner-up.

Against the Run 1 settings (A0), on the same validation splits, B8 raises ROC-AUC from 0.944 to 0.970 and accuracy at 0.5 from 0.882 to 0.918, and lowers false alarms at 0.90 recall from 14.1% to 7.2% (on healthy calls from 20.1% to 10.6%). These are validation figures; the test figures come from the final evaluation.

## Caution

Validation numbers are optimistic: early stopping and the threshold use the validation set, and 15 setups have now been compared on it across both passes. The honest estimate comes from the final evaluation on the locked test set and PVSD.
