import logging
import sys
import time
from datetime import datetime

from pydnp3 import opendnp3, openpal, asiopal, asiodnp3

# ------------------------------------------------------
# Setup basic logging
# ------------------------------------------------------
logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s'
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------
# Custom Command Handler
# This is where we handle control requests (Select/Operate)
# ------------------------------------------------------
class MyCommandHandler(opendnp3.ICommandHandler):
    def __init__(self):
        super(MyCommandHandler, self).__init__()

        # Store the latest setpoint values here
        self.production_constraint = 0   # index=0
        self.ramp_up_rate          = 0   # index=1
        self.ramp_down_rate        = 0   # index=2

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

    # ----------
    # SBO (Select) and Operate for AnalogOutputInt16
    # ----------
    def Select(self, command, index, op_type, num_retries):
        """
        Select is the 'Select' phase of select-before-operate. 
        We confirm here if the command *can* be operated on.
        """
        logger.info(f"Select (index={index}): command={command.value} op_type={op_type}")
        status = opendnp3.CommandStatus.SUCCESS # TODO validation
        return status

    def Operate(self, command, index, op_type, num_retries):
        """
        Operate is the final 'Operate' phase of select-before-operate (or a direct operate).
        Here we actually *execute* the command logic.
        """
        logger.info(f"Operate (index={index}): command={command.value} op_type={op_type}")

        # We only have 3 analog outputs (16-bit) mapped to indexes 0,1,2
        if index == 0:
            self.production_constraint = command.value
            logger.info(f"Production Constraint updated to {self.production_constraint}%")
        elif index == 1:
            self.ramp_up_rate = command.value
            logger.info(f"Ramp Up Rate updated to {self.ramp_up_rate}%/minute")
        elif index == 2:
            self.ramp_down_rate = command.value
            logger.info(f"Ramp Down Rate updated to {self.ramp_down_rate}%/minute")
        else:
            logger.warning(f"Operate received for unknown index={index}")
            return opendnp3.CommandStatus.NOT_SUPPORTED

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
        return True

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
                 listen_port=20000):

        # 1) Create a manager
        dnp3_logger = asiodnp3.ConsoleLogger().Create()
        self.manager = asiodnp3.DNP3Manager(1, dnp3_logger)  # (concurrency_hint, handler: IlogHandler, ...)
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

        # ...
        db_sizes = opendnp3.DatabaseSizes()
        db_sizes.numBinary = 2       # We have 2 binary inputs
        db_sizes.numAnalog = 6       # We have 6 analog inputs
        # If you have counters, binary output status, or analog output status, set them accordingly.

        outstation_config = asiodnp3.OutstationStackConfig(db_sizes)

        # ---- Link Layer Addresses ----
        outstation_config.link.LocalAddr = outstation_addr
        outstation_config.link.RemoteAddr = master_addr

        # ---- Timers, Buffers, Etc. ----
        # Adjust to your needs
        outstation_config.outstation.eventBufferConfig.maxBinaryEvents = 10
        outstation_config.outstation.eventBufferConfig.maxAnalogEvents = 20

        # Set class masks so the Master can poll for them
        # (Class 0 for static, Class 1/2/3 for event data)
        outstation_config.outstation.params.allowUnsolicited = False  # disable unsolicited
        # Your table says "The Client interface will be configured to poll for Class data and disable unsolicited."

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
            bi_config.clazz = opendnp3.PointClass.Class1                        # class 0 for static data, class 1, 2, 3 for hig, med, low priority event data 
            bi_config.evariation = opendnp3.EventBinaryVariation.Group2Var2     # event variation
            bi_config.svariation = opendnp3.StaticBinaryVariation.Group1Var2

        # *** Analogs *** 
        #    indexes: 
        #        0,1,2 => 32-bit floating (Watts, VAR, Export/Import)
        #        3,4,5 => 16-bit analog (Echo constraints)
        #    each with event class 1 for demonstration
        for i in range(6):
            ai_config = outstation_config.dbConfig.analog[i]
            ai_config.clazz = opendnp3.PointClass.Class1
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

        # 4) Create the outstation
        self.outstation = self.channel.AddOutstation(
            "my-outstation",               # id: str
            self.command_handler,          # commandHandler: ICmdHandler
            self.outstation_application,   # application: IOutstationApplication
            outstation_config              # config: OutstationStackConfig
        )

        # 5) Enable the outstation so it starts accepting connections
        self.outstation.Enable()
        logger.info("Outstation enabled.")

    def update_values(self):
        """
        Periodically update the outstation's data for demonstration.
        For real code, you would fetch live plant measurements here.
        """
        # 1) Create an UpdateBuilder
        builder = asiodnp3.UpdateBuilder()

        # 2) Add updates for each point:

        # Binary points (index=0 => Production Constraint Mode, index=1 => Power Gradient Constraint Mode)
        builder.Update(                 # measurement, index: opendnp3.Binary | opendnp3.Analog, index: ?, mode: opendnp3.EventMode
            opendnp3.Binary(True), 
            0, 
            opendnp3.EventMode.Detect
        )
        builder.Update(
            opendnp3.Binary(False), 
            1, 
            opendnp3.EventMode.Detect
        )

        # 32-bit analogs: indexes [0..2]
        # Example values for demonstration:
        builder.Update(
            opendnp3.Analog(12345.0), 
            0, 
            opendnp3.EventMode.Detect
        )  # Watts
        builder.Update(
            opendnp3.Analog(678.9), 
            1, 
            opendnp3.EventMode.Detect
        )    # VARs
        builder.Update(
            opendnp3.Analog(-50.0), 
            2, 
            opendnp3.EventMode.Detect
        )    # Export/Import Power

        # 16-bit analogs: indexes [3..5]
        # Echo the setpoints from the command handler
        cmd_handler = self.command_handler
        builder.Update(
            opendnp3.Analog(cmd_handler.production_constraint), 
            3, 
            opendnp3.EventMode.Detect
        )
        builder.Update(
            opendnp3.Analog(cmd_handler.ramp_up_rate), 
            4, 
            opendnp3.EventMode.Detect
        )
        builder.Update(
            opendnp3.Analog(cmd_handler.ramp_down_rate), 
            5, 
            opendnp3.EventMode.Detect
        )

        # 3) Apply the changes to the outstation
        self.outstation.Apply(builder.Build())

    def run_loop(self):
        """
        Simple run loop. You’d integrate this into your application’s main loop or use another scheduling mechanism.
        """
        logger.info("Entering main run loop. Press Ctrl+C to exit.")
        try:
            while True:
                self.update_values()
                time.sleep(5)
        except KeyboardInterrupt:
            logger.info("Shutting down outstation...")
            self.shutdown()

    def shutdown(self):
        """
        Gracefully shutdown everything.
        """
        self.channel.Shutdown()
        self.manager.Shutdown()

# ------------------------------------------------------
# Entry point
# ------------------------------------------------------
if __name__ == "__main__":
    outstation = DNP3Outstation(
        outstation_addr=101,  # As per your test requirement
        master_addr=100,      # The SCADA Master
        listen_ip="0.0.0.0",  # Listen on all interfaces
        listen_port=20000
    )
    outstation.run_loop()