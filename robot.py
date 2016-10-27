#Just a quick note, can people who work on this code add comments, so when other people get to it they know what is going on. Thank you.


from sr.robot import *
import time
import math

class MarkerNotFoundError(Exception): pass

class Test(Robot):#Object
    
    def __init__(self):
        print('Start Hobo init')
        super(Test, self).__init__()
        print('Robot initialised')
        while True:
            marker = self.find_markers(max_loop=20)[0]
            if marker > 0:
                #self.goTo(marker)
                print "pol_rot_x", marker.centre.polar.rot_x, "pol_rot_y", marker.centre.polar.rot_y#Marker rotation from robot
                self.turn(marker.centre.polar.rot_y)
                time.sleep(5)
                
        #while 1:
            #marker = self.find_markers(max_loop=10000)[0]
            #print "rot_x", marker.orientation.rot_x, "rot_y", marker.orientation.rot_y, "rot_y", marker.orientation.rot_z# marker rotation
            #print "pol_rot_x", marker.centre.polar.rot_x, "pol_rot_z", marker.centre.polar.rot_y#Marker rotation from robot
            
    def goTo(self, marker):
        lengthOne = float
        turnThree = float
        print('Markers', marker)
        turnOne = self.turn(marker.centre.polar.rot_x)
        turnTwo = ((90 - marker.orientation.rot_y))
        print('Turn one', turnOne)
        lengthOne = marker.dist
        print('Length from marker', marker.dist)
        lengthTwo = (lengthOne / math.sin(math.radians(90))) * (math.sin(math.radians(marker.orientation.rot_y)))
        print('Length two', lengthTwo)
        if  marker.orientation.rot_y > 0:
            turnThree = 270
            print(turnThree)
        else:
            print(turnThree)
            turnThree = 90
        self.turn(turnTwo)
        print('Turn one function:',self.turn)
        self.forwards(math.fabs(lengthTwo))
        if turnOne <= 90:
            self.turn(turnTwo)
        markers = self.see()
        for m in markers:
            lengthOne = marker.dist
            print('Length from marker', marker.dist)
        self.forwards(lengthOne)
        
    
    def find_markers(self, minimum=1, max_loop=20):
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
        power = speed * speed_power
        sleep_time = distance / speed
        print "D", distance, "ST",sleep_time, "P", power, "PR", power*ratio 
        self.motors[0].m0.power = power*ratio
        self.motors[0].m1.power = power
        time.sleep(sleep_time)
        self.motors[0].m0.power = 0
        self.motors[0].m1.power = 0
        
    def turn(self, degrees, power=50, ratio=-1, sleep_360=2.14):
        if degrees <= 0:
            degrees = 360 - math.fabs(degrees)
        if degrees < 25 or degrees > 335:
            power = power / 2
            sleep_360 = sleep_360 * 2
        print "Turn",degrees, "Power", power
        if degrees <= 180:
            self.motors[0].m0.power = power*-ratio
            self.motors[0].m1.power = power
            time.sleep(sleep_360/360*degrees)
        else:
            self.motors[0].m0.power = -power*ratio
            self.motors[0].m1.power = -power
            time.sleep(sleep_360/360*(180 - degrees))
        
        self.motors[0].m0.power = 0
        self.motors[0].m1.power = 0
        
                
    

        
if __name__ == "__main__":
    Test()


