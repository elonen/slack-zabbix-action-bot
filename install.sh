#!/bin/bash

set -e

# Check if the user 'zabbix' exists
if ! id -u zabbix >/dev/null 2>&1; then
    echo "The user 'zabbix' does not exist. Please create it or modify the service file to use an existing user."
    exit 1
fi

echo "Ok, the user 'zabbix' exists."
echo "Installing venv and dependencies..."

# Install dependencies
python3 -m venv _venv
./_venv/bin/pip install -r requirements.txt

echo "Ok, dependencies installed."
echo "Installing systemd service..."

# Install service file
sed "s#%INSTALLDIR%#$(pwd)#g" zabbix-slack-bot.service > zabbix-slack-bot_temp.service
sudo mv zabbix-slack-bot_temp.service /etc/systemd/system/zabbix-slack-bot.service

echo "Ok, service installed."
echo "Enabling and starting the service..."

# Reload systemd, enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable zabbix-slack-bot
sudo systemctl start zabbix-slack-bot

echo "All done."
