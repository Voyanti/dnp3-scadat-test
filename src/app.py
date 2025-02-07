import logging
from time import sleep

from outstation import DNP3Outstation
from loader import load_config, Options
from mqtt_wrapper import MQTTClientWrapper

logger = logging.getLogger(__name__)

from structs import Values, CommandValues
class SpoofValues(Values):
    max_capacity = 100e3
    def update_controls(self, controls: CommandValues):
        """ spoof setting inverter/controller by homeassistant.

            copies controls to values."""
        self.production_constraint_setpoint = controls.production_constraint_setpoint
        self.gradient_ramp_up = controls.gradient_ramp_up
        self.gradient_ramp_down = controls.gradient_ramp_down
        self.flag_gradient_constraint = controls.flag_gradient_constraint
        self.flag_production_constraint = controls.flag_production_constraint

    @property
    def values(self):
        """ return fake changing values, with controls applied """
        # spoof changes
        self.plant_ac_power_generated = self.max_capacity * self.production_constraint_setpoint
        self.grid_reactive_power += 2
        self.grid_exported_power += 3

        return self

def main() -> None:
    OPTS: Options = load_config()               # homeassistant config.yaml -> Options
    
    # setup mqtt client for reading latest values from homeassistant
    mqtt_client = MQTTClientWrapper(OPTS.mqtt_user, 
                                    OPTS.mqtt_password, 
                                    OPTS.mqtt_base_topic)
    mqtt_client.connect(OPTS.mqtt_host, 
                        OPTS.mqtt_port)
    mqtt_client.publish_discovery_messages()
    mqtt_client.subscribe()    # VRAAG: lees MQTT sensors vir Values, skryf na set topics vir CommandValues yes. echo terug na mqtt vir 
    
    outstation = DNP3Outstation(                # Configure Outstation
        outstation_addr=OPTS.outstation_addr,   # 101 for test, change in production
        master_addr=100,                        # The SCADA Master @ CCT
        listen_ip=OPTS.listen_ip,               # Listen on all interfaces == 0.0.0.0
        listen_port=20000,
        event_buffer_size=OPTS.event_buffer_size
    )

    loop(outstation, mqtt_client)               # main loop

def loop(station: DNP3Outstation, 
         mqtt_client: MQTTClientWrapper) -> None:
    logger.info("Entering main run loop. Press Ctrl+C to exit.")
    
    try:
        station.enable()
        mqtt_client.start_loop()

        # spoof_vals = SpoofValues()

        while True:
            # retry connecting to master
            sleep(5)

            latest_commands = station.command_values            # read controls from station
            logger.info(f"{latest_commands.production_constraint_setpoint}")
            mqtt_client.update_controls(latest_commands)        # write latest controls to mqtt

            sleep(0.005)

            latest_values = mqtt_client.values                  # read homeassistant values into object
            station.update_values(latest_values)                # update station values from last read homeassistant values

            sleep(1)

    except KeyboardInterrupt as e:
        logger.info("Shutting down outstation...")
    except:
        logger.info("Shutting down outstation due to exception...")
        raise
    finally:
        station.shutdown()
        mqtt_client.stop_loop()

if __name__ == "__main__":
    main()
