from __future__ import annotations


class ErrorDist:
    def __init__(
        self,
        max_fret: Optional[int] = None,
        max_hand_movement: Optional[int] = None,
        max_hand_speed: Optional[int] = None,
        max_min_pitch: Optional[int] = None,
        max_number_of_notes: Optional[int] = None,
        impossible_to_play: Optional[int] = None,
        duplicate_notes: Optional[int] = None,
    ):
        self.max_fret = max_fret
        self.max_hand_movement = max_hand_movement
        self.max_hand_speed = max_hand_speed
        self.max_min_pitch = max_min_pitch
        self.max_number_of_notes = max_number_of_notes
        self.impossible_to_play = impossible_to_play
        self.duplicate_notes = duplicate_notes

        self.all_errors = [
            "max_fret",
            "max_hand_movement",
            "max_hand_speed",
            "max_min_pitch",
            "max_number_of_notes",
            "impossible_to_play",
            "duplicate_notes",
        ]

    @staticmethod
    def for_guitar() -> ErrorDist:
        return ErrorDist(
            max_fret=1 / 7,
            max_hand_movement=1 / 7,
            max_hand_speed=1 / 7,
            max_min_pitch=1 / 7,
            max_number_of_notes=1 / 7,
            impossible_to_play=1 / 7,
            duplicate_notes=1 / 7,
        )

    @staticmethod
    def for_violin() -> ErrorDist:
        raise NotImplementedError

    def init_error_dict(self):
        return {i: None for i in self.all_errors}


class Thresholds:
    def __init__(
        self,
        fret_thresholds: Optional[int] = None,
        hand_movement_threshold: Optional[int] = None,
        speed_threshold: Optional[int] = None,
    ):
        self.fret_thresholds = fret_thresholds
        self.hand_movement_threshold = hand_movement_threshold
        self.speed_threshold = speed_threshold

    @staticmethod
    def for_guitar() -> Thresholds:
        return Thresholds(
            fret_thresholds=4,
            hand_movement_threshold=5,
            speed_threshold=12 / 0.01,
        )

    @staticmethod
    def for_violin() -> Thresholds:
        raise NotImplementedError


class GuitarParams:
    def __init__(
        self,
        open_string_pitches: Optional[List[int]] = [40, 45, 50, 55, 59, 64],
        min_max_pitch: Optional[List[int]] = [40, 85],
        number_of_strings: Optional[int] = 6,
        scale_length: Optional[int] = 630,
        number_of_frets: Optional[int] = 24,
        open_string_first: Optional[bool] = False,
    ):
        self.open_string_pitches = open_string_pitches
        self.min_max_pitch = min_max_pitch
        self.number_of_strings = number_of_strings
        self.scale_length = scale_length
        self.number_of_frets = number_of_frets
