import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from typing import List, Tuple, Dict, Optional, Callable
import numpy as np
import math
from loguru import logger as lg


class SongVisualizer:
    """Visualizes a song with a interactive GUI. Here, time is considered
    with a slider and in each time step one may look at the fingering positions
    on an instrument.

    ### Params
    * `num_finger_positions`: max number of frets or max number of fingerings on
    a string.
    * `num_strings`: number of strings.
    * `hand_position`: hand_position data, calculated previously relavant playability class.
    * `time_note_locations`: time_note_locations data, calculated previously relavant playability class.
    * `grid_function`: grid_function to create axis. Must take ax: plt.Axes, num_frets: int, num_strings: int
    and return ax and the x values in other words fret positions.

    ### Buttons
    * Reset button resets the slider to 0.
    * Auto Scroll button starts from the current `time_step` and goes on from there.

    ### Keyboard Inputs
    * rightarrow: increase the slider value.
    * leftarrow: decrease the slider value.
    * a: break the auto scroll.

    ### TODO:
    * Play the music!
    """

    def __init__(
        self,
        num_finger_positions: int,
        num_strings: int,
        hand_position: List[float],
        time_note_locations: Dict[Tuple[float, float], List[List[int]]],
        grid_function: Optional[Callable] = None,
    ) -> None:
        self.hand_position = hand_position
        self.time_note_locations = time_note_locations
        self.num_finger_positions = num_finger_positions
        self.num_strings = num_strings
        self.grid_function = (
            grid_function if grid_function is not None else self._create_grid
        )

        self.np_num_finger_positions = np.arange(self.num_finger_positions)
        self.np_num_strings = np.arange(self.num_strings)

        # Instantiating the plot
        self.fig, self.ax = plt.subplots()

        # Labeling the axes
        self.ax.set_xlabel("Finger Positions")
        self.ax.set_ylabel("Strings")

        self.ax, self.x_values = self.grid_function(
            self.ax, self.num_finger_positions, self.num_strings
        )

    def visualize(self):
        """Main visualization function. Uses,
        * `self.grid_function`
        * `self.time_note_locations`
        """

        note_positions_line = self.ax.plot(
            [],  # initially empty
            "bo",
            markersize=6,
        )

        hand_positions_line = self.ax.plot(
            [],  # initially empty
            linewidth=4,
            color="red",
        )

        # Adjust the main plot to make room for the sliders
        self.fig.subplots_adjust(bottom=0.25)

        # Make a vertically oriented slider to control the time steps
        ax_time = self.fig.add_axes([0.25, 0.1, 0.65, 0.03])

        time_step_slider = Slider(
            ax=ax_time,
            label="Time Step",
            valmin=0,
            valmax=len(self.time_note_locations),
            valinit=0,
            orientation="horizontal",
        )

        def _update(val):
            int_val = math.floor(val)
            current_fret_pos = list(self.time_note_locations.values())[int_val]

            if current_fret_pos != []:
                note_positions_line[0].set_data(
                    self._arange_fret_positions(current_fret_pos)
                )
            else:
                lg.warning(
                    f"Note positions of time_step {int_val} is empty. Please fix this."
                )

            hand_positions_line[0].set_data(
                self._arange_hand_position(int_val + 1, self.np_num_strings)
            )
            self.fig.canvas.draw_idle()

        time_step_slider.on_changed(_update)

        # Create a `matplotlib.widgets.Button` to reset the sliders to initial values.
        resetax = self.fig.add_axes([0.8, 0.025, 0.1, 0.05])
        reset_button = Button(resetax, "Reset", hovercolor="0.975")

        autoax = self.fig.add_axes([0.6, 0.025, 0.13, 0.05])
        auto_button = Button(autoax, "Auto Scroll", hovercolor="0.975")

        self.__stop_data = False

        def _reset(event):
            time_step_slider.reset()
            self.fig.canvas.flush_events()

        def _auto_scroll(event):
            for i in range(time_step_slider.val, len(self.time_note_locations)):
                # I know it's ugly but it's the way to go.
                time_duration = (
                    list(self.time_note_locations.keys())[i][1]
                    - list(self.time_note_locations.keys())[i][0]
                )
                time_step_slider.set_val(i)
                plt.pause(time_duration)
                if self.__stop_data:
                    break
            self.__stop_data = False

        def _onkey(event):
            if event.key == "right":
                time_step_slider.set_val(time_step_slider.val + 1)
            if event.key == "left":
                time_step_slider.set_val(time_step_slider.val - 1)
            if event.key == "a":
                self.__stop_data = True
            self.fig.canvas.draw()

        reset_button.on_clicked(_reset)
        auto_button.on_clicked(_auto_scroll)
        self.fig.canvas.mpl_connect("key_press_event", _onkey)

        self.fig.set_size_inches(15, 7.5)
        plt.show()

    def _arange_hand_position(self, index: int, num_strings: List[int]):
        """Given an index returns the hand_position of that index."""
        # lg.debug(self.hand_position[index])
        # return (
        #     [self.hand_position[index]],
        #     num_strings,
        # )
        if self.hand_position[index].is_integer():
            return (
                [self.x_values[int(self.hand_position[index])]],
                num_strings,
            )
        else:
            # basically get the middle of the two bars in x_values
            return (
                [
                    (
                        self.x_values[int(self.hand_position[index] + 0.5)]
                        + self.x_values[int(self.hand_position[index] - 0.5)]
                    )
                    / 2
                ],
                num_strings,
            )

    def _arange_fret_positions(self, finger_position: List[int]):
        """Given finger_position, return the x, y coordinates of them.
        ### Params:
        * finger_position: E.g. [0, -1, 5, -1, 3, 0]
        """
        x = []
        y = []
        for i, elem in enumerate(finger_position):
            if elem != -1:
                x.append(self.x_values[elem])
                y.append(i)
        return x, y

    def _create_grid(self, ax: plt.Axes, num_frets, num_strings):
        """Creates the strings, frets in order words the grid."""
        ax.vlines(x=num_frets, ymin=0, ymax=len(num_strings) - 1, color="black")
        ax.hlines(
            y=num_strings,
            xmin=0,
            xmax=max(num_frets),
            color="black",
            linewidth=[1 for num in range(len(num_strings))],
        )

        return ax
