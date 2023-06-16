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

# Make config.ini readable by zabbix user
echo "Chowning config.ini for zabbix"
chown zabbix config.ini
chmod o-rwx config.ini

echo "Installing systemd service..."

# Install service file
sed "s#%INSTALLDIR%#$(pwd)#g" slack-zabbix-action-bot.service > slack-zabbix-action-bot_TEMP.service
sudo mv slack-zabbix-action-bot_TEMP.service /etc/systemd/system/slack-zabbix-action-bot.service

echo "Ok, service installed."
echo "Enabling and starting the service..."

# Reload systemd, enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable slack-zabbix-action-bot
sudo systemctl start slack-zabbix-action-bot

echo "All done."
