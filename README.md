# slotModel
This is a personal project for slot simulation and balancing. It covers a full game simulation, a graphical interface for inspection and testing the slot, displaying the paylines, paytables and simulation statistics.

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
Activate the environment, in Bash run:
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
.venv/bin/activate
```
Install dependencies packages(numpy, PySide6)
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
