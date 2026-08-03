from slotmodel.sim.paytable.paytable_def import (
    Paytable,
    PaytableEntry,
)
from slotmodel.sim.reels import Symbol

# Each tuple contains the multipliers for 3, 4, and 5 connected symbols.
PAYTABLE = Paytable(
    reel_count=5,
    minimum_match_count=3,
    entries=(
        PaytableEntry(
            symbol=Symbol.WILD,
            multipliers=(10, 20, 75),
        ),
        PaytableEntry(
            symbol=Symbol.JEWEL,
            multipliers=(10, 20, 75),
        ),
        PaytableEntry(
            symbol=Symbol.CASTLE,
            multipliers=(5, 7, 25),
        ),
        PaytableEntry(
            symbol=Symbol.CHEST,
            multipliers=(4, 6, 20),
        ),
        PaytableEntry(
            symbol=Symbol.COIN,
            multipliers=(3, 5, 15),
        ),
        PaytableEntry(
            symbol=Symbol.KNIGHT,
            multipliers=(1, 2.5, 7.5),
        ),
        PaytableEntry(
            symbol=Symbol.A,
            multipliers=(1, 2.5, 7),
        ),
        PaytableEntry(
            symbol=Symbol.K,
            multipliers=(1, 2.5, 6.5),
        ),
        PaytableEntry(
            symbol=Symbol.Q,
            multipliers=(1, 2, 6),
        ),
        PaytableEntry(
            symbol=Symbol.J,
            multipliers=(1, 2, 5.50),
        ),
        PaytableEntry(
            symbol=Symbol.PAWN,
            multipliers=(1, 2, 5),
        ),
    ),
)
