from dataclasses import dataclass
import logging
import paho.mqtt.client as mqtt
from typing import Literal, Optional, Any, Callable, TypedDict
import json
import asyncio

from random import getrandbits
from time import time

from .mqtt_entities import DiscoveryPayload, MQTTBinarySensor, MQTTBoolValue, MQTTFloatValue, MQTTSensor, MQTTValues

from .ha_enums import HABinarySensorDeviceClass, HASensorDeviceClass, HASensorType
from .structs import CommandValues

logger = logging.getLogger(__name__)


class MQTTClientWrapper:
    def __init__(
        self, mqtt_user: str, mqtt_password: str, mqtt_base_topic: str, values: MQTTValues
    ) -> None:
        """
        Initialize the MQTT Client Wrapper

        :param client_id: Optional client ID. If None, Paho will generate one
        :param clean_session: Clean session flag
        :param transport: Transport protocol (tcp or websockets)
        """

        def generate_uuid():
            random_part = getrandbits(64)
            timestamp = int(time() * 1000)  # Get current timestamp in milliseconds
            node = getrandbits(48)  # Simulating a network node (MAC address)

            uuid_str = f"{timestamp:08x}-{random_part >> 32:04x}-{random_part & 0xFFFF:04x}-{node >> 24:04x}-{node & 0xFFFFFF:06x}"
            return uuid_str

        uuid = generate_uuid()
        # Create MQTT client
        self.client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"mqtt-outstation-{uuid}",
            protocol=mqtt.MQTTv5,  # API version 2
        )

        self.client.username_pw_set(mqtt_user, mqtt_password)
        self.base_topic = mqtt_base_topic
        self.availability_topic = f"{self.base_topic}/availability"

        # Set callback methods
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        self._values = values
        self.on_message_callback = None
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: dict,
        rc: int,
        properties: Optional[mqtt.Properties] = None,
    ):
        """
        Connection callback with detailed logging

        :param client: The client instance
        :param userdata: User-defined data
        :param flags: Response flags
        :param rc: Return code
        :param properties: Connection properties
        """
        if rc == 0:
            logger.info(f"Connected successfully. Flags: {flags}")
        else:
            logger.error(f"Connection failed. Return code: {rc}")

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        rc: int,
        properties: Optional[mqtt.Properties] = None,
    ):
        """
        Disconnection callback with logging

        :param client: The client instance
        :param userdata: User-defined data
        :param rc: Return code
        :param properties: Disconnection properties
        """
        if rc == 0:
            logger.info("Disconnected cleanly")
        else:
            logger.warning(f"Unexpected disconnection. Return code: {rc}")

    def handle_message(self) -> None:
        """
        Called inside _on_message, after a message is received, and self.values is updated
        Async Calls self.on_message_callback after verifying its definition.
        Can be used to pass values from homeassistant to the outstation
        """

        # Use call_soon_threadsafe to schedule the callback on the main event loop
        if self.on_message_callback and self._main_loop:
            logger.info(f"Readings received from MQTT, addin callback to main loop")

            async def run_callback():
                await self.on_message_callback(self._values)

            self._main_loop.call_soon_threadsafe(
                lambda: asyncio.create_task(run_callback())
            )
        else:
            raise NotImplementedError(f"{self}.on_message_callback not defined")

    def _on_message(
        self, client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage
    ):
        """
        Message receive callback. Puts messages in queue

        :param client: The client instance
        :param userdata: User-defined data
        :param message: Received message
        """
        try:
            # TODO assume sensor topic: f"{self.mqtt_base_topic}/production_constraint_setpoint/state"
            topic = message.topic
            value = message.payload.decode("utf-8")
            
            found_match: bool = False
            for val in self._values.values():
                if topic == val.source_topic: # type: ignore
                    found_match = True
                    if isinstance(val, MQTTFloatValue):
                        val.value = float(value)
                    elif isinstance(val, MQTTBoolValue):
                        val.value = bool(value)
                    else:
                        raise TypeError(f"unsuported type {type(val)} defined in MQTTWrapper _values")
                    logger.info(f"{value=} received from {topic=}")

            if not found_match:
                logger.error(f"MQTTWrapper values has no key {topic}")
                raise ValueError(f"MQTTWrapper values has no key {topic}")
            # setattr(self._values, variable_name, value)

            self.handle_message()

            logger.debug(f"Message processed on topic {message.topic}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")


    async def publish_control(
        self, controls: CommandValues
    ) -> None:
        """
        Publishes CommandValues to their respective MQTT command topics.

        :param controls: The commanded values relayed from outstation.
        :parama to_state_topic (Optional): publish to MQTT state topics, in addition to set topics. For testing/ verification purposes.
        """

        # publish setpoints from dnp outstation directly to fake CoCT device entities for debug
        for name, value in controls.asdict().items():
            # command_topic = f"{self.base_topic}/{control_name}/set"
            state_topic = f"{self.base_topic}/{name}/state"

            self.client.publish(
                topic=state_topic,
                payload=value,
                retain=True,
            )
            logger.info(
                f"Updated control {name=} on {state_topic=} with {value=}"
            )

    def publish_discovery_messages(self):
        logger.info(f"Publishing discovery topics.")

        for value in self._values.values():
            self.client.publish(
                topic=value.discovery_topic,
                payload=json.dumps(value.discovery_payload),
                retain=True,
            )
            logger.info(f"Published discovery to {value.discovery_topic}")

        self.client.publish(self.availability_topic, "online", retain=True)
        logger.info(f"Published availability online to {self.availability_topic}")

    def subscribe(self):
        """
        Subscribe to all state topics (set by inverter/ meter addons).
        """
        logger.info(f"Subscribing to MQTT topics.")

        for value in self._values.values():
            if not value.source_topic:
                continue

            self.client.subscribe(topic=value.source_topic)
            logger.info(f"Subscribed to {value.source_topic} at discovery {value.discovery_topic}")
        # additional subscriptions:

    def connect(
        self,
        host: str,
        port: int = 1883,
        keepalive: int = 60,
        bind_address: str = "",
        bind_port: int = 0,
    ):
        """
        Connect to MQTT broker

        :param host: Broker hostname or IP
        :param port: Broker port
        :param keepalive: Maximum period between communications
        :param bind_address: Local network interface to bind to
        :param bind_port: Local port to bind to
        """
        try:
            self.client.connect(host, port, keepalive, bind_address, bind_port)
            logger.info(f"Attempting to connect to {host}:{port}")
        except Exception as e:
            logger.error(f"MQTT Connection error: {e}")
            raise

    def start_loop(self):
        """
        Start the MQTT client loop
        """
        self.client.loop_start()
        logger.info("MQTT client loop started")

    def stop_loop(self):
        """
        Stop the MQTT client loop
        """
        self.client.publish(self.availability_topic, "offline", retain=True)
        logger.info("Published Offline availability status")
        self.client.loop_stop()
        logger.info("MQTT client loop stopped")


if __name__ == "__main__":
    pass
    # client = MQTTClientWrapper("", "", "scada")
    # print(client._build_payloads())

    # # test to ensure topic names and definition of structs.Values() lines up
    # entity_names = [entity["name"] for entity in client.read_entity_info] + [
    #     entity["name"] for entity in client.read_write_entity_info
    # ]
    # for name in entity_names:
    #     print(getattr(Values(), name))
