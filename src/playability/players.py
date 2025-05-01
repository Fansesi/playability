"""
This file implements following classes:
- GuitarPlayer
- ViolinPlayer
"""

from pretty_midi import PrettyMIDI
from typing import List, Dict, Optional, Union
from pathlib import Path
import numpy as np

from .base import BaseInstrumentPlayer
from .utils import create_finger_positions
from .vis import SongVisualizer
from .config import GuitarParams


class GuitarPlayer(BaseInstrumentPlayer):
    """Guitar player.

    ## Params:
    MIDIFile: Midi file to work with.
    error_distribution:
    thresholds:
    guitar_parameters: Parameters of guitar to create the guitar. Example:

    ```python
    guitar_params = {
        'open_string_pitches': None,
        'min_max_pitch': None,
        'number_of_strings': None,
        'scale_length': None,
        'num_frets': None,
    }
    ```
    """

    def __init__(
        self,
        MIDIFile: PrettyMIDI | str | Path,
        error_distribution: Optional[Dict[str, float]] = None,
        thresholds: Optional[Dict[str, int]] = None,
        guitar_parameters: Optional[GuitarParams] = None,
    ) -> None:
        if not guitar_parameters:
            self.guitar_parameters = GuitarParams()
        else:
            self.guitar_parameters = guitar_parameters

        super().__init__(
            MIDIFile,
            create_finger_positions(
                self.guitar_parameters.open_string_pitches,
                self.guitar_parameters.min_max_pitch,
                self.guitar_parameters.number_of_strings,
            ),
            error_distribution,
            thresholds,
            [],  # self._edge_case_1
        )

        self.post_init()

    def _edge_case_1(self):
        """TODO: Implement more edge cases like this."""
        raise NotImplementedError

    def visualize_guitar(self):
        """Visualizes the classical guitar fretboard."""
        visualizer = SongVisualizer(
            num_finger_positions=self.guitar_parameters.number_of_frets,
            num_strings=self.number_of_strings,
            hand_position=self.hand_position,
            time_note_locations=self.time_note_locations,
            grid_function=self.create_guitar_grid,
        )

        visualizer.visualize()

    def create_guitar_grid(
        self,
        ax,
        num_frets: Union[np.ndarray, List[int], int],
        num_strings: Union[np.ndarray, List[int], int],
    ):
        """Creates the guitar grid for the visualizer."""

        if isinstance(num_frets, int):
            num_frets = np.arange(num_frets)
        elif isinstance(num_frets, list[int]):
            num_frets = np.array(num_frets)

        if isinstance(num_strings, int):
            num_strings = np.arange(num_strings)
        elif isinstance(num_frets, list[int]):
            num_strings = np.array(num_strings)

        _fret_locs = self._create_fret_locations()
        _fret_locs = list(map(lambda x: x / 10, _fret_locs))
        _fret_locs.insert(0, 0.0)
        ax.vlines(x=_fret_locs, ymin=0, ymax=len(num_strings) - 1, color="black")
        ax.hlines(
            y=num_strings,
            xmin=0,
            xmax=max(_fret_locs),
            color="black",
            linewidth=[3 - num * 0.5 for num in range(len(num_strings))],
        )

        return ax, _fret_locs

    def _create_fret_locations(
        self,
        scale_length: Optional[Union[float, int]] = None,
        number_of_frets: Optional[int] = None,
    ):
        """
        ## Params
        * scale_length: in mm.
        * number_of_frets: number of frets on the guitar.
        """

        scale_length = (
            self.guitar_parameters.scale_length
            if scale_length is None
            else scale_length
        )
        number_of_frets = (
            self.guitar_parameters.number_of_frets
            if number_of_frets is None
            else number_of_frets
        )

        _const_from_rule = 17.817
        fret_positions = []
        scaling_factor = 0
        distance = 0

        for fret in range(0, number_of_frets):
            location = scale_length - distance
            scaling_factor = round(location / _const_from_rule, 2)
            distance = distance + scaling_factor
            fret_positions.append(distance)

        return fret_positions


class ViolinPlayer(BaseInstrumentPlayer):
    def __init__(self) -> None:
        pass
