"""
This file show some example usage of the API and its functions.

It starts off with some of the internals, and in the end how it all fits
together into complete callable analytics funcitons for computing
statistics related to the game.
"""
from pathlib import Path
import numpy as np

reel_path = (
    Path(__file__).parents[1]
    / "config"
    / "reels"
    / "candidates"
    / "high_vol.json"
)
# Reels are stored externally in .json files in config/reels/candiates
# This format is decent for reading and enditing but some type of
# better suited datastructure is better for millioins of simulations.
# For this we use numpy arrays
from slotmodel.sim.reels import read_reels
# read_reels parses the json file into a tuple object containg the reels
reels_tuple = read_reels(reel_path)
# From this we convert the tuple objects into a numpy matrix using
from slotmodel.sim.reels import compile_reels
reel_matrix = compile_reels(reels_tuple)

# This is a 3x5 slot. Now we want information about all the visible
# symbols for a particular stop on the reels. For that we first
# define a window which tells which indicies are visible from
# the stop positions, in this case we use (0,1,2) but e.g (-1,0,1)
# would also work.
window = np.asarray([0,1,2], dtype=np.int32)
# Next we initialize the class ScreenModel which keeps info about
# the reels and the visable symbols for each stop, which is precomputed
# upon creation. This object is central in the API
from slotmodel.sim.screens import ScreenModel
screen_model = ScreenModel(reels=reel_matrix, window_offsets=window)
# It precomputes for e.g stop 9 on the reels the visable symbols
# are e.g stop 9: [J,A,CASTLE] for e.g reel 0.

# To request the outcome of a single spin we use the spin_batch function
from slotmodel.sim.screens import spin_batch
# This returns a dataclass SpinBatch with fields {stops, screens}
# where stops:(batch_size, reel_count) contains the sampled stop
# positions, and screens (batch_size, row_size, reel_count)
# is a 3-dim array with all the visible stop screens from each sampled
# stop. E.g:
#           [8, 3, 4, 5, 6]
#           [2, 1, 7, 1, 5]
#           [5, 3, 7, 3, 9]
#
#
# It samples random numbers in range(reel_length) for each reel
# individually.

# Before requesting a spin we have to initialize a random generator,
# for this we use numpy's recommened default generator
rng_seed = 123
rng = np.random.default_rng(rng_seed)
single_spin = spin_batch(model=screen_model, batch_size=1, rng=rng)
# print(single_spin)

# To request many such screens, we have a choice either using
# spin_batch with a large batch, or using iter_spin_batches
# which will yield spin batches as an interator does.
# See slotmodel/sim/screen/screen_batch.py for info.

# To evaluate the outcome of a spin and calcualte the win multipliers according
# to the rules of the game we use the evaluator dataclass.
from slotmodel.sim.eval import PaylineEvaluator
# Since the rules of the games depended upon the paylines
# and the paytable used this class must recieve these as input.
# The paylines and paytable are defined in 
# slotmodel/sim/paylines and slotmodel/sim/paylines.

# To get these we have to import them
from slotmodel.sim.paylines import PAYLINES
from slotmodel.sim.paytable import PAYTABLE_HIGH_VOL
# Since these are defined in an ediatble and readable way, they must also 
# be converted into numpy friendly formats. We use the auxillary functions:
from slotmodel.sim.paytable import compile_paytable
from slotmodel.sim.paylines import compile_paylines
paylines_matrix = compile_paylines(PAYLINES)
paytable_matrix = compile_paytable(PAYTABLE_HIGH_VOL)

# Now we can initialize the evaluator:
evaluator = PaylineEvaluator(
    payline_rows=paylines_matrix, 
    payout_matrix=paytable_matrix,
    minimum_match_count=3,
)
# The minumum match_count argument tells the evaluator the
# mimimum number of identicalsymbols that need to connect right to left 
# for it to count as a win. To evaluate the outcome of our single spinn we use
# the method .evaluate()
# Note that this method only uses the screen information from the spin, 
# it doesn't need the stops. We get only the screens using .screens

spin_outcome = evaluator.evaluate(single_spin.screens)
# print(spin_outcome)
# This returns a PaylineEvaluation dataclass that contains arrays indicating 
# the winning symbols, the match count for each symbol and the corresponding
# payout multipliers for any matches according to the paytable 
# issued to the evaluator.

# The bonus game uses the same PaylineEvaluator for determining payline wins,
# but adds additional logic around the evaluation which are related to how the
# bonus game functions.
#
# The bonus spins contain sticky winning positions. The function
# evaluate_bonus_step() evaluates the paylines, determines which
# screen positions contributed to wins, determines which of those positions
# should become newly locked, and counts scatter symbols.

from slotmodel.sim.eval import evaluate_bonus_step

# A lock mask has the same shape as the screens:
# (batch_size, row_count, reel_count).
#
# True means that the symbol at that position is already sticky.
# For this simple example we start with no locked symbols.
locked_mask = np.zeros_like(single_spin.screens, dtype=np.bool_)

