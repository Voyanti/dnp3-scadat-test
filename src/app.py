import logging
from time import sleep
import asyncio

from .outstation import DNP3Outstation
from .loader import load_config, Options
from .mqtt_wrapper import MQTTClientWrapper
from .structs import Values, CommandValues

logger = logging.getLogger(__name__)


class SpoofValues(Values):
    max_capacity = 100e3

    def update_controls(self, controls: CommandValues):
        """spoof setting inverter/controller by homeassistant.

        copies controls to values."""
        self.production_constraint_setpoint = controls.production_constraint_setpoint
        self.gradient_ramp_up = controls.gradient_ramp_up
        self.gradient_ramp_down = controls.gradient_ramp_down
        self.flag_gradient_constraint = controls.flag_gradient_constraint
        self.flag_production_constraint = controls.flag_production_constraint

    @property
    def values(self):
        """return fake changing values, with controls applied"""
        # spoof changes
        self.plant_ac_power_generated = (
            self.max_capacity * self.production_constraint_setpoint
        )
        self.grid_reactive_power += 2
        self.grid_exported_power += 3

        return self


def setup_mqtt(OPTS: Options) -> MQTTClientWrapper:
    # setup mqtt client for reading latest values from homeassistant
    mqtt_client = MQTTClientWrapper(
        OPTS.mqtt_user, OPTS.mqtt_password, OPTS.mqtt_base_topic
    )
    mqtt_client.connect(OPTS.mqtt_host, OPTS.mqtt_port)
    mqtt_client.publish_discovery_messages()
    mqtt_client.subscribe()  # VRAAG: lees MQTT sensors vir Values, skryf na set topics vir CommandValues yes. echo terug na mqtt vir

    return mqtt_client


async def main() -> None:
    OPTS: Options = load_config()  # homeassistant config.yaml -> Options

    outstation = DNP3Outstation(  # Configure Outstation
        outstation_addr=OPTS.outstation_addr,  # 101 for test, change in production
        master_addr=100,  # The SCADA Master @ CCT
        listen_ip=OPTS.listen_ip,  # Listen on all interfaces == 0.0.0.0
        listen_port=20000,
        event_buffer_size=OPTS.event_buffer_size,
    )

    mqtt_client = setup_mqtt(OPTS)

    loop = asyncio.get_running_loop()
    outstation.command_handler._main_loop = loop
    mqtt_client._main_loop = loop
    # outstation.command_handler.on_command_callback = mqtt_client.publish_control
    outstation.command_handler.on_command_callback = lambda cmd, to_state_topic_and_set_topic=True: mqtt_client.publish_control(cmd, to_state_topic_and_set_topic)  # TODO
    mqtt_client.on_message_callback = outstation.update_values

    logger.info("Entering main run loop. Press Ctrl+C to exit.")

    try:
        outstation.enable()
        mqtt_client.start_loop()
        logger.info(f"sleep")
        sleep(3)
        logger.info(f"initialise values")
        await outstation.update_values(mqtt_client._values)
        outstation.update_commands()
        
        logger.info(f"running")

        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt as e:
        logger.info("Shutting down outstation...")
    except asyncio.CancelledError as ce:
        logger.info(f"Async Cancelled")
        raise ce
    except:
        logger.info("Shutting down outstation due to exception...")
        raise
    finally:
        outstation.shutdown()
        mqtt_client.stop_loop()


if __name__ == "__main__":
    asyncio.run(main())
