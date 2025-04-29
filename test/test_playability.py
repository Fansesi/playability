from pathlib import Path
import numpy as np
from loguru import logger as lg
from tqdm import tqdm
from typing import List, Tuple, Dict
import unittest

from src import GuitarPlayer, ViolinPlayer


class TestGuitarPlayer(unittest.TestCase):
    def setUp(self):
        self.midi_path = Path("data/test_midis/1.mid")
        self.midi_paths = Path("data/test_midis/").glob("*.mid")

    def test_guitar_playability(self):
        player = GuitarPlayer(self.midi_path)
        player.show_stats()

    def extensive_debug(self, player: GuitarPlayer):
        lg.debug(player.times_pitches)
        lg.debug(player.create_note_on_string([-1, -1, 21, 16, 12, 7]))
        lg.debug(player.time_note_locations)
        lg.debug(player.retr_indexes_elems([-1, -1, -1, -1, 12, 789, -1]))
        lg.debug(player.create_note_on_string(mid.guitar_fretboard[50]))
        lg.debug(player.hand_position)
        lg.debug(player.playability_rate)
        lg.debug(
            player.fret_threshold_error,
            mid.hand_movement_threshold_error,
            len(mid.time_note_locations),
        )


def _get_ex_mid() -> Playability:
    single_path = Path("data/test_midis/1.mid")
    mid = Playability(
        single_path,
        fret_threshold=4,
        hand_movement_threshold=5,
        error_distrubution=(0.2, 0.2, 0.2, 0.2, 0.1, 0.1),
        transpose=True,
    )
    return mid


def test_lots_of_midi():
    all_mid_path = list(Path("dataset_midi/").glob("*.mid"))[:100]

    playabilities = []
    for path in tqdm(all_mid_path):
        player = Playability(str(path), 4, 5, [0.333, 0.333, 0.001, 0.222, 0.111])
        playabilities.append(player.playability_rate)

    lg.info(f"Average of the playability rates is: {np.average(playabilities)}")


def test_single_midi():
    mid = _get_ex_mid()
    mid.show_stats(False, True, False)


def extensive_debug(mid):
    lg.debug(mid.times_pitches)
    lg.debug(mid.create_note_on_string([-1, -1, 21, 16, 12, 7]))
    lg.debug(mid.time_note_locations)
    lg.debug(mid.retr_indexes_elems([-1, -1, -1, -1, 12, 789, -1]))
    lg.debug(mid.create_note_on_string(mid.guitar_fretboard[50]))
    lg.debug(mid.hand_position)
    lg.debug(mid.playability_rate)
    lg.debug(
        mid.fret_threshold_error,
        mid.hand_movement_threshold_error,
        len(mid.time_note_locations),
    )


def test_visualization():
    mid = _get_ex_mid()
    mid.visualize_song()


def test_main():
    single_path = Path("data/test_midis/1.mid")

    error_distribution = {
        "max_fret": 1 / 7,
        "max_hand_movement": 1 / 7,
        "max_hand_speed": 1 / 7,
        "max_min_pitch": 1 / 7,
        "max_number_of_notes": 1 / 7,
        "impossible_to_play": 1 / 7,
        "duplicate_notes": 1 / 7,
    }

    thresholds = {
        "fret_thresholds": 4,
        "hand_movement_threshold": 5,
        "speed_threshold": 12 / 0.01,
    }
    guitar_params = {
        "open_string_pitches": [40, 45, 50, 55, 59, 64],
        "min_max_pitch": [40, 85],
        "number_of_strings": 6,
        "scale_length": 630,
        "number_of_frets": 24,
    }

    guitarist = GuitarPlayer(single_path, error_distribution, thresholds, guitar_params)
    guitarist.show_stats(
        time_step=False,
        hand=True,
        vel=False,
    )
    # guitarist.visualize_guitar()


if __name__ == "__main__":
    unittest.main()
