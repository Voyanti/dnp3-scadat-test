from dataclasses import dataclass
import logging
import paho.mqtt.client as mqtt
from typing import Literal, Optional, Any, Callable, TypedDict
import json
import asyncio

from random import getrandbits
from time import time

from .mqtt_entities import DiscoveryPayload, MQTTBaseValue, MQTTBinarySensor, MQTTBoolValue, MQTTEntityBase, MQTTFloatValue, MQTTIntValue, MQTTSensor, MQTTValues

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
        self.on_message_callback: Optional[Callable] = None
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
            logger.debug(f"Message callback")

            async def run_callback():
                await self.on_message_callback(self._values)

            self._main_loop.call_soon_threadsafe(
                lambda: asyncio.create_task(run_callback())
            )
        else:
            raise NotImplementedError(f"{self}.on_message_callback not defined")
        
    def _update_values(self, topic: str, new_value: str) -> str:
        """
        Update _values attribute by indexing with MQTT source topic


        Args:
            topic (str): MQTT topic on which the new value was received
            new_value (str): value to update the entity to 

        Raises:
            TypeError: if _values doesn't contain fields with values of type MQTTFloatValue/ MQTTBoolValue
            ValueError: if an entity with the mathcing source_topic could not be found

        Returns:
            str: name of the updated entity
        """        
        new_vals = self._values

        entity_name: str = ""
        for val in new_vals.values():
            if topic == val.source_topic: # type: ignore
                mqttval: MQTTBoolValue | MQTTFloatValue | MQTTIntValue = val # type: ignore
                entity_name = mqttval.entity.name
                if isinstance(val, MQTTFloatValue):
                    val.value = float(new_value)
                elif isinstance(val, MQTTBoolValue):
                    assert(new_value=="ON" or new_value=="OFF")
                    val.value = new_value
                else:
                    raise TypeError(f"unsuported type {type(val)} defined in MQTTWrapper _values")
                logger.info(f"Incoming msg: {val.entity.name} {new_value=} received from {topic=}")

        if not entity_name:
            logger.error(f"MQTTWrapper values has no key {topic}")
            raise ValueError(f"MQTTWrapper values has no key {topic}")
        
        return entity_name

    def _on_message(
        self, client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage
    ):
        """
        Message receive callback.

        :param client: The client instance
        :param userdata: User-defined data
        :param message: Received message
        """
        try:
            # TODO assume sensor topic: f"{self.mqtt_base_topic}/production_constraint_setpoint/state"
            topic = message.topic
            value = message.payload.decode("utf-8")

            entity_updated_name = self._update_values(topic, value)

            self.handle_message()   # add outstation callback to main loop
            self.publish_value(entity_updated_name)   # publish newly received values to debug MQTT entities

            logger.debug(f"Message processed on topic {message.topic}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise e


    async def publish_control(
        self, controls: CommandValues
    ) -> None:
        """
        Publishes CommandValues to their respective MQTT state topics.

        :param controls: The commanded values relayed from outstation.
        """

        # publish setpoints from dnp outstation directly to fake CoCT device entities for debug
        for name, control in controls.asdict().items():
            # command_topic = f"{self.base_topic}/{control_name}/set"
            state_topic = f"{self.base_topic}/{name}/state"

            value: MQTTBaseValue = self._values[name]
            real_set_topics: list[str] = value.additional_topics

            for topic in real_set_topics:
                # publish to set topic of actual device
                self.client.publish(
                    topic=topic,
                    payload=control,
                    retain=True,
                )
                logger.info(
                    f"Updated control {name=} on {topic=} with {control=}"
                )

            # publish to virtual device for debug
            self.client.publish(
                topic=state_topic,
                payload=control,
                retain=True,
            )
            logger.info(
                f"Updated debug control {name=} on {state_topic=} with {control=}"
            )

    def publish_value(
        self,
        entity_name: str
    ) -> None:
        """
        Publishes a single entity value from self._values to its _values.destination_topic.
        """
        for name, mqttvalue in self._values.items():
            if name != entity_name: 
                continue

            mqttval: MQTTBoolValue | MQTTFloatValue | MQTTIntValue = mqttvalue # type: ignore

            self.client.publish(
                topic=mqttval.destination_topic,
                payload=mqttval.value,
                retain=True,
            )

            display_val = mqttval.value
            if isinstance(mqttval, (MQTTFloatValue, MQTTIntValue)):
                display_val = float(display_val)*mqttval.multiplier
            logger.debug(
                f"Updated value {name=} on {mqttval.destination_topic} with value={display_val}"
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
