import argparse
import signal
import sys
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import configparser
import os
import logging
from zabbix_api import get_maintenance_periods, list_active_problems, update_maintenance_period


def send_maintenance_form(zapi_token, zapi_url, say, thread_ts=None):
    """
    Send a form to Slack to activate a maintenance period.
    Gets a list of maintenance periods from Zabbix.
    """
    maints = [{"text": {"type": "plain_text", "text": m['name']}, "value": m['maintenanceid']}
              for m in get_maintenance_periods(zapi_token, zapi_url)]
    say(
        text="Maintenance period activation",
        thread_ts=thread_ts,
        blocks=[
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "Select maintenance period:"},
                "accessory": {
                    "type": "static_select",
                    "placeholder": {"type": "plain_text", "text": "Maintenance"},
                    "options": maints,
                    "action_id": "maint_select"
                }
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "Select duration:"},
                "accessory": {
                    "type": "static_select",
                    "placeholder": {"type": "plain_text", "text": "Duration"},
                    "options": [
                        {"text": {"type": "plain_text", "text": "5 minutes"}, "value": f"{5*60}"},
                        {"text": {"type": "plain_text", "text": "15 minutes"}, "value": f"{15*60}"},
                        {"text": {"type": "plain_text", "text": "30 minutes"}, "value": f"{30*60}"},
                        {"text": {"type": "plain_text", "text": "1 hour"}, "value": f"{60*60}"},
                        {"text": {"type": "plain_text", "text": "2 hours"}, "value": f"{2*60*60}"},
                        {"text": {"type": "plain_text", "text": "4 hours"}, "value": f"{4*60*60}"},
                    ],
                    "action_id": "duration_select"
                }
            },
            { "type": "divider" },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": " "},
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Start maintenance"},
                    "action_id": "activate_clicked"
                }
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": " "},
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Cancel"},
                    "action_id": "cancel_clicked"
                }
            }
        ]
    )

def send_problems_list(zapi_token, zapi_url, say, thread_ts=None):
    """
    Get a list of active problems from Zabbix and send them to Slack.
    """
    problems = list_active_problems(zapi_token, zapi_url)
    if len(problems) == 0:
        say(text="No active problems found.", thread_ts=thread_ts)
        return

    icon_for_severity = {
        'Not classified': ':grey_question:',
        'Information': ':information_source:',
        'Warning': ':warning:',
        'Average': ':small_orange_diamond:',
        'High': ':small_red_triangle:',
        'Disaster': ':bangbang:',
    }
    def format_problem(p):
        return f"{icon_for_severity[p['status']]} *{p['host']}*: {p['problem']}"
    say(
        text="Active problems",
        thread_ts=thread_ts,
        blocks=[
            { "type": "section", "text": {"type": "mrkdwn", "text": "*Active problems*"} },
            { "type": "divider" },
            { "type": "section", "text": {"type": "mrkdwn", "text": "\n".join([format_problem(p) for p in problems])} }
        ]
    )


