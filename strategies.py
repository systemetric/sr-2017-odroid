"""A collection of strategies the robot should use to collect cubes."""


from sr.robot import *

import functools
from math import degrees
import time

from vector import Vector, marker2vector

strategies = {}  # type: Dict[Callable]


def strategy(name):
    # type: (Hashable) -> Callable
    """Register a strategy so that it can be accessed later."""
    # http://thecodeship.com/patterns/guide-to-python-function-decorators/
    # Usage:
    #     @strategy("a friendly strategy name")
    #     def route_nine():
    #         ...
    #
    # Then, in a subclass of Robot:
    #     strategies["a friendly strategy name"](self)
    def wrap(fn):
        strategies[name] = fn
        return fn
    return wrap


@strategy("test")
def route_test(robot):
    """
    Move onto marker A.
    """
    robot.log.debug("Starting route")
    robot.log.debug("Facing marker")
    robot.wheels.turn(45)  # Turn ~45 degrees to face the marker
    marker = robot.find_markers()[0]
    vec = marker2vector(marker)
    vec = robot.correct_for_cube_marker_placement(vec, marker.orientation.rot_y)
    vec = robot.correct_for_webcam_horizontal_placement(vec)
    robot.log.debug("Fine-tuning turn by %s degrees", degrees(vec.angle))
    robot.wheels.turn(degrees(vec.angle))
    #robot.faceMarker(marker)  # Perform corrections to face the marker
    robot.log.debug("Moving to cube")
    robot.moveToCube()
    robot.log.debug("On top of cube")
    robot.log.debug("Finished route")

@strategy("print vectors")
def route_test_vector(robot):
    while True:
        robot.log.debug("finding markers...")
        markers = robot.lookForMarkers(max_loop=3)
        robot.log.debug("found %s markers", len(markers))
        for marker in markers:
            vec = marker2vector(marker)
            robot.log.debug("found marker with vector %s", vec)
            robot.log.debug("vector to centre of cube: %s", robot.correct_for_cube_marker_placement(vec, marker.orientation.rot_y))
        time.sleep(5)

@strategy(9)
def route_nine(robot):
    """
    Collect cube B, cube C, cube A and return home, in a triangle shape.
    
    This is the anticlockwise version of route 9, where the robot first goes
    along the arena wall to its right, then turns left to collect cubes.
    """
    robot.wheels.forwards(3.5)  # Move halfway down the arena
    robot.wheels.turn(-90)  # Turn left to face into the arena
    # Get the closest marker of this type. TODO: refactor this into a function.
    marker = sorted(robot.find_specific_markers(MARKER_TOKEN_B), key=lambda m: m.dist)[0]
    robot.faceMarker(marker)
    robot.moveToCube()
    # Now on top of cube B
    marker = sorted(robot.find_specific_markers(MARKER_TOKEN_C), key=lambda m: m.dist)[0]
    robot.faceMarker(marker)  # We *should* be facing there already
    robot.moveToCube()
    # Now on top of cube C
    robot.wheels.turn(-135)  # Now facing cube A/our own corner
    marker = sorted(robot.find_specific_markers(MARKER_TOKEN_A), key=lambda m: m.dist)[0]
    robot.faceMarker(marker)
    robot.moveToCube()
    # Now on top of cube A, with all cubes collected
    # TODO: move home, optionally based on wall markers
