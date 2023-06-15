import time
from typing import Dict, List
import requests
from datetime import datetime


def get_maintenance_periods(api_token, api_url):
    """
    Get all maintenance period entries for a given Zabbix API token and URL.

    Args:
        api_token (str): The API token for authentication.
        api_url (str): Zabbix API URL.

    Returns:
        list: A list of dictionaries containing maintenance period entries with keys:
            - 'maintenanceid': The ID of the maintenance period
            - 'name': The name of the maintenance period
    """
    headers = {
        'Content-Type': 'application/json',
    }
    data = {
        "jsonrpc": "2.0",
        "method": "maintenance.get",
        "params": {
            "output": ["maintenanceid", "name"]
        },
        "auth": api_token,
        "id": 1
    }
    print("Sending request to Zabbix API @ " + api_url)
    response = requests.post(api_url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()['result']


def update_maintenance_period(api_token, api_url, maintenance_id, duration_sec):
    """
    Update a maintenance period with a new duration.

    Args:
        api_token (str): The API token for authentication.
        api_url (str): Zabbix API URL.
        maintenance_id (str): The ID of the maintenance period to update.
        duration_sec (int): The duration of the maintenance period in seconds.
    """
    headers = {
        'Content-Type': 'application/json',
    }
    now = int(time.time())
    data = {
        "jsonrpc": "2.0",
        "method": "maintenance.update",
        "params": {
            "maintenanceid": maintenance_id,
            "active_since": now,
            "active_till": now + duration_sec,
            "timeperiods": [
                {
                    "timeperiod_type": 0,
                    "start_date": now,
                    "period": duration_sec
                }
            ]
        },
        "auth": api_token,
        "id": 1
    }
    response = requests.post(api_url, headers=headers, json=data)
    response.raise_for_status()



def list_active_problems(api_token, api_url) -> List[Dict[str, str]]:
    """
    List all active problems for a given Zabbix API token and URL.

    Args:
        api_token (str): The API token for authentication.
        api_url (str): Zabbix API URL.

    Returns:
        list: A list of dictionaries containing active problems with keys:
            - 'started': The date and time the problem started
            - 'status': The severity of the problem
            - 'host': The host on which the problem occurred
            - 'problem': The description of the problem
    """
    headers = {
        'Content-Type': 'application/json',
    }
    data = {
        "jsonrpc": "2.0",
        "method": "trigger.get",
        "params": {
            "output": ["description", "lastchange", "priority"],
            "selectHosts": ["host"],
            "filter": {
                "value": 1  # value:1 means the trigger is in a problem state
            },
            "sortfield": "lastchange",
            "sortorder": "DESC",
            "recent": "true",
            "monitored": "true",
            "skipDependent": "true"
        },
        "auth": api_token,
        "id": 1
    }
    response = requests.post(api_url, headers=headers, json=data)
    response.raise_for_status()

    severity_mapping = {
        '0': 'Not classified',
        '1': 'Information',
        '2': 'Warning',
        '3': 'Average',
        '4': 'High',
        '5': 'Disaster',
    }

    problems = []
    for problem in response.json()['result']:
        problems.append({
            'started': datetime.fromtimestamp(int(problem['lastchange'])).strftime('%Y-%m-%d %H:%M:%S'),
            'status': severity_mapping.get(problem['priority'], 'Unknown'),
            'host': problem['hosts'][0]['host'],
            'problem': problem['description']
        })

    return problems
