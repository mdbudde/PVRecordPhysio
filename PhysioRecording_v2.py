#!/usr/bin/env python

# coding= utf-8

"""
GUI to configure and record physiologic data alongsice MRI data in Paravision environment.
Matt Budde, MCW, Copyright 2023

Quickstart:
In PV Terminal, start program: python PhysioRecording.py
Select configuration/channels to record, ensure they match the PC-SAM, POET, GRASS, or Infusion Pump output.
Start PV Recording (once after starting paravision)
Data will be automatically recorded to raw data folders.

Note: Custom Values/Flags can be set and updated during scans, but they have to be enabled
prior to starting recording. Useful for recording changes in delivered anesthesia in addition
to the real-time gas analyzer readings or other events such as stimulation events.
"""


"""
NEW CONSOLE Note: try this:

python -m pip install --upgrade "pip < 19.2"

and then

python -m pip install --upgrade "pip < 21.0".



"""



"""
Full details and programming Notes:

The program is organized as follows:
GUI:
    Uses pysimplegui27 for a user interface and interactive elements.
    Note that this requires an installation on the scanner console of :
        sudo yum install tkinter
    Only once for all users, I believe.

    Other python modules are automatically installed when starting with --user,
    so each user will need them installed during the first run of the program.

Configuration:
    The labjack (U3-HV) is connected to the SA Instruments Breakout box on the analog connections,
    which provide -10/+10V ranges. This exceeds the 0-5V range of the output.
    PC-SAM needs to be configure (and importantly, enabled) to output the correct data.

    The POET gas analyzer analog output (single channel) is also connected to the flexible (FIO4)
    connection, providing 0-2.4V. The POET output is undocumented, but it appears to scale from 0-1.2V
    for a 0-4% Iso reading, (other outputs such as O2 are different).

    The Harvard Apparatus output (single channel, pin-3 running/notrunning) is connected to the flexible (FIO6)
    connection, providing 0-2.4V. Logic low is 0-0.8V, logic high is 2-5V per the manual. ok to use 1.2V (2.4/2) as cutoff.

    Connections:
        Labjack,    Device,             Voltage                 Signal
        FIO0:       DAC1 PC-SAM,        low voltage 0-2.4V,   analog 0-5V=0-4096
        FIO1:       DAC1 PC-SAM,        low voltage 0-2.4V,           analog 0-5V=0-4096
        FIO2:       DAC1 PC-SAM,        low voltage 0-2.4V,           analog 0-5V=0-4096
        FIO3:       DAC1 PC-SAM,        low voltage 0-2.4V,           analog 0-5V=0-4096
        FIO4:       POET Gas Analyzer,  low voltage 0-2.4V,     For Iso: 0-4% = 0-2.4V.
        FIO7:       GRASS stimulator,   low voltage 0-2.4V      TBD
        FIO6:       HA Infusion Pump,   low voltage             high-running, low-not running


    Sample period is the time period of each sample.

    Both are set in the gui and saved to the users home directory: SARecording.ini as defaults.

    Additional custom values can be set and updated to new values during the recording, for example the isofluorane
    levels can be input and saved along with the other values. Events such as changes in gas or other stimulation
    events could also be logged.

    Note: There is no (seeminlgy) way to obtain the current scan time from pv, so the timestamps are
    probably approximate and not exact. They can be highly oversampled and should be tested whether they match
    the precise scan times, since that has not been rigorously evaluted.

Running:
    In the simple case, it can be started in  Run wihout Logging mode, which  simply just
    monitors and outputs to the  screen the sampled  values. Good for testing the recording
    and scaling of values to match what is expected. More testing needs to ensure and add more options.

    When started in PV mode, the program regularly communicates with the paravision interface, pvcmd,
    to get the scan status and current scan. The recording will only occur during a scanning process,
    (or reco, since often this is the status when doing recons during a scan.). The data will be saved to
    the current scan's data directory automatially.


Programming:
    The overall structure is:
        gui creation
        configuration reading and setup
        These are both static and passed between functions as the param structure

        Values that change during recording or while running are dynamic and passed in a seperate statusparam structure.
        This is a critical part of the program design to handle them seperately.

        Monitoring for gui events in an endless loop.
            If a scan starts or the run without pv option is selected, a seperate thread is started to do the value reading
    and save the data to a file, in StartRecording(). This has the advantage of simultaneously monitoring the gui/pv in the parent thread, with
    more accurate logging in the child thread. Two queues are setup to pass strings between the processes. One sends
    capture->parent data to the gui display. The parent->capture passes the custom values for saving. Some work was necessary to
    do this efficiently, and only with the initial start or with an update button  are the custom values passed into the parent->capture queue.
    Subprocesses commands send 'pvcmd' processes, but these are brief and return quickly. However, since these have more overhead, they
    are performed less often than the gui read, for example.
    There are considerable handling steps to terminate and/or close the processes/files/queues when necessary.

    To add or test additional recording values (PC-SAM has a lot of options), see the ConfigParam options lists and the
    convertInttoValue() function which converts integer (analog-to-digital) values to real-world units.





    NOTES:
    8-11-22
    - changed code to avoid errors during some setups where pvcmd calls would issue an error.
    - Also added a Scan_Experiment condition to avoid prescan/adjustment premature starts.
    
    10-26-22
    - added ability to record the stimulation status. this uses another connection to the labjack with a T-connector (BNC) to the stimulation
      trigger control module. (old laptop).
    - changed to log data during the Run without PV mode, since this may be useful in certain testing cases.
    - Fiber optic blood pressure connection/conversion was also added. Ensure this works in practice when in the animal and recording.

    10/18/23:
    - When tested with high frequency sampling (0.1 s), there seems to be a lock on the monitor. This is likely due to the default settings
      for     pvmonInterval = 4 and guitimeout = 400 since these were tested with 1s sampling. It should probably determine how ofter pv should be probed
      and convert this to loop number values and the gui timeout. In the above case, pv was sampled every 0.4s (0.1s * pvmonInterval) and the guitimeout was 0.4s as well.
      Need to better test high-frequency sampling and pv monitoring on the scanner.

    11/1/23:
    - Could not get precise values previously. Converted to the low voltage (U3-LV) device instead. Works better.
      Note that the SAI has 0-5V output, based on the conversions the 0-2.4V of the labjack should suffice for most metrics. Will
      need to test with others beyond Temp, RespRate, RespPeriod, etc, but these work much better now.
      Note SAI was 12-bit 0-5V, 0-4096, and the labjack is also 12-bit sampling. With the HV device, the accuracy was bad (-10/+10V)
      -The poet was reconnected and gives proper voltages with the multimeter, but no recordings. Need to figure out.
      -There are occasionally errors with the configuration and having to restart, error is analog on digital channel.  We should properly configure the labjack explicitly
      with the analog connections based on its hardware connections in the init function.

    TODO:
    - add timer and alert for monitoring by hand.
    - add module to control the stimulator to replace the old pc laptop and provide more options for experimental control (loops, variable timing, etc).
    - add toggle for saving during run without PV or not, since lots of files could get generated and may not be desired.


"""

import os
import subprocess
import sys
import time
import datetime
import string


#modules that will need to get checked and will be installed if not available.
modList = ['PySimpleGUI27','configparser','inputs','typing']
for mm in modList:
    try:
        print(mm)
        module_obj = __import__(mm)
        # create a global object containging our module
        globals()[mm] = module_obj
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", mm, "--user"])
    else:
        print('Found package ' + mm)

