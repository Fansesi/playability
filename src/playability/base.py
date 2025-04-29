from pretty_midi import PrettyMIDI
from typing import List, Dict, Optional, Union, Callable, Tuple
from pathlib import Path, PosixPath
import numpy as np
from loguru import logger as lg

from .constants import ERROR_TYPES, THRESHOLDS
from .utils import create_finger_positions
from .config import ErrorDist, Thresholds


class BaseInstrumentPlayer:
    """
    ## Description
    Base class for instruments. Instruments should inherit from this class
    and use the initialized variables here.

    ## Params:
    * `MIDIFile`: a PrettyMIDI object or a path of the .mid file to process.
    * `finger_positions`: finger positions. Should be imemented in the inherited
    class.
    * `error_distribution`: Distribution of error rates.
    * `thresholds`: Threshold for various errors. Please check THRESHOLDS.
    * `edge_handlers`: List of functions for various edge cases. Please check
    create_optimal_note_locations function for more details.
    """

    def __init__(
        self,
        MIDIFile: Union[PrettyMIDI, Union[str, Path]],
        finger_positions: Dict[int, List[int]] = None,
        error_distribution: Optional[ErrorDist] = None,
        thresholds: Optional[Thresholds] = None,
        edge_handlers: Optional[List[Callable]] = None,
    ) -> None:

        if not error_distribution:
            self.error_distribution = ErrorDist.for_guitar()
        else:
            self.error_distribution = error_distribution

        if not thresholds:
            self.thresholds = Thresholds.for_guitar()
        else:
            self.thresholds = thresholds

        self.finger_positions = finger_positions
        self.MAX_PITCH = max(list(self.finger_positions.keys()))
        self.MIN_PITCH = min(list(self.finger_positions.keys()))

        # Edge handlers are used in `self.create_optimal_note_locations`.
        # There might be unique edge cases for different instruments.
        # These edge handlers should return the cleaned data.
        self.edge_handlers = edge_handlers

        self.number_of_strings: int = len(
            self.finger_positions[list(self.finger_positions.keys())[0]]
        )

        self.midi_file = (
            PrettyMIDI(str(MIDIFile))
            if isinstance(MIDIFile, (str, Path, PosixPath))
            else MIDIFile
        )

        # Number of an errors occurence.
        # {"duplicate_notes": [x_many, total_time]}
        self.errors_numbers: Dict[str, List[Tuple[int, float]]] = (
            self.error_distribution.init_error_dict()
        )

        # Rate of of the errors. Will be calculated in post_init() based on
        # self.errors_numbers
        self.errors_rates: Dict[str, float] = self.error_distribution.init_error_dict()

        # Independent from self.finger_positions
        self.times_pitches = self.create_times_pitches(self.midi_file)
        self._remove_duplicate_notes()
        self._transpose_piece()

        # Hand position for each time step.
        # It's calculated as the average of the furthest notes.
        self.hand_position: List[float] = [-1.0]

        # Find the most optimal fingerings on finger_positions.
        self.time_note_locations: Dict[Tuple[float, float], List[List[int]]] = (
            self.create_optimal_note_locations()
        )

        # Hand velocities is calculated as the speed of hand while
        # moving from position to another. Will be calculated in post_init().
        self.hand_velocities: List[float] = []

        # Will be finalized in post_init().
        self.playability_rate = 100

    def post_init(self):
        """After finishing up the main specialized classes, this function should
        be called to fill up the following datas:
        * `finalize_notes()`: uses `self.times_pitches`, `self.finger_positions`
        and to create `time_note_locations`.
        DEPRECEATED.
        * `_post_process_hand_positions()`: uses `self.hand_positions` and
        `self.time_note_locations`.
        * `_calculate_hand_velocity()`: uses `self.hand_positions` and sets
        `self.hand_velocities`.
        * `_calculate_error_types_rates()`: uses `self.errors_numbers`.

        TODO: Decide on what to put to post_init(). Maybe just the error rates?
        """
        self._post_process_hand_positions()
        self._calculate_hand_velocity()
        self._calculate_hand_speed_error()
        self._calculate_max_number_of_notes()

        self._calculate_error_types_rates()
        self.calculate_final_playabilty()

    def create_optimal_note_locations(self):
        """
        ### Description
        Tries to find the most optimal note locations for each time step.
        Uses `self.time_pitches`.
        """

        time_bestlocs_dict = self.times_pitches.copy()
        for start_end_times, pitch_values in time_bestlocs_dict.items():
            if pitch_values == []:
                # means rest
                self.update_hand_pos(pos=[], is_rest=True)
                continue

            merged_lists = self._create_possible_places(pitch_values)

            if merged_lists == []:
                if self.edge_handlers != None:
                    for func in self.edge_handlers:
                        merged_lists = func(pitch_values)
                else:
                    lg.warning("You should probably create some edge handlers.")

            # If merged_lists still empty after these, just remove them by using np.unique
            # if merged_lists == []:
            #     notes = np.unique(notes)
            #     merged_lists = self._create_possible_places(notes)

            time_bestlocs_dict[start_end_times] = self.L2(merged_lists)

        return time_bestlocs_dict

    def L2(self, pos: List[List[int]], open_string_first: bool = True) -> List[int]:
        """
        ## Notes:
        * While calculating the fret error I'm not considering the times.
        Only the number a.t.m.
        """
        if pos == []:
            # TODO: try to catch every edge case.
            lg.error("Well, pos=[] again...")
            self.update_error("impossible_to_play", [1, 0.0])
            self.update_hand_pos([], True)
            return []

        if len(pos) == 1:
            self.update_hand_pos(pos[0])
            return pos[0]

        # I'm not going for the open stringed first approach this time.
        # TODO: Might be an parameter though?

        note_distances = []
        possible_hand_positions = []

        for position in pos:
            indices, elements = self._valid_idxs_elems(position)
            if elements == [0] and open_string_first:
                max_fret, min_fret = 0, 0
            else:
                max_fret, min_fret = self._maxmin_nonzero(elements)
            note_distances.append(max_fret - min_fret)
            possible_hand_positions.append((max_fret + min_fret) / 2)

        if min(note_distances) > self.thresholds.fret_thresholds:
            self.update_error("max_fret", [1, 0.0])

        min_dist_indices = []
        for index, elem in enumerate(note_distances):
            if elem == min(note_distances):
                min_dist_indices.append(index)

        if self.hand_position == [-1]:
            min_hand_index = possible_hand_positions.index(min(possible_hand_positions))
            self.update_hand_pos(pos[min_hand_index])
            return pos[min_hand_index]

        for index in min_dist_indices:
            if (
                abs(possible_hand_positions[index] - self.hand_position[-1])
                < self.thresholds.hand_movement_threshold
            ):  # good case
                self.update_hand_pos(pos[index])
                return pos[index]

        self.update_error("max_hand_movement", [1, 0.0])

        # if new hand position will be too far from the last hand position, increase the fret_threshold minimally
        # getting the indices of not the minimals but minimals + min_value
        min2_dist_indices = []
        for i, distance in enumerate(sorted(note_distances)):
            if distance == min(note_distances):
                pass
            else:
                min2_dist_indices.append(i)

        for index in min2_dist_indices:
            if (
                abs(possible_hand_positions[index] - self.hand_position[-1])
                < self.thresholds.hand_movement_threshold
            ):  # kinda-good case
                self.update_hand_pos(pos[index])
                return pos[index]

        # if the problem persist we look at all the min fret positions and take the one which has the minimum distance
        # from the previous hand position

        min_hand_distances = []
        for index in min_dist_indices:
            min_hand_distances.append(
                abs(self.hand_position[-1] - possible_hand_positions[index])
            )

        min_hand_index = min_hand_distances.index(min(min_hand_distances))
        self.update_hand_pos(pos[min_hand_index])
        return pos[min_hand_index]

    def update_hand_pos(self, pos: List[int], is_rest: bool = False):
        """Updates the hand position. Averages the positions of the notes played on the guitar.
        If is_rest=True, appends the last element of the self.hand_position. This parameter can be used
        by open strings first approach as well (we don't change hand position while playing only open strings.)
        """
        if is_rest == True:  # This means we are at rest
            self.hand_position.append(
                self.hand_position[-1]
            )  # Our hand position stays the same at this time_step
        else:
            indices, elements = self._valid_idxs_elems(pos)
            # Here if the min element of the hand position is 0 we don't consider that.
            # But if it's all open string, we keep the same hand position.
            if all(num == 0 for num in elements):
                self.hand_position.append(self.hand_position[-1])
            else:
                # Too lazy to write a function for this. Numpy does it great!
                elements = np.array(elements)
                nonzero_min = np.min(elements[np.nonzero(elements)])
                self.hand_position.append((nonzero_min + max(elements)) / 2)

    def _create_possible_places(self, notes: List[int]):
        container_list: List[List[List[int]]] = []

        for pitch in notes:
            container_list.append(
                self._create_note_on_string(self.finger_positions[pitch])
            )
        return self._merge_lists(container_list)[0]

    def _create_note_on_string(self, pitch_repr: List[int]) -> List[List[int]]:
        """Processes the data on self.guitar_strings to create the notes on single string.
        E.g. [-1, -1, 21, 16,TO 12, 7] => [[-1,-1,-1,21,-1,-1],[-1,-1,-1,-1,16,-1], ...]
        ## Params
        * pitch_repr pitch representation on the guitar just like stated above.

        ## Returns
        List[List[], List[], ...]
        """
        base_repr = [-1, -1, -1, -1, -1, -1]
        final_list = []

        indices, elements = self._valid_idxs_elems(pitch_repr)

        for i in range(len(indices)):
            base_repr_copy = base_repr.copy()
            base_repr_copy.pop(indices[i])
            base_repr_copy.insert(indices[i], elements[i])
            final_list.append(base_repr_copy)

        return final_list

    def _merge_lists(self, list_of_lists: List[List[List[int]]]):
        """With the help of merge_two_lists() method, this method merges multiple lists. list_of_lists param may include more than two lists
        which each inner lists indicates the single notes' places and the outer list indicates this process for all notes.
        I'm checking the problem of being in the same string in this method rather than in the merge_two_lists().
        Also we need to look at the situation where there is only 1 note.
        """

        # list_of_lists shouldn't be 1. That case should be handled in iterate_notes()
        # lg.debug(list_of_lists)
        # assert len(list_of_lists) != 1

        list_of_lists2 = list_of_lists.copy()
        # lg.info(f"Length of the list_of_lists: {len(list_of_lists2)}")

        while len(list_of_lists2) >= 2:
            list1: List[List[int]] = list_of_lists2[0]
            list2: List[List[int]] = list_of_lists2[1]
            list_merged = []

            for elem1 in list1:
                ind1, elements1 = self._valid_idxs_elems(elem1)
                for elem2 in list2:
                    ind2, elements2 = self._valid_idxs_elems(elem2)
                    if self._check_occurence(ind1, ind2):
                        # if there are occurence between two index lists this means
                        # they are on the same string. So continue the loop without adding them the main merged_list.
                        continue
                    else:
                        list_merged.append(self._merge_two_lists([elem1, elem2]))

            # remove the first and second list to add their merged one.
            list_of_lists2 = list_of_lists2[2:]
            list_of_lists2.insert(0, list_merged)

        # np is totally cool with this edge case though.
        return np.unique(list_of_lists2, axis=-2).tolist()

    def _merge_two_lists(self, list_of_lists: List[List[int]]):
        """Merges two lists like [-1, -1, -1, -1, 12, -1, -1], [-1, -1, -1, -1, 7, -1] => [-1, -1, -1, -1, 12, 7, -1]
        We are not considering the intersection here.
        Note: I'm going to merge the two then create one then merge another one with the created one and so on. With this approach
        I'll iterate all the possibilities while obeying the rules of not playing two notes at the same time on a single string.
        """

        if len(list_of_lists) != 2:
            lg.critical(
                "Number of lists to merge should be 2. Please provide List[List[int], List[int]] as list_of_lists parameter."
            )
            raise Exception

        base_repr = [-1, -1, -1, -1, -1, -1]
        ind1, elem1 = self._valid_idxs_elems(list_of_lists[0])
        ind2, elem2 = self._valid_idxs_elems(list_of_lists[1])

        base_repr = self._iterate_insertion(base_repr, ind1, elem1)
        base_repr = self._iterate_insertion(base_repr, ind2, elem2)

        return base_repr

    def create_times_pitches(
        self, mid: PrettyMIDI
    ) -> Dict[Tuple[float, float], List[int]]:
        """Structure is as follows: [[4,5,9], [15], [2], [14], ...].
        Each list indicates the created time_interval and inner integers are the
        pitches presence in that time_interval. The algorithm is iterated at
        each time step."""

        # we should be creating the intervals like this: [[start, min]]
        note_start_ends_randomized = []
        for note in mid.instruments[0].notes:
            if note.start not in note_start_ends_randomized:
                note_start_ends_randomized.append(note.start)
            if note.end not in note_start_ends_randomized:
                note_start_ends_randomized.append(note.end)

        min_intervals = {}  # every little interval we wish to look for

        # sort the times (both starts and ends)
        note_times = sorted(note_start_ends_randomized)

        for i in range(len(note_start_ends_randomized) - 1):
            # initializing the dictionary
            min_intervals[(note_times[i], note_times[i + 1])] = 0

        for time1, time2 in min_intervals.keys():
            tmp_pitches = []
            # lg.info(f"time1: {time1}, time2: {time2}")
            for note in mid.instruments[0].notes:
                if time1 >= note.start and time2 <= note.end:
                    tmp_pitches.append(note.pitch)
                else:
                    pass

                min_intervals[(time1, time2)] = tmp_pitches

        # E.g. :{(start, min_0): [65,71], (min_1, min_2): [34, 7, 8, 9]]}
        return min_intervals

    def _calculate_error_types_rates(self):
        """Calculatese `error_types_rates` using `self.errors_numbers`."""
        _number_of_notes = len(self.times_pitches)

        for element in list(self.errors_numbers.keys()):
            if not self.errors_numbers[element]:
                continue
            total_error = 0
            is_counted_error = False
            for num, time in self.errors_numbers[element]:
                if time != 0:
                    # then this is hand threshold errors or
                    # other errors that are only counted and
                    # the time elapsed doesn't matter.
                    is_counted_error = True
                    total_error += num
                else:
                    # then time does matter and we should
                    total_error += num * time

            if is_counted_error:
                self.errors_rates[element] = total_error / _number_of_notes
            else:
                self.errors_rates[element] = total_error / (
                    _number_of_notes * self.midi_file.get_end_time()
                )

    def _post_process_hand_positions(self) -> None:
        """It's still possible to move the hand while resting.
        TODO: Implement this and it's error rate."""

        return

    def show_stats(
        self,
        time_step: bool = False,
        hand: bool = False,
        vel: bool = False,
        nb_errors: bool = False,
        rates_errors: bool = True,
    ) -> None:
        """
        ### Description:
        Shows statistics about the created variables.

        ### Params:
        * `time_step`: show `self.time_note_locations`.
        * `hand`: show `self.hand_position`.
        * `vel`: show `self.hand_velocities`.
        * `nb_errors`: show `error_types_numbers`.
        * `rates_errors`: show `error_types_rates`.
        """
        if time_step:
            lg.info("self.time_note_locations data is:")
            for i in self.time_note_locations:
                print(i)
        if hand:
            lg.info(f"Hand position data is: \n{self.hand_position}")
        if vel:
            lg.info(f"Hand velocity data is: \n{self.hand_velocities}")
        if nb_errors:
            lg.info("Number of errors:")
            for error in self.errors_numbers:
                lg.info(f"{error}: {self.errors_numbers[error]}")
        if rates_errors:
            lg.info("Rates of errors:")
            for error in self.errors_rates:
                lg.info(f"{error}: {self.errors_rates[error]}")
        lg.info(f"Playability: {self.playability_rate}")

    def _calculate_hand_velocity(self) -> List[float]:
        """Calculates the speed of hand while moving from position to position.
        Uses `self.hand_position`,`self.time_note_locations`

        ### Returns
        A list containing the fret/sec of each inbetween-time-step (`i` and `i+1` where `i=0,1,...`)

        ### Notes
        When the duration_between_pos is 0, we set it to 0.1 secs. This way the hand
        velocity doesn't fluctuate much.
        """
        velocities = []

        # If self.hand_position is not calculated yet, only create the hand_velocity variable.

        for i in range(1, len(self.hand_position) - 1):
            # I hate to access these like this but it's the way to go.
            duration_between_pos = (
                list(self.time_note_locations.keys())[i][0]
                - list(self.time_note_locations.keys())[i - 1][1]
            )
            if duration_between_pos == 0:
                duration_between_pos = 0.1  # 0.1 sec = 100 ms
            velocities.append(
                abs(self.hand_position[i] - self.hand_position[i + 1])
                / duration_between_pos
            )

        self.hand_velocities = velocities

        return velocities

    def _calculate_hand_speed_error(self):
        r"""
        ### Description:
        Calculates hand velocity errors. Uses `self.hand_velocity`.

        ### Returns:
        * None. But creates and fills the `max_hand_speed` in the `self.errors_numbers`.
        """
        for i, speed in enumerate(self.hand_velocities):
            if speed > self.thresholds.speed_threshold:
                duration_between_pos = (
                    list(self.time_note_locations.keys())[i][0]
                    - list(self.time_note_locations.keys())[i - 1][1]
                )
                self.update_error("max_hand_speed", [1, duration_between_pos])

    def update_error(self, error_type: str, value: Tuple[int, float]):
        """Given error type, increase the corresponding value of it in the `self.errors_numbers`"""
        # if error_type in list(self.errors_numbers.keys()):
        if self.errors_numbers[error_type]:
            self.errors_numbers[error_type].append(value)
        else:
            # first initialization
            self.errors_numbers[error_type] = [value]

    def calculate_final_playabilty(self):
        r"""
        ### Description:

        Calculates `self.playability`. Uses `self.errors_rates`.

        ### Returns:
        * Sets `self.playability`."""

        for v in self.errors_rates.values():
            if v:
                self.playability_rate -= v

        return self.playability_rate

    def _transpose_note(
        self, note_pitch: int, pitch_range: List[int] = [40, 85]
    ) -> Tuple[int, bool]:
        """Given a note pitch, increase or decrese the pitch by 12 until it falls between possible pitch_range
        :Params:
        :note_pitch: pitch value to work on.
        :pitch_range: pitch range to work on. [min_pitch, max_pitch]

        Returns:
        (transposed_pitch, True)
        (not_transposed_pitch, False) already between the interval.
        """

        if note_pitch < pitch_range[0]:  # smaller than
            if (pitch_range[0] - note_pitch) % 12 == 0:
                return (pitch_range[0], True)
            else:
                return (
                    note_pitch + 12 * (1 + ((pitch_range[0] - note_pitch) // 12)),
                    True,
                )

        elif note_pitch > pitch_range[1]:  # greater than
            if (note_pitch - pitch_range[1]) % 12 == 0:
                return (pitch_range[1], True)
            else:
                return (
                    note_pitch - 12 * (1 + ((note_pitch - pitch_range[1]) // 12)),
                    True,
                )

        else:  # it falls between the range
            return (note_pitch, False)

    def _transpose_piece(self) -> None:
        """Tranpose pitches that are greater than the max pitch and
        less than the min pitch to nearest possible octave. Uses `self.times_pitches`.
        Updates the `max_min_pitch` accordingly."""

        for i, (start_time, end_time) in enumerate(self.times_pitches):
            for pitch_pos, pitch in enumerate(list(self.times_pitches.values())[i]):
                new_pitch, is_tranposed = self._transpose_note(
                    pitch, [self.MIN_PITCH, self.MAX_PITCH]
                )
                if is_tranposed:
                    self.update_error("max_min_pitch", [1, end_time - start_time])
                    self.times_pitches[(start_time, end_time)][pitch_pos] = new_pitch

    def _calculate_max_number_of_notes(self):
        """Calculates the error of maximum number of notes in a time step.
        Uses `self.times_pitches`. Updates the `max_number_of_notes` accordingly.
        """

        for start_end_times, pitch_values in self.times_pitches.items():
            if len(pitch_values) > self.number_of_strings:
                self.update_error(
                    "max_number_of_notes",
                    [
                        len(pitch_values) - self.number_of_strings,
                        start_end_times[1] - start_end_times[0],
                    ],
                )

    def _remove_duplicate_notes(self):
        """Removes the duplicates notes. Uses `self.times_pitches`."""

        for start_end_times, pitch_values in self.times_pitches.items():
            # Removing duplicates
            original_notes, nb_duplicates = self._find_duplicates(pitch_values)
            if nb_duplicates == 0:
                continue

            self.times_pitches[start_end_times] = original_notes

            self.update_error(
                "duplicate_notes",
                [nb_duplicates, start_end_times[1] - start_end_times[0]],
            )

            # If the problem persists, take the highest pitches.
            if len(original_notes) > self.number_of_strings:
                self.times_pitches[start_end_times] = sorted(
                    original_notes, reverse=True
                )[: self.number_of_strings - 1]

    @staticmethod
    def _find_duplicates(a_list: List[int]):
        """Given a list, finds the number of same elements and remove that from list.

        ## Returns
        Cleaned list and number of duplicates (not counting the original)."""

        originals = []
        nb_duplicates = 0
        for elem in a_list:
            if elem not in originals:
                originals.append(elem)
            else:
                nb_duplicates += 1

        return originals, nb_duplicates

    @staticmethod
    def _iterate_insertion(base: List[int], ind: List[int], elems: List[int]):
        """Iterate the insertion process over multiple indexes and elements."""

        assert len(ind) == len(elems)

        for i in range(len(ind)):
            base.pop(ind[i])
            base.insert(ind[i], elems[i])

        return base

    @staticmethod
    def _check_occurence(list1: List[int], list2: List[int]) -> bool:
        """Checks whether there are any occurrence between two List[int].
        If occurrence exists returns `True`, otherwise `False`"""
        for i in list1:
            if i in list2:
                return True

        return False

    @staticmethod
    def _valid_idxs_elems(a_list: List[int]) -> Tuple[List[int], List[int]]:
        """Returns the index of the element which is not -1 in a list shaped like
        [-1, -1, -1, -1, 12, -1, -1] and the element itself."""
        index = [-1]
        element = [-1]
        for i, elem in enumerate(a_list):
            if elem != -1:
                if -1 in index and -1 in element:
                    # All these -1 stuff because I don't want to mess up with
                    # the Tuple[List[int], List[int]] with optionals
                    index.remove(-1)
                    element.remove(-1)
                index.append(i)
                element.append(elem)

        # I'm even putting this statement here to show something like this never
        # going to happen
        assert index != [-1]

        return index, element

    @staticmethod
    def _maxmin_nonzero(a_list: List[int]):
        """Returns the max and min elements which are nonzero of a list respectively."""

        a_list2 = a_list.copy()
        for i in a_list2:
            if i == 0:
                a_list2.remove(0)
            elif i == -1:
                a_list2.remove(-1)
            else:
                continue

        return max(a_list2), min(a_list2)
