# slotModel
This is a personal project for slot simulation and balancing. It covers a full game simulation, a graphical interface for inspection and testing the slot, displaying the paylines, paytables and simulation statistics. The project contains configurable paylines,paytables and reels, as well as internal tools for simulations, computing statistics and optimizing reels using a genetic algorithm.

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