## do this differently for the labjackpython since the module and import calls are different
##pip install LabJackPython==2.1.0
##import u3

mm = 'u3'
ii = 'LabJackPython==2.1.0'
try:
    print(mm)
    module_obj = __import__(mm)
    # create a global object containging our module
    globals()[mm] = module_obj
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", ii,"--user"])
else:
    print('Found package ' + mm)


import PySimpleGUI27 as sg
from configparser import ConfigParser
from multiprocessing import Process, Queue
#import BrukerMRI as bruker #no need to read PV parameters in this program.
import u3 #LabPython U3 function

#Static values/configuration that are set before starting the recording processes
class ConfigParam:
    def __init__(self):
        self.homedir = os.path.expanduser('~')
        self.configfile = os.path.join(self.homedir,'SARecorder.ini')
        self.deviceU3 = None
        self.isU3 = False
        #Defaults and config to connection mapping
        self.SamplePeriod = 1.0  #seconds, appropriate for slow rates
        self.SelectedChannelMetrics = ['T1Temp','PRespRate','None','None','Iso','None','None'] #defaults
        self.ChannelNameList = ['DAC1','DAC2','DAC3','DAC4','POETANALOG','GRASS','HAPUMP'] #names from PC-SAM or POET device, in config file
        self.ChannelConfig = [u3.FIO0, u3.FIO1, u3.FIO2, u3.FIO3, u3.FIO4, u3.FIO7, u3.FIO6] #connected physically to these LabJack contacts
        self.ChannelPositive = [0, 1, 2, 3, 4, 7, 6] #positive channel values for these connections
        self.currentChannelMetricList = []
        self.currentChannelPositiveList = []
        self.currentChannelConfigList = []
        self.currentChannelDecimateList = []
        self.RateOptionsList = ['T1Temp','PRespRate','ECGRate','BP1Rate','BP1Mean','BP2Rate','BP2Mean','BP2Systol','BP2Diastol','BP3Rate','BP3Mean','BPCardRate','PRespPeriod','None']
        self.PoetOptionsList = ['Iso','O2','CO2','Other','None']
        self.GRASSOptionsList = ['ControlLine','None']
        self.HAPumpOptionsList = ['PumpStat','None']
        self.LogWindow = None
        self.LogHeaderWindow = None
        self.CustomEnabledFlag = False
        self.CustomEnabled1 = False
        self.CustomLabel1 = ''
        self.CustomEnabled2 = False
        self.CustomLabel2 = ''
        self.CustomEnabled3 = False
        self.CustomLabel3 = ''
        self.windowX = None
        self.windowY = None

#Dynamic values that change during recording (PV status) or can be altered during the scan (custom values).
class RecordingParam:
    def __init__(self):
        self.PVStatus = 'IDLE'
        self.recordingstatus = 'IDLE'
        self.logPath = ''
        self.scanstatus = 'Idle'
        self.experimentstatus = 'Idle' #Scan_Experiment for real scan, Setup_Experiment for setup
        self.statuscolor = 'black'
        self.scanstatuscolor = 'black'
        self.newscan = 0
        self.prevDset = ''
        self.studypath = ''
        self.datapath = ''
        self.expno = '0'
        self.AddExpAndStatus = False
        self.internalRecordingStatus = False
        self.internalRunMonitor = False
        self.captureProcessStarted = False
        self.captureProcess = None
        self.fileHandle = None
        self.ParentToCaptureQueue = None
        self.CaptureToParentQueue = None
        self.CustomValue1 = ''
        self.CustomValue2 = ''
        self.CustomValue3 = ''


