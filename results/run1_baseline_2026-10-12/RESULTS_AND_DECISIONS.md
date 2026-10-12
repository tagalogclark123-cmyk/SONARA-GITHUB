# Run 1: baseline results and the decisions that follow from them

Run date: 12 October 2026, Google Colab, T4 GPU. Notebook: `SONARA_Chapter3_Pipeline.ipynb` (repo commit `454f9b4`).

This is the first complete run of the pipeline under the revised protocol. It is recorded here as the **baseline** that every later change is measured against. All numbers below are copied from the executed notebook in this folder.

Files in this folder:

| File | Contents |
| :- | :- |
| `SONARA_Chapter3_Pipeline_run1_executed.ipynb` | The notebook exactly as it ran, with all outputs |
| `notebook_text_outputs.txt` | Every text output, including the per-epoch training log |
| `per_run_results.csv` | One row per model and seed (20 runs) |
| `figures/` | Figure 3.1, Figure 3.2, training curves, confusion matrices and ROC curves, zone simulation |

The trained weights and the CSV files written by the notebook were not saved to Drive, so they are not in this folder.

## 1. Protocol

| Item | Setting |
| :- | :- |
| Training data | SmartEars only: 6,000 five-second clips (2,000 Healthy, 2,000 Sick, 2,000 None) |
| Target classes | Non-distress (Healthy + None, 4,000 clips) and Distress (Sick, 2,000 clips) |
| External test | PVSD, 346 files (139 Healthy, 121 Unhealthy, 86 Noise); never used for training or threshold selection |
| Input | 16 kHz mono, the whole 5-second clip, 64 mel bands (25 ms window, 10 ms hop), power in dB, plus delta and delta-delta: 3 × 64 × 500 |
| Split | 70/15/15, stratified by source category, grouped by source recording; 5 seeds (7, 21, 42, 77, 99), a new split per seed |
| Augmentation | Time shift up to ±0.5 s (p = 0.5), time mask (p = 0.4), frequency mask (p = 0.4), loudness offset of ±6 dB (p = 0.2) |
| Loss | Weighted cross-entropy with class weights N̄/N_c and label smoothing 0.02 |
| Optimization | Adam, learning rate 1e-4, weight decay 1e-4, batch size 16, dropout 0.3, at most 50 epochs, early stopping patience 8. Not tuned. |
| Decision threshold | Highest threshold with validation distress recall ≥ 0.90; results at 0.5 also reported |

## 2. Results on the SmartEars test set

Mean ± standard deviation over 5 seeds. About 900 test clips per seed.

**Table R1. Threshold 0.5**

| Model | Parameters | Accuracy | Macro-F1 | Distress recall | Distress precision | Distress F1 |
| :- | -: | :- | :- | :- | :- | :- |
| Majority class | 0 | 0.665 ± 0.016 | 0.399 ± 0.006 | 0.000 | — | 0.000 |
| CNN front end only (no LSTM) | 39,106 | 0.730 ± 0.032 | 0.711 ± 0.035 | 0.714 ± 0.071 | 0.579 ± 0.042 | 0.638 ± 0.046 |
| DS-CNN | 148,610 | 0.874 ± 0.010 | 0.858 ± 0.013 | 0.812 ± 0.009 | 0.811 ± 0.033 | 0.811 ± 0.020 |
| MobileNetV3-Small | 1,519,906 | 0.866 ± 0.025 | 0.851 ± 0.027 | 0.831 ± 0.036 | 0.783 ± 0.049 | 0.805 ± 0.036 |
| CNN–BiLSTM | 1,221,186 | 0.863 ± 0.015 | 0.848 ± 0.017 | 0.821 ± 0.027 | 0.781 ± 0.025 | 0.800 ± 0.024 |

**Table R2. Recall-target threshold (validation distress recall ≥ 0.90)**

| Model | Threshold | Accuracy | Distress recall | Distress precision | Distress F1 | False-positive rate | ROC-AUC |
| :- | :- | :- | :- | :- | :- | :- | :- |
| CNN front end only (no LSTM) | 0.402 ± 0.023 | 0.639 ± 0.039 | 0.912 ± 0.019 | 0.481 ± 0.030 | 0.630 ± 0.026 | 0.499 ± 0.063 | 0.797 ± 0.032 |
| DS-CNN | 0.299 ± 0.023 | 0.835 ± 0.019 | 0.884 ± 0.016 | 0.703 ± 0.045 | 0.783 ± 0.024 | 0.189 ± 0.033 | 0.927 ± 0.006 |
| MobileNetV3-Small | 0.300 ± 0.028 | 0.833 ± 0.032 | 0.896 ± 0.015 | 0.697 ± 0.059 | 0.783 ± 0.037 | 0.198 ± 0.047 | 0.925 ± 0.014 |
| CNN–BiLSTM | 0.246 ± 0.031 | 0.803 ± 0.047 | 0.895 ± 0.021 | 0.656 ± 0.065 | 0.755 ± 0.043 | 0.243 ± 0.075 | 0.918 ± 0.019 |

