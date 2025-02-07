import logging
import paho.mqtt.client as mqtt
from typing import Optional, Any, Callable
import json

from random import getrandbits
from time import time
from structs import Values, CommandValues
from paho.mqtt.enums import CallbackAPIVersion

logger = logging.getLogger(__name__)


class MQTTClientWrapper:
    def __init__(self, mqtt_user: str, mqtt_password: str, mqtt_base_topic: str):
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
            callback_api_version=CallbackAPIVersion.VERSION2,
            client_id=f"mqtt-outstation-{uuid}", 
            protocol=mqtt.MQTTv5  # API version 2
        )

        self.client.username_pw_set(mqtt_user, mqtt_password)
        self.base_topic = mqtt_base_topic
        self.availability_topic = f"{self.base_topic}/availability"

        # Set callback methods
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        self._values = Values()

        # name, device_class, unit, sensor_type
        self.read_entity_info = [                                    # topics that require a state_topic only
            {"name": "plant_ac_power_generated", "device_class": "power", "unit_of_measurement": "W", "sensor_type": "sensor"},
            {"name": "grid_reactive_power", "device_class": "power", "unit_of_measurement": "Var", "sensor_type": "sensor"},
            {"name": "grid_exported_power", "device_class": "power", "unit_of_measurement": "W", "sensor_type": "sensor"},
        ]

        self.read_write_entity_info = [                              # topics that require a state_topic and command_topic
            {"name": "production_constraint_setpoint", "device_class": "battery", "unit_of_measurement": "%", "sensor_type": "number"},
            {"name": "gradient_ramp_up", "device_class": "battery", "unit_of_measurement": "%", "sensor_type": "number"},
            {"name": "gradient_ramp_down", "device_class": "battery", "unit_of_measurement": "%", "sensor_type": "number"},
            {"name": "flag_production_constraint", "device_class": "running", "unit_of_measurement": "", "sensor_type": "binary_sensor"},
            {"name": "flag_gradient_constraint", "device_class": "running", "unit_of_measurement": "", "sensor_type": "binary_sensor"},
        ]

        self.discovery_payloads = self._build_payloads()

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
            variable_name = message.topic.split("/")[-2]
            value = message.payload.decode("utf-8")
            setattr(self._values, variable_name, value)

            logger.debug(f"Message received on topic {message.topic}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    @property
    def values(self):
        """Get the mqtt internal data values (read-only)"""
        logger.info(f"read values as updated from on_message")
        return self._values

    def update_controls(self, controls: CommandValues):
        for entity in self.read_write_entity_info:
            control_name = entity['name']
            command_topic = f"{self.base_topic}/{control_name}/set"
            value = getattr(controls, control_name)

            self.client.publish(
                topic=command_topic,
                payload=value,
                retain=True,
            )
            logger.info(f"Updated control {control_name=} on {command_topic=} with {value=}")

    def _build_payloads(self) -> dict:
        device = {
            "manufacturer": "CoCT Addon",
            "model": "Virtual DNP3 Device",
            "identifiers": [f"CoCT_DNP3_virtual"],
            "name": f"CoCT_DNP3_virtual"
        }

        param_names_units_class = self.read_entity_info + self.read_write_entity_info

        payloads = {}
        for entity in param_names_units_class:
            param, device_class, unit, sensor_type = entity["name"], entity["device_class"], entity['unit_of_measurement'], entity["sensor_type"]
            state_topic = f"{self.base_topic}/{param}/state"

            discovery_payload = {
                "name": param,
                "unique_id": f"CoCT_scada_{param}",
                "state_topic": state_topic,
                "availability_topic": self.availability_topic,
                "device": device,
                "device_class": device_class,
                "unit_of_measurement": unit
            }

            if sensor_type == "number" or sensor_type == "binary_sensor":
                discovery_payload["command_topic"] = f"{self.base_topic}/{param}/set"

                if sensor_type == "number":
                    discovery_payload["min"] = "0"
                    discovery_payload["max"] = "100"
                    discovery_payload["step"] = "1"
                elif sensor_type == "binary_sensor":
                    discovery_payload.pop("unit_of_measurement")

            discovery_topic = f"homeassistant/{sensor_type}/scada/{param}/config"
            payloads[discovery_topic] = discovery_payload

        return payloads

    def publish_discovery_messages(self):
        logger.info(f"Publishing discovery topics.")

        for discovery_topic, discovery_payload in self.discovery_payloads.items():
            self.client.publish(
                discovery_topic, json.dumps(discovery_payload), retain=True
            )
            logger.info(f"Published discovery to {discovery_topic}")

        self.client.publish(self.availability_topic, "online", retain=True)
        logger.info(f"Published availability online to {self.availability_topic}")

    def subscribe(self):
        """
        Subscribe to all state topics (set by inverter/ meter addons).
        """
        for discovery_topic, discovery_payload in self.discovery_payloads.items():
            sensor_type = discovery_topic.split("/")[1]
            if sensor_type == "sensor":
                self.client.subscribe(discovery_payload["state_topic"])
                logger.info(f"Subscribed to {discovery_payload['state_topic']}")

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
    client = MQTTClientWrapper("", "", "scada")
    print(client._build_payloads())

    # test to ensure topic names and definition of structs.Values() lines up
    entity_names = [entity["name"] for entity in client.read_entity_info] + [entity["name"] for entity in client.read_write_entity_info]
    for name in entity_names:
        print(getattr(Values(), name))