# Start of Main program (called as sole function from __main__() at end of file)
def main():
    #setup and open the gui and start loopinginternalRecordingStatus = False
    # These could be tweaked for performance.
    pvmonInterval = 4 #only check on PV every this many loops, lower means more checks, but may introduce too much overhead
    guitimeout = 100 #ms for polling gui, longer makes it more responsive.

    #First get defaults and check status of PV or LabJack connections/communications.
    param = ConfigParam()
    statusparam = RecordingParam()

    checkPVconfig()
    param = getSARecorderConfig(param)

    #start the user interface.
    window = guisetup(param)
    param.LogWindow = window['-LOGWINDOW-']
    param.LogHeaderWindow = window['-LOGHEADERWINDOW-']

    param = openandConfigureU3(param)
    if param.isU3==False:
        print("U3 not loaded or configured.\n  Doing logging with sleep timer.")
        window['-LJSTATUS-'].update('Not Connected', text_color = 'red')
    else:
        window['-LJSTATUS-'].update('Connected', text_color = 'green')


    # Create an event loop
    loopInterval = 0
    while True:

        wincurrLoc = window.CurrentLocation()
        param.windowX = wincurrLoc[0]
        param.windowY = wincurrLoc[1]

        #The pvcmd commands to paravision have a lot of overhead, so do them less frequently than
        # doing a window read.
        loopInterval = loopInterval + 1
        if (loopInterval % pvmonInterval) == 0:
            statusparam = MonitorPVstatus(param, statusparam)

        # if monitoring PV while recording, update the scan status
        if statusparam.internalRecordingStatus == True or statusparam.internalRunMonitor == True:
            if statusparam.scanstatus == 'SCANNING' or statusparam.scanstatus == 'RECO' or statusparam.scanstatus == 'ADJUST':
                scanstatuscolor = 'green'
            else: 
                scanstatuscolor = 'black'
                statusparam.recordingstatus = "IDLE"
                statusparam.logPath = ''

            if statusparam.captureProcessStarted == True:
                if statusparam.captureProcess.is_alive():
                    try:
                        captureout = statusparam.CaptureToParentQueue.get(block=False)
                        param.LogWindow.update(captureout, append=True)
                    except:
                        pass


        if statusparam.recordingstatus in ('Recording','Monitoring'):
            statusparam.statuscolor = 'green'
        else:
            statusparam.statuscolor = 'black'

        window['-LOGPATH-'].update(statusparam.datapath)
        window['-STATUS-'].update(statusparam.recordingstatus, text_color = statusparam.statuscolor)
        window['-PVSTATUS-'].update(statusparam.scanstatus + "; " + statusparam.experimentstatus, text_color = statusparam.scanstatuscolor)


        #without a timeout, this function halts until an action occurs
        event, values = window.read(timeout=guitimeout)

        # End program if user closes window or
        # presses the Quit button
        if event == "Quit" or event == None: #sg.WIN_CLOSED is supposed to work, but doesn't. WIN_CLOSED is None anyway, so this does work.
            try:
                setSARecorderConfig(values, param) #this will fail if the window is closed, but not 'Quit'
                statusparam.captureProcess.terminate()
                statusparam.fileHandle.close()
            except:
                pass
            break

        # Record button to start or stop PV recording
        if event == "-RECORD-":
            if statusparam.internalRecordingStatus == False:
                #Start the recording (button changed to allow start)
                param.AddExpAndStatus = True
                param.LogWindow.update('Saving and Loading Channel Configuration.\n',append=True)
                setSARecorderConfig(values, param)
                param = getSARecorderConfig(param)
                statusparam.internalRecordingStatus = True
                window['-RECORD-'].update('Stop Recording', button_color=('black','red'))
                window['-UPDATE-'].update(disabled=True)
                window['-RUNMONITOR-'].update(disabled=True)
                param.LogWindow.update('Start Recording\n',append=True)

                #Check for custom values.
                statusparam.CustomValue1 = values["-CUSTOMVALUE1-"]
                statusparam.CustomValue2 = values["-CUSTOMVALUE2-"]
                statusparam.CustomValue3 = values["-CUSTOMVALUE3-"]

            else:
                #Stop the recording (button changed to allow restart)
                statusparam.internalRecordingStatus = False
                param.AddExpAndStatus = False
                window['-RECORD-'].update('Per Scan Recording', button_color=('black','green'))
                window['-UPDATE-'].update(disabled=False)
                window['-RUNMONITOR-'].update(disabled=False)
                try:
                    statusparam.fileHandle.close()
                    statusparam.captureProcess.terminate()
                    statusparam.CaptureToParentQueue.close()
                    statusparam.PaptureToCarentQueue.close()
                except:
                    pass
                statusparam.newscan = 1
                param.LogWindow.update('Stop Recording\n',append=True)

        #Start/stop monitoring values without using PV status or data logging to file
        if event == "-RUNMONITOR-":
            if statusparam.internalRunMonitor == False:
                #Start the recording (button changed to allow start)
                statusparam.internalRunMonitor = True
                statusparam.internalRecordingStatus == False
                param.AddExpAndStatus = True
                setSARecorderConfig(values, param)
                param = getSARecorderConfig(param)
                window['-UPDATE-'].update(disabled=True)
                window['-RECORD-'].update(disabled=True)
                window['-RUNMONITOR-'].update('Stop Monitor', button_color=('white','red'))

                #Check for custom values.
                statusparam.CustomValue1 = values["-CUSTOMVALUE1-"]
                statusparam.CustomValue2 = values["-CUSTOMVALUE2-"]
                statusparam.CustomValue3 = values["-CUSTOMVALUE3-"]

                StartRecording(param, statusparam)


            else:
                #Stop the recording (button changed to allow restart)
                statusparam.internalRunMonitor = False
                statusparam.internalRecordingStatus == False
                param.AddExpAndStatus = False
                window['-UPDATE-'].update(disabled=False)
                window['-RECORD-'].update(disabled=False)
                window['-RUNMONITOR-'].update('Continuous Recording', button_color=('white','blue'))
                StopRecording(param, statusparam)

        # Save the  current configuration. This is now less necessary since start events resave the current config.
        if event == "Save" or event == "-UPDATE-":
            param.LogWindow.update('Saving and Loading Channel Configuration.\n',append=True)
            setSARecorderConfig(values, param)
            param = getSARecorderConfig(param)
            param.LogWindow.update('Updated Config\n',append=True)

        #
        # This cascades from custom1, which must be the first option,
        # and 2/3 are only available if 1 is enabled, 3 if 2, etc.
        # note enabled/label are the settings before starting (static: param), whereas values
        # are dynamic so are contained in a different structure (statusparam)
        if values["-CUSTOMENABLED1-"] == True:
            window["-CUSTOMENABLED2-"].update(disabled=False)
            window["-CUSTOMVALUE2-"].update(disabled=False)
            window["-CUSTOMLABEL2-"].update(disabled=False)
            param.CustomEnabledFlag = True
            param.CustomEnabled1 = True
            param.CustomLabel1 = values["-CUSTOMLABEL1-"]

            if values["-CUSTOMENABLED2-"] == True:
                window["-CUSTOMENABLED3-"].update(disabled=False)
                window["-CUSTOMVALUE3-"].update(disabled=False)
                window["-CUSTOMLABEL3-"].update(disabled=False)
                param.CustomEnabled2 = True
                param.CustomLabel2 = values["-CUSTOMLABEL2-"]
                if values["-CUSTOMENABLED3-"] == True:
                    param.CustomEnabled3 = True
                    param.CustomLabel3 = values["-CUSTOMLABEL3-"]
                else:
                    param.CustomEnabled3 = False
                    param.CustomLabel3 = ''

            else:
                window["-CUSTOMENABLED3-"].update(disabled=True)
                window["-CUSTOMVALUE3-"].update(disabled=True)
                window["-CUSTOMLABEL3-"].update(disabled=True)
                param.CustomEnabled2 = False
                param.CustomLabel2 = ''
        else:
            window["-CUSTOMENABLED2-"].update(disabled=True)
            window["-CUSTOMVALUE2-"].update(disabled=True)
            window["-CUSTOMLABEL2-"].update(disabled=True)
            window["-CUSTOMENABLED3-"].update(disabled=True)
            window["-CUSTOMVALUE3-"].update(disabled=True)
            window["-CUSTOMLABEL3-"].update(disabled=True)
            param.CustomEnabledFlag = False
            param.CustomEnabled1 = False
            param.CustomLabel1 = ''

        if statusparam.internalRunMonitor == True or statusparam.internalRecordingStatus == True:
            window["-CUSTOMENABLED1-"].update(disabled=True)
            window["-CUSTOMLABEL1-"].update(disabled=True)
            window["-CUSTOMENABLED2-"].update(disabled=True)
            window["-CUSTOMLABEL2-"].update(disabled=True)
            window["-CUSTOMENABLED3-"].update(disabled=True)
            window["-CUSTOMLABEL3-"].update(disabled=True)
        else:
            window["-CUSTOMENABLED1-"].update(disabled=False)
            window["-CUSTOMLABEL1-"].update(disabled=False)


        # custom values were updated with button during the recording.
        #Note, without the button, chnages were immediate with half-typed values being used/passed.
        # therefore, the update button is a better option.  Also, the values can be entered before and event
        # and updated with the button at the appropraite time (stimulation, gas challenge, etc).
        if event == "-CUSTOMUPDATE-":
            #Check for custom values.
            statusparam.CustomValue1 = values["-CUSTOMVALUE1-"]
            statusparam.CustomValue2 = values["-CUSTOMVALUE2-"]
            statusparam.CustomValue3 = values["-CUSTOMVALUE3-"]

            if param.CustomEnabled1 == True:
                customstring = statusparam.CustomValue1.replace(" ","")
                if param.CustomEnabled2 == True:
                    customstring = customstring + "," + statusparam.CustomValue2.replace(" ","")
                    if param.CustomEnabled3 == True:
                        customstring = customstring + "," + statusparam.CustomValue3.replace(" ","")

                if statusparam.captureProcessStarted == True:
                    if statusparam.captureProcess.is_alive():
                        statusparam.ParentToCaptureQueue.put(customstring)
        # except:
        #     pass

    window.close()  #quit the main process if the while loop is broken. Ends program and therefore kills child processes.


