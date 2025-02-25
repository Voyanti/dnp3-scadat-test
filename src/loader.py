import json
import os
import logging
from dataclasses import dataclass
from cattrs import Converter

logger = logging.getLogger(__name__)


@dataclass
class Options:
    server: str = "vpn.example.com"
    outstation_addr: int = 101        # DNP3 address e.g. 101
    listen_ip: str = "0.0.0.0"              # binding ip on device for DNP3 connections e. g. 0.0.0.0/localhost
    event_buffer_size: int = 20

    mqtt_host: str = "localhost"
    mqtt_port: int = 1884
    mqtt_user: str = "mqtt-user"
    mqtt_password: str = "mqtt-user"
    mqtt_base_topic: str = "scada"

    plant_ac_generated_topic: str = "test/plant/state"
    plant_ac_generated_watts_per_unit: float = 1000
    grid_reactive_topic: str = "test/reactive/state"
    plant_ac_generated_var_per_unit: float = 1000
    grid_export_topic: str = "test/export/state"
    plant_export_watts_per_unit: float = 1000

    # plant_active_power_set_topic: str
    # plant_ramp_up_set_topic: str
    # plant_ramp_down_set_topic: str
    max_total_nominal_active_power_kwh: float = 125


DEFAULT_OPTIONS = Options()

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