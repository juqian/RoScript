## README

The RoScript recorder

### 1. Dependencies

(1) Make sure the running environment has been properly set. 	  

```shell
set PYTHONHOME=C:\BLABLABLA\Python
set PYTHONPATH=%PYTHONHOME%\DLLs;%PYTHONHOME%\Lib\;%PYTHONHOME%\Lib\site-packages
set PATH=%PYTHONHOME%;%PYTHONHOME%\Scripts
```

(2) Install dependencies


    python.exe -m ensurepip
    python.exe -m pip install --upgrade pip
    python -m pip install -r requirements.txt 

(2) Add RoScript to the Python library

There are two ways:

   - by creating a link in the Python installation

​       Go to `Python/Lib/site-packages/`. Create a new file named `roscript.pth`. Copy the path of the `roscript` code folder to the file, such as:

	C:\BLABLABLA\RoScript

- by add `roscript` to `PYTHONPATH`

 ```shell
set PYTHONPATH=%PYTHONPATH%;C:\BLABLABLA\RoScript 
 ```

### 2. Run ###

- Generate test script from video
```
	python record_script.py --src ./test.avi --export ./results/test --measure 78 155 
	                     --vtype dualCamera --keyboards ./keyboards/SAMSUNG_GALAXY_NOTE4
	Description：
		src -- the path of the input human action video
		export -- the directory to save the generated script
		measure -- the actual width and height of the device under test (in millimeters).
		vtype -- video type (`singleCamera` or `dualCamera`)
		keyboards -- directory containing the keyboard models (can be ignore if do not recognize keyboard actions)
		
	Outputs：
		+ frames
			- frame1.png
			- ...
		+ images
			- default.snapscreen
			- image1-1.png
			- image2-1.png
			- image2-2.png	
			- ...
		+ script.py
```

Demo:
```
python record_script.py --src demo\GoPro\single.avi --vtype singleCamera --export test\single --measure 58 40 
python record_script.py --src demo\GoPro\dual.avi --vtype dualCamera --export test\dual --measure 58 40 
```

Ensure no non-English character in the paths. 

