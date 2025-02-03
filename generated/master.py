import logging
import sys
import time
from datetime import datetime

from pydnp3 import opendnp3, openpal, asiopal, asiodnp3

# Setup logging
logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s'
)
logger = logging.getLogger(__name__)

class MyMasterApplication(opendnp3.IMasterApplication):
    def __init__(self):
        super(MyMasterApplication, self).__init__()

    def AssignClassDuringStartup(self):
        return False

    def OnReceiveIIN(self, iin):
        logger.info(f"Received IIN: {iin.ToString()}")

    def OnTaskComplete(self, info):
        logger.info(f"Task Complete: {info.ToString()}")

    def OnTaskStart(self, type, id):
        logger.info(f"Task Start - Type: {type} ID: {id}")

class MySOEHandler(opendnp3.ISOEHandler):
    def __init__(self):
        super(MySOEHandler, self).__init__()

    def Process(self, info, values):
        logger.info(f"Processing {len(values)} measurements:")
        for value in values:
            logger.info(f"  Index {value.index}: {value.value}")

    def Start(self):
        logger.info("SOE Handler Started")

    def End(self):
        logger.info("SOE Handler Ended")

class DNP3Master:
    def __init__(self, 
                 master_addr=100,
                 outstation_addr=101,
                 remote_ip="127.0.0.1",
                 remote_port=20000):

        # Create DNP3 manager
        self.manager = asiodnp3.DNP3Manager(1)

        # Create channel
        channel_listener = asiodnp3.PrintingChannelListener().Create()
        self.channel = self.manager.AddTCPClient(
            "client-channel",
            opendnp3.levels.ALL_COMMS,
            asiopal.ChannelRetry().Default(),
            remote_ip,
            '127.0.0.1',
            remote_port,
            channel_listener
        )

        # Master stack configuration
        master_stack = asiodnp3.MasterStackConfig()
        master_stack.master.responseTimeout = openpal.TimeDuration().Seconds(2)
        master_stack.master.disableUnsolOnStartup = True
        master_stack.link.LocalAddr = master_addr
        master_stack.link.RemoteAddr = outstation_addr

        # Create master
        self.soe_handler = MySOEHandler()
        self.master_app = MyMasterApplication()
        self.master = self.channel.AddMaster(
            "master",
            self.soe_handler,
            self.master_app,
            master_stack
        )

        # Enable the master
        self.master.Enable()
        logger.info("Master enabled")

    def send_analog_command(self, value, index):
        """Send analog output command to outstation"""
        command = opendnp3.AnalogOutputInt16(value)
        self.master.DirectOperate(
            command,
            index,
            lambda task: self._command_callback(task)
        )

    def _command_callback(self, task):
        """Callback for command response"""
        logger.info(f"Command result: {task.ToString()}")

    def poll_class_data(self):
        """Poll for all class data"""
        header = opendnp3.Header().AllObjects(60, 1)  # Class 0 data
        self.master.ScanRange(header, lambda task: self._scan_callback(task))

    def _scan_callback(self, task):
        """Callback for scan response"""
        logger.info(f"Scan result: {task.ToString()}")

    def run_demo(self):
        """Demo sequence"""
        try:
            while True:
                # Poll for data
                logger.info("Polling for class data...")
                self.poll_class_data()
                time.sleep(2)

                # Send some commands
                logger.info("Sending analog output commands...")
                # Production constraint (0-100%)
                self.send_analog_command(75, 0)
                time.sleep(1)
                # Ramp up rate (%/minute)
                self.send_analog_command(10, 1)
                time.sleep(1)
                # Ramp down rate (%/minute)
                self.send_analog_command(5, 2)
                time.sleep(5)

        except KeyboardInterrupt:
            logger.info("Shutting down master...")
            self.shutdown()

    def shutdown(self):
        """Cleanup"""
        self.channel.Shutdown()
        self.manager.Shutdown()

if __name__ == "__main__":
    master = DNP3Master(
        master_addr=100,
        outstation_addr=101,
        remote_ip="127.0.0.1",
        remote_port=20000
    )
    master.run_demo()