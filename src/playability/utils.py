from typing import List, Tuple, Dict
from loguru import logger as lg


def create_finger_positions(
    open_string_pitches: List[int],
    min_max_pitch: Tuple[int, int],
    number_of_strings: int,
) -> Dict[int, List[int]]:
    """
    ## Params:
    * `open_string_pitches`: pitches of the open string from low to high.
    Default to normal tuning.
    * `min_max_pitch`: minimum and maxiumu pitches. Default to normal tuning.
    * `number_of_strings`: number of strings on guitar.

    ## Note:
    For normal tuned 6 stringed classical guitar, one may use:
    ```python
    open_string_pitches = [40, 45, 50, 55, 59, 64]
    min_max_pitch = [40, 85]
    number_of_strings = 6
    ```"""

    fretboard = {
        i: [-1 for k in range(number_of_strings)]
        for i in range(min_max_pitch[0], min_max_pitch[1] + 1)
    }
    # for i in fretboard:
    #     lg.debug(i)
    _max_playable_fret = min_max_pitch[1] - open_string_pitches[-1]

    for string_num in range(number_of_strings):
        _fret = 0
        for position in range(
            open_string_pitches[string_num],
            open_string_pitches[string_num] + _max_playable_fret + 1,
        ):
            fretboard[position][string_num] = _fret
            _fret += 1

    return fretboard