class ZabbixSlackBot:
    app = None
    allowed_channels = []
    bot_username: str = ""
    zabbix_token: str = ""
    zabbix_url: str = ""


    def check_allowed_channels(self, body, say):
        """
        Check if the bot is allowed to operate on the channel.
        """
        channel_id = None
        thread_ts = None
        try :
            channel_id = body["event"]["channel"]
            thread_ts = body["event"]['thread_ts']
        except KeyError:
            try:
                channel_id = body["container"]["channel_id"]
                thread_ts = body["container"]['thread_ts']
            except KeyError:
                logging.error("No channel_id found in body")
                return False
        if channel_id not in self.allowed_channels:
            say(text="Sorry, bot is not allowed to operate on this channel.", thread_ts=thread_ts)
            return False
        return True


    def __init__(self, app):
        self.app = app

        # (dummy - called when maintenance period selection is changed)
        @app.action("maint_select")
        def action_maint_select(ack, body, client):
            logging.debug("maint_select - action")
            ack()


        # (dummy - called when duration selection is changed)
        @app.action("duration_select")
        def action_duration_select(ack, body, client):
            logging.debug("duration_select - action")
            ack()


        @app.event("app_mention")
        def handle_app_mentions(ack, body, say, client):
            """
            Handle mentions of the app in the Slack channel
            and respond with different keywords.

            Show usage if no known keywords are found.

            Args:
                body (dict): A dictionary containing the request body.
                say (callable): A function to send a message in the Slack channel.
                client (slack_sdk.WebClient): A Slack client instance.
            """
            logging.info("app_mention - event")
            ack()
            if not self.check_allowed_channels(body, say):
                return

            event = body["event"]
            channel_id = event["channel"]
            show_usage = True

            actions = [
                {
                    'desc': 'Show active problems',
                    'keywords': ['list', 'show', 'problems'],
                    'call': lambda: send_problems_list(self.zabbix_token, self.zabbix_url, say, thread_ts=event['ts'])
                },
                {
                    'desc': 'Maintenance activation form',
                    'keywords': ['mute', 'maintenance'],
                    'call': lambda: send_maintenance_form(self.zabbix_token, self.zabbix_url, say, thread_ts=event['ts'])
                },
            ]

            # Handle commands, if any
            evt_keywords = event.get("text", "").split()
            for act in actions:
                if any([kw in evt_keywords for kw in act['keywords']]):
                    show_usage = False
                    act['call']()

            # Show usage if no valid command was found
            if show_usage:
                def fmt_action_usage(a):
                    return f"`{'|'.join(a['keywords'])}` - {a['desc']}"
                usage_txt = "*USAGE:* `@{bot_usename} [command] ...`\nCommands are:\n" + "\n".join([fmt_action_usage(a) for a in actions])
                say(
                    text=usage_txt,
                    channel=channel_id,
                    thread_ts=event['ts']
                )


        @app.action("activate_clicked")
        def action_activate_clicked(ack, body, say, client):
            """
            Perform action when the "activate_clicked" button is clicked in the message.
            Update the maintenance period in Zabbix,
            delete the form message and
            send a notification to the channel.

            Args:
                ack (callable): Function to acknowledge the action.
                body (dict): Payload received from the app action.
                say (callable): Function to send a message.
                client (slack_sdk.WebClient): A Slack client instance.
            """
            logging.info("activate_clicked - action")
            ack()
            if not self.check_allowed_channels(body, say):
                return

            # Process the form
            thread_ts = None
            try:
                thread_ts = body["container"]["thread_ts"]
                selections = body['state']['values']
                selected_dict = {
                    action: {
                        'value': selections[k][action]['selected_option']['value'],
                        'text': selections[k][action]['selected_option']['text']['text']
                    }
                    for k in selections
                    for action in selections[k]
                }
                selected_maint = selected_dict['maint_select']
                selected_duration = selected_dict['duration_select']
                update_maintenance_period(self.zabbix_token, self.zabbix_url, selected_maint['value'], int(selected_duration['value']))

            except (KeyError, TypeError) as e:
                logging.error("Form submission error: " + str(e))
                say(text="Form submission error. Missing selection?", thread_ts=thread_ts)
                return

            except Exception as e:
                logging.error("Processing error: " + str(e))
                say(text="Processing error. Please try again.", thread_ts=thread_ts)
                return

            # Post a confirmation message to the channel (not thread)
            user = body["user"]["name"]
            say(text=f"User *{user}* activated maintenance period `{selected_maint['text']}` for {selected_duration['text']}")

            # Delete the form message now that we're done with it
            channel_id = body['channel']['id']
            message_ts = body['message']['ts']
            client.chat_delete(
                channel=channel_id,
                ts=message_ts
            )


        @app.action("cancel_clicked")
        def action_cancel_clicked(ack, body, say, client):
            """
            Perform action when the "cancel_clicked" button is clicked in the message.
            Delete the form message.
            """
            logging.info("cancel_clicked - action")
            ack()
            if not self.check_allowed_channels(body, say):
                return

            channel_id = body['channel']['id']
            message_ts = body['message']['ts']
            client.chat_delete(
                channel=channel_id,
                ts=message_ts
            )


def main():
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d,%H:%M:%S', level=logging.INFO)

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Zabbix bot')
    parser.add_argument('--config', dest='config_file', default='config.ini', help='path to the config file')
    args = parser.parse_args()

    # Read config file
    config = configparser.ConfigParser()
    config.read(args.config_file)
    app_token = config['SLACK']['APP_TOKEN']
    bot_token = config['SLACK']['BOT_TOKEN']
    if 'XXXXXX' in bot_token or 'XXXXXX' in app_token:
        logging.error("Please set proper tokens in the config file")
        sys.exit(1)

    # Initialize the bot
    app = App(token=bot_token)
    bot = ZabbixSlackBot(app)
    bot.allowed_channels = [id.strip() for id in config['SLACK']['ALLOWED_CHANNELS'].split(',')]
    bot.bot_username = config['SLACK']['BOT_USERNAME']
    bot.zabbix_url = config['ZABBIX']['URL']
    bot.zabbix_token = config['ZABBIX']['API_TOKEN']

    # Handle SIGTERM and CTRL-C without exception
    def signal_handler(sig, frame):
        logging.info("Exiting...")
        sys.exit(0)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Run forever
    logging.info("Starting zabbix bot...")
    SocketModeHandler(app, app_token).start()


if __name__ == "__main__":
    main()
