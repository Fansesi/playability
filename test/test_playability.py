from pathlib import Path
import unittest

from src.playability import GuitarPlayer, ErrorDist, Thresholds, GuitarParams


class TestGuitarPlayer(unittest.TestCase):
    def setUp(self):
        self.midi_path = Path("data/test_midis/2.mid")
        self.midi_paths = Path("data/test_midis/").glob("*.mid")

        # self.player = self.get_player(self.midi_path)

    def get_player(self, path):
        return GuitarPlayer(
            MIDIFile=path,
            error_distribution=ErrorDist.for_guitar(),
            thresholds=Thresholds.for_guitar(),
            guitar_parameters=GuitarParams(),
        )

    def test_all(self):
        for p in sorted(list(self.midi_paths)):
            print("=" * 50 + f" {p.name} " + "=" * 50)
            player = self.get_player(p)
            player.show_stats()

    def test_single(self):
        print("=" * 50 + "single midi test" + "=" * 50)
        print("=" * 50 + f" {self.midi_path.name} " + "=" * 50)
        player = GuitarPlayer(self.midi_path)
        player.show_stats()


if __name__ == "__main__":
    unittest.main()
