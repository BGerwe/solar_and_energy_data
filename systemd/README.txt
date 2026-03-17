# Deployment on Raspberry Pi

## 1. Install the systemd service (API server)

    sudo cp solar-api.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable solar-api
    sudo systemctl start solar-api

Check status:
    sudo systemctl status solar-api

View logs:
    journalctl -u solar-api -f

## 2. Schedule the data collector (cron)

    crontab -e

Add this line:
    */30 * * * * cd /home/pi/solar_and_energy_data && /home/pi/miniconda3/envs/solar_api_data/bin/python collect_enphase.py >> logs/collect.log 2>&1

## Notes

- Edit solar-api.service to match your actual user, paths, and conda env location.
- Create the logs directory: mkdir -p /home/pi/solar_and_energy_data/logs
- If deploying on Windows instead, use Task Scheduler:
  - Action: Start a program
  - Program: C:\Users\Brian\miniconda3\envs\solar_api_data\python.exe
  - Arguments: collect_enphase.py
  - Start in: C:\Users\Brian\OneDrive\Documents\Python\solar_and_energy_data
  - Trigger: Every 30 minutes
