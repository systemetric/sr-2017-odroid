
import serial


class StepperMotors():
    def __init__(self, port, log, timeout=None):
        self.log = log
        self.mbed = serial.Serial(port, timeout=timeout, writeTimeout=timeout)

    def move(self, amount):
        """
        Move the motors `abs(amount)`cm.
        If negative, go backwards
        """
        if amount > 0:
            self.forwards(amount)
        else:
            self.backwards(amount)
    
    def turn(self, amount):
        """
        Turn amount degrees right (clockwise)
        This function is clever and will turn the right direction
        """
        amount %= 360
        if amount > 180:
            self.turn_left(360-amount)
        else:
            self.turn_right(amount)
        
    
    def forwards(self, amount):
        """
        Go forwards `amount` cm.
        """
        self.send_command("f", amount)
        
    def backwards(self, amount):
        """
        Go backwards `amount` cm.
        """
        self.send_command("b", amount)
    
    def turn_left(self, amount):
        """
        Turn left `amount` degrees.
        This function is not clever and will turn more than 180 degrees if asked.
        """
        self.send_command("l", amount)
    
    def turn_right(self, amount):
        """
        Turn right `amount` degrees.
        This function is not clever and will turn more than 180 degrees if asked.
        """
        self.send_command("r", amount)
    
    def send_command(self, command, data):
        """
        Send the `command` (character) to the mbed with 1 byte of data (int)
        """
        
        try:
            self.mbed.write(command)
            self.mbed.write(chr(data))
        except serial.SerialTimeoutException:
            self.log.error("Timeout sending {} character to mbed with data {}. Not retrying.".format(command, data))
            return "Error"
        while not self.mbed.inWaiting():
            response = self.mbed.read(1)
        if response != "d":
            self.log.error("Mbed sent us a bad response. May or may not have done `{}`".format(command))
            return "Error"
        self.mbed.flushInput()
        return
        