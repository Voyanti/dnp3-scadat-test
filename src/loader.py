import json
import os
import logging
from dataclasses import dataclass
from cattrs import Converter

logger = logging.getLogger(__name__)


@dataclass
class Options:
    outstation_addr: int
    listen_ip: str

    mqtt_host: str
    mqtt_port: int
    mqtt_user: str
    mqtt_password: str

def load_config(config_path = '/data/options.json') -> Options:
    """
    Reads the Home Assistant add-on configuration from the options.json file.
    Returns a dictionary containing the configuration values.

    """
    logger.info("Loading config json")
    
    try:
        if not os.path.exists(config_path):
            logging.info(f"Config file not found at {config_path}. Using default options")
            default_config = Options(
                outstation_addr=101,
                listen_ip="0.0.0.0",
                mqtt_host="core-mosquitto",
                mqtt_port = 1883,
                mqtt_user="mqtt-user",
                mqtt_password="mqtt-user"
                )
            return default_config

        with open(config_path, 'r') as config_file:
            config = json.load(config_file)
            
        logger.log("Loaded config json")
        converter = Converter()
        opts = converter.structure(config, Options)
        return opts
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse config file: {str(e)}")
    except Exception as e:
        raise Exception(f"Error reading config: {str(e)}")