"""
Get/Set Configuration
"""
def getSARecorderConfig(param):
    config = ConfigParser()
    try:
        if os.path.exists(param.configfile):
            config.read(param.configfile)
            param.SelectedChannelMetrics[0] = config['Main']['DAC1']
            param.SelectedChannelMetrics[1] = config['Main']['DAC2']
            param.SelectedChannelMetrics[2] = config['Main']['DAC3']
            param.SelectedChannelMetrics[3] = config['Main']['DAC4']
            param.SelectedChannelMetrics[4] = config['Main']['POETANALOG']
            param.SelectedChannelMetrics[5] = config['Main']['GRASS']
            param.SelectedChannelMetrics[6] = config['Main']['HAPUMP']
            param.SamplePeriod = float(config['Main']['SamplePeriod'])
            param.CustomLabel1 = config['Main']['CUSTOMLABEL1']
            param.CustomLabel2 = config['Main']['CUSTOMLABEL2']
            param.CustomLabel3 = config['Main']['CUSTOMLABEL3']
            param.CustomEnabled1 = config['Main']['CUSTOMENABLED1'] == 'True'
            param.CustomEnabled2 = config['Main']['CUSTOMENABLED2'] == 'True'
            param.CustomEnabled3 = config['Main']['CUSTOMENABLED3'] == 'True'
            param.windowX = float(config['Main']['WINDOWX'])
            param.windowY = float(config['Main']['WINDOWY'])

        #else: these will stay as defaults
    except:
        pass

    #remove any value from recording with None setting for the current channel set
    param.currentChannelMetricList = []
    param.currentChannelConfigList = []
    param.currentChannelPositiveList = []
    for i in range(len(param.SelectedChannelMetrics)):
        if not param.SelectedChannelMetrics[i] == 'None':
            param.currentChannelMetricList.append(param.SelectedChannelMetrics[i])
            param.currentChannelConfigList.append(param.ChannelConfig[i])
            param.currentChannelPositiveList.append(param.ChannelPositive[i])

    return param


def setSARecorderConfig(values, param):
    parser = ConfigParser()
    parser['Main'] = {}
    parser['Main']['DAC1'] = values['-DAC1-'][0]
    parser['Main']['DAC2'] = values['-DAC2-'][0]
    parser['Main']['DAC3'] = values['-DAC3-'][0]
    parser['Main']['DAC4'] = values['-DAC4-'][0]
    parser['Main']['POETANALOG'] = values['-POETANALOG-'][0]
    parser['Main']['GRASS'] = values['-GRASS-'][0]
    parser['Main']['HAPUMP'] = values['-HAPUMP-'][0]
    parser['Main']['SamplePeriod'] = values['-SamplePeriod-']
    parser['Main']['CUSTOMLABEL1'] = values['-CUSTOMLABEL1-']
    parser['Main']['CUSTOMLABEL2'] = values['-CUSTOMLABEL2-']
    parser['Main']['CUSTOMLABEL3'] = values['-CUSTOMLABEL3-']
    parser['Main']['CUSTOMENABLED1'] = str(values['-CUSTOMENABLED1-'])
    parser['Main']['CUSTOMENABLED2'] = str(values['-CUSTOMENABLED2-'])
    parser['Main']['CUSTOMENABLED3'] = str(values['-CUSTOMENABLED3-'])
    parser['Main']['CUSTOMENABLED2'] = str(values['-CUSTOMENABLED2-'])
    parser['Main']['CUSTOMENABLED3'] = str(values['-CUSTOMENABLED3-'])
    parser['Main']['WINDOWX'] = str(param.windowX)
    parser['Main']['WINDOWY'] = str(param.windowY)
    with open(param.configfile, "w") as fp:
        parser.write(fp)


"""
Functions for the GUI monitoring window
"""
def guisetup(param):

    layoutTop = [[sg.Text("Sample Period (sec)",size=[20,1]), sg.Input(size=(10, 1), background_color='white', enable_events=True, default_text=str(param.SamplePeriod), key="-SamplePeriod-")]]

    #two rows, labels and selectors.
    layoutChannels = [[sg.Text('DAC1 (PC-SAM)',size=[14,1], justification='center'),
                        sg.Text("DAC2 (PC-SAM)",size=[14,1], justification='center'),
                        sg.Text("DAC3 (PC-SAM)",size=[14,1], justification='center'),
                        sg.Text("DAC4 (PC-SAM)",size=[14,1], justification='center'),
                        sg.Text("Poet (Gas)",size=[14,1], justification='center'),
                        sg.Text("GRASS (Stim)",size=[14,1], justification='center'),
                        sg.Text("Pump (Infusion)",size=[14,1], justification='center')],
                        [sg.Listbox(values=param.RateOptionsList, default_values=[param.SelectedChannelMetrics[0],], enable_events=True, size=(12, 7), key="-DAC1-"),
                        sg.Listbox(values=param.RateOptionsList, default_values=[param.SelectedChannelMetrics[1],], enable_events=True, size=(12, 7), key="-DAC2-"),
                        sg.Listbox(values=param.RateOptionsList, default_values=[param.SelectedChannelMetrics[2],], enable_events=True, size=(12, 7), key="-DAC3-"),
                        sg.Listbox(values=param.RateOptionsList, default_values=[param.SelectedChannelMetrics[3],], enable_events=True, size=(12, 7), key="-DAC4-"),
                        sg.Listbox(values=param.PoetOptionsList, default_values=[param.SelectedChannelMetrics[4],], enable_events=True, size=(12, 7), key="-POETANALOG-"),
                        sg.Listbox(values=param.GRASSOptionsList, default_values=[param.SelectedChannelMetrics[5],], enable_events=True, size=(12, 7), key="-GRASS-"),
                        sg.Listbox(values=param.HAPumpOptionsList, default_values=[param.SelectedChannelMetrics[6],], enable_events=True, size=(12, 7), key="-HAPUMP-")]]

    layoutCustomBox = [[sg.Text('',size=[14,1], justification='center'),
                        sg.Text('Custom1',size=[14,1], justification='center'),
                        sg.Text("Custom2",size=[14,1], justification='center'),
                        sg.Text("Custom3",size=[14,1], justification='center')],
                        [sg.Text('Enabled?',size=[14,1], justification='right'),
                        sg.Text('',size=[3,1]),
                        sg.Checkbox("", size=(11, 1), default=param.CustomEnabled1, enable_events=True, key="-CUSTOMENABLED1-"),
                        sg.Checkbox("",size=(11, 1), default=param.CustomEnabled2, disabled=True, enable_events=True, key="-CUSTOMENABLED2-"),
                        sg.Checkbox("",size=(11, 1), default=param.CustomEnabled3, disabled=True, enable_events=True, key="-CUSTOMENABLED3-")],
                        [sg.Text('Labels',size=[14,1], justification='right'),
                        sg.Input(size=(14, 1), background_color='white', enable_events=True, default_text=param.CustomLabel1, key="-CUSTOMLABEL1-"),
                        sg.Input(size=(14, 1), background_color='white', disabled=True, enable_events=True, default_text=param.CustomLabel2, key="-CUSTOMLABEL2-"),
                        sg.Input(size=(14, 1), background_color='white', disabled=True, enable_events=True, default_text=param.CustomLabel3, key="-CUSTOMLABEL3-")],
                        [sg.Text('Values',size=[14,1], justification='right'),
                        sg.Input(size=(14, 1), background_color='white', enable_events=True, default_text=str("0.0"), key="-CUSTOMVALUE1-"),
                        sg.Input(size=(14, 1), background_color='white', disabled=True, enable_events=True, default_text=str(""), key="-CUSTOMVALUE2-"),
                        sg.Input(size=(14, 1), background_color='white', disabled=True, enable_events=True, default_text=str(""), key="-CUSTOMVALUE3-"),
                        sg.Button("Update ",key='-CUSTOMUPDATE-',size=[14,1])]]

    layoutStatus = [
                [sg.Text("Labjack Status:", size=[16,1]), sg.Text("Not Connected", size=[80,1], key="-LJSTATUS-", text_color='black', background_color='white')],
                [sg.Text("Recording Status:", size=[16,1]), sg.Text("IDLE", size=[80,1], key="-STATUS-", text_color='black', background_color='white')],
                [sg.Text("Paravision Status:", size=[16,1]), sg.Text("IDLE", size=[80,1], key='-PVSTATUS-', text_color='black', background_color='white')],
                [sg.Text("Data Path:", size=[16,1]), sg.Text("None", size=[80,1], key='-LOGPATH-', text_color='black', background_color='white')],
                [sg.Text(" ", size=[140,1], key='-EMPTY-', font='courier 10')],
                [sg.Text(" ", size=[140,1], key='-LOGHEADERWINDOW-', font='courier 10 bold')],
                [sg.Multiline(default_text='', size=[140,14], key='-LOGWINDOW-', autoscroll=True, text_color='black', background_color='white',font='courier 10')]
                 ]
    layoutActions = [
                #[sg.Text("Low Volt LJ Inputs (FIO)"),sg.Listbox(values=['True','False'], default_values=[useFIOinputs,], enable_events=True, size=(10, 4), key="-useFIOinputs-")],
                [sg.Button("Save Settings",key='-UPDATE-',size=[14,1]),
                sg.Button("Per Scan Recording",key='-RECORD-',button_color=('black','green'),size=[14,1]),
                sg.Button("Continuous Recording",key='-RUNMONITOR-',button_color=('white','blue'),size=[14,1]),
                sg.Button("Quit",size=[14,1])]]


    layoutFull = [[sg.Frame(layout=layoutTop, title='General')], [sg.Frame(layout=layoutChannels, title='Channels')], [sg.Frame(layout=layoutCustomBox, title='Custom',size=[80,1])], [sg.Frame(layout=layoutStatus, title='Status')], [sg.Frame(layout=layoutActions, title='')]]
    # Create the window
    window = sg.Window("PhysioRecording", layoutFull, location=(param.windowX, param.windowY))
    window.Finalize()
    window.TKroot.focus_force()

    return window

