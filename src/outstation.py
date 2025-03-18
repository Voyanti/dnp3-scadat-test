import logging
import sys
import time
from datetime import datetime
import asyncio

from enum import IntEnum
from typing import Callable, Optional

from .mqtt_entities import MQTTValues
from .structs import CommandValues

# no stubs or definitions available for deprecated wrapper library
from pydnp3 import opendnp3, openpal, asiopal, asiodnp3 # type: ignore

# ------------------------------------------------------
# Setup basic logging
# ------------------------------------------------------
logger = logging.getLogger(__name__)

# OutstationStackConfig Indexes
class BinaryAddressIndex(IntEnum):
    b_production_constraint = 0
    b_power_gradient_constraint = 1
class AnalogAddressIndex(IntEnum):
    a_total_power = 0                           # by Embedded Generation (EG) PLant
    a_reactive_power = 1                        # at point of connection (POC) to CCT
    a_exported_or_imported_power = 2            # at POC

    a_production_constraint_setpoint = 3        # 0 - master output index
    a_power_gradient_constraint_ramp_up = 4     # 1
    a_power_gradient_constraint_ramp_down = 5   # 2
# ------------------------------------------------------
# Custom Command Handler
# This is where we handle control requests (Select/Operate)
# ------------------------------------------------------
class MyCommandHandler(opendnp3.ICommandHandler):
    def __init__(self) -> None:
        super(MyCommandHandler, self).__init__()

        self.command_values = CommandValues(
            production_constraint_setpoint=100,
            gradient_ramp_up=100,
            gradient_ramp_down=100
        )

        # Define a callback that takes a CommandValues object as argument, for passing commands from outstation 
        self.on_command_callback: Optional[Callable] = None
        self.outstation_command_updater_callback: Optional[Callable] = None
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None

    def Start(self):
        """
        Called when a new series of commands is begun (Task Start).
        """
        logger.info("CommandHandler: Start receiving commands.")

    def End(self):
        """
        Called when a series of commands has completed (Task End).
        """
        logger.info("CommandHandler: Done receiving commands.")

    def handle_commands(self) -> None:
        """ 
        Async Calls self.on_command_callback after verifying its definition
        """
        # Use call_soon_threadsafe to schedule the callback on the main event loop
        if self.on_command_callback and self._main_loop:
            logger.info(f"Commands received from master, adding callback to event loop")
            async def run_callback():
                await self.on_command_callback(self.command_values)
            
            self._main_loop.call_soon_threadsafe(
                lambda: asyncio.create_task(run_callback())
            )
        else:
            raise NotImplementedError(f"{self}.on_command_callback not defined")
    # ----------
    # SBO (Select) and Operate for AnalogOutputInt16
    # ----------
    def Select(self, command, index):
        """
        Select is the 'Select' phase of select-before-operate. 
        We confirm here if the command *can* be operated on.
        """
        logger.info(f"Select (index={index}): command={command.value}")
        status = opendnp3.CommandStatus.SUCCESS # TODO validation
        return status

    def Operate(self, command, index, op_type):
        """
        Operate is the final 'Operate' phase of select-before-operate (or a direct operate).
        Here we actually *execute* the command logic.
        """
        logger.info(f"Operate (index={index}): command={command.value} op_type={op_type}")

        # We only have 3 analog outputs (16-bit) mapped to indexes 0,1,2
        if index == 0:
            self.command_values.production_constraint_setpoint = command.value
            logger.info(f"Production Constraint updated to {command.value}%")
        elif index == 1:
            self.command_values.gradient_ramp_up = command.value
            logger.info(f"Ramp Up Rate updated to {command.value}%/minute")
        elif index == 2:
            self.command_values.gradient_ramp_down = command.value
            logger.info(f"Ramp Down Rate updated to {command.value}%/minute")
        else:
            logger.warning(f"Operate received for unknown index={index}")
            return opendnp3.CommandStatus.NOT_SUPPORTED

        self.handle_commands()

        if self.outstation_command_updater_callback:
            self.outstation_command_updater_callback()
        else:
            logger.error("No outstation_command_updater_callback defined")

        # Return success status
        return opendnp3.CommandStatus.SUCCESS


    # DNP3 requires that each command type we plan to support 
    # be explicitly handled: 
    def PerformFunction(self, name, function_code, headers, config):
        """
        If you need to handle custom function codes or array of commands, handle here.
        """
        logger.info(f"PerformFunction called: {name} code={function_code}")
        return opendnp3.CommandStatus.SUCCESS


