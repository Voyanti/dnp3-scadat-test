import logging
import queue
import paho.mqtt.client as mqtt
from typing import Optional, Any, Callable

from random import getrandbits
from time import time
from structs import Values, Controls

logger = logging.getLogger(__name__)

class MQTTClientWrapper:
    def __init__(self, 
                mqtt_user: str,
                mqtt_password: str):
        """
        Initialize the MQTT Client Wrapper
        
        :param client_id: Optional client ID. If None, Paho will generate one
        :param clean_session: Clean session flag
        :param transport: Transport protocol (tcp or websockets)
        """      
        # Create message queue
        self.message_queue = queue.Queue()

        def generate_uuid():
            random_part = getrandbits(64)
            timestamp = int(time() * 1000)  # Get current timestamp in milliseconds
            node = getrandbits(48)  # Simulating a network node (MAC address)

            uuid_str = f'{timestamp:08x}-{random_part >> 32:04x}-{random_part & 0xFFFF:04x}-{node >> 24:04x}-{node & 0xFFFFFF:06x}'
            return uuid_str
            
        uuid = generate_uuid()
        # Create MQTT client
        self.client = mqtt.Client(
            client_id=f"mqtt-outstation-{uuid}", 
            protocol=mqtt.MQTTv5  # API version 2
        )

        self.client.username_pw_set(mqtt_user, mqtt_password)
        
        # Set callback methods
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        self._values = Values()

    def _on_connect(self, 
                    client: mqtt.Client, 
                    userdata: Any, 
                    flags: dict, 
                    rc: int, 
                    properties: Optional[mqtt.Properties] = None):
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

    def _on_disconnect(self, 
                       client: mqtt.Client, 
                       userdata: Any, 
                       rc: int, 
                       properties: Optional[mqtt.Properties] = None):
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

    def _on_message(self, 
                    client: mqtt.Client, 
                    userdata: Any, 
                    message: mqtt.MQTTMessage):
        """
        Message receive callback. Puts messages in queue
        
        :param client: The client instance
        :param userdata: User-defined data
        :param message: Received message
        """
        try:
            self._update_values(message.topic, message.payload.decode('utf-8'))  # retained values on other addon restart will be used - maybe not wanted
            logger.debug(f"Message received on topic {message.topic}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def _update_values(self, topic: str, value):
        if topic == "asdf":     self._values.power_gradient_constraint_ramp_down = value
        elif topic == "fghj":   self._values.power_gradient_constraint_ramp_up = value
        elif topic == "dfgh":   self._values.power_gradient_constraint_mode = value
        elif topic == "sdfg":   self._values.exported_or_imported_power = value
        elif topic == "ghjk":   self._values.total_power_generated = value
        elif topic == "hjkl":   self._values.reactive_power = value
        # TODO complete and define better mapping method
        else: raise ValueError(f"Unconfigured topic {topic}.")

    @property
    def values(self):
        """Get the mqtt internal data values (read-only)"""
        return self._value
    
    def update_controls(self, controls: Controls):
        payload = {
            "TODO": "TODO"
        }

        self.client.publish(topic = "",
                            payload = payload,
                            retain = True)

    def subscribe(self, 
                  topic: str, 
                  qos: int = 0, 
                  options: Optional[mqtt.SubscribeOptions] = None):
        """
        Subscribe to a topic
        
        :param topic: Topic to subscribe to
        :param qos: Quality of Service level
        :param options: Optional subscribe options for MQTTv5
        """
        result, mid = self.client.subscribe(topic, qos, options)
        if result == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"Subscribed to topic: {topic}")
        else:
            logger.error(f"Failed to subscribe to topic: {topic}")
        return result, mid

    def connect(self, 
                host: str, 
                port: int = 1883, 
                keepalive: int = 60, 
                bind_address: str = "",
                bind_port: int = 0):
        """
        Connect to MQTT broker
        
        :param host: Broker hostname or IP
        :param port: Broker port
        :param keepalive: Maximum period between communications
        :param bind_address: Local network interface to bind to
        :param bind_port: Local port to bind to
        """
        try:
            self.client.connect(
                host, 
                port, 
                keepalive, 
                bind_address, 
                bind_port
            )
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
        self.client.loop_stop()
        logger.info("MQTT client loop stopped")
