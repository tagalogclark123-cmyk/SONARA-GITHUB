# SONARA project context (working notes)

**Purpose of this file.** A complete record of the SONARA capstone work done with Claude Code: the project, the data, every methodological decision and why it was made, all results so far, the current state of each notebook, open items, and how the work is done. It exists so that nothing is lost if the conversation is compacted or a new session starts. **Read this first in any new session, and update it whenever something changes** (new results, decisions, pushes, open items).

Last updated: 16 October 2026, after the hyperparameter tuning results came in (Run 2 settings kept). Next expected event: the team runs `SONARA_Final_Evaluation.ipynb` once in Colab and sends the executed notebook link.

---

## 1. Project at a glance

| Item | Detail |
| :- | :- |
| Title (manuscript) | SONARA: Bioacoustic Surveillance for Coop-Level Detection of Respiratory Distress in Poultry Using Supervised Machine Learning |
| Degree | BS Data Science, Data Science Department, College of Information Technology and Computing (USTP; field site under consideration: USTP Claveria) |
| Team | Arcel Joy Bacuetes, Ray Bernados, Karl Michael Gaca, Edrian Jugan, Gabriella Mae Lapad (Gabby), Clark James Tagalog |
| Adviser | Jhun Brian M. Andam |
| Panel | Albert Christopher Daniot II, MDS ("Chooks" in the internal matrix); Angelie P. Sabanal-Abao, MSc; Matthew R. Maulion, MSc (panel head, "Matt") |
| User in this session | Clark (GitHub `tagalogclark123-cmyk`; the team's Drive account owns the Drive files) |
| What SONARA is | ESP32 sensing nodes (INMP441 I2S microphone, SX1278 LoRa, 18650 battery) record poultry audio per coop zone; a Raspberry Pi 4 gateway classifies 5-s clips as Distress / Non-distress and raises zone-level alerts via a fixed node-to-zone mapping |
| Current stage | Panel revisions after the proposal defense; rebuilding the ML pipeline honestly; tuning done (Run 2 settings kept); **final evaluation ready to run** |

---

## 2. Where everything lives

### GitHub repository: `tagalogclark123-cmyk/SONARA-GITHUB` (public)

Local clone: `D:\SONARA-GITHUB` (an older clone existed at `D:\SONARA GITHUB`, no longer used). Branch `main`. GitHub CLI `gh` is installed and signed in as `tagalogclark123-cmyk`.

| Path | What it is | Status |
| :- | :- | :- |
| `Smartears/Healthy`, `Smartears/Sick`, `Smartears/None` | SmartEars audio, 2,000 clips each | Data |
| `PVSD/Healthy`, `PVSD/Unhealthy`, `PVSD/Noise` | PVSD audio, 346 files | Data (external test only) |
| `SONARA_CNN_OCT9.ipynb`, `SONARA_NEW_V5 (2).ipynb` | The team's original V5 training notebook (source of the old 0.890 result) | Superseded, kept for history |
| `SONARA_REVAMP_DATASET (2).ipynb` | Original dataset/feature notebook | Superseded |
| `test/SONARA_DATASET_V2.ipynb`, `test/SONARA_TRAIN_V6.ipynb` | Notebooks written in a separate claude.ai conversation (Drive-based, 4-s crops) | Superseded by the notebooks below; not run |
| `test/sonara_models.py` | Model definitions shared with the Pi benchmark (CNN_BiLSTM, CNNFrontEndOnly, DSCNN, mobilenet_v3_small) | In use |
| `test/pi_latency_benchmark.py` | Times models on the Raspberry Pi 4; changed to time a 5-s clip (500 frames) | In use |
| `SONARA_Chapter3_Pipeline.ipynb` | Run 1 pipeline (4 models × 5 seeds, SmartEars train/val/test, PVSD external) | Done (Run 1) |
| `SONARA_Run2_FirstPass.ipynb` | Run 2 first pass (normalization, ImageNet weights, recipe), validation only | Done |
| `SONARA_Run2_SecondPass.ipynb` | Run 2 second pass (no normalization, loudness check, 3-class, gain augmentation) | Done |
| `SONARA_Hyperparameter_Tuning.ipynb` | Optuna search over 22 training settings for B8; writes `chosen_system_model_config.json` | Done (16 Oct): Run 2 settings kept |
| `SONARA_Final_Evaluation.ipynb` | Final evaluation: trains B8, C2, A0 on 5 seeds, opens locked test + PVSD once, zone alerts, Pi export | **To run next** |
| `results/run1_baseline_2026-10-12/` | Run 1 record: `RESULTS_AND_DECISIONS.md`, executed notebook, text outputs, figures, `per_run_results.csv` | Committed |
| `results/run2_first_pass/` | First-pass record: `FINDINGS.md`, executed notebook, text outputs | Committed |
| `results/run2_second_pass/` | Second-pass record: `FINDINGS.md` (with the B8 decision), executed notebook, text outputs | Committed |
| `results/hyperparameter_tuning/` | Tuning record: `FINDINGS.md`, executed notebook, text outputs, `search_trials.csv`, `optuna_study.db`, importance CSV and figures, `confirm/*.json`, `confirmation_results.csv`, `chosen_system_model_config.json` | Committed |
| `PROJECT_CONTEXT.md` | This file (no private details: the repo is public) | Committed |

Merged pull requests: #1 Chapter 3 pipeline aligned with V2/V6 and 5-s clips · #2 Run 1 record + first-pass notebook · #3 first-pass record + second-pass notebook · #4 tuning notebook · #5 second-pass record + final evaluation · #6 widened hyperparameter search.

### Google Drive (team account)

**This repository is public, so Drive file IDs and private details are not kept in this file.** Claude keeps them in its local memory (`sonara-drive-files`); team members can find the files in the shared Drive.

| Item | Location |
| :- | :- |
| Manuscript (Google Doc "SONARA: BIOACOUSTIC SURVEILLANCE", tabs listed in §5) | Team Drive |
| Revision Matrix Answers (draft, with verbatim changes) | Team Drive |
| Executed Colab notebooks (Run 1, first pass, second pass, tuning) | Team Drive; copies of the executed notebooks are in `results/` |
| Run 2 outputs | `MyDrive/SONARA/run2_first_pass/`, `MyDrive/SONARA/run2_second_pass/` |
| Tuning outputs | `MyDrive/SONARA/hyperparameter_tuning/` (also copied to `results/hyperparameter_tuning/`) |
| Final evaluation outputs (after running) | `MyDrive/SONARA/final_evaluation/` |

To read an executed Colab notebook: `download_file_content` with the file ID, base64-decode the content, parse the JSON, and print stream outputs per cell.

---

## 3. The data

### SmartEars (training, validation and test)

- 6,000 clips: Healthy 2,000, Sick 2,000, None 2,000. 44.1 kHz, mono, 16-bit, durations 4.985 to 5.00 s (259 clips slightly under 4.99 s).
- File names: `rpiNNNN-YYYYMMDDhhmmss.wav` or `rpiNNNN-YYYYMMDDhhmmss-k.wav`. `rpiNNNN` is the recording device, the timestamp is the recording start, `-k` is a segment of the same recording.
- 5,248 distinct source recordings; **534 recordings are cut into several clips (up to 8)**; 69 recordings contain clips of different classes; 90 devices, 1,258 device-days. **0 exact duplicate files.**
- Label mapping: Healthy → Normal → Non-distress (0); None → Noise → Non-distress (0); Sick → Distress (1). Binary ratio 4,000 : 2,000 (2 : 1).

### PVSD (Poultry Vocalization Signal Dataset; external test only)

- 346 files at 48 kHz mono: Healthy 139 (6.1 to 906 s, median 20.8 s), Unhealthy 121 (0.46 to 134 s, 26.4% shorter than 5 s), Noise 86 (0.58 to 104 s, 11.6% shorter than 5 s).
- Labels come from a treated versus untreated group of birds (few groups), not per-clip review. Used only as a stress test of transfer to other recordings.
- Short files are padded on the features (dB channel with the file's own minimum, deltas with 0); each file is scored by averaging non-overlapping 5-s windows (at most 50, evenly spaced).

---

## 4. Pipeline as it stands (shared by the current notebooks)

| Step | Setting |
| :- | :- |
| Preprocessing | Resample to 16 kHz (`scipy.signal.resample_poly`), mono, stored as int16 |
| Input | **The whole 5-second clip** (80,000 samples). Decided by the user: no strong reason to drop a second; labels describe the whole clip |
| Features | torchaudio MelSpectrogram (n_fft 400 = 25 ms, hop 160 = 10 ms, 64 mels, power 2) → AmplitudeToDB → delta and delta-delta → 3 × 64 × 500 |
| Normalization | None (per-clip normalization hurt in Run 2) |
| Split | Stratified by source category, **grouped by source recording**, `StratifiedGroupKFold` |
| Locked test set | 15% of SmartEars from `LOCK_SEED = 2026` (3 of 20 folds): **871 clips, id `bf636617`**. Never used before the final evaluation |
| Development set | The other 85% (5,129 clips); per seed split into train (14 of 17 folds ≈ 70% of all) and validation (3 of 17 ≈ 15%) |
| Seeds | Run 2 exploration: 7, 21, 42. Final: 7, 21, 42, 77, 99. Tuning search split: seed 1 |
| Loss | Weighted cross-entropy (class weights N̄/N_c from training clips) with label smoothing |
| Checkpoint | Lowest validation loss |
| Threshold | Chosen per run on its own validation clips: highest threshold reaching the target distress recall (grid 0.01 to 0.99, step 0.005). Targets: **90% (primary) and 95%** |
| Loudness check | Re-score clips with the dB channel shifted by −20 to +20 dB, threshold fixed |

---

## 5. Manuscript state and what must change

The manuscript is the team's Google Doc (see §2). Main tab: **FINAL SHEET** (Chapters 1 to 3 + references; title page dated July 2026; no results chapter yet). Other tabs: Internal Revision Matrix (18 rows, all "Not started" except one "Under review" as of 9 Oct), Rev Matrix Summary (copy of the Revision Matrix Answers), REVISION MATRIX (first-defense matrix, filled in with page numbers), request letters (BAI, chancellor), proposal scripts, tables of contents, glossary, older drafts ("Copy of FINAL SHEET", "project proposal", "ch 3 revision", "not final"), TRL, IP, techno deck, business plan, pitch deck, techno interview report, "weakpoints" (an earlier critique), cost, equations, and administrative tabs.

**Tracked suggestions already in FINAL SHEET** (from the Revision Matrix Answers doc; not yet accepted): reframed contribution (an evaluated surveillance pipeline), restructured objectives (framework / classifier + zone attribution / test and validation), CNN vs BiLSTM roles, EDA rationale for merging Normal and Noise, system-level validation paragraphs (controlled playback + veterinary observation), variable definitions for Eqs 3-1 to 3-3, label smoothing explanation (0.02 → targets 0.99/0.01, Szegedy et al. 2016), softmax definition, PCC wording (Hair et al. 2019, "minimum check only"), node placement calibration (90% grid coverage), parameter breakdown text with bracketed fill-ins.

**Chapter 3 text that no longer matches the method (must be rewritten from the final results):**

- 3.1.1: "balanced by limiting samples" → real 2 : 1 ratio with class weights; SmartEars only for training; PVSD external.
- 3.1.2: "1 to 2 second windows" → whole 5-s clip; augmentation list (fan/cage/speech noise) → the tuned augmentation actually used.
- 3.1.4: add grouping by source recording and the locked test set.
- 3.2.1: model is now expected to be MobileNetV3-Small with ImageNet weights (B8), not the CNN–BiLSTM; Table 3.1 must be rebuilt from the final evaluation; old 0.890 / 0.844 / 0.940 must not be cited; remove "Table X", the 3-class DS-CNN row and "compact enough for a Pi" until measured.
- 3.2.2 to 3.2.3: hyperparameters now come from the documented search; state that seeds were not tuned.
- 3.2.4: PCC kept only as a minimum check; baselines and confidence intervals carry the comparison.
- 3.3.2: threshold rule (90% and 95% validation recall), not "typically 0.5".
- 3.3.5: final evaluation design; zone simulation is a simulation; playback and field tests still needed.
- Other known issues: Qiu et al. (2025) is a BiLSTM-TDOA **localization** paper but is described as classification only (2.4.2, Table 2.1); Du et al. (2018) listed twice; Section 3.5 "third objective" paragraph has old and new text merged; leftover "Localization" wording (3.3 heading, scope); SmartEars missing from Chapter 2; overclaims in Chapter 2 ("definitively proved", "gold standard", "unexcelled", "perfectly mirrors", "effortlessly outperform", "ensures the high diagnostic accuracy").

### Panel comments (Internal Revision Matrix, 18 rows) and where they stand

| Row(s) | Panelist → member | Comment (short) | Where the answer comes from |
| :- | :- | :- | :- |
| 1 | Chooks → Clark | Combining two features is not a contribution | Reframed contribution (suggestion in Doc); evaluated pipeline + honest evaluation |
| 2 | Chooks → Clark | Restructure objectives (framework / develop / evaluate) | Suggestion in Doc |
| 3 | Chooks → Karl | Explain CNN (spectral) vs BiLSTM (temporal) roles | Suggestion in Doc; now also: CNN–BiLSTM no longer the chosen model |
| 4 | Chooks → Ray | EDA should match the binary task | New Figure 3.2 (Distress vs Non-distress) from the pipeline; errors by Normal vs Noise reported |
| 5 | Chooks → Karl | Why classify at the gateway; how is a detection validated | Validation section (offline, playback, field); gateway reasoning; zone simulation |
| 6 | Angelie → Gabby | Research pipeline diagram | Not done yet |
| 7, 9, 18 | Angelie/Matt → Edrian, Gabby, Arcel | Define equations and variables | Done in Doc (teammates added "where:" lists) |
| 8 | Angelie → Karl | Why label smoothing 0.02 | Explanation in Doc; now tuned by search (0 to 0.2) |
| 10 | Angelie → Karl | Define softmax | Suggestion in Doc |
| 11, 12, 17 | Angelie/Matt → Clark | PCC 1.25 is a rule of thumb; use baselines | PCC as minimum check; majority class + trained baselines + CIs |
| 13 | Matt → Karl | How the triangular node placement issue was resolved | Dropped triangulation; zone-level attribution |
| 14 | Matt → Ray | Node placement optimal vs maximum coverage; sick birds avoid feeders | Calibration protocol text in Doc (90% grid coverage); vet confirmation pending |
| 15, 16 | Matt → Karl | Model comparison fairness, parameter counts, hyperparameters, runtime | All models binary on the same splits; parameter breakdown; search; CPU timing; Pi timing pending |

### Earlier claude.ai conversation (pasted by the user, 9 to 12 Oct)

It audited the project and code, found V5 bugs (BiLSTM read the last time step, `best_state` not deep-copied, threshold tuned for accuracy, PVSD pooled, unseeded crops), proposed Fixes 1 to 9, contribution options (transfer evidence + zone attribution protocol), revised objectives, a three-level validation plan (offline / controlled playback / field with vet labels), node calibration protocol (coverage C* and leakage L*), PCC replacement by baselines, and manuscript fixes. It also created the V2/V6 notebooks and a "SONARA Panel Revision Plan" Claude Doc (not accessible here).

**Open hardware decision from that conversation (not resolved):** LoRa cannot realistically carry audio (a 5-s 16 kHz 16-bit clip is about 160 kB; LoRa SF7 is about 5.5 kbps plus duty-cycle limits). Options: Wi-Fi from ESP32 to the Pi, a small on-node model sending events over LoRa, or short compressed clips at low duty cycle. Questions only the team can answer: source of the "80% coverage" figure, the earlier triangular placement, Pi 4 RAM, LoRa band (NTC rules), Claveria approval status.

---

## 6. Decision log (chronological, with reasons)

| Date | Decision | Reason |
| :- | :- | :- |
| 9 Oct | Build one Colab notebook aligned with Chapter 3 that reads audio from GitHub | User request; avoids Drive setup |
| 9 Oct | Do **not** pool PVSD with SmartEars; PVSD is external test only | PVSD is small, from few bird groups, cohort-labeled; pooling lets models learn the dataset |
| 9 Oct | One clip-level input per file, not 1 to 2 s windows | Labels describe the whole clip; short slices create wrong labels |
| 9 Oct | Group splits by source recording | 534 recordings are cut into several clips; random splits leak |
| 9 Oct | Keep the real 2 : 1 ratio with class weights (no undersampling) | No data discarded; loss already compensates |
| 9 Oct | Threshold from a validation recall target, also report 0.5 | Missing distress is the costly error |
| 9 Oct | All comparison models binary on the same splits and seeds; 5 seeds, mean ± SD | Panel comments 15 and 16; fair comparison |
| 9 Oct | Align the pipeline with V2/V6 (dB features, masking, models from `test/sonara_models.py`) | One consistent method |
| 9 Oct | **Use the whole 5-s clip instead of a 4-s crop** (user's call) | No justifiable reason for 4 s |
| 12 Oct | Record Run 1 as the baseline; CNN–BiLSTM no longer assumed final | Run 1 showed it is not better than DS-CNN or MobileNetV3 |
| 12 Oct | Raise numbers only by legitimate means; validation-only selection; locked test set | User: "no leak, as ethically as possible" |
| 12 Oct | Run 2 first pass: normalization, ImageNet weights, recipe | Highest-expected-value changes |
| 13 Oct | Run 2 second pass: remove normalization, loudness check, 3-class, ±12 dB gain | First pass showed normalization hurt; robustness to mic level matters for INMP441 |
| 14 Oct | **System model = B8** (MobileNetV3-Small, ImageNet, no normalization, ±12 dB gain on every clip); C2 EfficientNet-B0 runner-up; A0 CNN–BiLSTM baseline | Pre-declared rule: highest validation ROC-AUC among Pi-deployable, level-robust setups; smaller model when tied (C2 vs B8 tied 0.9699 vs 0.9698) |
| 14 Oct | Report two operating points: 90% (primary) and 95% recall | User asked; both fixed before opening the test set |
| 14 Oct | Tune training settings by search instead of defaults; seeds are **not** tuned | User: convention is not a justification; tuning seeds would be cherry-picking |
| 14 Oct | Widen the search to 22 settings and a one-day budget (200 trials or 20 h) | User: "as wide as possible", can wait up to a day |
| 14 Oct | Only B8 is tuned; C2 and A0 keep Run 2 settings | Time; must be disclosed in the paper (favours B8 slightly) |
| 16 Oct | **Tuning result: keep the Run 2 settings for B8** | Pre-declared rule: the 3 best search settings were all lower on all 3 confirmation splits (0.9657 to 0.9673 vs 0.9704) |

---

## 7. Results so far

### Run 1 (12 Oct): `SONARA_Chapter3_Pipeline.ipynb`, 4 models × 5 seeds, new test split per seed

Test set about 900 clips per seed; mean ± SD.

| Model | Params | Acc @0.5 | Distress F1 @0.5 | ROC-AUC | Acc @recall-target | FPR @recall-target | PVSD ROC-AUC |
| :- | -: | :- | :- | :- | :- | :- | :- |
| Majority class | 0 | 0.665 | 0 | 0.500 | — | — | — |
| CNN front end only | 39,106 | 0.730 ± 0.032 | 0.638 | 0.797 | 0.639 | 0.499 | 0.650 |
| DS-CNN | 148,610 | 0.874 ± 0.010 | 0.811 | 0.927 | 0.835 | 0.189 | 0.558 |
| MobileNetV3-Small (random init) | 1,519,906 | 0.866 ± 0.025 | 0.805 | 0.925 | 0.833 | 0.198 | 0.525 |
| CNN–BiLSTM | 1,221,186 | 0.863 ± 0.015 | 0.800 | 0.918 | 0.803 | 0.243 | 0.799 |

Findings: CNN–BiLSTM not better than DS-CNN or MobileNetV3 (1 to 2 wins of 5); BiLSTM helps over its front end (5/5); false alarms concentrated on healthy calls; no model transfers to PVSD at its SmartEars threshold (all below 0.65 majority accuracy); short PVSD files flagged far less. Weights were not saved (SAVE_TO_DRIVE off). Full record: `results/run1_baseline_2026-10-12/RESULTS_AND_DECISIONS.md`.

### Run 2 first pass (12 Oct): validation only, seeds 7/21/42, locked test id `bf636617`

| Setup | ROC-AUC | Acc @0.5 | False alarms @0.90 recall |
| :- | :- | :- | :- |
| A0 CNN–BiLSTM, Run 1 settings | 0.944 | 0.882 | 14.1% |
| A1 + normalization | 0.934 | 0.877 | 16.4% |
| A2 + normalization + recipe | 0.946 | 0.885 | 13.3% |
| B0 MobileNetV3-Small, Run 1 settings | 0.936 | 0.874 | 17.8% |
| B1 + normalization | 0.901 | 0.833 | 28.4% |
| B2 + normalization + ImageNet | 0.955 | 0.892 | 11.4% |
| B3 + normalization + recipe | 0.938 | 0.880 | 15.5% |
| B4 + normalization + ImageNet + recipe | 0.961 | 0.913 | 8.6% |
| C1 EfficientNet-B0 + normalization + ImageNet + recipe | 0.964 | 0.919 | 7.4% |

"Recipe" = AdamW, lr 3e-4, weight decay 0.01, 2 warm-up epochs + cosine, mixup 0.2, max 40 epochs, patience 10. Findings: ImageNet weights +0.055 AUC (3/3); recipe helps (3/3); normalization hurts (0/3). Record: `results/run2_first_pass/FINDINGS.md`.

### Run 2 second pass (13 to 14 Oct): validation only, same splits

| Setup | ROC-AUC | Acc @0.5 | FA @0.90 recall | Recall at −20 / −10 / +10 / +20 dB |
| :- | :- | :- | :- | :- |
| A3 CNN–BiLSTM + recipe, no normalization | 0.953 | 0.895 | 11.5% | 0.39 / 0.80 / 0.86 / 0.62 |
| B5 MobileNetV3 + ImageNet + recipe, no normalization | 0.964 | 0.917 | 7.3% | 0.72 / 0.87 / 0.88 / 0.84 |
| C2 EfficientNet-B0 + ImageNet + recipe, no normalization | 0.970 | 0.931 | 6.1% | 0.66 / 0.86 / 0.89 / 0.79 |
| B6 B4 + three classes | 0.962 | 0.910 | 8.6% | flat (normalized) |
| B7 B5 + three classes | 0.969 | 0.927 | 6.4% | 0.76 / 0.88 / 0.88 / 0.82 |
| **B8 B5 + ±12 dB gain on every clip** | **0.970** | **0.918** | **7.2%** | **0.85 / 0.89 / 0.90 / 0.89** |

Per seed, C2 vs B8 ROC-AUC: 0.9691/0.9678, 0.9733/0.9723, 0.9674/0.9694 (tie). Sizes: B8 1,519,906 params (6.1 MB), Colab CPU 11.7 ms/clip; C2 4,010,110 (16 MB), 43.8 ms; CNN–BiLSTM 70.8 ms. Four seed-42 runs trained on a CPU session (same code). B8 vs A0 on validation: AUC 0.944 → 0.970, acc 0.882 → 0.918, FA 14.1% → 7.2%, healthy-call FA 20% → 11%. Record: `results/run2_second_pass/FINDINGS.md`.

### Hyperparameter tuning (14 to 16 Oct): validation only

- 71 trials in 20.3 h of training (30 completed, 37 pruned, 4 interrupted by disconnects). Search split seed 1. Run 2 settings scored 0.9684; best trial 0.9733 (trial 3).
- The search converged on Adam + constant learning rate + label smoothing 0.15 to 0.20 + mixup 0.4 to 0.8 + ±18 to 24 dB loudness on 25% of clips + 3 time and 3 frequency masks.
- Trials 3 and 23 had identical settings and scored 0.9733 vs 0.9692: run-to-run noise (about 0.004) is as large as the best trial's lead.
- Importance (fANOVA, rough): loudness share 0.16, mixup 0.12, warm-up 0.10, loudness size 0.07; optimizer, schedule, class weights ≤ 0.006.
- Confirmation on seeds 7/21/42 (ROC-AUC, FA @0.90, FA @0.95): Run 2 settings 0.9704, 6.9%, 13.4%; trial 3 0.9657, 6.3%, 14.6%; trial 47 0.9673, 7.3%, 15.0%; trial 38 0.9627, 8.3%, 19.2%. Every candidate lower on all 3 seeds; all met the loudness condition.
- Run 2 settings ranked 12th of 30 completed trials on the search split; 21 completed trials scored above 0.96. Trial 9 (Adam, lr 0.0062) collapsed to 0.5.
- Per seed confirmation (7 / 21 / 42): Run 2 settings 0.9698 / 0.9723 / 0.9692; trial 3 0.9647 / 0.9668 / 0.9657; trial 47 0.9683 / 0.9689 / 0.9648; trial 38 0.9616 / 0.9698 / 0.9566. Trial 3 peaked at or near its 60-epoch cap.
- **Process problems (do not change the decision):** (1) some sessions had no GPU: trials 23, 27, 32, 33, 34 took 2 to 3.5 h each (about 12.5 of the 20 search hours) and three seed-7 confirmation runs took 1 to 3 h, so only about 70 settings were tried instead of 150 to 200; (2) trials 21 to 25 repeated trials 1 to 5 exactly because the TPE sampler is seeded with a fixed number and restarted after a disconnect (66 distinct settings). Fix for any future use: seed the sampler per session.
- **Decision: Run 2 settings kept** (written to `chosen_system_model_config.json`). Record: `results/hyperparameter_tuning/FINDINGS.md` (includes suggested paper wording and the process problems).

---

## 8. Hyperparameter tuning (`SONARA_Hyperparameter_Tuning.ipynb`, design; run finished 16 Oct)

- Study name `sonara_b8_wide_v2`, stored in `MyDrive/SONARA/hyperparameter_tuning/optuna_study.db` (resumes after disconnects).
- **Stage 1 search:** Optuna TPE (multivariate, grouped), 25 random start trials, median pruning (15 startup trials, 10 warm-up epochs), divergence stops a trial. Budget: up to **200 trials or 20 hours of training** (counted across sessions). Search split = seed 1. Score = validation ROC-AUC at the best checkpoint. Trial 1 = Run 2 B8 settings (verified to reproduce its earlier score).
- **22 searched settings:** optimizer (AdamW, Adam, SGD Nesterov 0.9); lr 1e-6 to 1e-2 log (SGD 1e-4 to 0.3); weight decay 1e-7 to 0.3 log; batch size 8 to 128 (powers of 2); class weights balanced/none; schedule cosine/constant/plateau; warm-up 0 to 5; max epochs 20 to 100 step 10; patience 5 to 20 step 5; head dropout 0 to 0.7; label smoothing 0 to 0.2 step 0.01; mixup 0 to 1.0 step 0.1; gain 0 to 24 dB step 3; gain share 0.25 to 1 step 0.125; time shift 0 to 2 s step 0.25; shift share 0 to 1 step 0.25; time- and frequency-mask probability 0 to 0.8 step 0.1; max mask width 2.5% to 40% step 2.5%; number of masks 1 to 3 (each).
- **Not tuned:** seeds; model and features; recall targets; small constants (SGD momentum, plateau halving and 2-epoch wait, cosine floor 2%, minimum mask 5 frames / 3 bands).
- **Stage 2 confirm:** top 3 distinct settings + Run 2 settings retrained on seeds 7, 21, 42, loudness check at ±10 dB at both 90% and 95% recall thresholds.
- **Stage 3 decide (rule fixed in advance):** a tuned setting replaces the Run 2 settings only if mean validation ROC-AUC is higher, higher on ≥ 2 of 3 seeds, and recall and false-alarm rate change ≤ 0.10 at ±10 dB at both operating points. Otherwise keep Run 2 settings. Writes `chosen_system_model_config.json`.
- Outputs: `search_trials.csv`, `setting_importance.csv` (fANOVA), `figure_setting_importance.png`, `figure_setting_vs_score.png`, `confirmation_results.csv`.

## 9. Final evaluation (`SONARA_Final_Evaluation.ipynb`, not yet run)

- Refuses to start until `chosen_system_model_config.json` exists (path `MyDrive/SONARA/hyperparameter_tuning/`); applies it to B8. C2 and A0 keep Run 2 settings.
- Stage A: train B8, C2, A0 on seeds 7, 21, 42, 77, 99 (development data only); each run saves weights, validation predictions and thresholds for 90% and 95%.
- Stage B: `frozen_models.json` with thresholds, setups and weight MD5s, plus a fingerprint.
- Stage C: opens the locked test set (871 clips) and PVSD once; logs every opening in `test_opened_log.json` (warns if models changed after an opening); saves probabilities, including the test clips at every loudness shift.
- Stage D: tables at both operating points (mean ± SD over seeds, 95% bootstrap CIs over recordings, 1,000 resamples), 90% vs 95% comparison table, threshold 0.5 table, false alarms by source, paired seed-by-seed comparisons, seed-averaged models, loudness check, ROC + confusion matrices.
- PVSD per file at both operating points.
- Stage E: zone alert simulation (one clip per zone every 30 s; false alerts counted as alert-hours per week; rule grid windows 10/20/40/60 clips × shares 0.2 to 0.6; choose shortest median time to alert at outbreak share 0.3 with ≤ 1 false alert-hour per week, on validation; report on test). Clips drawn independently, so real false alerts are likely higher.
- Stage F: TorchScript export of B8 seed 42 with feature extraction (`sonara_system_model.pt`), plain weights for `test/pi_latency_benchmark.py`, `deployment_config.json` with both operating points (90% primary).
- Expect about 3 hours on a T4 (more if tuned settings use many epochs or small batches).

---

## 10. Open items and next steps

1. ~~Run the tuning notebook~~ Done 16 Oct; Run 2 settings kept; record in `results/hyperparameter_tuning/` (committed).
2. **Run the final evaluation once**, start to finish, on a GPU session; do not change settings after Stage C. It reads `chosen_system_model_config.json` from `MyDrive/SONARA/hyperparameter_tuning/`. Record results in `results/final_evaluation/`.
3. Run `test/pi_latency_benchmark.py` on the Raspberry Pi 4 with the exported weights (row 16).
4. Rewrite Chapter 3 from the final results (§5 list), build the new Table 3.1, write the results chapter.
5. Decide the node-to-gateway link (LoRa vs Wi-Fi vs on-node model) with the adviser.
6. Playback calibration (coverage and cross-zone leakage) and field validation with the campus veterinarian (Claveria approval pending).
7. Fill in the Internal Revision Matrix answers (draft answers exist in the Revision Matrix Answers doc; some need updating to the new model and results).
8. Research pipeline diagram (row 6).
9. Fix references (Qiu et al. 2025 description, duplicate Du et al. 2018, missing SmartEars/PVSD citations).
10. ~~Commit `PROJECT_CONTEXT.md` and `results/hyperparameter_tuning/`~~ Pushed 16 Oct.

---

## 11. How the user wants the work done

- Be honest about what is and is not supported; never claim results that were not measured; say when something was only tested on sample clips.
- No data leakage; improvements only by legitimate means; selection on validation; test opened once.
- Every setting should be justified (by evidence or search), not by "it is the default".
- Explain in plain language; the user often asks "why" and "what changes".
- Pushing: when asked, create a branch, commit, push, open a PR with `gh`, merge it to `main`, return local to `main`. Commit messages end with the co-author line; PR bodies end with the Claude Code line.
- The team runs notebooks in Colab themselves and sends Drive links to executed notebooks.
- Keep this file updated as the conversation goes.

---

## 12. Tooling notes for Claude (environment)

- Machine: Windows 11, i5-12450H, 16 GB RAM, **no GPU** (full training only in Colab). Shells: PowerShell and Git Bash.
- **As of 16 Oct the old scratchpad venv is partly broken** (its pandas package files were removed, probably by temp-folder cleanup). For data analysis use the system Python (it has pandas; do not use `-I`, which hides the user site-packages). Rebuild a venv before any further smoke tests of notebooks.
- Test environment (Python venv): `C:/Users/Clark/AppData/Local/Temp/claude/D--SONARA-GITHUB/3b79cc34-8d30-4bc4-ab1e-ffa6c64fc150/scratchpad/venv` with torch 2.14.1 CPU, torchaudio 2.11, torchvision 0.29.1, librosa, soundfile, scikit-learn, optuna 5.0, nbformat. Sample data for smoke tests in that scratchpad's `data/` (113 SmartEars clips + a stand-in PVSD folder of 18 files, one 1.5 s and one 15 s per class). ImageNet weights cached in the new scratchpad's `torch_home`.
- Notebooks are written as percent-format Python sources and converted to `.ipynb`: `build_nb.py` (`parse`, `to_ipynb`) in the old scratchpad; sources and build scripts in the session scratchpad `C:/Users/Clark/AppData/Local/Temp/claude/D--SONARA-GITHUB/bf6dd8bd-b990-44ca-bc1b-eb065150e278/scratchpad/`: `sonara_tuning.py` + `build_tuning.py`, `sonara_final.py` + `build_final.py`, `sonara_run2.py` (first pass), `sonara_run3.py` + `gen_run3.py` (second pass); Chapter 3 pipeline source `sonara_nb.py` in the old scratchpad. Smoke mode replaces the repo path, turns off Drive and sets `QUICK_RUN = 40`. These scratchpads are temporary; if they are gone, edit the `.ipynb` files in the repo directly.
- Bash heredocs that contain Python triple quotes sometimes fail ("unexpected EOF"); write such scripts with the Write tool instead.
- Earlier, a shallow fetch made the old clone shallow; it was repaired with `git fetch --unshallow`.

---

## 13. Setup names (glossary)

| Name | Meaning |
| :- | :- |
| A0 | CNN–BiLSTM, Run 1 settings (Adam 1e-4, plateau, 50 epochs, patience 8, gain ±6 dB at 20%) |
| A1 / A2 / A3 | A0 + normalization / + normalization + recipe / + recipe without normalization |
| B0 to B8 | MobileNetV3-Small variants (B4: normalization + ImageNet + recipe; B5: ImageNet + recipe; B6/B7: three classes; **B8: B5 + ±12 dB gain on every clip = system model**) |
| C1 / C2 | EfficientNet-B0 + ImageNet + recipe, with / without normalization (C2 = runner-up) |
| Recipe | AdamW, lr 3e-4, wd 0.01, warm-up 2 + cosine, mixup 0.2, 40 epochs, patience 10 |
| Locked test set | 871 SmartEars clips, id `bf636617`, from `LOCK_SEED = 2026` |
| Operating points | Thresholds set on validation for 90% (primary) and 95% distress recall |

---

## Change log of this file

- 14 Oct 2026: created after PR #6.
- 16 Oct 2026: tuning results added (Run 2 settings kept); next step is the final evaluation.
- 16 Oct 2026: tuning output files from the user's zip added to `results/hyperparameter_tuning/`; recorded CPU sessions and repeated trials.
- 16 Oct 2026: removed Drive file IDs, the team email and private details before pushing (the repo is public); they are kept in Claude's local memory.
