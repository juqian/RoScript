# roscript #

The RoScript test execution engine

## 1. Installation

- Tested Platform: 
   - Windows 10 x64
   - Python 3.6

- Robots
  
  -  [EBB command set](http://evil-mad.github.io/EggBot/ebb.html) compatible robots, e.g., AxiDraw V3
  
- Dependencies

  - OpenCV: computer vision library (tested on OpenCV 3.4.2.16)
  
    `Visual C++ Redistributable for Visual Studio 2015` may be required, or the following dll `API-MS-WIN-DOWNLEVEL-SHLWAPI-L1-1-0.DLL` may need to be downloaded from a site like [https://www.dll-files.com/](https://www.dll-files.com/ "https://www.dll-files.com/") and copied to `Python/Lib/site-packages/cv2`.
  
  - OpenCV-contrib: additional CV algorithms
  
  - others: see `requirements.txt 

- Code Structure

	```
	+ config     # configurations 
	+ rsc        # keyboard models and other resources
	+ demo       # cases for demonstration
	  + Iphone5S\iOS-Sys     
	    + config                       # backup of the configurations used for debugging
	    + images                       # the widget images
	    + temp                         # some runtime images
	    - send_sms.py                  # the test script
	    - send_sms.png                 # a graphical view of the test script
	- xxx.py     # source code
	- README.md
	```

## 2. Setting up the Hardware Devices

See [The Test Execution Guide](./doc/test_exec_guide.md) for more detail. 

## 3. Executing Test Scripts with RoScript

### 3.1 Setting parameters for the test device

Manually set parameters according to the used robots, including the serial port, the robot device name, etc.

### 3.2 Setting parameters for the subject under test

Manually or use the UI to automatically set parameters for the subject under test, e.g., a mobile phone.

### 3.3 Running Test Scripts

(1) Make sure the running environment has been properly set. 	  

```shell
set PYTHONHOME=C:\BLABLABLA\Python
set PYTHONPATH=%PYTHONHOME%\DLLs;%PYTHONHOME%\Lib\;%PYTHONHOME%\Lib\site-packages
set PATH=%PYTHONHOME%;%PYTHONHOME%\Scripts
```

(2) Add RoScript to the Python library

There are two ways:

   - by creating a link in the Python installation

​       Go to `Python/Lib/site-packages/`. Create a new file named `roscript.pth`. Copy the path of the `roscript` code folder to the file, such as:

	C:\BLABLABLA\RoScript

- by add `roscript` to `PYTHONPATH`

 ```shell
set PYTHONPATH=%PYTHONPATH%;C:\BLABLABLA\RoScript
 ```

(3) Run test script

Go to `demo\Iphone5S\iOS-Sys` and run `send_sms.py`.

```shell
cd demo\Iphone5S\iOS-Sys
python.exe send_sms.py
```

Then, there will be messages in the console showing that the instructions in `send_sms.py` were executed.

	[Virtual Debug] click('message.png'): Succeed!
	[Virtual Debug] click('write.png'): Succeed!
	[Virtual Debug] press keyboard('Iphone26key', '[123]'): Succeed!
	[Virtual Debug] press keyboard('Iphone9key', '13236569169'): Succeed!
	[Virtual Debug] click('message_input.png'): Succeed!
	[Virtual Debug] press keyboard('Iphone26key', 'test[Return]'): Succeed!
	[Virtual Debug] click('send.png'): Succeed!
	[Virtual Debug] reset_arms(): Succeed!
	[Virtual Debug] assert_exist('send_message.png'): Yes!

Meanwhile, there will be also log files generated under folder `demo\Iphone5S\iOS-Sys`

### 3.4 Virtual Debugging

One may run test script in a virtual debugging mode without a real robot. To run in virtual debug model, a sequence of robot captured photos of the subject device under test must be provided in the `temp` folder under the test script directory.

There are two ways to run in virtual debugging mode.

(1)  Enable virtual debugging by setting the configuration files

Copy `demo\Iphone5S\iOS-Sys\config` to folder `config` under the tool directory to recover the debugging enviornment.   
Go to `config\config.yaml`, set the `VirtualDebug` option to `true`.    
Then, run the test scripts like normal python code.

(2) Enable virtual debugging by providing addition command line parameters
```shell
cd demo\Iphone5S\iOS-Sys
python.exe send_sms.py -vd
# or
python.exe send_sms.py -vdf ./temp
```