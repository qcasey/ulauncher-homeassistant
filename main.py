import requests
import json
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction

ON_OFF_TYPES = ["light", "switch", "automation", "scene", "group", "input_boolean", "media_player", "climate", "camera"]
ACTION_WORDS = ["on", "off", "open", "close"]

icon_files = {
    "logo": "images/icon.png",
    "automation": "images/automation.png",
    "cover": "images/cover.png",
    "group": "images/group.png",
    "light": "images/light.png",
    "scene": "images/scene.png",
    "switch": "images/switch.png",
}


class HomeAssistantExtension(Extension):
    def __init__(self):
        super(HomeAssistantExtension, self).__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())


class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        items = []
        query = (event.get_argument() or str()).lower()

        hass_url = extension.preferences["hass_url"]
        if not hass_url:
            return RenderResultListAction(
                [
                    ExtensionResultItem(
                        icon=icon_files["logo"],
                        name="Invalid Home Assistant URL",
                        on_enter=HideWindowAction(),
                    )
                ]
            )
        # Trim hass URL
        hass_url = hass_url.strip("/")

        hass_key = extension.preferences["hass_key"]
        if not hass_key:
            return RenderResultListAction(
                [
                    ExtensionResultItem(
                        icon=icon_files["logo"],
                        name="Empty Home Assistant API Key",
                        on_enter=HideWindowAction(),
                    )
                ]
            )

        if len(query.strip()) == 0:
            return RenderResultListAction(
                [
                    ExtensionResultItem(
                        icon=icon_files["logo"],
                        name="No input",
                        on_enter=HideWindowAction(),
                    )
                ]
            )

        action_word = query.split()[0].lower().strip()
        is_action_word = action_word in ACTION_WORDS
        entity_query_list = query.split()[1:] if is_action_word else query.split()

        if not entity_query_list:
            return RenderResultListAction(
                [
                    ExtensionResultItem(
                        icon=icon_files["logo"], name="", on_enter=HideWindowAction()
                    )
                ]
            )

        # Set up HASS state query
        state_query = hass_url + "/api/states"
        headers = {
            "Authorization": "Bearer " + hass_key,
            "content-type": "application/json",
        }

        response = requests.get(state_query, headers=headers)
        if not response:
            return RenderResultListAction(
                [
                    ExtensionResultItem(
                        icon=icon_files["logo"],
                        name=response.text,
                        on_enter=HideWindowAction(),
                    )
                ]
            )

        # Parse all entities and states
        for entity in json.loads(response.text):
            # May want to make this configurable later
            if len(items) > 6:
                break

            # Not likely, but worth checking
            if "entity_id" not in entity or "attributes" not in entity:
                continue

            if "friendly_name" not in entity["attributes"]:
                entity["friendly_name"] = entity["entity_id"]

            # Don't add this item if the query doesn't appear in either friendly_name or id
            entity_appears_in_search = True
            for entity_query_item in entity_query_list:
                if (
                    entity_query_item
                    not in entity["attributes"]["friendly_name"].lower()
                    and entity_query_item not in entity["entity_id"]
                ):
                    entity_appears_in_search = False

            if not entity_appears_in_search:
                continue

            entity_class = entity["entity_id"].split(".")[0]
            entity_icon = (
                icon_files[entity_class]
                if entity_class in icon_files
                else icon_files["logo"]
            )

            # If we require an action beyond just displaying state
            if is_action_word:

                # ON / OFF action
                if action_word == "on" or action_word == "off":
                    if entity_class in ON_OFF_TYPES:
                        data = {
                            "endpoint": "{}/api/services/homeassistant/turn_{}".format(
                                hass_url, action_word
                            ),
                            "service_data": {"entity_id": entity["entity_id"]},
                            "hass_key": hass_key,
                            "headers": headers,
                        }

                        items.append(
                            ExtensionResultItem(
                                icon=entity_icon,
                                name="Turn {} {}".format(
                                    action_word,
                                    entity["entity_id"],
                                ),
                                description="{} is currently {}".format(
                                    entity["entity_id"],
                                    entity["state"],
                                ),
                                on_enter=ExtensionCustomAction(
                                    data, keep_app_open=False
                                ),
                            )
                        )

                # OPEN / CLOSE action (for covers)
                elif action_word == "open" or action_word == "close":
                    if entity_class == "cover":
                        data = {
                            "endpoint": "{}/api/services/cover/{}_cover".format(
                                hass_url, action_word
                            ),
                            "service_data": {"entity_id": entity["entity_id"]},
                            "hass_key": hass_key,
                            "headers": headers,
                        }

                        items.append(
                            ExtensionResultItem(
                                icon=entity_icon,
                                name="{} {}".format(
                                    action_word,
                                    entity["entity_id"],
                                ),
                                description="{} is currently {}".format(
                                    entity["entity_id"],
                                    entity["state"],
                                ),
                                on_enter=ExtensionCustomAction(
                                    data, keep_app_open=False
                                ),
                            )
                        )

            # Otherwise, assume it's a state query
            else:
                items.append(
                    ExtensionResultItem(
                        icon=entity_icon,
                        name=entity["entity_id"],
                        description=entity["state"],
                        on_enter=HideWindowAction()
                        if entity["state"] == "on" or entity["state"] == "off"
                        else CopyToClipboardAction(entity["state"]),
                    )
                )

        if len(items) == 0:
            items.append(
                ExtensionResultItem(
                    icon=icon_files["logo"],
                    name="Entity not found",
                    on_enter=HideWindowAction(),
                )
            )

        return RenderResultListAction(items)


class ItemEnterEventListener(EventListener):
    def on_event(self, event, extension):
        data = event.get_data()

        # Make POST request to HA service
        requests.post(
            data["endpoint"],
            data=json.dumps(data["service_data"]),
            headers=data["headers"],
        )


if __name__ == "__main__":
    HomeAssistantExtension().run()
