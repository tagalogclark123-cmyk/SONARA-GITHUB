# Run 2, first pass: validation results

Results received 13 October 2026. Notebook: `SONARA_Run2_FirstPass.ipynb`, Google Colab, T4 GPU. All 27 runs finished (9 setups × 3 seeds).

**Every number here is a validation result.** The locked test set (871 clips, id `bf636617`, `LOCK_SEED = 2026`) and PVSD were not used. These numbers are for choosing a setup, not for the paper's results table.

Files: `SONARA_Run2_FirstPass_executed.ipynb` (the notebook as it ran) and `notebook_text_outputs.txt` (all text output, including per-epoch logs). The CSV files and `locked_test_set.csv` are in Google Drive under `MyDrive/SONARA/run2_first_pass`.

## Protocol

- Development data: 5,129 SmartEars clips; about 4,220 for training and 900 for validation per seed (seeds 7, 21, 42), grouped by source recording.
- Input, augmentation and loss as in Run 1.
- "Run 1 settings": Adam, learning rate 1e-4, at most 50 epochs. "Recipe": AdamW, learning rate 3e-4 with warm-up and cosine decay, mixup, at most 40 epochs.
- "False alarms @0.90 recall": share of Non-distress validation clips flagged when the threshold is set, on the same validation set, to catch 90% of Distress clips.

## Table F1. Validation results (mean ± SD over 3 seeds)

| Setup | Model | Settings | ROC-AUC | Accuracy @0.5 | Distress F1 @0.5 | False alarms @0.90 recall | …on Normal | …on Noise |
| :- | :- | :- | :- | :- | :- | :- | :- | :- |
| A0 | CNN–BiLSTM | Run 1 settings | 0.944 ± 0.005 | 0.882 ± 0.005 | 0.837 ± 0.007 | 0.141 ± 0.013 | 0.201 | 0.073 |
| A1 | CNN–BiLSTM | + normalization | 0.934 ± 0.008 | 0.877 ± 0.014 | 0.830 ± 0.016 | 0.164 ± 0.029 | 0.233 | 0.086 |
| A2 | CNN–BiLSTM | + normalization + recipe | 0.946 ± 0.003 | 0.886 ± 0.007 | 0.842 ± 0.004 | 0.133 ± 0.019 | 0.195 | 0.065 |
| B0 | MobileNetV3-Small | Run 1 settings | 0.936 ± 0.001 | 0.874 ± 0.010 | 0.823 ± 0.015 | 0.178 ± 0.009 | 0.242 | 0.107 |
| B1 | MobileNetV3-Small | + normalization | 0.901 ± 0.017 | 0.833 ± 0.022 | 0.771 ± 0.027 | 0.284 ± 0.042 | 0.372 | 0.186 |
| B2 | MobileNetV3-Small | + normalization + ImageNet weights | 0.955 ± 0.003 | 0.892 ± 0.008 | 0.845 ± 0.015 | 0.114 ± 0.002 | 0.163 | 0.060 |
| B3 | MobileNetV3-Small | + normalization + recipe | 0.938 ± 0.010 | 0.880 ± 0.009 | 0.831 ± 0.010 | 0.155 ± 0.020 | 0.213 | 0.091 |
| B4 | MobileNetV3-Small | + normalization + ImageNet weights + recipe | 0.961 ± 0.006 | 0.913 ± 0.010 | 0.874 ± 0.016 | 0.086 ± 0.024 | 0.115 | 0.054 |
| C1 | EfficientNet-B0 | normalization + ImageNet weights + recipe | 0.964 ± 0.002 | 0.919 ± 0.005 | 0.882 ± 0.011 | 0.074 ± 0.004 | 0.107 | 0.037 |

## Table F2. Effect of each change, against its parent setup on the same seeds

| Change | On | ROC-AUC change | Seeds better | False-alarm change | Seeds better |
| :- | :- | :- | :- | :- | :- |
| Normalization | CNN–BiLSTM (A1 vs A0) | −0.010 | 0 of 3 | +0.023 | 0 of 3 |
| Normalization | MobileNetV3-Small (B1 vs B0) | −0.035 | 0 of 3 | +0.106 | 0 of 3 |
| ImageNet weights | MobileNetV3-Small (B2 vs B1) | +0.055 | 3 of 3 | −0.170 | 3 of 3 |
| Recipe | CNN–BiLSTM (A2 vs A1) | +0.012 | 3 of 3 | −0.031 | 2 of 3 |
| Recipe | MobileNetV3-Small, random start (B3 vs B1) | +0.037 | 3 of 3 | −0.129 | 3 of 3 |
| Recipe | MobileNetV3-Small, ImageNet start (B4 vs B2) | +0.006 | 3 of 3 | −0.028 | 3 of 3 |
| Larger model | EfficientNet-B0 vs MobileNetV3-Small (C1 vs B4) | +0.002 | 1 of 3 | −0.012 | 2 of 3 |

## Table F3. Size and speed

| Model | Parameters | Size (MB) | Colab CPU, one thread (ms per clip) | Training time per run (min) |
| :- | -: | -: | -: | -: |
| CNN–BiLSTM | 1,221,186 | 4.88 | 41.3 | about 8 |
| MobileNetV3-Small | 1,519,906 | 6.08 | 7.6 | about 6 |
| EfficientNet-B0 | 4,010,110 | 16.04 | 21.8 | about 14 |

## Findings

1. **ImageNet-pretrained weights help clearly.** On MobileNetV3-Small they raise validation ROC-AUC by 0.055 and cut false alarms at 0.90 recall from 28% to 11%, on all 3 seeds.
2. **The training recipe helps on every model**, on all 3 seeds for ROC-AUC. The gain is largest for a model trained from random weights and smallest on top of pretrained weights.
3. **Per-clip normalization made results worse** on both models, on all 3 seeds. It was expected to help and did not. The models appear to use the absolute loudness of a clip, which normalization removes.
4. **Every pretrained and recipe setup in this pass also had normalization switched on.** The combination of pretrained weights and recipe *without* normalization was not tested, and Finding 3 suggests it could be better still. This is the main gap of the first pass.
5. **The best two setups are close.** EfficientNet-B0 (C1) leads MobileNetV3-Small (B4) by 0.002 ROC-AUC and is ahead on only 1 of 3 seeds, while being 2.6 times larger and about 3 times slower. By the rule that a change must help on most seeds, the larger model shows no clear advantage.
6. **Against the Run 1 CNN–BiLSTM settings (A0)**, B4 raises validation accuracy from 0.882 to 0.913 and ROC-AUC from 0.944 to 0.961, and lowers false alarms at 0.90 recall from 14.1% to 8.6%. False alarms on healthy vocalizations fall from 20% to 12%.
7. **The CNN–BiLSTM gains little** from the changes tested (ROC-AUC 0.944 to 0.946) and is the slowest of the three models on a CPU.

## Open questions for the second pass

- Pretrained weights and recipe without normalization (the gap in Finding 4).
- Whether reliance on absolute loudness is a risk on other microphones. This can be checked without touching the test data by shifting the level of validation clips and measuring how much the scores move.
- Training on three classes and reporting two.
- A model pretrained on audio (AudioSet) instead of photos.

## Caution

Validation numbers are optimistic: early stopping and the threshold both use the validation set, and nine setups were compared on it. The honest estimate comes from the final evaluation on the locked test set and PVSD.
