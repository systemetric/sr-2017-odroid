"""Generic code used in many strategies.

This file is part of the code for the Hills Road/Systemetric entry to
the 2017 Student Robotics competition "Easy as ABC".
"""


from __future__ import division

from sr.robot import *

import time
from math import sqrt
import logging
from operator import attrgetter

try:
    # noinspection PyUnresolvedReferences
    from typing import Callable, List
except ImportError:
    pass

from mbed_link import Mbed, MovementInterruptedError
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
        kwargs = {"opposite_direction": False, "ignore_C": False}
        self.routeChange = False

        self.log.info("Start TobyDragon init")
        super(CompanionCube, self).__init__(init=False)
        self.init()
        self.wheels = Mbed(self.log)
        self.log.info("Robot initialised")
        self.log.info("Battery(voltage = %s, current = %s)", self.power.battery.voltage, self.power.battery.current)
        switch_state = self.wheels.get_switch_state()
        self.log.info("DIP switch is %s", switch_state)
        self.log.info("Waiting for start signal...")
        self.wait_start()
        self.log.info("Start signal recieved!")
        strategies.strategies[self.strategy](self, *args, **kwargs)
        self.log.info("Strategy exited.")
        #self.was_a_triumph()

    def are_we_moving(self, initial_markers, final_markers):
        # type: (List[Marker], List[Marker]) -> bool
        """
        Checks if two sets of markers are different enough to make it seem like we're moving.
        """
        self.log.debug("Checking if we've moved.")
        similar_markers = 0
        self.log.debug("initial_markers: %s", map(attrgetter("info.code"), initial_markers))
        self.log.debug("final_markers: %s", map(attrgetter("info.code"), final_markers))
        initial_marker_codes = set(map(attrgetter("info.code"), initial_markers))
        final_marker_codes = set(map(attrgetter("info.code"), final_markers))
        if not initial_marker_codes.intersection(final_marker_codes):
            self.log.debug("All the markers are different, we've probably moved.")
            return True
        if (initial_markers and not final_markers) or (final_markers and not initial_markers):
            # We saw markers and then lost them, or we couldn't see anything and now we can.
            self.log.debug("We can see markers before/after and can't see markers after/before, we've probably (emphasis on probably) moved.")
            return True
        for initial_marker in initial_markers:
            for final_marker in final_markers:
                if initial_marker.info.code != final_marker.info.code:
                    # Markers aren't the same, no point comparing them.
                    continue
                # Markers are similar if the difference in distance is less than 0.1 metres and the difference in angle is less than 15 degrees.
                are_markers_similar = abs(initial_marker.dist - final_marker.dist) < 0.1 and abs(initial_marker.rot_y - final_marker.rot_y) < 15
                self.log.debug("Markers %s and %s are similar: %s", initial_marker.info.code, final_marker.info.code, are_markers_similar)
                similar_markers += are_markers_similar
        self.log.debug("We have moved!" if not similar_markers else "We have not moved!")
        return not similar_markers

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

    def move_to_cube(self, marker, crash_continue=False, check_at=1.0, max_safe_distance=3, angle_tolerance=1.0, distance_after=0.0):
        # type: (Marker, float, float, float) -> None
        """
        Given a cube marker, face and move to the cube.

        At check_at metres away from the cube, stop and check if we're still
        facing the right way, unless we started less than max_safe_distance away
        from the cube. "The right way" is defined as within angle_tolerance of
        the angle we should be facing.
        """
        marker_code = marker.info.code
        distance = self.face_cube(marker)
        for i in xrange(2):
            markers = self.find_markers(filter_func=lambda m: m.info.code == marker_code)
            if not markers:
                self.log.debug("Can't see the right marker any more (pre-turn, i=%s), hoping we're facing the right way.", i)
                break
            marker = markers[0]
            self.log.debug("facing cube, rot_y = %s", marker.rot_y)
            distance = self.face_cube(marker)
            markers = self.find_markers(filter_func=lambda m: m.info.code == marker_code)
            if not markers:
                self.log.debug("Can't see the right marker any more (pre-check, i=%s), hoping we're facing the right way.", i)
                break
            marker = markers[0]
            vec = marker2vector(marker)
            vec = corrections.correct_all_cube(vec, marker.orientation.rot_y)
            self.log.debug("Corrected cube angle is %s", vec.angle)
            if abs(vec.angle) <= angle_tolerance:
                self.log.debug("This is allowed, not facing any more.")
                break
            else:
                self.log.debug("This is too far out, going round again (if this is the first time this message appears)")
        move = self.wheels.move
        if crash_continue:
            move = self.move_continue
        if distance <= max_safe_distance:
            self.log.debug("Moving straight to cube, since distance (%s) is under max safe distance (%s)", distance, max_safe_distance)
            try:
                move(distance+distance_after)
            except MovementInterruptedError:
                return 'Crash'
        else:
            # We need to check where we are once we're check_at distance from the cube
            distance_to_move = distance - corrections.cube_width - check_at
            self.log.debug("Cube is %s metres away, moving %s metres then checking", distance, distance_to_move)
            try:
                move(distance_to_move)
            except MovementInterruptedError:
                return 'Crash'
            while True:  # If the robot is over 1 degrees off:
                markers = self.find_markers(filter_func=lambda m: m.info.code == marker.info.code)
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
            try:
                move(vec.distance+distance_after)
            except MovementInterruptedError:
                return 'Crash'
        self.log.debug("Done moving to cube")
        return 'Ok'

    def move_continue(self, distance):
        """
        Attempt to continuously move a distance, retrying if required.

        Returns True if movement completed, False if there was an error (and we tried to keep going).
        """
        try:
            self.wheels.move(distance)
        except MovementInterruptedError:
            while True:
                self.log.debug("Failed to move %sm. Attempting to continue", distance)
                time.sleep(1)
                try:
                    self.wheels.retry()
                except MovementInterruptedError:
                    continue
                else:
                    return False
        else:
            return True

    def move_home_from_A(self):
        # type: () -> None
        """Given we are at our A cube and facing roughly home, get home.

        If we can see either of the two markers inside our home area,
        we can move home accurately. Otherwise, we will blindly move
        forwards and hope we're facing in the right direction.
        """
        right_marker_code = self.zone * 7
        righter_marker_code = (right_marker_code + 1) % 28
        left_marker_code = (right_marker_code - 1) % 28
        lefter_marker_code = (left_marker_code - 1) % 28
        other_codes = set(range(28))
        other_codes.remove(left_marker_code)
        other_codes.remove(lefter_marker_code)
        other_codes.remove(right_marker_code)
        other_codes.remove(righter_marker_code)
        markers = sorted(self.see_markers(lambda m: m.info.marker_type == MARKER_ARENA), key=attrgetter("dist"))
        marker_codes = [m.info.code for m in markers]
        self.log.debug("Seen %s arena markers (codes: %s)", len(markers), marker_codes)

        walls = [
            list(range(0, 7)),
            list(range(7, 14)),
            list(range(14, 21)),
            list(range(21, 28))
        ]

        # This sucks. Deal with it.
        if (left_marker_code in marker_codes or right_marker_code in marker_codes
                or lefter_marker_code in marker_codes or righter_marker_code in marker_codes):
            if left_marker_code in marker_codes:
                self.log.debug("Can see left marker!")
                left_marker = filter(lambda m: m.info.code == left_marker_code, markers)[0]
                self.wheels.turn(left_marker.rot_y + 16)
            elif right_marker_code in marker_codes:
                self.log.debug("Can see right marker!")
                right_marker = filter(lambda m: m.info.code == right_marker_code, markers)[0]
                self.wheels.turn(right_marker.rot_y - 16)
            elif lefter_marker_code in marker_codes:
                self.log.debug("Can see lefter marker!")
                lefter_marker = filter(lambda m: m.info.code == lefter_marker_code, markers)[0]
                self.wheels.turn(lefter_marker.rot_y + 34)
            elif righter_marker_code in marker_codes:
                self.log.debug("Can see righter marker!")
                righter_marker = filter(lambda m: m.info.code == righter_marker_code, markers)[0]
                self.wheels.turn(righter_marker.rot_y - 34)
            else:
                self.log.critical("Python is lying to us! This can't happen.")
            # (sqrt(2 * 2.5^2) = 3.5355 metres)
            self.wheels.low_power_move(1.5)
            self.wheels.low_power_move(2)
        elif other_codes.intersection(marker_codes):
            bad_marker_codes = other_codes.intersection(marker_codes)
            self.log.warn("Other teams' codes (%s) are visible! We're probably facing into another team's corner :(", bad_marker_codes)
            self.move_home_from_other_A()
        else:
            self.log.warn("Can't see any useful arena markers (ours or theirs), driving forwards and praying...")
            self.wheels.low_power_move(1.5)
            self.wheels.low_power_move(2)

    def move_home_from_other_A(self, marker=None):
        # type: () -> None
        walls = [
            list(range(0, 7)),
            list(range(7, 14)),
            list(range(14, 21)),
            list(range(21, 28))
        ]

        inner_markers = [0, 6, 7, 13, 14, 20, 21, 27]
        outer_markers = [1, 5, 8, 12, 15, 19, 22, 26]

        right_marker_code = self.zone * 7
        left_marker_code = (right_marker_code - 1) % 28
        other_codes = set(range(28))
        other_codes.remove(left_marker_code)
        other_codes.remove(left_marker_code - 1)
        other_codes.remove(right_marker_code)
        other_codes.remove((right_marker_code + 1) % 28)
        our_markers = {(left_marker_code - 1) % 28, left_marker_code, right_marker_code, (right_marker_code + 1) % 28}

        # - move to 1.5 m away from a marker
        # - look at marker.orientation.rot_y and turn parallel with the marker (towards our corner)
        # - go forwards, checking every N metres that we're still parallel with the wall
        # - if we can see an arena marker in front of us, drive to 1.5 m from it and repeat/go home

        if marker is None:
            markers = sorted(self.see_markers(lambda m: m.info.marker_type == MARKER_ARENA), key=lambda m: ([walls.index(wall) for wall in walls if m.info.code not in wall][0] in (self.zone, (self.zone - 1) % 4), m.dist))  # Arena markers, sorted by whether they're on one of our walls and then by the closest (the first element will be the closest marker that's on one of our walls)
            marker = markers[0]
            self.log.debug("Fixating upon marker %s (%s metres away)", marker.info.code, marker.dist)
        else:
            self.log.info("Told to fixate upon marker %s (%s metres away)", marker.info.code, marker.dist)

        # Check that we can move.
        has_moved = False
        trying_to_move = True
        while (not has_moved) and trying_to_move:
            trying_to_move = True
            initial_markers = self.see_markers()
            self.wheels.turn(marker.rot_y)  # Face the marker
            # Find the marker again
            markers = self.see_markers(predicate=lambda m: m.info.code == marker.info.code)
            if not markers:
                self.log.error("We turned to the marker and now can't see it.")  # Don't move!
                return
            marker = markers[0]
            # This is the index in `walls` of the wall we fixated upon.
            orig_marker_wall = [walls.index(wall) for wall in walls if marker.info.code in wall][0]
            # Move to 1.5 metres away from the marker
            self.log.debug("Moving to 1.5 metres from the marker")
            if marker.dist > 1.55:
                self.move_continue(marker.dist - 1.5)
            else:
                self.log.debug("We're closer than we should be (%s metres)!", marker.dist)
                trying_to_move = False  # Otherwise we loop forever, since we never try to move.
            markers = self.see_markers(predicate=lambda m: m.info.code == marker.info.code)
            if not markers:
                self.log.error("We moved closer to the marker (maybe) and now can't see it. Moving backwards slightly and trying again.")
                self.wheels.move(-0.15, ignore_crash=True)
                continue
            final_markers = self.see_markers()
            has_moved = self.are_we_moving(initial_markers, final_markers)
            if not has_moved:
                self.log.error("We're stuck! Moving back slightly, then trying to move to the marker again forever, since there's nothing else we can do.")
                self.wheels.move(-0.15, ignore_crash=True)
            else:
                self.log.info("We're not stuck!")
        marker = markers[0]
        # Move to 1.5 metres away from the wall
        self.log.debug("Moving to 1.5 metres from the WALL")
        # 1.75 is the distance to wall plus half of robot width.
        dist = sqrt(1.75**2 + 1.75**2 - 2 * 1.75 * 1.75 * cosd(marker.orientation.rot_y))
        if marker.orientation.rot_y < 0:
            # turning right first, then left
            self.log.debug("Turning right first (marker.orientation.rot_y = %s)", marker.orientation.rot_y)
            angle = (180 - marker.orientation.rot_y) / 2
        else:
            # turning left first, then right
            self.log.debug("Turning left first (marker.orientation.rot_y = %s)", marker.orientation.rot_y)
            angle = (-180 - marker.orientation.rot_y) / 2
        self.log.debug("Going to turn %s, move %s, turn %s", angle, dist, -angle)
        self.log.debug("marker.dist is %s", marker.dist)
        self.wheels.turn(angle)
        self.move_continue(dist)
        self.wheels.turn(-angle)
        # TODO(jdh): make sure we're 1.5 metres away
        # We should now be 1.5 metres away from the wall, facing the marker head-on.
        markers = False
        while not markers:
            markers = self.cone_search(marker_id=marker.info.code)
            if not markers:
                self.log.error("Couldn't find the marker we fixated upon! Waiting and trying again -- hopefully whatever's in the way will move eventually.")
                time.sleep(2)
        marker = markers[0]
        self.wheels.turn(marker.rot_y)
        if marker.dist > 1.75:
            self.move_continue(marker.dist - 1.75)
        else:
            self.log.warn("We're closer than we should be! Not moving backwards, though.")  # since hopefully we still have some cubes...
        self.log.debug("We should now be 1.5 metres away from the wall and facing the marker head-on.")
        parallel_to_wall = False
        while not parallel_to_wall:
            markers = self.see_markers(predicate=lambda m: m.info.code == marker.info.code)
            if not markers:
                self.log.error("We moved to face the marker and now can't see it. Waiting and trying again -- hopefully we'll see it eventually.")
                time.sleep(2)
            marker = markers[0]
            # Turn parallel to the wall (see Slack for diagram, search "parallel to wall" in #brainstorming)
            if orig_marker_wall in (self.zone, (self.zone + 1) % 4):
                self.log.debug("Turning left (to have wall on right)")
                self.wheels.turn(-(90 - marker.orientation.rot_y))  # Turn left (wall on right, heading anticlockwise)
            else:
                self.log.debug("Turning right (to have wall on left)")
                self.wheels.turn(90 + marker.orientation.rot_y)  # Turn right (wall on left, heading clockwise)
            # We should now be facing along the wall. Check that we did actually turn:
            markers = self.see_markers(predicate=lambda m: m.info.code == marker.info.code)
            if markers:
                self.log.warn("We didn't manage to turn parallel to the wall, since the marker that should be next to us is in front of us (code %s)!", markers[0].info.code)
                self.wheels.move(-0.1, ignore_crash=True)
            else:
                self.log.debug("We're parallel to the wall, continuing on the way home.")
                parallel_to_wall = True
        # Look for wall markers that won't vanish on us and that aren't on the wall we're moving along.
        self.log.debug("Original wall (orig_marker_wall): %s", orig_marker_wall)
        markers = self.see_markers(predicate=lambda m: m.info.marker_type == MARKER_ARENA and m.dist <3 and m.info.code not in walls[orig_marker_wall])
        while not markers:
            self.log.debug("Can't see any matching wall markers (wall, close, not the wall we first saw), going forwards a bit.")
            self.move_continue(1)
            time.sleep(1)
            markers = self.see_markers(predicate=lambda m: m.info.marker_type == MARKER_ARENA and m.dist <3 and m.info.code not in walls[orig_marker_wall])
        marker = markers[0]
        self.log.debug("We see %s wall markers.", len(markers))
        self.log.debug("Checking if wall marker is on one of our walls (%s or %s, since we're in zone %s)", self.zone, (self.zone - 1) % 4, self.zone)
        if orig_marker_wall not in (self.zone, (self.zone - 1) % 4):
            # We started at a wall opposite our corner, go round again
            self.log.info("Recursing, since we need to go along another wall to get home. If this message appears more than once, something might be wrong.")
            # Pass ourselves a sensible marker.
            marker = sorted(markers, key=attrgetter("dist"))[0]
            self.move_home_from_other_A(marker=marker)
            self.log.info("Finished recursing, hopefully we're home now. Returning.")
            return
        self.log.debug("We should now be facing our corner.")
        markers = self.see_markers(predicate=lambda m: m.info.marker_type == MARKER_ARENA and m.info.code not in walls[orig_marker_wall])
        marker_codes = [m.info.code for m in markers]
        if our_markers.intersection(marker_codes):
            self.log.debug("We can see some of our corner markers! (These ones: %s)", our_markers.intersection(marker_codes))
            markers = [m for m in markers if m.info.code in our_markers.intersection(marker_codes)]
            # Get an inner marker if we can see one, but an outer marker will do.
            marker = sorted(markers, key=lambda m: (m.info.code in inner_markers, m.info.code in outer_markers))[-1]
            marker_wall = [walls.index(wall) for wall in walls if marker.info.code in wall][0]
            if marker.info.code in inner_markers:
                self.log.debug("Driving to 1 metre away from inner marker %s (on wall %s)", marker.info.code, marker_wall)
                self.wheels.turn(marker.rot_y)
                if marker.dist > 1:
                    self.move_continue(marker.dist - 1)
                else:
                    self.log.warn("Marker is only %s metres away, which is less than the expected 1 metre! We may not make it home...", round(marker.dist, 2))
                turn_to_corner = 45 if marker_wall == (self.zone - 1) % 4 else -45
                self.log.debug("Turning into the corner (%s degrees)", turn_to_corner)
                # Turn right if the marker is on the left of home, otherwise turn left.
                self.wheels.turn(turn_to_corner)
                self.move_continue(1.5)  # Go home.
                self.log.info("We should now be home!")
            elif marker.info.code in outer_markers:
                self.log.debug("Driving to 2 metres away from outer marker %s (on wall %s)", marker.info.code, marker_wall)
                self.wheels.turn(marker.rot_y)
                if marker.dist > 2:
                    self.move_continue(marker.dist - 2)
                else:
                    self.log.warn("Marker is only %s metres away, which is less than the expected 2 metres! We may not make it home...", round(marker.dist, 2))
                turn_to_corner = 45 if marker_wall == (self.zone - 1) % 4 else -45
                self.log.debug("Turning into the corner (%s degrees)", turn_to_corner)
                # Turn right if the marker is on the left of home, otherwise turn left.
                self.wheels.turn(turn_to_corner)
                self.move_continue(3)  # Go home.
                self.log.info("We should now be home!")
            else:
                self.log.error("We can see marker %s (on wall %s), but we don't know what to do with it!", marker.info.code, marker_wall)
        else:
            self.log.warn("We can't see any of our corner markers, but we should be able to (we see these: %s). We can't get home now!", marker_codes)
            # TODO(jdh): getting home from here

    def get_more_cubes(self):
        self.log.critical("##### THIS CODE SHOULD NEVER RUN #####")
        self.log.info("Going to get some more cubes!")
        self.move_continue(-1.5)
        self.move_continue(-1.5)
        self.wheels.turn(45)
        for _ in xrange(4):
            self.wheels.turn(90)
            self.log.debug("Finding cube markers.")
            markers = sorted(self.see_markers(predicate=lambda m: m.info.marker_type == MARKER_TOKEN_B and 1 < m.dist < 2), key=attrgetter("dist"))
            if markers:
                self.log.debug("We see a B cube, driving to it...")
                self.move_to_cube(markers[0], crash_continue=True)
            else:
                self.log.info("We can't see any B markers at the right distance :( Going to roughly where it should be.")
                self.move_continue(1.5)
            markers = sorted(self.see_markers(predicate=lambda m: m.info.marker_type == MARKER_TOKEN_A and 1 < m.dist < 2), key=attrgetter("dist"))
            if markers:
                self.log.debug("We see an A cube, driving to it...")
                self.move_to_cube(markers[0], crash_continue=True)
            else:
                self.log.info("We can't see any A markers at the right distance :( Going to roughly where it should be.")
                self.move_continue(1.5)
            self.log.debug("Turning round the corner...")
        self.wheels.turn(-45)
        self.log.info("Going home")
        self.move_home_from_A()
        self.log.info("Done getting more cubes.")

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
        markers = []
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

    def find_markers_approx_position(self, marker_type, dist, dist_tolerance=0.5):
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

    def cone_search(self, marker_type=None, marker_id=None, dist=None,
                    dist_tolerance=0.5, start_angle=-45, stop_angle=45, delta_angle=15):
        # type: (...) -> List[Marker]
        """Search for markers, turning from side to side.

        As soon as markers satisfying the passed criteria are found,
        this function exits and returns them.

        The order of this function's arguments is not stable. Callers
        should use keyword args only, never positional args.
        """
        self.log.info("Starting cone search (%s, %s, %s)...", start_angle, stop_angle, delta_angle)
        self.log.debug("Criteria:")
        self.log.debug("  type == %s", marker_type)
        self.log.debug("  ID == %s", marker_id)
        try:
            self.log.debug("  %s <= dist <= %s", dist - dist_tolerance, dist + dist_tolerance)
        except TypeError:
            self.log.debug("  dist == %s", dist)
        angles = [0, start_angle] + [delta_angle for _ in range(0, stop_angle - start_angle, delta_angle)]
        angle_turned = 0

        def predicate(marker):
            # type: (Marker) -> bool
            correct_type = marker_type is None or marker.info.marker_type == marker_type
            correct_id = marker_id is None or marker.info.code == marker_id
            correct_dist = dist is None or dist - dist_tolerance <= marker.dist <= dist + dist_tolerance
            return correct_type and correct_id and correct_dist

        for angle in angles:
            self.wheels.turn(angle)
            angle_turned += angle
            markers = self.see_markers(predicate)
            if markers:
                self.log.info("Found %s markers matching criteria, stopping search.", len(markers))
                return markers
            else:
                time.sleep(0.5)
        self.log.info("Found no markers matching criteria.")
        self.wheels.turn(-angle_turned)  # Turn back to where we were facing originally.
        return []

    def cone_search_approx_position(self, marker_type, dist, dist_tolerance=0.5, max_left=45, max_right=45, delta=15, sleep_time=0.5):
        # type: (...) -> list
        """
        Search for a specific marker type at an appproximate distance with tolerances
        outside of the visual range of the camera
        """
        self.log.info("Doing a cone based search with extremities (%s, %s) and delta %s for markers of type %s approximately %s metres away, give or take %s metres", max_left, max_right, delta, marker_type, dist, dist_tolerance)
        angles = [0, -max_left] + ([delta]*(((max_left + max_right) // delta) + 1))
        for angle in angles:
            self.wheels.turn(angle)
            markers = self.find_markers_approx_position(marker_type, dist, dist_tolerance)
            if markers:
                self.log.info("Finished marker type cone search and found %s markers of type %s", len(markers), marker_type)
                return markers
            time.sleep(sleep_time)
        self.wheels.turn(-max_right)  # close enough
        self.log.info("Finished marker type cone search with no markers found")
        return []

    def cone_search_specific_marker(self, marker_id, max_left=45, max_right=45, delta=15, sleep_time=0.5):
        # type: (...) -> list
        """
        Search for a specific marker outside of the visual range of the camera
        """
        self.log.info("Doing a cone based search with extremities (%s, %s) and delta %s for a marker (id %s)", max_left, max_right, delta, marker_id)
        angles = [0, -max_left] + ([delta]*(((max_left + max_right) // delta) + 1))
        for angle in angles:
            self.wheels.turn(angle)
            markers = self.see_markers(predicate=lambda marker: marker.info.code == marker_id)
            if markers:
                self.log.info("Finished specific marker cone search and found %s markers of id %s", len(markers), marker_id)
                return markers
            time.sleep(sleep_time)
        self.wheels.turn(-max_right)  # close enough
        self.log.info("Finished specific marker cone search with no markers found")
        return []

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

    def was_a_triumph(self):
        """
        It was
        """
        self.power.beep(250, frequency=392) # G4
        self.power.beep(250, frequency=370) # F#4
        self.power.beep(250, frequency=330) # E4
        self.power.beep(250, frequency=330) # E4
        self.power.beep(1, frequency=370)   # F#4


if __name__ == "__main__":
    CompanionCube()