**Table R3. CNN–BiLSTM compared with each other model on the same seeds** (difference = CNN–BiLSTM minus the other model; wins = seeds out of 5 where the CNN–BiLSTM is higher)

| Compared with | Distress F1 | ROC-AUC | PVSD ROC-AUC |
| :- | :- | :- | :- |
| CNN front end only | +0.126 (5 wins) | +0.121 (5 wins) | +0.149 (5 wins) |
| DS-CNN | −0.027 (1 win) | −0.009 (2 wins) | +0.241 (5 wins) |
| MobileNetV3-Small | −0.028 (1 win) | −0.008 (2 wins) | +0.274 (5 wins) |

**Table R4. Share of test clips flagged as Distress at the recall-target threshold, by source category**

| Model | Distress (recall) | Normal (false alarms) | Noise (false alarms) |
| :- | :- | :- | :- |
| CNN front end only | 0.912 | 0.546 | 0.451 |
| DS-CNN | 0.884 | 0.268 | 0.110 |
| MobileNetV3-Small | 0.896 | 0.263 | 0.132 |
| CNN–BiLSTM | 0.895 | 0.330 | 0.157 |

**Training behaviour.** The CNN–BiLSTM stopped after 15 to 45 epochs depending on the seed, with its best epoch between 7 and 37. DS-CNN stopped after 29 to 42 epochs and MobileNetV3-Small after 24 to 37.

**Minimum check.** For seed 42 the test proportions are 0.637 / 0.363, so the Proportional Chance Criterion is 0.538 and 1.25 × PCC is 0.672. The CNN–BiLSTM accuracy of 0.792 at the recall-target threshold exceeds it.

## 3. Results on the external PVSD set

Per file, at each run's recall-target threshold. 225 Non-distress and 121 Distress files, so always predicting Non-distress scores 0.650 accuracy.

**Table R5**

| Model | Accuracy | Distress recall | False-positive rate | ROC-AUC | PR-AUC |
| :- | :- | :- | :- | :- | :- |
| CNN front end only | 0.525 ± 0.043 | 0.764 ± 0.092 | 0.603 ± 0.085 | 0.650 ± 0.117 | 0.557 ± 0.117 |
| DS-CNN | 0.502 ± 0.073 | 0.724 ± 0.080 | 0.618 ± 0.129 | 0.558 ± 0.078 | 0.393 ± 0.095 |
| MobileNetV3-Small | 0.462 ± 0.110 | 0.664 ± 0.088 | 0.647 ± 0.188 | 0.525 ± 0.111 | 0.408 ± 0.104 |
| CNN–BiLSTM | 0.474 ± 0.068 | 0.945 ± 0.088 | 0.780 ± 0.090 | 0.799 ± 0.066 | 0.751 ± 0.075 |

For the CNN–BiLSTM on seed 42, 86.3% of Healthy files, 76.7% of Noise files and 79.3% of Unhealthy files were classified as Distress. The 42 files shorter than 5 seconds were flagged 31.0% of the time, against 88.5% for longer files.

## 4. Gateway timing and zone simulation

**Table R6. Inference time for one 5-second clip, Colab CPU, one thread** (not the Raspberry Pi 4)

| Step | Median (ms) | 95th percentile (ms) |
| :- | -: | -: |
| Feature extraction | 3.0 | 3.4 |
| CNN–BiLSTM | 35.1 | 39.2 |
| CNN front end only | 31.7 | 43.9 |
| DS-CNN | 64.1 | 73.1 |
| MobileNetV3-Small | 7.8 | 8.4 |

**Zone simulation** (software only; test clips stand in for audio packets; alert when 40% of the last 20 clips in a zone are classified as Distress; CNN–BiLSTM, seed 42, threshold 0.245). Zone 2 received distress clips from minute 30.

| Zone | Clips | True Distress | Detected Distress | False alarms | Missed | Alerts raised | First alert (min) |
| :- | -: | -: | -: | -: | -: | -: | -: |
| Zone 1 (healthy) | 120 | 0 | 42 | 42 | 0 | 5 | 23.5 |
| Zone 2 (outbreak) | 120 | 38 | 56 | 20 | 2 | 1 | 32.0 |
| Zone 3 (healthy) | 120 | 0 | 29 | 29 | 0 | 3 | 12.5 |

## 5. What the results show