"""
Functions for checking on Paravision status or other features
"""
def checkPVconfig():
    # test for pvcmd functionality, returns with command not found if unsuccessful
    cmd="pvcmd -a ParxServer -r ListPs "
    process = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    dummyOut, error = process.communicate()

    if "command not found"  in dummyOut:
        print("Start this program from a Terminal window started from Paravision")
        print("It will not work from any terminal.")
        print("pvcmd try unsuccessful.")
        print("Quitting")
        exit()


def MonitorPVstatus(param, statusparam):

    #if statusparam.internalRunMonitor == True:
    #    return statusparam

    try:
        #this gets the data path associated with the GUI creator
        cmd="pvcmd -a ParxServer -r ListPs | grep 'DSET PATH' | awk '{printf(\"%s\", $3)}'"
        process = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        dsetpath, error = process.communicate()
	    #print(dsetpath)
        statusparam.studypath = dsetpath.split('pdata')[0]
        statusparam.datapath = statusparam.studypath.rstrip('/') #remove the trailing slash
        statusparam.datapath = statusparam.datapath.rsplit('/',1)[0] #remove the last expno 

        if (statusparam.datapath == None) or (statusparam.datapath == ""):
            statusparam.datapath = param.homedir
            statusparam.studypath = param.homedir

        #cmd="pvcmd -a ParxServer -r DsetGetPath -psid " + gui_psid + " -path STUDY"
        #process = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        #statusparam.studypath, error = process.communicate()
        # print(statusparam.studypath)
    except:
        statusparam.studypath = param.homedir
        statusparam.datapath = statusparam.studypath

    #this gets the scan that is currently running since it was started from the 'pipemaster' parent
    cmd="pvcmd -a ParxServer -r ListPs | grep -B 3 'pipeMaster' | grep -m 1 PSID | awk '{printf(\"%s\", $2)}'"
    process = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    statusparam.psid, error = process.communicate()
    #print(statusparam.psid)

    if len(statusparam.psid)>0:
        try:
            #print "Scan Active, PSID: "+psid
            cmd="pvcmd -a ParxServer -r DsetGetPath -psid "+statusparam.psid+" -path EXPNO"
            process = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            statusparam.datapath, error = process.communicate()
            statusparam.datapath = statusparam.datapath.split('pdata')[0] #if pdata exists remove everything after
            statusparam.datapath = statusparam.datapath.rstrip('/')
            print(statusparam.datapath)
            pathlist=string.rsplit(statusparam.datapath,'/',1)
            expno=pathlist[1]
            statusparam.expno = expno
            statusparam.datapath = pathlist[0] #now get the main subject path


            cmd="pvcmd -a ParxServer -r ParamGetValue -psid "+statusparam.psid+" -param SUBJECT_study_instance_uid"
            process = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            studyRegID, error = process.communicate()


            cmd="pvcmd -a ParxServer -r ParamGetValue -psid "+statusparam.psid+" -param ACQ_scan_type"
            process = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            statusparam.experimentstatus, error = process.communicate()
            # print(statusparam.experimentstatus)
            statusparam.experimentstatus = statusparam.experimentstatus.split("_")[0] #Scan or Setup
            if not (statusparam.experimentstatus in ["Scan","Setup"]):
                 statusparam.experimentstatus = 'Idle'
            #    return statusparam

            cmd="pvcmd -a JPingo -r DSetServer.GetScanStatus -registration "+studyRegID+" -expno "+expno
            process = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            statusparam.scanstatus, error = process.communicate()
            if not (statusparam.scanstatus in ["SCANNING","RECO","ADJUST"]):
                 statusparam.scanstatus = 'Idle'
            #    return statusparam
        except:
            statusparam.expno = '0'
            statusparam.scanstatus = "Idle"
            statusparam.experimentstatus = "Idle"
            return statusparam

        if statusparam.internalRunMonitor == True:
            if statusparam.captureProcessStarted == False:
                StartRecording(param, statusparam)
            if statusparam.captureProcessStarted == True:
                UpdateRecording(param, statusparam)
            return statusparam

        if statusparam.internalRecordingStatus == True:
            if statusparam.datapath != statusparam.prevDset:
                statusparam.newscan = 1

            if statusparam.newscan==1 and (statusparam.scanstatus=="SCANNING" or statusparam.scanstatus == "RECO") and (statusparam.experimentstatus == "Scan"):
                StartRecording(param, statusparam)

    else:
        statusparam.scanstatus = "Idle"
        statusparam.experimentstatus = "Idle"
        statusparam.expno = '0'
        if statusparam.internalRecordingStatus == True:
            # print('Recording; Stopping')
            StopRecording(param, statusparam)

        if statusparam.internalRunMonitor == True:
            if statusparam.captureProcessStarted == True:
                UpdateRecording(param, statusparam)


    return statusparam


def FormattedLine(headerList,dataList):
    # Calculate the maximum width for each column
    widths = [
        max(len(str(item[i])) for item in [headerList])
        for i in range(len(headerList))
    ]
       
    header_line = " | ".join([
        "{:<{width}}".format(dataList[i], width=widths[i])
        for i in range(len(dataList))
    ])
    return header_line


