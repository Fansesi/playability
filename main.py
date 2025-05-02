from src.playability import GuitarPlayer
from loguru import logger as lg
import sys


def viz_guitar():
    player = GuitarPlayer("data/test_midis/1.mid")
    player.visualize_guitar()


def playability_guitar():
    player = GuitarPlayer("data/test_midis/2.mid")
    # print(player.times_pitches)
    player.show_stats(nb_errors=False, rates_errors=True)


if __name__ == "__main__":
    lg.remove()
    lg.add(
        sink=sys.stderr,
        format="<green>{time:HH:mm:ss:ms}</green>|<level>{level: <8}</level>|<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan>-<level>{message}</level>",
    )
    viz_guitar()