bonus_step = evaluate_bonus_step(
    screens=single_spin.screens,
    locked_mask=locked_mask,
    evaluator=evaluator,
    min_scatter_count=3,
)
# bonus_step is a BonusStepEvaluation dataclass containing:
#
# bonus_step.payline_evaluation
#     The ordinary PaylineEvaluation produced by evaluator.evaluate().
#
# bonus_step.scatter_counts
#     Number of scatter symbols present on each screen.
#
# bonus_step.winning_pos_mask
#     Boolean mask identifying physical screen positions that participated
#     in a payline win. Scatter symbols are excluded from this mask.
#
# bonus_step.new_lock_mask
#     Winning positions that were not already locked. These become sticky
#     if the bonus spin continues.
#
# bonus_step.cont_mask
#     One boolean per screen. True if at least one new sticky position was
#     found and therefore another respin should occur.

# print(bonus_step.payline_evaluation.total_multiplier_per_spin)
# print(bonus_step.scatter_counts)
# print(bonus_step.winning_pos_mask)
# print(bonus_step.new_lock_mask)
# print(bonus_step.cont_mask)

# Usually you do not need to manually implement the sticky-respin loop.
# The analytics API provides simulate_bonus_free_spin_batch(), which
# simulates complete bonus free spins including the guaranteed wild,
# sticky positions and subsequent respins.

from slotmodel.sim.analytics import simulate_bonus_free_spin_batch

bonus_free_spin = simulate_bonus_free_spin_batch(
    model=screen_model,
    evaluator=evaluator,
    batch_size=1,
    rng=rng,
    min_scatter_count=3,
)

# The result contains one completed bonus free-spin result per simulated spin.
#
# final_screens
#     The terminal screens after all sticky respins have finished.
#
# final_locked_mask
#     Positions that were sticky at the end of each free spin.
#
# payout_multipliers
#     Final payout multiplier of each completed free spin.
#
# respin_counts
#     Number of respins generated during each free spin.
#
# retrigger_counts
#     Whether a retrigger was obtained during the free-spin sequence.

# print(bonus_free_spin.final_screens)
# print(bonus_free_spin.final_locked_mask)
# print(bonus_free_spin.payout_multipliers)
# print(bonus_free_spin.respin_counts)
# print(bonus_free_spin.retrigger_counts)

# To simulate complete bonus games rather than individual bonus free spins,
# use simulate_bonus_games(). A bonus game consists of several free spins
# and may gain additional free spins through retriggers.

from slotmodel.sim.analytics import simulate_bonus_games

bonus_games = simulate_bonus_games(
    model=screen_model,
    evaluator=evaluator,
    total_bonus_games=1000,
    batch_size=1000,
    rng=rng,
    initial_free_spins=10,
    retrigger_free_spins=10,
    min_scatter_count=3,
)

# print(bonus_games.payout_multipliers)
# print(bonus_games.free_spin_counts)
# print(bonus_games.respin_counts)
# print(bonus_games.retrigger_counts)


# For statistical analysis of the complete game, sim_report() performs
# both base-game and bonus-game Monte Carlo simulation and combines the
# results into a ParameterReport.
#
# Internally, its base-game simulation is essentially:
#
#     spin_batch(...)
#     evaluator.evaluate(...)
#     scatter_bonus_trigger_mask(...)
#
# while bonus games are simulated separately using simulate_bonus_games().

from slotmodel.sim.analytics import sim_report

report = sim_report(
    model=screen_model,
    evaluator=evaluator,
    total_spins=100_000,
    total_bonus_games=10_000,
    seed=123,
    min_scatter=3,
    initial_free_spins=10,
    retrigger_free_spins=10,
)

# The resulting ParameterReport contains statistics such as:
#
# report.rtp_base
#     Estimated RTP produced directly by base-game payline wins.
#
# report.bonus_freq
#     Estimated probability that a base-game spin triggers the bonus.
#
# report.mean_bonus_payout
#     Mean payout of a simulated bonus game.
#
# report.rtp_bonus
#     Estimated bonus contribution to RTP:
#
#         bonus frequency * mean bonus payout
#
# report.rtp_total
#     Combined base-game and bonus-game RTP.
#
# print(report)
#
#
#
##### OPTIMIZING THE REELS ####
#
# The optimizer implements a genetic algorithm for finding reel sets that
# perform well according to a user defined fitness function.
#
# The optimizer itself does not know anything about RTP,
# bonus frequency, volatility or ParameterReport. It only knows how to
# evolve reel matrices.
#
# The caller supplies a fitness function with the form:
#
#     fitness(candidate_reels, evaluation_seed) -> float
#
# or:
#
#     fitness(candidate_reels, evaluation_seed) -> FitnessEvaluation
#
# The candidate passed to the fitness function is a reel matrix with shape:
#
#     (reel_count, reel_length)
#
# The fitness function can therefore construct a ScreenModel for the
# candidate, simulate the game using sim_report(), and assign a score
# according to how closely the resulting statistics match the desired
# game profile.

from slotmodel.optim.optimizer import (
    FitnessEvaluation,
    Optimizer,
    OptimizerConfig,
)

# For more detailed usage of the optimzer, see the find_candiate.py script