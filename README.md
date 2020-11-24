# Home Assistant - Ulauncher Extension

A [Ulauncher](https://ext.ulauncher.io/) extension to view and control devices in your [HomeAssistant](https://www.home-assistant.io/) instance.

![Demo](./demo.gif)

## Requirements

You'll need the Requests lib: 

`pip install requests`

As well as the URL / API Key for your Home Assistant instance. You can generate a new long lived API Key by going to /profile (or clicking your name in the bottom left).

## To-Do

Ideally all homeassistant services would be exposed, like media players and climate controls. The rough idea would be 

`<keyword> <service> <entity search>`

I don't use a lot of these so I cannot test them, however I welcome PRs. Speaking of...

## Contributing

I welcome all issues and contributions! Please run main.py through the [Black formatter](https://github.com/psf/black) to keep things tidy :)
