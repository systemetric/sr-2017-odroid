"""Generic code used in many strategies.

This file is part of the code for the Hills Road/Systemetric entry to
the 2017 Student Robotics competition "Easy as ABC".
"""


from sr.robot import *

import time
from math import sqrt
import logging
from operator import attrgetter

#try:
    #from typing import Callable, List  # pylint: disable=import-error
#except ImportError:
    #pass

from mbed_link import IOBoard
import strategies
import corrections
from trig import sind, cosd, asind
from vector import Vector, marker2vector


class CompanionCube(Robot):
    """
    A path-finding robot.
    """

    def __init__(self):
        # Please use `log.debug`, `log.info`, `log.warning` or `log.error` instead of `print`
        self.init_logger()
        
        self.strategy = "b c a"
        args = []
        self.routeChange = False

        self.log.info("Start TobyDragon init")
        super(CompanionCube, self).__init__(init=False)
        self.init()
        self.log.info("Initialising wheels")
        self.wheels = IOBoard(self.log)
        self.log.info("Robot initialised")
        self.log.info("Battery(voltage = %s, current = %s)", self.power.battery.voltage, self.power.battery.current)
        switch_state = self.wheels.get_switch_state()
        self.log.info("DIP switch is %s", switch_state)
        self.log.info("Waiting for start signal...")
        self.wait_start()
        self.log.info("Start signal recieved!")
        strategies.strategies[self.strategy](self, *args)

    def faceMarker(self, marker):
        # type: (Marker) -> None
        """
        Given a marker, point towards it.
        """
        self.log.info("faceMarker is DEPRECATED. Turning to face marker")
        self.log.debug("marker.centre.polar.rot_y = %s", marker.centre.polar.rot_y)  # The angle the marker is from the robot
        self.log.debug("marker.orientation.rot_y = %s", marker.orientation.rot_y)  # The rotation of the marker
        turnOne = marker.centre.polar.rot_y  # Turns the robot to face the marker
        self.wheels.turn(turnOne)
        marker = self.find_markers()[0]
        while abs(marker.centre.polar.rot_y) > 5.0:  # If the robot is not facing the marker
            marker = self.find_markers(delta_angle=10)[0]
            self.log.debug("Not correctly aligned")
            self.log.debug("marker.centre.polar.rot_y = %s", marker.centre.polar.rot_y)  # The angle the marker is from the robot
            turnOne = marker.centre.polar.rot_y  # Turns the robot to face the marker
            self.wheels.turn(turnOne)

    def face_cube(self, marker):
        # type: (Marker) -> float
        """
        Given a cube marker, face the centre of the cube.
        Returns the distance required to travel on top of that cube
        """
        self.log.info("Facing marker...")
        vec = marker2vector(marker)
        vec = corrections.correct_all_cube(vec, marker.orientation.rot_y)
        self.log.debug("Turning %s degrees", vec.angle)
        self.wheels.turn(vec.angle)
        return vec.distance + corrections.cube_width

    def move_to_cube(self, marker, check_at=1.0, max_safe_distance=3, angle_tolerance=1.0, distance_after=0.0):
        # type: (Marker, float, float, float) -> None
        """
        Given a cube marker, face and move to the cube.

        At check_at metres away from the cube, stop and check if we're still
        facing the right way, unless we started less than max_safe_distance away
        from the cube. "The right way" is defined as within angle_tolerance of
        the angle we should be facing.
        """
        distance = self.face_cube(marker)
        if distance <= max_safe_distance:
            self.log.debug("Moving straight to cube, since distance (%s) is under max safe distance (%s)", distance, max_safe_distance)
            validMovement = self.wheels.forwards(distance+distance_after)
            if validMovement == 'Error':
                return 'Crash'
        else:
            # We need to check where we are once we're check_at distance from the cube
            distance_to_move = distance - corrections.cube_width - check_at
            self.log.debug("Cube is %s metres away, moving %s metres then checking", distance, distance_to_move)
            validMovement = self.wheels.forwards(distance_to_move)
            if validMovement == 'Error':
                return 'Crash'
            while True:  # If the robot is over 1 degrees off:
                markers = self.find_markers(filter_func = lambda m: m.info.code == marker.info.code)
                if not markers:
                    return 'Cant see'
                marker = markers[0]
                vec = marker2vector(marker)
                vec = corrections.correct_all_cube(vec, marker.orientation.rot_y)
                if abs(vec.angle) <= angle_tolerance:
                    break
                self.log.debug("Not correctly aligned")
                self.log.debug("We're %s degrees off, correcting...", vec.angle)  # The angle the marker is from the robot
                self.wheels.turn(vec.angle)
            self.log.debug("Moving the rest of the way to the cube (%s + cube_size (0.255)); this should be about 1.255 metres", vec.distance)
            validMovement = self.wheels.forwards(vec.distance+distance_after)
            if validMovement == 'Error':
                return 'Crash'
        self.log.debug("Done moving to cube")
        return 'Ok'

    def see_markers(self, predicate=None, attempts=3):
        # type: (Callable[[Marker], bool], int) -> List[Marker]
        """
        Return a list of visible markers that satisfy the given predicate.

        The predicate will be called on each marker, and should return a
        boolean showing whether the marker should be included in the returned
        list. It defaults to None, meaning that all visible markers will be
        returned. Strictly speaking, any falsy markers will be discarded, but
        since markers are instances of collections.namedtuple(), they are
        always truthy.

        If no markers are visible, multiple attempts to see a marker will be
        made, in case of a transient fault with the camera. The number of
        attempts can be changed by altering the attempts parameter, which must
        be greater than zero.
        """
        self.log.info("Looking for markers (%s attempts)...", attempts)
        assert attempts > 0
        for i in xrange(attempts):
            markers = filter(predicate, self.see())
            if markers:
                self.log.info("Found %s markers (attempt %s), returning.", len(markers), i + 1)
                break
            else:
                self.log.debug("No markers found (attempt %s), retrying...", i + 1)
        else:
            self.log.warn("No markers found after %s attempts!", attempts)
        return markers

    def find_closest_marker(self, marker_type):
        # type: (...) -> Marker
        """
        Find and return the closest marker of a given marker type.
        
        If no markers can be found, an IndexError will be raised.
        """
        self.log.info("Finding closest marker of type %s", marker_type)
        markers = [m for m in self.find_markers(filter_func=lambda marker: marker.info.marker_type == marker_type)]
        return sorted(markers, key=attrgetter("dist"))[0]

    def find_marker_approx_position(self, marker_type, dist, dist_tolerance = 0.5):
        """
        Find and return a list of markers at an approximate location.

        The list may be empty, in which case no markers could be seen at that distance.
        """
        self.log.info("Finding marker of type %s approximately %s metres away, give or take %s metres", marker_type, dist, dist_tolerance)
        markers = []
        for marker in self.lookForMarkers(max_loop=5):
            if marker.info.marker_type == marker_type and dist - dist_tolerance <= marker.dist <= dist + dist_tolerance:
                self.log.debug("Found a MATCHING %s marker (id %s) %s metres away at %s degrees",
                               marker.info.marker_type, marker.info.code, marker.dist, marker.rot_y)
                markers.append(marker)
            else:
                self.log.debug("Found a non-matching %s marker (id %s) %s metres away at %s degrees",
                               marker.info.marker_type, marker.info.code, marker.dist, marker.rot_y)
        # markers = [m for m in self.lookForMarkers(max_loop=5) if m.info.marker_type == marker_type and dist - dist_tolerance <= m.dist <= dist + dist_tolerance]
        self.log.info("Found %s markers matching criteria", len(markers))
        return markers

    def cone_search_approx_position(self, marker_type, dist, dist_tolerance = 0.5, max_left=45, max_right=45, delta=15, sleep_time=0.5):
        """
        Search for a specific marker type at an appproximate distance with tolerances
        outside of the visual range of the camera
        """
        self.log.info("Doing a cone based search with extremities (%s, %s) and delta %s for markers of type %s approximately %s metres away, give or take %s metres", max_left, max_right, delta, marker_type, dist, dist_tolerance)
        angles = [0, -max_left]+[delta for i in range(0, max_left+max_right, delta)]
        for angle in angles:
            self.wheels.turn(angle)
            markers = self.find_marker_approx_position(marker_type, dist, dist_tolerance)
            if markers:
                self.log.info("Finished marker type cone search and found %s markers of type %s", len(markers), marker_type)
                return markers
            time.sleep(sleep_time)
        self.log.info("Finished marker type cone search with no markers found")

    def cone_search_specific_marker(self, marker_id, max_left=45, max_right=45, delta=15, sleep_time=0.5):
        """
        Search for a specific marker outside of the visual range of the camera
        """
        self.log.info("Doing a cone based search with extremities (%s, %s) and delta %s for a marker (id %s)", max_left, max_right, delta, marker_id)
        angles = [0, -max_left]+[delta for i in range(0, max_left+max_right, delta)]
        for angle in angles:
            self.wheels.turn(angle)
            markers = self.see_markers(predicate=lambda marker: marker.info.code == marker_id)
            if markers:
                self.log.info("Finished specific marker cone search and found %s markers of id %s", len(markers), marker_id)
                return markers
            time.sleep(sleep_time)
        self.log.info("Finished specific marker cone search with no markers found")

    def find_markers(self, minimum=1, max_loop=10, delta_angle=20, filter_func=lambda marker: True):
        """
        Find at least minimum markers.
        Try max_loop attempts for each direction.
        """

        # Scan 0.
        self.log.debug("Searching for markers... (direction = 0)")
        markers = self.lookForMarkers(max_loop=max_loop)
        markers = filter(filter_func, markers)
        if len(markers) >= minimum:
            # If found correct number of markers, stop and return them
            return markers
        else:
            angle = delta_angle
            while angle <= 180:
                # If the robot cannot see a marker
                self.log.debug("Searching for markers... (direction = %s)", delta_angle)
                self.wheels.turn(angle)
                markers = filter(filter_func, self.lookForMarkers(max_loop=max_loop))
                if len(markers) >= minimum:
                    self.routeChange = True
                    return markers
                self.wheels.turn(-angle * 2)
                markers = filter(filter_func, self.lookForMarkers(max_loop=max_loop))
                if len(markers) >= minimum:
                    self.routeChange = True
                    return markers
                self.wheels.turn(angle)
                angle += delta_angle
            self.log.error("Couldn't find the requested marker!")
        # Current direction is ~360 (no change)
        self.log.error("Markers (minimum %s) not found with %s loops per direction", minimum, max_loop)
        self.routeChange = True
        return markers 

    def lookForMarkers(self, max_loop=float("inf"), sleep_time=0.5):
        """
        Look for markers.
        if none found within max_loop, return []
        """
        self.log.warn("Deprecation warning: use see_markers instead!")
        self.log.info("Looking for markers with %s attempts...", max_loop)
        time.sleep(sleep_time)  # Rest so camera can focus
        markers = self.see()
        i = 0
        while i <= max_loop and len(markers) == 0:
            self.log.debug("Cannot see a marker")
            i += 1
            markers = self.see()
        return markers

    def find_specific_markers(self, marker_type, delta_angle=20):
        """
        Searches for markers in a similar way to find_markers().
        """
        self.log.debug("Finding marker of type %s", marker_type)
        self.log.warn("Not yet implemented")
        # The maximum number of times to check for a marker from one angle.
        max_loop = 5
        # Get a list of markers that are of the requested type.
        markers = filter(lambda m: m.info.marker_type == marker_type, self.lookForMarkers(max_loop=max_loop))
        if len(markers) == 0:
            # Turn slightly left in case we're facing just right of the marker.
            self.wheels.turn(-delta_angle)
            i = 0
            # Search for markers in a full circle
            while i <= 360 and len(markers) == 0:
                markers = filter(lambda m: m.info.marker_type == marker_type, self.lookForMarkers(max_loop=max_loop))
                if len(markers) == 0:
                    self.wheels.turn(delta_angle)
                    i += delta_angle
        return markers

    def get_vec_to_corner(self, marker):
        """
        Given a marker, get the vector to the corner to the left of it.

        See <https://hillsroadrobotics.slack.com/files/anowlcalledjosh/F414B8RPX/office_lens_20170204-144813.jpg>
        or <https://imgur.com/R9E8kpD> for an image showing how this works.
        """
        d = marker.dist
        l = marker.info.offset % 7 + 1
        alpha = marker.rot_y
        beta = marker.orientation.rot_y
        beta_prime = 90 - beta
        self.log.debug("d=%s, l=%s, alpha=%s, beta=%s", d, l, alpha, beta)
        n = sqrt(l**2 + d**2 - 2 * l * d * cosd(beta_prime))
        delta = asind(l * sind(beta_prime) / n)
        self.log.debug("delta=%s", delta)
        gamma = alpha - delta
        return Vector(distance=n, angle=gamma)

    def check_cube_alignment(self):
        """
        Looks to see what cubes are ahead of the robot and checks if they are in the expected position
        """
        RA_marker = False
        LA_marker = False
        C_Marker = False
        self.log.info("Looking for markers to align with")
        markers = self.see_markers()
        for m in markers:
            if m.info.marker_type == MARKER_TOKEN_A:
                if m.rot_y <= 0:
                    RA_marker = self.check_cube_angle(m, -70)
                else:
                    LA_marker = self.check_cube_angle(m, 15)
            if m.info.marker_type == MARKER_TOKEN_B:
                self.check_cube_angle(m, 18)
            if m.info.marker_type == MARKER_TOKEN_C:
                self.log.info("Can see markers with marker type of 'C'")
                if m.rot_y <= -5 or m.rot_y >= 5:
                    self.log.info("'C' marker is out of position, orientation is %s", m.rot_y)
                    C_Marker = False
                else:
                    C_Marker = True
        return [RA_marker, LA_marker, C_Marker]

    def check_cube_angle(self, marker, expectedPosition):
        self.log.info("Can see markers with %s, number %s", marker.info.marker_type, marker.info.code)
        if marker.rot_y <= expectedPosition - 5 or marker.rot_y >= expectedPosition + 5:
            self.log.info("%s marker is out of position, orientation is %s", marker.info.marker_type, marker.rot_y)
            return False
        else:
            return True

    def init_logger(self):
        """
        Initialise logger.
        """
        self.log = logging.getLogger(__name__)
        self.log.setLevel(logging.DEBUG)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        # Example: "filename:42 - do_stuff() - INFO: stuff happened"
        formatter = logging.Formatter("%(module)s:%(lineno)d - %(funcName)s() - %(levelname)s: %(message)s")
        console_handler.setFormatter(formatter)
        self.log.addHandler(console_handler)


if __name__ == "__main__":
    CompanionCube()
