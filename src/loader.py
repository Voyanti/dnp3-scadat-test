from json import load, JSONDecodeError
import os
import logging
from dataclasses import dataclass
from cattrs import Converter
from yaml import CLoader 
from yaml import load as load_yaml
logger = logging.getLogger(__name__)


@dataclass
class Topic:
    topic: str = "test/active_power/set"

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
    grid_reactive_var_per_unit: float = 1000
    grid_export_topic: str = "test/export/state"
    grid_export_watts_per_unit: float = 1000

    plant_active_power_set_topics: list[Topic] = [Topic()]
    plant_ramp_up_set_topic: str = "test/ramp_up/set"
    plant_ramp_down_set_topic: str = "test/ramp_down/set"
    max_total_nominal_active_power_kw: float = 125


def load_config(config_path = '/data/options.json') -> Options:
    """
    Reads the Home Assistant add-on configuration from the options.json file.
    Returns a dictionary containing the configuration values.

    """
    logger.info("Loading config json")
    
    try:
        if not os.path.exists(config_path):
            raise IOError(f"Config file not found at {config_path}")

        with open(config_path, 'r') as config_file:
            if config_path[-4:] == "yaml":      # local config
                config = load_yaml(config_file, Loader=CLoader)
            elif config_path[-4:] == "json":    # config as parsed by homeassistant
                config = load(config_file)
            else:
                raise FileNotFoundError
            
        logger.info("Loaded config json")
        converter = Converter(forbid_extra_keys=False)
        opts = converter.structure(config, Options)
        return opts
        
    except JSONDecodeError as e:
        raise ValueError(f"Failed to parse config file: {str(e)}")
    except IOError as e:
        logging.error(str(e))
        raise
    except FileNotFoundError as e:
        logging.error(f"Unsopported config file extention at {config_path}")
        raise
    except Exception as e:
        raise Exception(f"Error reading config: {str(e)}")