def StartRecording(param, statusparam):

    if statusparam.internalRecordingStatus == True:
        dstr=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        statusparam.logPath = statusparam.datapath+"/PhysioRecordingLog"+dstr+".txt"
        try:
            statusparam.fileHandle = open(statusparam.logPath,"w",buffering=0)
        except:
            param.LogWindow.update("Could not open logging file\n", append=True)
            print(statusparam.logPath)
            return statusparam
        #print "Starting Process:\nLogging to "+statusparam.logPath
        param.LogWindow.update("Starting Process:\nLogging to "+statusparam.logPath + "\n", append=True)
    
    if statusparam.internalRunMonitor == True and statusparam.captureProcessStarted == False:
        param.AddExpAndStatus = True
        dstr=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        if statusparam.studypath == '' or statusparam.studypath == None:
            statusparam.logPath = param.homedir+"/PhysioRecordingLog"+dstr+".txt"
        else:
            statusparam.logPath = statusparam.datapath+"/PhysioRecordingLog"+dstr+".txt"

        try:
            statusparam.fileHandle = open(statusparam.logPath,"w",buffering=0)
        except:
            param.LogWindow.update("Could not open logging file\n", append=True)
            print(statusparam.logPath)
            return statusparam
        #print "Starting Process:\nLogging to "+statusparam.logPath
        param.LogWindow.update("Starting Process:\nLogging to "+statusparam.logPath + "\n", append=True)

    # else:
    #     dstr=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    #     statusparam.logPath = param.homedir + "/PhysioRecordingLog"+dstr+".txt" # os.devnull
    #     statusparam.datapath = statusparam.logPath
    #     #statusparam.fileHandle = open(statusparam.logPath,"w",buffering=0)
    #     try:
    #         statusparam.fileHandle = open(statusparam.logPath,"w",buffering=0)
    #     except:
    #         param.LogWindow.update("Could not open logging file\n", append=True)
    #         return statusparam
	  
    #     #print "Starting Process:\nLogging to "+statusparam.logPath



    # Update the header in the gui, do this here so no need to communicate via a queue.
    headerList = ["Count", "TimeMS"]

    if param.AddExpAndStatus == True:
        headerList.extend(["ScanStat","ExpStat","Exp"])
    # No spaces in custom values allowed.
    if param.CustomEnabledFlag == True:
        headerList.append(param.CustomLabel1.replace(" ", ""))
        if param.CustomEnabled2 == True:
            headerList.append(param.CustomLabel2.replace(" ", ""))
            if param.CustomEnabled3 == True:
                headerList.append(param.CustomLabel3.replace(" ", "")) 

    headerList.extend(param.currentChannelMetricList)
    headerList.append("Warnings")
    headerOut = FormattedLine(headerList, headerList)
    param.LogHeaderWindow.update(headerOut)


    #start the logger in a separate process
    statusparam.ParentToCaptureQueue  = Queue()
    statusparam.CaptureToParentQueue = Queue()
    p = Process(target=CaptureAndWriteLog, args=(statusparam.fileHandle, param, statusparam.ParentToCaptureQueue, statusparam.CaptureToParentQueue))
    statusparam.recordingstatus = "Recording"
    statusparam.captureProcess = p
    statusparam.captureProcess.start()
    statusparam.captureProcessStarted = True
    #p.join() # this blocks until the process terminates, which we don't want
    statusparam.prevDset=statusparam.datapath
    statusparam.newscan=0

    #Include experiment number and scan status if continuous logging
    if param.AddExpAndStatus == True:
        customstring = statusparam.scanstatus + "," + statusparam.experimentstatus + "," + statusparam.expno
    else:
        customstring = ""

    # No spaces in custom values allowed.
    if param.CustomEnabled1 == True:
        customstring = customstring + "," + statusparam.CustomValue1.replace(" ","")
        if param.CustomEnabled2 == True:
            customstring = customstring + "," + statusparam.CustomValue2.replace(" ","")
            if param.CustomEnabled3 == True:
                customstring = customstring + "," + statusparam.CustomValue3.replace(" ","")
        
    if (param.AddExpAndStatus == True) or (param.CustomEnabled1 == True):    
        # Overwrite the status in the queue by removing the old one if needed
        #while not statusparam.ParentToCaptureQueue.empty():
        #    statusparam.ParentToCaptureQueue.get_nowait()  # Remove the current items to replace it
	while True:
	    try:
        	statusparam.ParentToCaptureQueue.get_nowait()  # Remove the current items to replace it
	    except: # Queue.Empty:
		break
        statusparam.ParentToCaptureQueue.put(customstring)

    return statusparam


def UpdateRecording(param, statusparam):
    statusparam.recordingstatus = "Recording"
    if statusparam.captureProcess.is_alive()==1:
        #Include experiment number and scan status if continuous logging
        if param.AddExpAndStatus == True:
            customstring = statusparam.scanstatus + "," + statusparam.experimentstatus + "," + statusparam.expno
        else:
            customstring = ""

        # No spaces in custom values allowed.
        if param.CustomEnabled1 == True:
            customstring = customstring + "," + statusparam.CustomValue1.replace(" ","")
            if param.CustomEnabled2 == True:
                customstring = customstring + "," + statusparam.CustomValue2.replace(" ","")
                if param.CustomEnabled3 == True:
                    customstring = customstring + "," + statusparam.CustomValue3.replace(" ","")
            
        if (param.AddExpAndStatus == True) or (param.CustomEnabled1 == True):   
            #while not statusparam.ParentToCaptureQueue.empty():
            #    statusparam.ParentToCaptureQueue.get_nowait()  # Remove the current items to replace it 
	    # the old while/get_nowait code was throwing errors and halding the program.
	    # this while/try/except loop seems to be the more preferred option to handle emptying more directly and safely.  Needs to be tested to determine if it works.
	    while True:
	        try:
        	    statusparam.ParentToCaptureQueue.get_nowait()  # Remove the current items to replace it
	        except:# Queue.empty:
		    break
            statusparam.ParentToCaptureQueue.put(customstring)
    
    return statusparam



def StopRecording(param, statusparam):
    statusparam.recordingstatus = "Monitoring"
    statusparam.scanstatus = 'Idle'
    statusparam.experimentstatus = 'Idle'
    try:
        if statusparam.captureProcess.is_alive()==1:
            param.LogWindow.update("Stopped Logging.\n", append=True)
            statusparam.captureProcess.terminate()
    except:
        pass
    try:
        if statusparam.fileHandle.closed==0:
            statusparam.fileHandle.close()
    except:
        pass
    try:
        statusparam.CaptureToParentQueue.close()
        statusparam.ParentToCaptureQueue.close()
    except:
        pass
    statusparam.captureProcessStarted = False
    statusparam.prevDset=""

    return statusparam


