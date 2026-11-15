from rich._palettes import STANDARD_PALETTE
from rich.palette import Palette
from rich.table import Table


def test_rich_cast():
    table = STANDARD_PALETTE.__rich__()
    assert isinstance(table, Table)
    assert table.row_count == 16


def test_match():
    palette = Palette([(0, 0, 0), (255, 255, 255), (255, 0, 0)])
    assert palette.match((255, 255, 255)) == 1
    assert palette.match((250, 250, 250)) == 1
    assert palette.match((255, 0, 0)) == 2
    assert palette.match((0, 0, 0)) == 0
