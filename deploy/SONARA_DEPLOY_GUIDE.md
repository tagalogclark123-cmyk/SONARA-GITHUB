# SONARA Farm Deployment Guide (3 Nov 2026)

Goal: record as many 5-second clips as possible from every node, with notes that say what was happening in each pen. The Pi saves every clip and also classifies it live. It never deletes anything.

## Quick commands (cheat sheet)

**From the laptop (PowerShell, connected to the router's Wi-Fi):**

| What | Command |
| --- | --- |
| Log in to the Pi | `ssh keith@192.168.1.247` |
| Set the Pi's clock (do this first at each farm) | `ssh -t keith@192.168.1.247 "sudo date -s '$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')'"` |
| Copy all data to the laptop | `scp -r keith@192.168.1.247:~/sonara_deploy C:\Users\<you>\Downloads\farm_data_nov3` |

If PowerShell says `ssh`/`scp` "is not recognized", type `C:\Windows\Sysnative\OpenSSH\ssh.exe` (or `scp.exe`) instead.

**On the Pi (after logging in):**

| What | Command |
| --- | --- |
| Load the shortcuts (if `live` is "not found") | `source ~/.bashrc` |
| Watch clips arrive (Ctrl+C leaves the view only) | `live` |
| Same, without the shortcut | `tail -n 30 -f ~/sonara_deploy/live.log` |
| Totals per node | `summary` |
| Write a field note | `note "node 2 = pen C, 35 broilers, 4 weeks, caretaker: 5 sneezing"` |
| Check the time | `date` |
| Is collection running? | `systemctl status sonara-collect --no-pager` |
| Start / stop / restart collection | `sudo systemctl start sonara-collect` / `stop` / `restart` |
| Free disk space | `df -h ~` |
| Pi's IP address | `hostname -I` |
| Shut down safely (wait for the green light to stop, then unplug) | `sudo shutdown now` |

## What changed from the earlier tests

- **Nodes record back to back.** Before, a node recorded one clip every 20 to 30 s. Now each node records the next clip as soon as the last one is sent. With one node that's about 6 clips per minute (about 380 per hour).
- **Up to 5 nodes share one bridge.** Before sending, each node asks the bridge for a turn, so only one node sends at a time and the USB link never overloads. The link carries one clip about every 4.3 s in total. With 5 nodes, each node gets about 2 to 3 clips per minute.
- **More information per clip.** The bridge now reports how many packets it received and whether it had to drop any. That tells us where the packet loss seen on 30 Oct comes from.
- **Classification can't slow the link down.** It runs in a separate, low-priority process.

## Files

All files are in the GitHub repo's `deploy/` folder (download the repo, or copy them from Karl's laptop: `Downloads\SONARA_deploy`). The commands below use Karl's laptop path; change it to wherever you saved the folder.

| File | Goes on |
| --- | --- |
| `sonara_deploy_node/sonara_deploy_node.ino` | every node (set NODE_ID first) |
| `sonara_deploy_bridge/sonara_deploy_bridge.ino` | the bridge ESP32 (no settings) |
| `pi/sonara_collect.py`, `pi/sonara_classify_worker.py`, `pi/sonara_note.py`, `pi/sonara-collect.service`, `pi/install.sh` | the Pi, folder `~/sonara_deploy_app/` |

## Step 1. Flash the nodes (laptop, Arduino IDE)

Do this for **each** node:

1. Open `sonara_deploy_node.ino`.
2. Change `#define NODE_ID 1` so every node has its own number: 1, 2, 3, 4, 5.
3. Leave `BRIDGE_MAC` as it is (D4:E9:F4:B2:BF:28) unless you change the bridge board.
4. Board: **ESP32 Dev Module**. Choose the node's COM port and click Upload.
5. Write the number on the node with tape or a marker: **NODE 1**, **NODE 2**, and so on.
6. Open the Serial Monitor at 115200 baud. You should see `SONARA deployment node 1 started ... mic OK`. If it says `mic FAILED`, check the INMP441 wiring.

Two nodes with the same NODE_ID will mix their clips together. Double-check before you leave.

## Step 2. Flash the bridge

1. Open `sonara_deploy_bridge.ino`. There's nothing to change.
2. Board **ESP32 Dev Module**. Upload to the bridge ESP32 (the one with MAC D4:E9:F4:B2:BF:28).
3. Plug it into the Pi by USB.

## Step 3. Set up the Pi (once, at home, with internet)

From the laptop (PowerShell), copy the folder:

```
scp -r C:\Users\gacak\Downloads\SONARA_deploy\pi keith@192.168.1.247:~/sonara_deploy_app
```

Then SSH in (`ssh keith@192.168.1.247`) and run:

```
bash ~/sonara_deploy_app/install.sh
source ~/.bashrc
```

This copies the model files from your home folder, stops old SONARA scripts, and sets up collection to start **automatically every time the Pi powers on**. After a power cut it restarts by itself.

## Step 4. Bench test at home BEFORE 3 Nov (at least 30 min)

The firmware is new and has only been checked on a computer, not on real boards. Test it at home first.

1. Power the bridge (on the Pi) and one node (power bank).
2. On the Pi: `sudo systemctl start sonara-collect`, then `live`.
3. Every 9 to 10 s you should see a line like this:
   `node 1 clip 12 rec 14:03:21 | lvl -48.0 dBFS | RSSI -45 | p=0.06 | last20: 0/12`
