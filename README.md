# Playability of Stringed Instruments
[![Python 3.11](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/release/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![GitHub license](https://img.shields.io/github/license/Fansesi/playability)](https://github.com/Fansesi/guitar_playability/blob/main/LICENSE)

A library for simulating the playing of any (even the ones that doesn't exists!) stringed instruments and trying to choose the right finger/hand positions for a given MIDI file/score.

## Errors
Currently 7 types of errors are calculated. Explanation of error types are as follows:
* `max_fret`: maximum length of the notes apart in frets numbers. Although it depends on the position, a skilled player can play notes that are 5 frets apart but in order to be more calculate the score more generally, threshold is set to 4.
* `max_hand_movement`: maximum number of frets that a hand can move between two different shapes between two time steps. Threshold is set to 5 as default.
* `max_hand_speed`: maximum speed of hand in fret/sec.
* `max_min_pitch`: calculates how many pitches which are out of guitars maximum and minimum pitch values, exist. If `transpose` is set to True, transpose those pitches to nearest possible octave. Else, delete them.
* `max_number_of_notes`: maximum number of notes in a time step. Currently, library supports 6 strings guitars so it's set to 6. If it's more than 6, delete the possible octaves. If the problem persist, remove some of the bass notes.
* `impossible_to_play`: errors that are not catched or literally impossible to play on a guitar (e.g. E2 and G2 at the same time)   
* `duplicate_notes`: calculates how many duplicate notes exist.

## Usage
`show_stats()`, displays all the needed information which is calculated by the `GuitarPlayer`. `visualize_song()`, starts the GUI which consists of the fretboard, note locations in a time step and hand positions.  

```python
single_path = Path("data/test_midis/1.mid")

# See default configurations under config.py file
error_distribution = ErrorDist.for_guitar()
thresholds = Thresholds.for_guitar()
guitar_params = GuitarParams()

player = GuitarPlayer(single_path, error_distribution, thresholds, guitar_params)

# To display statistics and all the calculations about the piece.
player.show_stats(
    time_step=False,
    hand=True,
    vel=False,
)
# To display the fretboard, fingerings and hand positions.
player.visualize_guitar()
```

## Todo
- [ ] Try to find more edge cases and handle them. 
- [ ] Implement the ViolinPlayer.
- [ ] Consider the bares and half bares for guitars.
- [ ] Make the music play in the GUI.
- [ ] Implement more tests.
