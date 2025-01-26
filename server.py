import logging
import sys
import time
from pydnp3 import asiodnp3, opendnp3, asiopal, openpal

log_filters = openpal.LogFilters(opendnp3.levels.NORMAL | opendnp3.levels.ALL_COMMS)


# Configure logging
logging.basicConfig(level=logging.DEBUG)
_log = logging.getLogger(__name__)


class MyOutstationApplication(opendnp3.IOutstationApplication):
    """
    Custom implementation of the outstation application layer.
    """
    def __init__(self):
        super(MyOutstationApplication, self).__init__()

    def ColdRestart(self):
        _log.info("Cold Restart requested")
        return opendnp3.RestartOperationResult(opendnp3.RestartMode.UNSUPPORTED, 0)

    def WarmRestart(self):
        _log.info("Warm Restart requested")
        return opendnp3.RestartOperationResult(opendnp3.RestartMode.UNSUPPORTED, 0)


class MyCommandHandler(opendnp3.ICommandHandler):
    """
    Custom command handler for processing DNP3 commands from the master.
    """
    def __init__(self):
        super(MyCommandHandler, self).__init__()

    def Select(self, command, index):
        _log.info(f"Select command received: {command} at index {index}")
        return opendnp3.CommandStatus.SUCCESS

    def Operate(self, command, index, op_type):
        _log.info(f"Operate command received: {command} at index {index}")
        return opendnp3.CommandStatus.SUCCESS


def main():
    # Create a DNP3Manager to manage the server
    manager = asiodnp3.DNP3Manager(1, asiodnp3.ConsoleLogger().Create())
    _log.info("DNP3Manager created.")

    # Create a TCP server (listening on all interfaces at port 20000)
    

    # Define retry strategy
    retry = asiopal.ChannelRetry.Default()

    # Create a TCP server channel
    channel = manager.AddTCPServer(
        "server",                            # Channel ID
        opendnp3.levels.NORMAL,              # Log levels
        retry,                               # Retry strategy
        "0.0.0.0",                           # Listen on all interfaces
        20000,                               # Port number
        asiodnp3.PrintingChannelListener.Create()  # Channel listener
    )
    _log.info("TCP server started, listening on port 20000.")

    # Create a custom command handler and application layer
    command_handler = MyCommandHandler()
    application = MyOutstationApplication()

    # Define database sizes for the outstation
    db_sizes = opendnp3.DatabaseSizes.AllTypes(10)  # 10 points for each type

    # Create the outstation stack configuration
    config = asiodnp3.OutstationStackConfig(db_sizes)
    config.outstation.params.allowUnsolicited = True
    config.link.LocalAddr = 10
    config.link.RemoteAddr = 1

    # Add the outstation to the channel
    outstation = channel.AddOutstation(
        "outstation",                     # Unique ID for the outstation
        MyCommandHandler(),               # Custom command handler
        MyOutstationApplication(),        # Custom outstation application
        config                            # Outstation stack configuration
    )
    _log.info("Outstation added to the channel.")

    # Enable the outstation
    outstation.Enable()
    _log.info("Outstation enabled. Listening for connections...")

    # Run indefinitely
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        _log.info("Shutting down DNP3 Outstation...")
        manager.Shutdown()


if __name__ == "__main__":
    main()