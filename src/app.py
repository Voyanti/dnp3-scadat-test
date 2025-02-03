import logging
from time import sleep
from queue import Queue

from outstation import DNP3Outstation
from loader import load_config, Options
from mqtt_wrapper import MQTTClientWrapper

logger = logging.getLogger(__name__)
RECV_Q = Queue()

def loop(station: DNP3Outstation):
    logger.info("Entering main run loop. Press Ctrl+C to exit.")
    try:
        while True:
            station.update_values()
            sleep(5)
            while not RECV_Q.empty(): # loop over queue. Note queue can still grow between evaluation and return
                # update outstation data point with value from mqtt message
                message = RECV_Q.get()
                # TODO will we use MQTT to get the event info? what if we need to use a template sensor
            # alternative: block until an update is received: RECV_Q.get()
    except KeyboardInterrupt as e:
        logger.info("Shutting down outstation...")
        station.shutdown()
    except:
        logger.info("Shutting down outstation due to exception...")
        station.shutdown()
        raise

if __name__ == "__main__":
    try:
        OPTS: Options = load_config()
        
        mqtt_client = MQTTClientWrapper(OPTS.mqtt_user, OPTS.mqtt_password)
        mqtt_client.connect(OPTS.mqtt_host, OPTS.mqtt_port)

        mqtt_client.start_loop()
        outstation = DNP3Outstation(
            outstation_addr=OPTS.outstation_addr,   # As per your test requirement
            master_addr=100,                        # The SCADA Master
            listen_ip=OPTS.listen_ip,               # Listen on all interfaces
            listen_port=20000
        )

        loop(outstation)
    finally:
        mqtt_client.stop_loop()