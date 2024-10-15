# PVRecordPhysio
Recording time-locked animal physiology alongside MRI (Bruker) paravision

GUI to configure and record physiologic data alongsice MRI data in Paravision environment.

Once hardware has been connected and configured, this program will record values to a text file at a prescribed 
interval alongside the MRI data. This approach makes it easier to view and use the values in subsequent processing. 
It continuously monitors the status of Paravision and runs in two modes:
  <br>Continuous: Logs to a single text file in the current experiment's data directory.
  <br>Per-Scan: Logs to a separate text file within each scan directory each time a new scan is started.

<br><br>

**Installation**: <br>
Copy the PhysioRecording_v2.py to the home directory on a Paravision console.

The script will attempt to use pip/user commands if the modules are not found. 
In practice, the pysimplegui27 fails to start, but works if the script is restarted.

May need to run:
sudo yum install tkinter  #requires su/root
pip install typing --user
pip install configparser --user
pip install pysimplegui27 --user

On a recent installation, it was necessary to do downgrade pip first to get the installation working:
python -m pip install --upgrade "pip < 19.2"
then:
python -m pip install --upgrade "pip < 21.0".
<br><br>


**Quickstart**:<br>
In a Terminal window started from paravision (critical), start program: python PhysioRecording_v2.py
Select configuration/channels to record, ensure they match the PC-SAM, POET, GRASS, or Infusion Pump output.
Start PV Recording (once after starting paravision)
Data will be automatically recorded to raw data folders.

Note: Custom Values/Flags can be set and updated during scans, but they have to be enabled
prior to starting recording. Useful for recording changes in delivered anesthesia in addition
to the real-time gas analyzer readings or other events such as stimulation events.

**Setup**:<br>
A labjack device (U3-HV) is connected to each of the instruments to capture analog values.
Most useful is the SA Instruments Breakout Box, but also have options for gas analyzers, pumps, and stimulators, 
some of which have been used.
<br><br>

**Example Display** (unconnected example):<br>
![image](https://github.com/user-attachments/assets/1bdc22e0-cef0-47a8-ba0c-38accdf73fab)


<br><br>
Matt Budde, MCW, Copyright 2024
