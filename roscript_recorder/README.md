## roscript_recorder

The RoScript test script recorder

## 1. Dependencies

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

## 2. Setting up the Recording Environment

See the [The Test Script Recording Guide](./doc/script_record_guide.md).

## 3. Record Scripts

- Generate test script from video (Ensure no non-English character in the paths)
```
	python record_script.py --i ./test.avi --o ./results/test --dev 78 155 
	                     --mode dualCamera --keyboards ./keyboards/SAMSUNG_GALAXY_NOTE4 -color_file color.yaml
	Description：
		i -- the input video path
		o -- the output directory
		dev -- the physical width and height of the device under test (in millimeters).
		mode -- the recording mode (`singleCamera` or `dualCamera`)
		keyboards -- directory containing the keyboard models (can be ignore if do not recognize keyboard actions)
		color_file -- a configuration file with the hand color range customed (otherwise use the default color range)
	    
		
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
		+ script.py.html
```

Demo:
```
python record_script.py --i demo\GoPro\single.avi --mode singleCamera --o test\single --dev 58 40 
python record_script.py --i demo\GoPro\dual.avi --mode dualCamera --o test\dual --dev 58 40 
```



