#Just a quick note, can people who work on this code add comments, so when other people get to it they know what is going on. Thank you.


from sr.robot import *
import time
import math

class MarkerNotFoundError(Exception):
    """
    This exception should always be handled.
    """
    pass

class Test(Robot):#Object
    """
    A test framework for the DC motor based robot.
    When adding functionality such as 'turn' or 'goto_marker', please add it as
    a function with an appropriate name.
    """
    def __init__(self):
        print('Start Hobo init')
        # Initialise the motors and powerboard
        # We're inheriting from sr.robot.Robot so any documentation with robot.*
        # Should instead be written as self.*
        super(Test, self).__init__()
        # Completed initialisation
        print('Robot initialised')
        # Test functionality currently being worked on
        while True:
            marker = self.find_markers(max_loop=20)[0]
            if marker > 0:
                self.goTo(marker)
            
        #while 1:
            #marker = self.find_markers(max_loop=10000)[0]
            #print "rot_x", marker.orientation.rot_x, "rot_y", marker.orientation.rot_y, "rot_z", marker.orientation.rot_z# marker rotation
            #print "pol_rot_x", marker.centre.polar.rot_x, "pol_rot_z", marker.centre.polar.rot_y#Marker rotation from robot
            
    def goTo(self, marker):
        """
        Go to the given marker
        """
        lengthOne = 1.0
        print('Marker:', marker)
        turnOne = 180 - (marker.orientation.rot_y + marker.centre.polar.rot_y)
        print('Turn one', turnOne)
        lengthOne = marker.dist
        print('Length from marker', marker.dist)
        lengthTwo = (lengthOne / math.sin(math.radians(90))) * (math.sin(math.radians(marker.orientation.rot_y)))
        print('Length two', lengthTwo)
        turnTwo = 90
        self.turn((turnOne / 2))
        print('Turn one function:',self.turn)
        self.forwards(math.fabs(lengthTwo))
        self.turn(turnTwo)
        markers = self.see()
        for m in markers:
            lengthOne = marker.dist
            print('Length from marker', marker.dist)
        self.forwards(lengthOne)
        
    
    def find_markers(self, minimum=1, max_loop=20):
        """
        Find at least `mimimum` markers.
        If tried `max_loop` times, give up and raise an exception.
        Things calling `find_markers` should be prepared for this exception and
        respond to it as necessary.
        """
        cur = 0
        markers = []
        while len(markers) < minimum:
            cur += 1
            print("Searching for markers...")
            markers = self.see()
            if cur == max_loop:
                raise MarkerNotFoundError("Marker (minimum {}) not found after {} loops".format(minimum, max_loop))
        return markers
        
    def forwards(self, distance, speed=0.75, ratio=-1.05, speed_power = 77):
        """
        Go forwards `distance` meters at speed `speed` in m/s.
        ratio and speed_power are for calibration purposes and should not be
        changed unless the robot stops moving in a straight line at the correct
        speed
        """
        power = speed * speed_power
        self.motors[0].m0.power = power*ratio
        self.motors[0].m1.power = power
        sleep_time = distance / speed
        print "ST",sleep_time, "P", power, "PR", power*ratio
        time.sleep(sleep_time)
        print "Slept"
        self.motors[0].m0.power = 0
        self.motors[0].m1.power = 0
        
    def turn(self, degrees, power=50, ratio=-1, sleep_360=2.14):
        """
        Turn `degrees` degrees. (0-360)
        """
        self.motors[0].m0.power = power*-ratio
        self.motors[0].m1.power = power
        time.sleep(sleep_360/360*degrees)
        self.motors[0].m0.power = 0
        self.motors[0].m1.power = 0
        

if __name__ == "__main__":
    Test()