4. If you have a second node, power it on too. Lines from both nodes should appear, and some will show `wait 2.1s` (the turn-taking working).
5. After 30 min run `summary`. Check that clips per hour is about 350 or more for one node, damaged is close to 0, and "packets dropped in bridge" is 0.
6. Play two or three WAV files on the laptop to confirm they sound right.

**If it doesn't work**, fall back to the tested setup: flash `sonara_test_node.ino` and `sonara_test_bridge.ino` and run `sonara_field_test.py` like on 30 Oct. That handles 1 node only, one clip every 20 s. Send the error output to Claude.

## Step 5. At the farm

**Connecting to the Pi at the farm**
- Take the router **PLDTHOMEFIBR5Bx7n** (no internet needed). Power it on, then the Pi. Connect your laptop to that Wi-Fi.
- The Pi's address on this router is **192.168.1.247**: `ssh keith@192.168.1.247`
- If PowerShell says `ssh` or `scp` "is not recognized", use the normal **Windows PowerShell** (not the x86 one), or type `C:\Windows\Sysnative\OpenSSH\ssh.exe` in place of `ssh` (and `...\scp.exe` in place of `scp`).
- The router uses Wi-Fi channel 11 and the nodes use channel 1, so they don't get in each other's way. Don't change the firmware's channel.
- Collection does not need the router. If it fails, clips keep saving; write notes on paper with the time and type them in later.

**Before you start:**
- [ ] Get permission from the farm owner or manager to record, and to publish the audio later (ask about this separately).
- [ ] **Set the Pi's clock at EACH farm** (the router has no internet, so the Pi can't set its own time). From the laptop's PowerShell:
  `ssh -t keith@192.168.1.247 "sudo date -s '$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')'"`
  Then log in and check with `date`. Every clip's timestamp depends on this.
- [ ] **New farm = new run folder.** At the second farm, powering the Pi on starts a new folder automatically. Then type `note "farm 2 start: <farm name>"`.
- [ ] Place the nodes. Keep each mic about 1 to 2 m from the birds and the bridge within about 10 m of each node, in clear view. **Don't put a node inside a wire cage** (on 24 Oct this lost most of the audio). Keep nodes off the ground and away from water, fans and feeders.
- [ ] Write one note per node (see below) saying where it is.

**Start:** collection is already running if the Pi was powered on (`live` to check). If not: `sudo systemctl start sonara-collect`.

**While it runs:**
- If `live` says "command not found", run `source ~/.bashrc` first.
- `live` shows each clip as it arrives. Ctrl+C only leaves the view; collection keeps going.
- `summary` shows clips per node, damaged clips and flags.
- Every 1 to 2 hours, check that every node still appears in `live` and replace any empty power banks. You'll see a `!! node 3: no clip for 5 min` warning when a node stops.

## Notes: the most important part

The clips are only useful for research if we know what was happening. Type a note whenever something happens:

```
note "node 1 = pen A, 40 broilers, 4 weeks, caretaker says healthy, mic 1.5 m from birds"
note "node 2 = pen C, 35 broilers, 4 weeks, caretaker says 5 birds sick (sneezing, nasal discharge) since 1 Nov"
note "feeding started, very noisy"
note "heard coughing near node 2"
note "vet checked pen C: suspected respiratory infection (vet's words)"
note "node 3 moved to pen D"
note "rain started"
```

- Write down **who** said a bird was sick (caretaker, owner, vet) and **what they saw**. Don't write a diagnosis unless a vet gave it.
- Note feeding times, cleaning, people walking in, machines, rain, and anything else loud.
- Notes are saved with the time in `~/sonara_deploy/notes.csv`.

## Step 6. Stop and copy the data

```
sudo systemctl stop sonara-collect
summary
```

Then copy everything to the laptop (PowerShell, laptop on the same network):

```
scp -r keith@192.168.1.247:~/sonara_deploy C:\Users\gacak\Downloads\farm_data_nov3
```

To stop collection starting automatically after the deployment: `sudo systemctl disable sonara-collect`.

## How much data and power to expect (estimates, not measured)

| Nodes | Clips per hour, total | Disk per day |
| --- | --- | --- |
| 1 | about 380 | about 1.5 GB |
| 2 to 5 | about 800 (link limit) | about 3 GB |

- The Pi stops saving audio when free space falls below 2 GB and warns you in `live`. Check free space with `df -h ~`. A full day with 5 nodes needs about 3 GB free.
- A node uses roughly 0.5 to 0.7 W. A 10,000 mAh power bank should last very roughly 1.5 to 2 days, but we never measured it. Note the time each node goes quiet so we get the real runtime.
- Some power banks switch off when the current is low. If a node goes quiet within minutes, try another power bank.

## Files in each run folder (`~/sonara_deploy/runs/<start time>/`)

- `clips/node<N>/` has every WAV file.
- `clips.csv` has one row per clip: recording time, packets lost, damaged (more than 33 of 667 lost), sound level, signal, node and bridge counters.
- `predictions.csv` has the probability, flag and zone alert (8 of the last 20 usable clips flagged).
- `bridge.csv` has the bridge heartbeat. `pi_health.csv` has temperature and disk use. `summary.txt` has the totals.

A flag is a model output on farm audio that nobody has labelled. It is not a diagnosis. Flagged clips get checked later by listening and against the notes.