1. **All trained models are far above the majority-class floor**, except that the CNN front end on its own is weak (0.730 accuracy at threshold 0.5).
2. **The CNN–BiLSTM is not better than DS-CNN or MobileNetV3-Small on SmartEars.** The three are within about one point of accuracy and ROC-AUC, and the CNN–BiLSTM is ahead on only 1 or 2 of 5 seeds. DS-CNN reaches the same level with about one eighth of the parameters.
3. **Adding the BiLSTM to the convolution layers helps on every seed** (ROC-AUC +0.12). The front-end-only model underfits even the training data, so this shows the two convolution layers alone are not enough. It does not show that a recurrent layer is the only way to fix that.
4. **The CNN–BiLSTM trains less steadily** than the other two: its accuracy at the recall-target threshold varies more across seeds (SD 0.047 against 0.019 for DS-CNN) and its best epoch ranges from 7 to 37.
5. **Reaching 0.90 distress recall costs many false alarms.** The threshold falls to about 0.25 to 0.30 and 19% to 24% of Non-distress clips are flagged. Healthy vocalizations are flagged about twice as often as noise.
6. **Clip-level false alarms become zone-level false alerts.** In the simulation both healthy zones raised alerts under the 40%-of-20 rule.
7. **No model transfers to PVSD at its SmartEars threshold.** Every model is below the 0.650 majority-class accuracy there. The CNN–BiLSTM is the only one whose ranking of PVSD files is clearly above chance (ROC-AUC 0.799, higher than the others on all 5 seeds), but its threshold flags most files of every class.
8. **PVSD results are affected by file length**, and PVSD labels describe a treated versus untreated group of birds, not individual clips. PVSD accuracy should be read as a stress test, not as a measure of disease detection.

## 6. Earlier figures this run replaces

The previous manuscript reported 0.890 accuracy, 0.844 distress F1 and 0.940 ROC-AUC for the CNN–BiLSTM. That run pooled PVSD with SmartEars, split files at random, tuned the threshold for accuracy, used a single split, and read the LSTM output in a way that gave the backward direction almost no context. Under the revised protocol the comparable figures are 0.863 ± 0.015 accuracy, 0.800 ± 0.024 distress F1 and 0.918 ± 0.019 ROC-AUC. The earlier figures and the earlier Table 3.1 should not be cited.

## 7. Decisions and their justification

| Decision | Justification |
| :- | :- |
| Use the whole 5-second clip as the model input | SmartEars labels describe the whole clip. Shorter windows would carry labels that may not match their content, and there was no strong reason to discard one second. |
| Train, validate and test on SmartEars only; keep PVSD as an external test | PVSD is small, comes from few groups of birds, and is labeled by cohort. Run 1 confirms that the two datasets behave very differently. |
| Group the split by source recording | 534 SmartEars recordings are cut into several clips. A random split by file would place slices of one recording in both training and test data. |
| Keep the real 2 : 1 class ratio and use class weights | No data is discarded, and the loss already compensates for the imbalance. |
| Train every comparison model on the same binary task, splits and seeds | The panel pointed out that a three-class model cannot be compared with a binary one. |
| Report mean ± SD over 5 seeds | A single split cannot separate a real difference from split-to-split variation. Run 1 shows differences of one to three points between seeds. |
| Report results at 0.5 and at a recall-target threshold | Missing distress is the costly error, so the operating threshold is set from recall. The 0.5 results allow comparison with other work. |
| **The CNN–BiLSTM is no longer assumed to be the final model** | Run 1 does not show it to be better than lighter models on SmartEars. The model will be chosen in the next phase from candidates that run on the Raspberry Pi 4 gateway. |
| **Run 1 is the baseline for all later changes** | Any improvement is claimed only if it is measured under this same protocol. |

## 8. Rules for the next phase

- The split method stays as in Run 1: stratified by source category and grouped by source recording. PVSD stays external.
- A single test set is locked before any experiment (15% of SmartEars, `LOCK_SEED = 2026` in `SONARA_Run2_FirstPass.ipynb`). Experiments use only the other 85%, split into training and validation data per seed.
- Run 1 drew a new test set for each seed, so its test clips overlap the development data of the next phase. For that reason the final evaluation retrains the Run 1 CNN–BiLSTM under the locked protocol and compares the chosen setup against that, not against the Run 1 tables.
- Changes are selected using **validation** results only. Test and PVSD results are read once for the configuration finally chosen, so that they remain an honest estimate.
- A candidate model must run on the Raspberry Pi 4. Its inference time is measured there with `test/pi_latency_benchmark.py`.
- Every experiment is recorded in a new folder under `results/`, next to this one.

## 9. Limitations of this run

- Inference times are from a Colab CPU, not the Raspberry Pi 4.
- The zone-level results are a software simulation. They are not the controlled playback test or the comparison with veterinary observation.
- Hyperparameters were set by hand and were the same for every model, which may not suit each model equally.
- DS-CNN and the front-end-only model are reimplementations written for this comparison.
- The trained weights from this run were not kept.
