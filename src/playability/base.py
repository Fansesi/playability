from pretty_midi import PrettyMIDI
from typing import List, Dict, Optional, Union, Callable, Tuple
from pathlib import Path, PosixPath
from loguru import logger as lg
from collections import defaultdict

from .config import ErrorDist, Thresholds


class BaseInstrumentPlayer:
    """
    Base class for instruments that processes MIDI files to determine playability.

    Instruments should inherit from this class and implement instrument-specific logic.

    Parameters:
        midi_file: A PrettyMIDI object or path to a .mid file to process
        finger_positions: Dictionary mapping pitch to possible positions on the instrument
        error_distribution: Distribution of error rates
        thresholds: Threshold values for various error types
        edge_handlers: Functions to handle edge cases when notes can't be placed
    """

    def __init__(
        self,
        midi_file: Union[PrettyMIDI, Union[str, Path]],
        finger_positions: Dict[int, List[int]] = None,
        error_distribution: Optional[ErrorDist] = None,
        thresholds: Optional[Thresholds] = None,
        edge_handlers: Optional[List[Callable]] = None,
    ) -> None:
        # Initialize configurations
        self.error_distribution = error_distribution or ErrorDist.for_guitar()
        self.thresholds = thresholds or Thresholds.for_guitar()
        self.finger_positions = finger_positions
        self.edge_handlers = edge_handlers

        # Validate finger positions
        if not self.finger_positions:
            raise ValueError("finger_positions must be provided")

        # Get instrument constraints
        self.MAX_PITCH = max(self.finger_positions.keys())
        self.MIN_PITCH = min(self.finger_positions.keys())
        self.number_of_strings = len(
            self.finger_positions[next(iter(self.finger_positions))]
        )

        # Load MIDI data
        self.midi_file = (
            PrettyMIDI(str(midi_file))
            if isinstance(midi_file, (str, Path, PosixPath))
            else midi_file
        )

        # Initialize tracking variables
        # E.g. {"duplicate_notes": [x_many, total_time]}
        self.errors_numbers = defaultdict(list)
        self.errors_rates = {}
        self.hand_position = [-1.0]  # Starting hand position
        self.hand_velocities = []
        self._problematic_times = []
        self.playability_rate = 100.0

        # Process MIDI data
        self.times_pitches = self._extract_time_pitches()
        self._remove_duplicate_notes()
        self._transpose_piece()

        # Generate optimal note placements
        self.time_note_locations = self._create_optimal_note_locations()

        # Finalize processing
        self.post_init()

    def post_init(self) -> None:
        """
        Finalize processing after base initialization.

        This should be called after completing specialized instrument class setup.
        """
        self._post_process_hand_positions()
        self._calculate_hand_velocity()
        self._calculate_hand_speed_error()
        self._calculate_error_rates()
        self._calculate_playability()
        self._post_process_time_note_locations()

    def _extract_time_pitches(self) -> Dict[Tuple[float, float], List[int]]:
        """
        Extract pitch data organized by time intervals from the MIDI file.

        Returns:
            Dictionary mapping time intervals to lists of pitches active during that interval
        """
        # Collect all unique start and end times
        time_points = set()
        for note in self.midi_file.instruments[0].notes:
            time_points.add(note.start)
            time_points.add(note.end)

        time_points = sorted(time_points)
        intervals = {}

        # For each time interval, find active notes
        for i in range(len(time_points) - 1):
            start_time, end_time = time_points[i], time_points[i + 1]
            interval = (start_time, end_time)
            active_pitches = []

            for note in self.midi_file.instruments[0].notes:
                if note.start <= start_time and note.end >= end_time:
                    active_pitches.append(note.pitch)

            intervals[interval] = active_pitches

        return intervals

    def _remove_duplicate_notes(self) -> None:
        """Remove duplicate pitches from each time interval."""
        for interval, pitches in list(self.times_pitches.items()):
            if not pitches:
                continue

            # Use set to efficiently remove duplicates
            unique_pitches = list(set(pitches))
            num_duplicates = len(pitches) - len(unique_pitches)

            if num_duplicates > 0:
                duration = interval[1] - interval[0]
                self.update_error("duplicate_notes", [num_duplicates, duration])
                self.times_pitches[interval] = unique_pitches

                # If we still have too many notes, keep only the highest ones
                if len(unique_pitches) > self.number_of_strings:
                    self.times_pitches[interval] = sorted(unique_pitches, reverse=True)[
                        : self.number_of_strings
                    ]
                    self.update_error(
                        "max_number_of_notes",
                        [len(unique_pitches) - self.number_of_strings, duration],
                    )

    def _transpose_piece(self) -> None:
        """
        Transpose notes that fall outside the instrument's pitch range.

        Notes are shifted by octaves to bring them within the playable range.
        """
        for interval, pitches in list(self.times_pitches.items()):
            duration = interval[1] - interval[0]
            transposed = False

            for i, pitch in enumerate(pitches):
                if pitch < self.MIN_PITCH or pitch > self.MAX_PITCH:
                    # Calculate octave shift
                    if pitch < self.MIN_PITCH:
                        octaves_up = ((self.MIN_PITCH - pitch - 1) // 12) + 1
                        new_pitch = pitch + (12 * octaves_up)
                    else:  # pitch > self.MAX_PITCH
                        octaves_down = ((pitch - self.MAX_PITCH - 1) // 12) + 1
                        new_pitch = pitch - (12 * octaves_down)

                    # Ensure we're not going out of bounds
                    new_pitch = min(max(new_pitch, self.MIN_PITCH), self.MAX_PITCH)

                    pitches[i] = new_pitch
                    transposed = True

            if transposed:
                self.update_error("max_min_pitch", [1, duration])
                self.times_pitches[interval] = pitches

    def _create_optimal_note_locations(
        self,
    ) -> Dict[Tuple[float, float], List[List[int]]]:
        """
        Find optimal positions for notes on the instrument for each time interval.

        Returns:
            Dictionary mapping time intervals to optimal note positions
        """
        result = {}

        for interval, pitches in self.times_pitches.items():
            if not pitches:
                # Rest - maintain hand position
                self.update_hand_pos([], is_rest=True)
                result[interval] = []
                continue

            # Check if we have too many notes for our instrument
            if len(pitches) > self.number_of_strings:
                pitches = pitches[: self.number_of_strings]
                self.update_error(
                    "max_number_of_notes",
                    [len(pitches) - self.number_of_strings, interval[1] - interval[0]],
                )

            # Find possible placements for this set of notes
            placements = self._generate_placements(pitches)

            # Handle when no valid placements are found
            if not placements:
                if self.edge_handlers:
                    for handler in self.edge_handlers:
                        placements = handler(pitches)
                        if placements:
                            break

                if not placements:
                    self._problematic_times.append(interval)
                    self.update_error(
                        "impossible_to_play", [1, interval[1] - interval[0]]
                    )
                    self.update_hand_pos([], True)
                    result[interval] = []
                    continue

            # Select best placement based on hand position
            best_placement = self._select_optimal_placement(placements)
            result[interval] = best_placement

        return result

    def _generate_placements(self, pitches: List[int]) -> List[List[int]]:
        """
        Generate all possible placements for a set of pitches.

        Parameters:
            pitches: List of pitch values to place on the instrument

        Returns:
            List of possible placement combinations, each represented as a list
        """
        if not pitches:
            return []

        # Get all possible positions for each pitch
        position_options = []
        for pitch in pitches:
            if pitch not in self.finger_positions:
                return []  # Pitch can't be played on this instrument

            positions = self.finger_positions[pitch]
            string_positions = []

            # Create placement options for each string that can play this note
            for string_idx, fret in enumerate(positions):
                if fret != -1:  # -1 indicates note can't be played on this string
                    placement = [-1] * self.number_of_strings
                    placement[string_idx] = fret
                    string_positions.append(placement)

            position_options.append(string_positions)

        # If any pitch has no placement options, return empty list
        if any(not options for options in position_options):
            return []

        # Combine options ensuring no string conflicts
        return self._combine_placements(position_options)

    def _combine_placements(
        self, position_options: List[List[List[int]]]
    ) -> List[List[int]]:
        """
        Recursively combine position options ensuring no string conflicts.

        Parameters:
            position_options: List of placement options for each pitch

        Returns:
            List of valid combined placements
        """
        # Base case: if we have options for only one pitch
        if len(position_options) == 1:
            return position_options[0]

        result = []
        first_options = position_options[0]

        # Recursively combine the remaining options
        remaining_combinations = self._combine_placements(position_options[1:])

        # Try combining each first option with each remaining combination
        for first_option in first_options:
            first_strings = {i for i, fret in enumerate(first_option) if fret != -1}

            for combination in remaining_combinations:
                combination_strings = {
                    i for i, fret in enumerate(combination) if fret != -1
                }

                # Check for string conflicts
                if not first_strings.intersection(combination_strings):
                    # Combine the placements
                    new_placement = [-1] * self.number_of_strings
                    for i, fret in enumerate(first_option):
                        if fret != -1:
                            new_placement[i] = fret

                    for i, fret in enumerate(combination):
                        if fret != -1:
                            new_placement[i] = fret

                    result.append(new_placement)

        return result

    def _select_optimal_placement(self, placements: List[List[int]]) -> List[int]:
        """
        Select the optimal placement based on hand position and comfort.

        Parameters:
            placements: List of possible placement options

        Returns:
            The optimal placement
        """
        if not placements:
            return []

        if len(placements) == 1:
            self.update_hand_pos(placements[0])
            return placements[0]

        # Calculate fret spans for each placement
        placement_metrics = []
        for placement in placements:
            frets = [
                fret for fret in placement if fret > 0
            ]  # Ignore -1 and 0 (open string)

            if not frets:
                # Only open strings
                span = 0
                hand_pos = self.hand_position[-1]  # Keep current hand position
            else:
                span = max(frets) - min(frets)
                hand_pos = (max(frets) + min(frets)) / 2

            placement_metrics.append(
                {
                    "placement": placement,
                    "span": span,
                    "hand_pos": hand_pos,
                    "distance": abs(hand_pos - self.hand_position[-1]),
                }
            )

        # First, filter by span (prefer smaller spans)
        min_span = min(m["span"] for m in placement_metrics)
        span_threshold = self.thresholds.fret_thresholds

        if min_span > span_threshold:
            self.update_error("max_fret", [1, 0.0])

        # Filter placements with acceptable spans
        acceptable_span = min_span * 1.2  # Allow some flexibility
        span_candidates = [m for m in placement_metrics if m["span"] <= acceptable_span]

        if not span_candidates:
            span_candidates = placement_metrics

        # Now find the placement that minimizes hand movement
        movement_threshold = self.thresholds.hand_movement_threshold
        movement_candidates = [
            m for m in span_candidates if m["distance"] <= movement_threshold
        ]

        if movement_candidates:
            # Best placement is the one with minimum distance
            best = min(movement_candidates, key=lambda m: m["distance"])
        else:
            # No placement within movement threshold
            self.update_error("max_hand_movement", [1, 0.0])
            best = min(span_candidates, key=lambda m: m["distance"])

        self.update_hand_pos(best["placement"])
        return best["placement"]

    def update_hand_pos(self, pos: List[int], is_rest: bool = False) -> None:
        """
        Update the hand position based on the current note placement.

        Parameters:
            pos: Current note placement
            is_rest: Whether this is a rest period
        """
        if is_rest or not pos:
            # For rests, maintain current hand position
            self.hand_position.append(self.hand_position[-1])
            return

        # Filter out non-playing positions (-1) and open strings (0)
        frets = [fret for fret in pos if fret > 0]

        if not frets:
            # All open strings or no-play positions
            self.hand_position.append(self.hand_position[-1])
        else:
            # Hand position is the average of min and max played frets
            self.hand_position.append((min(frets) + max(frets)) / 2)

    def _calculate_hand_velocity(self) -> None:
        """
        Calculate hand velocity between consecutive positions.

        Velocities are measured in frets per second.
        """
        self.hand_velocities = []

        if len(self.hand_position) < 3:
            return

        intervals = list(self.time_note_locations.keys())

        for i in range(1, len(self.hand_position) - 1):
            # Ensure we have valid interval data
            if i - 1 >= len(intervals) or i >= len(intervals):
                continue

            # Calculate time difference between positions
            time_diff = intervals[i][0] - intervals[i - 1][1]

            # Avoid division by zero or very small time intervals
            if time_diff < 0.1:
                time_diff = 0.1

            # Calculate velocity (frets per second)
            velocity = (
                abs(self.hand_position[i] - self.hand_position[i + 1]) / time_diff
            )
            self.hand_velocities.append(velocity)

    def _calculate_hand_speed_error(self) -> None:
        """Check for hand movements that exceed speed thresholds."""
        if not self.hand_velocities:
            return

        intervals = list(self.time_note_locations.keys())

        for i, speed in enumerate(self.hand_velocities):
            if i >= len(intervals) - 1:
                continue

            if speed > self.thresholds.speed_threshold:
                duration = intervals[i + 1][0] - intervals[i][1]
                self.update_error("max_hand_speed", [1, duration])

    def update_error(self, error_type: str, value: List) -> None:
        """
        Record an error occurrence.

        Parameters:
            error_type: Type of error
            value: [count, duration] for the error
        """
        self.errors_numbers[error_type].append(value)

    def _calculate_error_rates(self) -> None:
        """Calculate error rates based on recorded errors."""
        total_notes = len(self.times_pitches)
        total_duration = self.midi_file.get_end_time()

        for error_type, errors in self.errors_numbers.items():
            if not errors:
                self.errors_rates[error_type] = 0
                continue

            # Check if this is a count-based or duration-based error
            if all(time == 0 for _, time in errors):
                # Count-based error
                total_count = sum(count for count, _ in errors)
                self.errors_rates[error_type] = total_count / total_notes
            else:
                # Duration-based error
                total_weighted = sum(count * time for count, time in errors)
                self.errors_rates[error_type] = total_weighted / (
                    total_notes * total_duration
                )

    def _calculate_playability(self) -> None:
        """Calculate overall playability score."""
        self.playability_rate = 100.0

        for rate in self.errors_rates.values():
            if rate:
                self.playability_rate -= rate

        # Ensure playability is between 0 and 100
        self.playability_rate = max(0, min(100, self.playability_rate))

    def _post_process_hand_positions(self) -> None:
        """Process hand positions for advanced analysis."""
        # This method is left for subclasses to implement
        pass

    def _post_process_time_note_locations(self) -> None:
        """Fill in missing note locations with previous data."""
        if not self.time_note_locations or not self._problematic_times:
            return

        locations = list(self.time_note_locations.items())

        for problem_time in self._problematic_times:
            # Find the preceding valid placement
            prev_placement = None
            for interval, placement in locations:
                if interval[1] <= problem_time[0]:
                    prev_placement = placement
                elif interval[0] >= problem_time[1]:
                    break

            if prev_placement is not None:
                self.time_note_locations[problem_time] = prev_placement

    def show_stats(
        self,
        time_step: bool = False,
        hand: bool = False,
        vel: bool = False,
        nb_errors: bool = False,
        rates_errors: bool = True,
    ) -> None:
        """
        Display statistics about the analysis.

        Parameters:
            time_step: Show note locations by time
            hand: Show hand positions
            vel: Show hand velocities
            nb_errors: Show error counts
            rates_errors: Show error rates
        """
        if time_step:
            lg.info("Note locations by time interval:")
            for interval, placement in self.time_note_locations.items():
                lg.info(f"{interval}: {placement}")

        if hand:
            lg.info(f"Hand positions: {self.hand_position}")

        if vel:
            lg.info(f"Hand velocities: {self.hand_velocities}")

        if nb_errors:
            lg.info("Error counts:")
            for error_type, errors in self.errors_numbers.items():
                lg.info(f"{error_type}: {errors}")

        if rates_errors:
            lg.info("Error rates:")
            for error_type, rate in self.errors_rates.items():
                lg.info(f"{error_type}: {rate:.4f}")

        lg.info(f"Playability score: {self.playability_rate}%")
