# Slack Zabbix Action Bot

A simple, interactive Slack bot integrating with the Zabbix monitoring system. List active problems and activate maintenance periods using socket mode and Zabbix jsonrpc API. For real-time notifications, use incoming webhooks.
Runs as a systemd service.

## Usage

1. Create Slack app, install to workspace using the manifest below:

```yaml
display_information:
    name: Zabbix bot
    description: Sysops Zabbix monitoring bot
    background_color: "#7a1600"
features:
    bot_user:
        display_name: Zabbix
        always_online: false
oauth_config:
    scopes:
        bot:
        - app_mentions:read
        - chat:write
        - chat:write.customize
        - commands
        - im:write
        - incoming-webhook
        - reactions:write
        - reactions:read
settings:
    event_subscriptions:
        bot_events:
        - app_mention
    interactivity:
        is_enabled: true
    org_deploy_enabled: false
    socket_mode_enabled: true
    token_rotation_enabled: false
```

3. Configure bot in `config.ini`
   1. Add "App Level Token" for the Slack app, with scope `connections:write`. Copy the token (`xapp-XXXXX`) to `config.ini`
   2. In bot's "Features / OAuth & Permissions / OAuth Tokens", click "Install to [org]". Select channel and accept. Copy the token (`xoxb-XXXXX`) to `config.ini`
   3. From Slack, copy your monitoring channel ID and add it to `ALLOWED_CHANNELS` in `config.ini`
   4. In Zabbix, add an API token to some user. Needs permissions to update maintenance periods and list active problems.

4. Install the systemd service with `install.sh`, or manually (read the script).

5. Test bot with commands (e.g. `@zabbix_bot list`). If no reply appears, look into `/var/log/slack-zabbix-action-bot.log`

## Bot Commands

- `list` or `problems`: List active problems
- `mute` or `maintenance`: Show a form to activate a maintenance period

Trigger command by mentioning the bot with a keyword: `@zabbix mute`.
Shows usage if no keyword is given.

## License

Copyright 2023-2026 by Jarno Elonen.

Licensed under the MIT License.
