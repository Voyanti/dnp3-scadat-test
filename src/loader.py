import json
import os
import logging
from dataclasses import dataclass
from cattrs import Converter

logger = logging.getLogger(__name__)


@dataclass
class Options:
    server: str
    outstation_addr: int        # DNP3 address e.g. 101
    listen_ip: str              # binding ip on device for DNP3 connections e. g. 0.0.0.0/localhost
    event_buffer_size: int

    mqtt_host: str
    mqtt_port: int
    mqtt_user: str
    mqtt_password: str
    mqtt_base_topic: str

    plant_ac_generated_topic: str
    grid_reactive_topic: str
    grid_export_topic: str


DEFAULT_OPTIONS = \
    Options(server="vpn.example.com",
            outstation_addr=101,
            listen_ip="0.0.0.0",
            event_buffer_size=20,
            mqtt_host="localhost",
            mqtt_port = 1884,
            mqtt_user="mqtt-user",
            mqtt_password="mqtt-user",
            mqtt_base_topic="scada",
            plant_ac_generated_topic = "test/plant/state",
            grid_reactive_topic = "test/reactive/state",
            grid_export_topic = "test/export/state")

def load_config(config_path = '/data/options.json') -> Options:
    """
    Reads the Home Assistant add-on configuration from the options.json file.
    Returns a dictionary containing the configuration values.

    """
    logger.info("Loading config json")
    
    try:
        if not os.path.exists(config_path):
            logging.info(f"Config file not found at {config_path}. Using default options")
            return DEFAULT_OPTIONS

        with open(config_path, 'r') as config_file:
            config = json.load(config_file)
            
        logger.info("Loaded config json")
        converter = Converter()
        opts = converter.structure(config, Options)
        return opts
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse config file: {str(e)}")
    except Exception as e:
        raise Exception(f"Error reading config: {str(e)}")