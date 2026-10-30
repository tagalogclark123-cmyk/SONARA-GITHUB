# SONARA Field Monitor (local dashboard)

A farmer-facing dashboard for the recorded field sessions in `field_data/`. It runs on your own
computer at **http://localhost:8000**. Nothing goes online, and there is nothing to install besides Python.

## What it shows

A sidebar with four pages. Every number comes from `field_data`; nothing is made up.

- **Dashboard**
  - Four cards for the selected recording: birds in the pen (from `sessions.csv`), unusual sounds
    (flagged usable clips), sensor connection, and "Check birds" alerts.
  - **Recorded pens**: one card per recording (a folder in `field_data/` with `report/clips.csv`),
    showing the highest status reached. Click a card, or use the menu at the top, to select it.
  - **Alert panel**: what happened and what to do, with a warning when many recordings did not arrive.
  - **Sensor node**: how many recordings arrived intact. Battery is not shown because it is not measured.
  - **Recent activity**: recording started/ended, unusual sounds, sensor connection lost/back, alerts.
  - **Sounds in this recording**: normal, unusual, and not received.
- **Zone Replay**: the zone status clip by clip (Play, slider, Listen), the sound under the slider,
  and a timeline of the recording.
- **Unusual Sounds**: each unusual sound next to a normal sound from the same pen (chosen
  automatically: not flagged, low score, about as loud), each with a Play button.
- **Help**: what the status means and what SONARA can and cannot do.

**Sound pictures** (spectrograms) are hidden at first; "Show sound pictures" turns them on. While a
sound plays, a white line moves across its picture so you can see which marks you hear. They are
log-mel spectrograms with the same settings as the model input (16 kHz, 400-sample window,
160-sample hop, 64 mel bands, dB), computed in the browser from the WAV files (`static/spectro.js`).
The colour scale is fixed (-55 to +20 dB), so clips can be compared.

Sensor connection is **Good** when at least 95% of recordings arrived intact, **Weak** from 75%,
**Poor** below that.

Scores, the model's test results and the session-by-session comparison are not on this page.
They are in the session reports (`field_data/<session>/report/`) and `results/final_evaluation/FINDINGS.md`.

**Your own logo:** save it as `dashboard/static/logo.png` (square works best) and click Refresh.

---

## How to run it

### 1. Get the latest version of the repo

If you already have `SONARA-GITHUB` on your computer, get the newest files first:
in VS Code, open the `SONARA-GITHUB` folder, then **Source Control** (left bar) > **...** > **Pull**.
Or in a terminal inside the folder: `git pull`.

If you don't have it yet:
`git clone https://github.com/tagalogclark123-cmyk/SONARA-GITHUB.git`

The `dashboard` folder sits next to `field_data`, so the dashboard finds the recordings by itself.

### 2. Open the folder in VS Code

**File > Open Folder...**, choose your `SONARA-GITHUB` folder. You should see `dashboard` and
`field_data` in the Explorer on the left.

### 3. Start the dashboard

**Terminal > New Terminal** (or `` Ctrl+` ``). The terminal opens in the `SONARA-GITHUB` folder. Type:

```
python dashboard/server.py
```

You should see:

```
SONARA Field Monitor
  Data folder: ...\SONARA-GITHUB\field_data
  Found 5 sessions, 463 clips

  Open this in your browser:  http://localhost:8000
  Press Ctrl+C here to stop.
```

### 4. Open it

**Ctrl+click** `http://localhost:8000` in the terminal. Keep the terminal open while you use the
dashboard. To stop it, click inside the terminal and press **Ctrl+C**.

Every time you open VS Code again, repeat steps 3 and 4. Tip: in the terminal, press the **Up arrow**
to bring back the last command.

### Shortcut without VS Code

Double-click `dashboard/start_dashboard.bat` in File Explorer. A black window opens and starts the
server. Then open http://localhost:8000. Close the window to stop it.

---

## After a new field session

1. Run `tools/sonara_field_report.py` as usual, so the new session folder has `report/clips.csv`.
2. Add a row for it in `field_data/sessions.csv` (site, pen, birds, age, health, notes).
3. Put the session folder in `field_data/`.
4. In the browser, click **Refresh**. No restart is needed.

## Settings

`dashboard/settings.json` holds the alert rule (8 of the last 20 usable clips), the damaged-clip rule
(more than 33 of 667 packets lost) and the "No data" time (10 minutes). Edit it, save, and click
**Refresh**.

Whether a clip is "unusual" comes from what the gateway decided at the time (the `flagged` column in
`clips.csv`, threshold 0.535). The dashboard does not re-score clips. Do not tune the threshold on
field data: it was chosen on validation data.

---

## If something goes wrong

| What you see | What to do |
|---|---|
| `'python' is not recognized...` | Try `py dashboard/server.py`. If that also fails, install Python from python.org and tick **Add python.exe to PATH** during setup. Then close and reopen VS Code. |
| `can't open file ... server.py: No such file` | The terminal is in the wrong folder. Go to the `SONARA-GITHUB` folder (`cd path\to\SONARA-GITHUB`) and try again. If you are already inside `dashboard`, use `python server.py`. |
| `Cannot find the data folder` | `field_data` is not next to `dashboard`. Run `python dashboard/server.py --data "C:\path\to\field_data"`. |
| `Port 8000 is already in use` | The dashboard is probably already running in another terminal. Or use another port: `python dashboard/server.py --port 8001`, then open http://localhost:8001. |
| Page shows "Could not load the recordings" | Read the message on the page and in the terminal. Usually a session's `clips.csv` is missing or broken. |
| A session is missing | Its folder has no `report/clips.csv`. Run the field report for it first. |
| "Recording not available" next to a sound | The WAV is not in that session's `audio/` folder. |
| Page cannot be reached | The terminal running `server.py` was closed. Start it again (step 3). |
| Page looks like an old version | Press **Ctrl+F5** in the browser. |

Needs Python 3.8 or newer. Check with `python --version`.
