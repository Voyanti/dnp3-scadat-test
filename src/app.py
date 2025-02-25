import logging
from time import sleep
import asyncio

from .ha_enums import HABinarySensorDeviceClass, HASensorDeviceClass
from .mqtt_entities import MQTTBinarySensor, MQTTBoolValue, MQTTFloatValue, MQTTIntValue, MQTTSensor, MQTTValues

from .outstation import DNP3Outstation
from .loader import load_config, Options
from .mqtt_wrapper import MQTTClientWrapper

logger = logging.getLogger(__name__)


def initMQTTValues(OPTS: Options):
    values = MQTTValues(    
        plant_ac_power_generated = MQTTFloatValue(
                    MQTTSensor("plant_ac_power_generated", HASensorDeviceClass.POWER, "W"), multiplier=OPTS.plant_ac_generated_watts_per_unit),
        grid_reactive_power = MQTTFloatValue(
                    MQTTSensor("grid_reactive_power", HASensorDeviceClass.REACTIVE_POWER, "Var"), multiplier=OPTS.plant_ac_generated_var_per_unit),
        grid_exported_power = MQTTFloatValue(
                    MQTTSensor("grid_exported_power", HASensorDeviceClass.POWER, "W"), multiplier=OPTS.plant_export_watts_per_unit),
        production_constraint_setpoint= MQTTIntValue(  # 0 - master output index
                    MQTTSensor("production_constraint_setpoint", HASensorDeviceClass.BATTERY, "%")), 
        gradient_ramp_up = MQTTIntValue(  # 1
                    MQTTSensor("gradient_ramp_up", HASensorDeviceClass.BATTERY, "%")),
        gradient_ramp_down = MQTTIntValue(  # 2
                    MQTTSensor("gradient_ramp_down", HASensorDeviceClass.BATTERY, "%")),
        flag_dont_production_constraint = MQTTBoolValue(
                    MQTTBinarySensor("flag_dont_production_constraint",  HABinarySensorDeviceClass.RUNNING), True),
        flag_dont_gradient_constraint = MQTTBoolValue(
                    MQTTBinarySensor("flag_dont_gradient_constraint",  HABinarySensorDeviceClass.RUNNING), True)
        )
    
    # build discovery payloads
    for val in values.values():
        val.build_payload(OPTS.mqtt_base_topic)     # type:ignore

    # initialise source MQTT topics
    values["flag_dont_gradient_constraint"].source_topic = values["flag_dont_gradient_constraint"].discovery_payload["command_topic"]
    values["flag_dont_production_constraint"].source_topic = values["flag_dont_production_constraint"].discovery_payload["command_topic"]
    # from_topic (mqtt source topic) is the command topic for switches

    # # analog values read from inverter/logger
    values["plant_ac_power_generated"].source_topic = OPTS.plant_ac_generated_topic
    values["grid_reactive_power"].source_topic = OPTS.grid_reactive_topic
    values["grid_exported_power"].source_topic = OPTS.grid_export_topic

    return values


def setup_mqtt(OPTS: Options) -> MQTTClientWrapper:
    # setup mqtt client for reading latest values from homeassistant
    mqtt_client = MQTTClientWrapper(
        OPTS.mqtt_user, OPTS.mqtt_password, OPTS.mqtt_base_topic, initMQTTValues(OPTS)
    )
    mqtt_client.connect(OPTS.mqtt_host, OPTS.mqtt_port)
    mqtt_client.publish_discovery_messages()
    mqtt_client.subscribe()  # VRAAG: lees MQTT sensors vir Values, skryf na set topics vir CommandValues yes. echo terug na mqtt vir

    return mqtt_client


async def main() -> None:
    # load home assistant add-on config
    OPTS: Options = load_config()  # homeassistant config.yaml -> Options

    # setup outstation
    outstation = DNP3Outstation(  # Configure Outstation
        outstation_addr=OPTS.outstation_addr,  # 101 for test, change in production
        master_addr=100,  # The SCADA Master @ CCT
        listen_ip=OPTS.listen_ip,  # Listen on all interfaces == 0.0.0.0
        listen_port=20000,
        event_buffer_size=OPTS.event_buffer_size,
    )

    # setup mqtt host, port, user, password, and initialise MQTTvalues
    mqtt_client = setup_mqtt(OPTS)

    # pass reference to main loop for queueing callbacks
    main_loop = asyncio.get_running_loop()
    outstation.command_handler._main_loop = main_loop
    mqtt_client._main_loop = main_loop

    # callbacks:
    # controls received => publish the updated controls to debug/ fake entity topics
    outstation.command_handler.on_command_callback = mqtt_client.publish_control  
    # values read from inverters updated => update the analog and binary values on the outstation side
    mqtt_client.on_message_callback = outstation.update_values

    logger.info("Entering main run loop. Press Ctrl+C to exit.")

    try:
        outstation.enable()
        mqtt_client.start_loop()
        logger.info(f"sleep")
        sleep(3)
        logger.info(f"initialise values")

        # initialise outstation values and commands - to ensure validity flag read by dnp server is not RESTART
        await outstation.update_values(mqtt_client._values)
        outstation.update_commands()

        logger.info(f"running") # operate using callbacks

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
        logger.info("Shutting down")
        outstation.shutdown()
        mqtt_client.stop_loop()


if __name__ == "__main__":
    asyncio.run(main())