"""
Functions for recording of values through the labjack
"""
def openandConfigureU3(param):
    print("Trying to open LabJack U3 device.\n")
    param.isU3 = False
    try:
        param.deviceU3 = u3.U3()  # Opens first found U3 over USB; this does an auto open

        if isinstance(param.deviceU3, u3.U3):
            # Configure all FIO and EIO lines to analog inputs.
            #AnalogConfig = param.deviceU3.configIO(FIOAnalog=0xFF, EIOAnalog=0xFF)
            AnalogConfig = param.deviceU3.configIO()
            print(AnalogConfig)
            param.isU3 = True

            # Check if the U3 is an HV
            if param.deviceU3.configU3()['VersionInfo'] & 18 == 18:
                param.isHV = True
                param.lowVoltage = False
            else:
                param.isHV = False
                param.lowVoltage = True

            param.deviceU3.getCalibrationData()
            print(param.deviceU3.calData)
		
            print("LabJack U3 device Enabled.\n")
    except:
        print("LabJack U3 device failed to enable.\n")
        param.isU3 = False
    print(param)


    # Configure the device appropriately for the values to measure.
    # in hindsigt, this wasn't necessary since we could enable all 5 connected channels
    # and simply only poll the ones wanted from their configuration.
    #if param.isU3 == True:
        #param = getSARecorderConfig(param)
        #param.nChannels = len(param.currentChannelMetricList)
        #argList = []
        #for i in range(param.nChannels):
	    #argList.append(param.currentChannelConfigList[i])
	    #print(argList)
	    
        #print("Configuring LabJack.\n")
        #AnalogConfig = param.deviceU3.configAnalog(*argList)
	              
    
    
    #for ii in [0, 1, 2, 3]:
        #sl, off = param.deviceU3.getCalibratedSlopeOffset(False, True, False, ii)
        #print("channel " + ii + " slope: " + str(sl) + " offset: " + str(off))
  

    return param


# this is the function called as a new thread with  multiprocessing.
#fd is the log file file handle.
#param is the static parameters.
#p2cQ is the paraent->capture messaging queue; custom values get read from here (just a preformatted string)
#c2pQ is the capture->parent messaging queue; strings sent to the parent for display in the gui, in addition to  recording to file.
#c2pHeadQ is the capture->parent messaging queue; strings sent to the parent for display in the gui as a header line.
def CaptureAndWriteLog(fd, param, p2cQ, c2pQ):
    #get recording configuration and setup output lists

    nChannels = len(param.currentChannelMetricList)
    results = [0] * nChannels
    resultsCalibratedInteger = [0.0] * nChannels
    resultsCalibratedVoltage = [0.0] * nChannels
    warningstr = [' ']*nChannels #used for warnings of values outside of plausible ranges

    #Setup the loop and timing values
    ptime=time.time()
    starttime=ptime

    # Write the header, this is simply csv formatted
    headerString = "Count, TimeMS, "
    headerString = headerString + ", ".join(param.currentChannelMetricList)
    
    if param.AddExpAndStatus == True:
        headerString = headerString + ", Status, ExpStatus, Exp"

    if param.CustomEnabledFlag == True:
        headerString = headerString + ", " + param.CustomLabel1.replace(" ", "")
        if param.CustomEnabled2 == True:
            headerString = headerString + ", " + param.CustomLabel2.replace(" ", "")
            if param.CustomEnabled3 == True:
                headerString = headerString + ", " + param.CustomLabel3.replace(" ", "")

    fd.write(headerString+'\n')
    #print(headerString)

    # Write the header, this is formatted for easier gui readability
    headerList = ["Count", "TimeMS"]
    if (param.AddExpAndStatus == True):
        headerList.extend(['ScanStat','ExpStat','Exp'])
    if param.CustomEnabledFlag == True:
        headerList.append(param.CustomLabel1.replace(" ", ""))
        if param.CustomEnabled2 == True:
            headerList.append(param.CustomLabel2.replace(" ", ""))
            if param.CustomEnabled3 == True:
                headerList.append(param.CustomLabel3.replace(" ", "")) 
    headerList.extend(param.currentChannelMetricList)
    headerList.append("Warnings")
    headerOut = FormattedLine(headerList, headerList)

    c2pQ.put(headerOut + '\n')
    #param.LogWindow.update(headerString + '\n', append=True)
    #time.sleep(param.SamplePeriod) # do a delay here so the first measurement is at 1 sample period

    # here, the sampling rate is also adjusted to account for delays in processing by estimating the expected and actual delays
    sleepDelayAdjusted = param.SamplePeriod
    elapsedTimePredicted = 0
    currIter = 0
    seperator = ', '
    currcustomstr = ''
    while 1:

        # Get the current time
        ntime=time.time()
        nowtime=(ntime - starttime)
        elapsedms=str("%.01f" % nowtime )

        # Setup data to monitor
        dataList=[str(currIter), elapsedms]

        if param.isU3 == True:
            #Sample all channels simultaneously in a single command
            ainCommand = [None] * nChannels
            for i in range(nChannels):
                ainCommand[i] = u3.AIN(PositiveChannel=param.currentChannelPositiveList[i] , NegativeChannel=31 , QuickSample=False, LongSettling=True)
            results =  param.deviceU3.getFeedback(ainCommand)
            #print(results)

            #print("debug:")
            for i in range(nChannels):
                #if (param.isHV) and (param.currentChannelPositiveList[i] < 4):
                    #localisLowVoltage = True #channels 0-3 are the high voltage channels.
                #else:
                    #localisLowVoltage = True #all others are low 0-2.4 V
                    
                #print(results[i])
                resultsCalibratedVoltage[i] = param.deviceU3.binaryToCalibratedAnalogVoltage(results[i], isLowVoltage=True, channelNumber=param.currentChannelPositiveList[i])
                
                resultsCalibratedInteger[i], warningstr[i] = convertCalibratedVoltagetoValue(resultsCalibratedVoltage[i], param.currentChannelMetricList[i], param.currentChannelPositiveList[i])
                #print("")
                
                
            #print(param.currentChannelPositiveList)
            #print(resultsCalibratedVoltage)
            #Convert values to appropriate readings for each channel
            #for i in range(nChannels):
            #    resultsCalibratedInteger[i], warningstr[i] = convertInttoValue(results[i], param.currentChannelMetricList[i], param.currentChannelPositiveList[i])
        else:
            # this is redundant, but do it for clarity
            resultsCalibratedInteger = [0.0] * nChannels

        # Write out all data to the file 
        datastring = ['0']  * nChannels
        for n in range(len(resultsCalibratedInteger)):
            datastring[n] = '{:.3f}'.format(resultsCalibratedInteger[n])

        
        rowstring=str(currIter) + ", " + elapsedms + ", " + seperator.join(datastring)

        if (param.CustomEnabledFlag == True) or (param.AddExpAndStatus == True):
            try:
                currcustomstr = p2cQ.get(block=False)
                # print(currcustomstr)
            except:
                pass

            if (param.AddExpAndStatus == True):
                expstatlist = currcustomstr.split(",")[0:3]
                customlist = currcustomstr.split(",")[3:]
                dataList.extend(expstatlist)
                dataList.extend(customlist)
            else:
                customlist = currcustomstr.split(",")
                dataList.extend(customlist)

            rowstring = rowstring + ", " + currcustomstr
        fd.write(rowstring+'\n') #print to file with newline


        # print(dataList)
        # Data to monitor
        for n in range(len(resultsCalibratedInteger)):
            dataList.append('{:.1f}'.format(resultsCalibratedInteger[n]))

        dataList.append(' '.join(warningstr))
        try:
            dataOut = FormattedLine(headerList, dataList)

            #warnings are displayed in the dynamic output, but not saved to the file.
            c2pQ.put(dataOut + '\n')
        except:
            print('Formatting Error. Skipping')

        # Adjust the sleep time to account for processing delays to try and maintain the sample period accuracy
        # basically, adjust the delay based on the expected and actual time of the last recording.
        elapsedTimePredicted = param.SamplePeriod * currIter
        sleepDelayAdjusted = param.SamplePeriod - (nowtime - elapsedTimePredicted)
        if sleepDelayAdjusted < 0:
            sleepDelayAdjusted = 0

        time.sleep(sleepDelayAdjusted)

        #update the number of iterations
        currIter = currIter + 1


