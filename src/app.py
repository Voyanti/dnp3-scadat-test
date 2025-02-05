import logging
from time import sleep

from outstation import DNP3Outstation
from loader import load_config, Options
from mqtt_wrapper import MQTTClientWrapper

logger = logging.getLogger(__name__)

from structs import Values, CommandValues
class SpoofValues(Values):
    def update_controls(self, controls: CommandValues):
        """ spoof setting inverter/controller by homeassistant.

            copies controls to values."""
        self.production_constraint_setpoint = controls.production_constraint_setpoint
        self.power_gradient_constraint_ramp_up = controls.power_gradient_constraint_ramp_up
        self.power_gradient_constraint_ramp_down = controls.power_gradient_constraint_ramp_down

    @property
    def values(self):
        """ return fake changing values, with controls applied """
        # spoof changes
        self.total_power_generated += 1
        self.reactive_power += 2
        self.exported_or_imported_power += 3

        return self

def main():
    OPTS: Options = load_config()               # homeassistant config.yaml -> Options
    
    # setup mqtt client for reading latest values from homeassistant
    mqtt_client = MQTTClientWrapper(OPTS.mqtt_user, OPTS.mqtt_password)
    mqtt_client.connect(OPTS.mqtt_host, OPTS.mqtt_port)
    mqtt_client.subscribe(topic = "scada/*")    # VRAAG: lees MQTT sensors vir Values, skryf na set topics vir CommandValues yes. echo terug na mqtt vir 
    
    outstation = DNP3Outstation(                # Configure Outstation
        outstation_addr=OPTS.outstation_addr,   # 101 for test, change in production
        master_addr=100,                        # The SCADA Master @ CCT
        listen_ip=OPTS.listen_ip,               # Listen on all interfaces == 0.0.0.0
        listen_port=20000,
        event_buffer_size=OPTS.event_buffer_size
    )

    loop(outstation, mqtt_client)               # main loop

def loop(station: DNP3Outstation, 
         mqtt_client: MQTTClientWrapper):
    logger.info("Entering main run loop. Press Ctrl+C to exit.")
    
    try:
        mqtt_client.start_loop()
        station.enable()

        spoof_vals = SpoofValues()

        while True:
            latest_commands = station.command_values
            spoof_vals.update_controls(latest_commands)        

            latest_values = spoof_vals.values
            station.update_values(latest_values)

            sleep(1)

            """
            # latest_controls = station.controls  # read controls from station
            # mqtt_client.update_controls(latest_controls)        # write latest controls to mqtt

            # sleep(0.005)

            # latest_values = mqtt_client.values                  # read homeassistant values into object
            # station.update_values(latest_values)                # update station values from last read homeassistant values

            # sleep(1)
            """

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
