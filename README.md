# slotModel
This is a personal project for slot simulation and balancing. It covers a full game simulation, a graphical interface for inspection and testing the slot, displaying the paylines, paytables and simulation statistics. The project contains configurable paylines, paytables and reels, as well as internal tools for simulations, computing statistics and optimizing reels using a genetic algorithm.

## About
The project contains two versions of the game; one with higher volatility where more of the RTP is distributed into the tail of the P(X) (X : payout) and has a more rare bonus game, and
one lower volatility version where they payout is concentrated more in the lower end. The RTP for the higher volatility version is ~ 96% and was found using a genetic algorithm optimizing the reels for a number of target variables. The lower volatility version has an RTP of ~ 95%, and was optimized by hand through modification of the paytable and reel symbols.

The game itself is a 3x5 slot with 15 paylines. The reels have a length of 51, and there are 11 symbols including a wild symbol(diamond symbol), and a scatter symbol(four clover).
The wild symbol can substitute for any other symbol except the scatter.

A win is obtained when at least 3 symbols are connected on a payline, starting from the leftmost reel. If a win contains wild(s) then the base win multiplier is further increased depending on the number of wilds that is included on the payline 1:2x, 2:4x, 3:8x, 4:16x, 5:32x. The wilds symbols themselves follow a payout depending on the paytable. A payline with only wilds counts as a win with the wild symbol. 

The game has a bonus game feature with 10 free spins. This happens when 3 scatter symbols are obtained on the screen. Each free spin is sticky respin, meaning that if a win is obtained on any payline the symbols are locked, and the remaining symbols are spun again, this continues until there is no additional win to re-initiate the sticky sequence(or the screen becomes filled).

There is functionality in the API to simulate the base game spins and complete bonus games individually. For more information about the API usage, please see the python files in scripts directory.

### Installation
Requirements: Python >= 3.10.
#### Step 1
Clone the repository
```
git clone https://github.com/obacklin/slotModel.git
```
#### Step 2
Create virtual environment and install package dependencies
##### Windows
Initialize virtual environment, run: 
```
python -m venv .venv
```
Activate the environment, in PowerShell run:
```
.\.venv\Scripts\activate
```
Install dependencies packages(numpy, PySide6)
```
python -m pip install -e .
```
##### Linux/Mac
Initialize virtual environment, run: 
```
python3 -m venv .venv
```
Activate the environment, In PowerShell run:
```
source .venv/bin/activate
```
Install packages dependencies(numpy, PySide6)
```
python3 -m pip install -e .
```
### Running the GUI
To run the Graphical interface, on windows run:
```
python -m gui
```
On Linux/Mac run:
```
python3 -m gui
```
<div align="center">
  <img alt="Slot Display" src="https://github.com/obacklin/slotModel/blob/main/assets/mereads/SlotDisplay.png" width=92%>
</div>

### Contact
Oskar Bäcklin - oskar_backlin@live.com