#def convertInttoValue(value,metric,channel):
    ##will need to test and build these out for more options.

    ##The U3-HV device measures -10 to +10 Volts and converts to a 16-bit unsigned integer.
    ##All data from the SAI breakout box is 0 to +5 Volts (12-bit conversion)
    ##so 2^16 / 2 is 32768; subtract this from all values to get 0=0.
    ## We could use the labjack calibration to convert integer to voltages, but that is unnecessary since we'd have to reconvert to values anyway.

    ## There might need to be some additional calibration or other refinements that go into this setup.
    ## most of the values were found emperically and don't entirely make logical sense.
    #warningstr = ''

    #### SA Instruments Connections from Breakout Box ###
    #if metric == "T1Temp":
        #result = (value - 32768)/180.0
                ##temp is in celcius as value/180 according to the SA manual.
        #if result < 0:
            #warningstr = 'Neg Temp'
    #elif metric == "PRespRate":
        #result = (value - 32944)/8.0 * 5.0/10.0
                ##rates are supposed to be BPM/count, but the 32944 is the lowest value empirically for respiration
                ##also unclear is why the /16.0 is necessary, but this also works empirically.
                ##it may be due to the 12 to 16 bit conversion, which is a factor of 16 (2^4).
        #if result < 0:
            #warningstr = 'Neg Resp Rate'
    #elif metric == "ECGRate":
        #result = (value - 32944)/8.0 * 5.0/10.0
                ##not tested.
        #if result < 0:
            #warningstr = 'Neg ECG Rate'
    #elif metric == "PRespPeriod":
        #result = (value - 32944)/8.0 * 5.0
    #elif ((metric == "BP2Rate") or (metric == "BP3Rate") or (metric == "BP1Rate")):
        #bp2rateoffset = -112
        #result = (value - 32768 + bp2rateoffset)/8.0 * 5.0/10.0
                ##not tested.
    #elif ((metric == "BP2Mean") or (metric == "BP3Mean") or (metric == "BP1Mean")):
        #bp2meanoffset = -48
        #result = ((value - 32768 + bp2meanoffset)/8 * 5.0/10. - 90 ) / 3.
                ##not tested.
  

    #### POET Gas analyzer conditions ###
    #elif metric == "IsoLevel":
        ##it appears that the integer to voltage conversion is simply int/8194, which means a value of iso=4 is 2.4 volts (12-bit).
        ##need to test to confirm.
        ##note that with the FIO connections, values are from 0-2.4V, Not -/+.
        #result = (value)/8194.0  #old: 10000.0*0.822 #scaling determined from testing = 1/1.21 and manual recording of read values to Poet displayed values, so approximate.
        #if result > 5:
            #warningstr = 'High Iso'
    #elif metric == "O2":
        #result = (value)/1000.0
        #if result < 17:
            #warningstr = 'Low O2'
    #elif metric == "CO2":
        #result = (value)/1000.0
        #if result < 17:
            #warningstr = 'Low O2'
  
    #### GRASS stimulator, not tested or setup with hardware ###
    #elif metric == "ControlLine":
        #if (value > 32768):
            #result = 1
        #else:
            #result = 0
  
    #### Harvard Apparatus Syringe Injection Pump ###
    #elif metric == "PumpStat": #Syringe pump injector, the 3 pin of the 9-pin output is high-running, low-not running.
        #if (value > 16384):  #need to test after setting up connections
            #result = 1
        #else:
            #result = 0
    #else:
        #result = (value - 32768)/1.0

    #return result, warningstr



def convertCalibratedVoltagetoValue(value,metric,channel):
    #will need to test and build these out for more options.

    #The U3-HV device measures -10 to +10 Volts and converts to a 16-bit unsigned integer.
    #All data from the SAI breakout box is 0 to +5 Volts (12-bit conversion)
    #so 2^16 / 2 is 32768; subtract this from all values to get 0=0.
    # We could use the labjack calibration to convert integer to voltages, but that is unnecessary since we'd have to reconvert to values anyway.

    # There might need to be some additional calibration or other refinements that go into this setup.
    # most of the values were found emperically and don't entirely make logical sense.
    warningstr = ''

    #print(value)

    ### SA Instruments Connections from Breakout Box ###
    if metric == "T1Temp":
        T1TempOffset = 0 #0.006
        result = (value - T1TempOffset) * (4096/5.0*4.0) /180.0
        #temp is in celcius as value/180 according to the SA manual.
        if result < 0:
            result = 0
        result = round(result,1)
    elif metric == "PRespRate":
        PRespRateOffset = 0.006
        result = (value - PRespRateOffset) * (4096/5.0/4.0)
                #rates are supposed to be BPM/count, but the 32944 is the lowest value empirically for respiration
        if result < 0:
            result = 0
        result = round(result,0)
    elif metric == "ECGRate":
        ECGRateOffset = 0.006
        result = (value - ECGRateOffset) * (4096/5.0/4.0)
        #not tested.
        if result < 0:
            warningstr = 'Neg ECG Rate'
    elif metric == "PRespPeriod":
        PRespPeriodOffset = 0.006
        result = (value - PRespPeriodOffset) * (4096/5.0*4.0)
    elif ((metric == "BP2Rate") or (metric == "BP3Rate") or (metric == "BP1Rate")):
	#14-bit; 1 BPM/count 
        result = value * (4096/5.0/4.0)
        #not tested.
    elif ((metric == "BP2Mean") or (metric == "BP3Mean") or (metric == "BP1Mean") or ('Systol' in metric) or ('Diastol' in metric)):
        print(value)
	VOffset = 0.006
        result = (((value-VOffset) * (1024/5.0)) - 90 ) / 3.0
	#10-bit; 90 counts = 0 mmHg; 3 mmHg/count 
        #not tested.
  

    ### POET Gas analyzer conditions ###
    elif metric == "Iso":
        #it appears that the integer to voltage conversion is iso=4 to 2.4 volts (12-bit).
        #need to test to confirm.
        #note that with the FIO connections, values are from 0-2.4V, Not -/+.
        result = (value)/2.4 * 8  #old: 10000.0*0.822 #scaling determined from testing = 1/1.21 and manual recording of read values to Poet displayed values, so approximate.
        if result > 5:
            warningstr = 'High Iso'
        result = round(result,2)
    elif metric == "O2":
        #not tested
        result = (value)/1000.0
        if result < 17:
            warningstr = 'Low O2'
    elif metric == "CO2":
        #not tested
        result = (value)/1000.0
        if result > 10:
            warningstr = 'High CO2'
  
    ### GRASS stimulator, not tested or setup with hardware ###
    elif metric == "ControlLine":
        #not tested
        if (value > 0.8):
            result = 1
        else:
            result = 0
  
    ### Harvard Apparatus Syringe Injection Pump ###
    elif metric == "PumpStat": #Syringe pump injector, the 3 pin of the 9-pin output is high-running, low-not running.
        if (value > 0.8):  #need to test after setting up connections
            result = 1
        else:
            result = 0
    else:
        result = (value - 32768)/1.0

    return result, warningstr




"""
Start of Main function
"""


if __name__ == "__main__":
    main()
