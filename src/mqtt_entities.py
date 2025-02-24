from dataclasses import dataclass
from typing import Optional, TypedDict

from .ha_enums import HABinarySensorDeviceClass, HASensorDeviceClass, HASensorType
import logging

logger = logging.getLogger(__name__)


class DiscoveryPayload(TypedDict, total=False):
    # not all are required attributes e.g. unit
    name: str
    unique_id: str
    state_topic: str
    availability_topic: str
    device: dict
    device_class: str
    unit_of_measurement: str
    command_topic: str


class MQTTEntityBase:
    def __init__(self, name: str):
        self.name = name

    def to_discovery_payload(
        self, device_payload: dict, base_topic: str
    ) -> DiscoveryPayload:
        state_topic = f"{base_topic}/{self.name}/state"
        availability_topic = f"{base_topic}/availability"
        discovery_payload: DiscoveryPayload = {
            "name": self.name,
            "unique_id": f"CoCT_scada_{self.name}",
            "state_topic": state_topic,
            "availability_topic": availability_topic,
            "device": device_payload,
        }
        return discovery_payload


class MQTTSensor(MQTTEntityBase):
    def __init__(self, name: str, device_class: HASensorDeviceClass, unit: str):
        super().__init__(name)
        self.sensor_type = HASensorType.SENSOR
        self.device_class = device_class
        self.unit = unit

    def to_discovery_payload(
        self, device_payload: dict, base_topic: str
    ) -> DiscoveryPayload:
        base_payload = super().to_discovery_payload(device_payload, base_topic)
        add_dict: DiscoveryPayload = {
            "device_class": self.device_class.value,
            "unit_of_measurement": self.unit,
        }
        payload = base_payload.copy()
        payload.update(add_dict)

        return payload


class MQTTBinarySensor(MQTTEntityBase):
    def __init__(self, name: str, device_class: HABinarySensorDeviceClass):
        super().__init__(name)
        self.sensor_type = HASensorType.BINARY_SENSOR
        self.device_class = device_class

    def to_discovery_payload(
        self, device_payload: dict, base_topic: str
    ) -> DiscoveryPayload:
        command_topic = f"{base_topic}/{self.name}/set"

        base_payload = super().to_discovery_payload(device_payload, base_topic)
        add_dict: DiscoveryPayload = {
            "device_class": self.device_class.value,
            "command_topic": command_topic,
        }
        payload = base_payload.copy()
        payload.update(add_dict)

        return payload


class MQTTBaseValue:
    """
    Contains value mapping for which topic to subscribe to,
    which topic to publish to, as well as discovery information
    """

    def __init__(self, entity: MQTTBinarySensor | MQTTSensor) -> None:
        self.entity = entity

    def build_payload(self, base_topic) -> None:
        self.discovery_topic = (
            f"homeassistant/{self.entity.sensor_type.value}/scada/{self.entity.name}/config"
        )
        self.discovery_payload: DiscoveryPayload = self._build_payload(base_topic)
        self.source_topic: str = ""
        self.destination_topic: str = self.discovery_payload["state_topic"]

    def _build_payload(self, base_topic: str) -> DiscoveryPayload:
        """
        :returns: dict of (discovery_topic: str, discovery_payload:DiscoveryPayload)
        """
        logger.info("Building discovery payload")

        entity = self.entity
        device_payload = {
            "manufacturer": "CoCT Addon",
            "model": "Virtual DNP3 Device",
            "identifiers": [f"CoCT_DNP3_virtual"],
            "name": f"CoCT_DNP3_virtual",
        }

        if not isinstance(
            entity.device_class, (HASensorDeviceClass, HABinarySensorDeviceClass)
        ):
            logger.error(
                f"{entity.name} device class is of type {type(entity.device_class)}.\
                    Expected HASensorDeviceClass | HABinarySensorDeviceClass"
            )

        discovery_payload: DiscoveryPayload = entity.to_discovery_payload(
            device_payload=device_payload, base_topic=base_topic
        )

        logger.info(f"Built discovery payload {discovery_payload}")
        return discovery_payload


class MQTTFloatValue(MQTTBaseValue):
    def __init__(self, entity: MQTTSensor, value: float = 0.0) -> None:
        super().__init__(entity)
        self.value = value


class MQTTBoolValue(MQTTBaseValue):
    def __init__(self, entity: MQTTBinarySensor, value: bool = False) -> None:
        super().__init__(entity)
        self.value = value


class MQTTIntValue(MQTTBaseValue):
    def __init__(self, entity: MQTTSensor, value: int = 0) -> None:
        super().__init__(entity)
        self.value = value


class MQTTValues(TypedDict):
    """
    Collection of MQTTValues, each with their associated MQTTEntity & value.

    Also has discovery_topic, discovery_payload and source and destination topic attributes 
    after member.build(topics(base_topic)) has been called on all the members
    """

    # W/Var
    # by Embedded Generation (EG) Plant Watts
    plant_ac_power_generated: MQTTFloatValue
    # at point of connection (POC) to CCT Vars
    grid_reactive_power: MQTTFloatValue
    # at POC Watts
    grid_exported_power: MQTTFloatValue

    # %
    production_constraint_setpoint: MQTTIntValue  # 0 - master output index
    gradient_ramp_up: MQTTIntValue  # 1
    gradient_ramp_down: MQTTIntValue  # 2

    # enable/disable
    flag_dont_production_constraint: MQTTBoolValue
    flag_dont_gradient_constraint: MQTTBoolValue
