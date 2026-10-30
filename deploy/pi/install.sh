#!/bin/bash
# SONARA deployment setup on the Pi. Run once:   bash ~/sonara_deploy_app/install.sh
set -e
APP=/home/keith/sonara_deploy_app
cd "$APP"
for f in sonara_system_model.pt deployment_config.json; do
  if [ ! -f "$APP/$f" ]; then
    if [ -f "$HOME/$f" ]; then cp "$HOME/$f" "$APP/"; echo "copied $f from home folder"; 
    else echo "WARNING: $f not found: the Pi will collect audio but not classify."; fi
  fi
done
~/sonara-env/bin/python -c "import serial, numpy; print('python packages OK')"
# stop anything else that might hold the bridge's USB port
pkill -f sonara_field_test.py 2>/dev/null || true
pkill -f sonara_receiver.py 2>/dev/null || true
pkill -f sonara_classify.py 2>/dev/null || true
for s in $(systemctl list-unit-files --no-legend 'sonara*' | awk '{print $1}' | grep -v sonara-collect); do
  echo "disabling old service $s"; sudo systemctl disable --now "$s" || true
done
sudo cp "$APP/sonara-collect.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sonara-collect
grep -q "alias note=" ~/.bashrc || echo "alias note='~/sonara-env/bin/python $APP/sonara_note.py'" >> ~/.bashrc
grep -q "alias live=" ~/.bashrc || echo "alias live='tail -n 30 -f ~/sonara_deploy/live.log'" >> ~/.bashrc
grep -q "alias monitor=" ~/.bashrc || echo "alias monitor='~/sonara-env/bin/python $APP/sonara_dash.py'" >> ~/.bashrc
grep -q "bashrc" ~/.profile 2>/dev/null || echo '[ -f ~/.bashrc ] && . ~/.bashrc' >> ~/.profile
grep -q "alias summary=" ~/.bashrc || echo "alias summary='cat \$(ls -d ~/sonara_deploy/runs/*/ | tail -1)summary.txt'" >> ~/.bashrc
echo
echo "Installed. Collection starts automatically whenever the Pi powers on."
echo "  start now:   sudo systemctl start sonara-collect"
echo "  stop:        sudo systemctl stop sonara-collect"
echo "  dashboard:   monitor     (Ctrl+C closes it; collection keeps running)"
echo "  live view:   live        (Ctrl+C leaves the view; collection keeps running)"
echo "  summary:     summary"
echo "  field note:  note \"what you saw\""
echo "Open a NEW terminal (or run: source ~/.bashrc) for the shortcuts to work."