# ------------------------------------------------------
# Custom Outstation Application
# Used to handle time writes, cold/warm restarts, etc.
# ------------------------------------------------------
class MyOutstationApplication(opendnp3.IOutstationApplication):
    def __init__(self):
        super(MyOutstationApplication, self).__init__()

    # def OnStateChange(self, state):
    #     logger.info(f"OutstationApplication - state changed: {(state.__getstate__())}")

    def SupportsWriteAbsoluteTime(self):
        return False

    def WriteAbsoluteTime(self, ms_since_epoch):
        """
        Handle time sync from master, if master tries to set outstation time.
        For demonstration, we do nothing special here.
        """
        logger.info(f"Master wrote time: {ms_since_epoch} ms since epoch.")
        return True

    def GetUTCTime(self):
        """
        If the Master asks for outstation's time, we return local system time in ms since epoch.
        If you want local SA time with offset, you can add offset logic here.
        """
        now = datetime.utcnow()
        epoch = datetime(1970, 1, 1)
        return int((now - epoch).total_seconds() * 1000)


# ------------------------------------------------------
# Main class to configure and run the outstation
# ------------------------------------------------------
class DNP3Outstation:
    def __init__(self,
                 outstation_addr=101,
                 master_addr=100,
                 listen_ip="0.0.0.0",
                 listen_port=20000,
                 event_buffer_size=20) -> None:

        # 1) Create a manager
        # self.manager = asiodnp3.DNP3Manager(1, asiodnp3.ConsoleLogger().Create())  # (concurrency_hint, handler: IlogHandler, ...)
        self.manager = asiodnp3.DNP3Manager(1)  # (concurrency_hint, handler: IlogHandler, ...)
        # self.manager.SetLogFilters(openpal.LogFilters(opendnp3.levels.NORMAL))
        logger.info("DNP3 Manager created.")

        # 2) Create a TCP Server (the channel)
        channel_listener = asiodnp3.PrintingChannelListener().Create()
        self.channel = self.manager.AddTCPServer(
            "server-channel",                            # id: str
            opendnp3.levels.ALL_COMMS,                  # levels: int
            asiopal.ChannelRetry().Default(),           # retry: ChannelRetry
            listen_ip,                                  # endpoint: str
            listen_port,                                # port: int
            channel_listener                            # listener: IChannelListener
        )
        logger.info(f"Outstation channel listening on {listen_ip}:{listen_port}")

        # 3) Configure the outstation
        self.command_handler = MyCommandHandler()
        self.outstation_application = MyOutstationApplication()

        # stack, database config
        outstation_config = self.configureOutstationStack(outstation_addr, 
                                                          master_addr, 
                                                          event_buffer_size)

        # 4) Create the outstation
        self.outstation = self.channel.AddOutstation(
            "my-outstation",               # id: str
            self.command_handler,          # commandHandler: ICmdHandler
            self.outstation_application,   # application: IOutstationApplication
            outstation_config              # config: OutstationStackConfig
        )

        self.command_handler.outstation_command_updater_callback = self.update_commands

    def enable(self):
        # 5) Enable the outstation so it starts accepting connections
        self.outstation.Enable()
        logger.info("Outstation enabled.")

    def configureOutstationStack(self, outstation_addr, master_addr, event_buffer_size) -> asiodnp3.OutstationStackConfig:
        # db Sizes
        db_sizes = opendnp3.DatabaseSizes()         # all sizes zero
        db_sizes.numBinary = 2       # We have 2 binary inputs
        db_sizes.numAnalog = 6       # We have 6 analog inputs
        # If you have counters, binary output status, or analog output status, set them accordingly.

        outstation_config = asiodnp3.OutstationStackConfig(db_sizes)    # configuration struct that contains all the config information for a dnp3 outstation stack.
        
        # Defines the number of events to keep in buffer. hHen a value is updated using UpdateBuilder, an event is added to the buffer 
        config = opendnp3.EventBufferConfig()
        config.maxBinaryEvents = event_buffer_size
        config.maxAnalogEvents = event_buffer_size
        outstation_config.outstation.eventBufferConfig = config
        # ---- Link Layer Addresses ----
        outstation_config.link.LocalAddr = outstation_addr
        outstation_config.link.RemoteAddr = master_addr
        # VRAAG: disable unsolicited TODO support setting this to diabled from master?
        outstation_config.outstation.params.allowUnsolicited = False        

        # db Config
        # ---- Define the database layout: 8 total points ----
        #  - 2 binary inputs
        #  - 6 analog inputs
        #  - 3 analog outputs
        #  (You only configure in DB what you want to serve to the Master)

        # *** Binaries *** (indexes 0,1)
        #   - Production Constraint Mode (ON/OFF)
        #   - Power Gradient Constraint Mode (ON/OFF)
        for i in range(2):
            bi_config = outstation_config.dbConfig.binary[i]
            # class id for event interrogations. static interrogations are always class 0
            bi_config.clazz = opendnp3.PointClass.Class1                        # class 0 for static data, class 1, 2, 3 for hig, med, low priority event data 
            bi_config.evariation = opendnp3.EventBinaryVariation.Group2Var2     # event variation
            bi_config.svariation = opendnp3.StaticBinaryVariation.Group1Var2 

        # *** Analogs *** 
        #    indexes: 
        #        0,1,2 => 32-bit floating (Watts, VAR, Export/Import)
        #        3,4,5 => 16-bit analog (Echo constraints)
        for i in range(6):
            ai_config = outstation_config.dbConfig.analog[i]
            ai_config.clazz = opendnp3.PointClass.Class2
            if i in [0,1,2]:
                # 32-bit analog input 
                # Use Object30 Var5 for static, Object32 Var7 for event
                ai_config.svariation = opendnp3.StaticAnalogVariation.Group30Var5
                ai_config.evariation = opendnp3.EventAnalogVariation.Group32Var7
            else:
                # i in [3,4,5] => 16-bit analog input
                # Use Object30 Var4 for static, Object32 Var4 for event
                ai_config.svariation = opendnp3.StaticAnalogVariation.Group30Var4
                ai_config.evariation = opendnp3.EventAnalogVariation.Group32Var4

        # *** Analog Outputs *** 
        #   indexes: 0,1,2 => 16-bit analog outputs
        #   You won't see these in the DB config by default. We only handle them in the command handler.
        #   But if you want to keep track of an 'analog output status' (Obj 40 Var 2 or 42, etc.), 
        #   you can configure them similarly in the outstation’s database if desired.
        return outstation_config

    async def update_values(self, values: MQTTValues) -> None:
        """
        Update the outstation's data with plant measurements.
        Used as a callback in plant-measurement-receiving-class (MQTTWrapper)
        """

        # make sure to update homeassistant with command handler controls bedore updating the values read

        # 1) Create an UpdateBuilder
        builder = asiodnp3.UpdateBuilder()

        # 2) Add updates for each point:
        # Binary points (index=0 => Production Constraint Mode, index=1 => Power Gradient Constraint Mode)
        builder.Update(                 # measurement, index: opendnp3.Binary | opendnp3.Analog, index: ?, mode: opendnp3.EventMode (Detect, Force, Suppress)
            opendnp3.Binary(values["flag_dont_production_constraint"]._value), 
            BinaryAddressIndex.b_production_constraint, 
            opendnp3.EventMode.Detect   # will only generate an event if a change actually occured from this update. use force to create an event for each update, suppress for no events
        )
        builder.Update(
            opendnp3.Binary(values["flag_dont_gradient_constraint"]._value), 
            BinaryAddressIndex.b_power_gradient_constraint, 
            opendnp3.EventMode.Detect
        )

        # 32-bit analogs: indexes [0..2]
        # Example values for demonstration:
        builder.Update(
            opendnp3.Analog(values["plant_ac_power_generated"].value), 
            AnalogAddressIndex.a_total_power, 
            opendnp3.EventMode.Detect
        )  # Watts
        builder.Update(
            opendnp3.Analog(values["grid_reactive_power"].value), 
            AnalogAddressIndex.a_reactive_power, 
            opendnp3.EventMode.Detect
        )    # VARs
        builder.Update(
            opendnp3.Analog(values["grid_exported_power"].value), 
            AnalogAddressIndex.a_exported_or_imported_power, 
            opendnp3.EventMode.Detect
        )    # Export/Import Power

        # # verify that values read, match commands set earlier
        # # assert cmd_handler.command_values.production_constraint_setpoint == values.production_constraint_setpoint
        # # assert cmd_handler.command_values.gradient_ramp_up == values.gradient_ramp_up
        # # assert cmd_handler.command_values.gradient_ramp_down == values.gradient_ramp_down

        # 3) Apply the changes to the outstation
        self.outstation.Apply(builder.Build())

    def update_commands(self) -> None:
        """
        Update the outstation's data with plant measurements.
        Used as a callback in plant-measurement-receiving-class (MQTTWrapper)
        """
        builder = asiodnp3.UpdateBuilder()

        # 16-bit analogs: indexes [3..5]
        # Echo the setpoints from the command handler
        cmd_handler = self.command_handler

        builder.Update(
            opendnp3.Analog(cmd_handler.command_values.production_constraint_setpoint), 
            AnalogAddressIndex.a_production_constraint_setpoint, 
            opendnp3.EventMode.Detect
        )
        builder.Update(
            opendnp3.Analog(cmd_handler.command_values.gradient_ramp_up), 
            AnalogAddressIndex.a_power_gradient_constraint_ramp_up, 
            opendnp3.EventMode.Detect
        )
        builder.Update(
            opendnp3.Analog(cmd_handler.command_values.gradient_ramp_down), 
            AnalogAddressIndex.a_power_gradient_constraint_ramp_down, 
            opendnp3.EventMode.Detect
        )

        # 3) Apply the changes to the outstation
        self.outstation.Apply(builder.Build())

    def shutdown(self):
        """
        Gracefully shutdown everything.
        """
        self.channel.Shutdown()
        self.manager.Shutdown()