# ScratchFoot v0.1
A Scratch emulation layer in Greenfoot.

ScratchFoot provides a subclass of World and subclass of Actor which make available much of the functionality of Scratch in Greenfoot.  
Using ScratchFoot, you should be able to convert many Scratch programs to use Greenfoot.  This may be useful for

* overcoming limitations of Scratch.  E.g., when the Scratch canvas is just too small for your application, or when Scratch starts 
running too slowly because you have so many scripts running.
* making the transition from the simple (and wonderful) world of Scratch to the more real-world of Java programming.

ScratchFoot emulates the following nice features from Scratch:
* multiple scripts can be created for a Sprite.  Specifically, you can create multiple forever loops, multiple "when I receive message" scripts,
multiple "when key clicked" scripts, etc.  These scripts all seemingly run in parallel (just as in Scratch).
* clone sprites.
* ask for user input.
* do all the math, if statements, etc., but in Java syntax, which is much more compact.
* use wait(), glideTo(), etc.
* use multiple costumes, multiple backdrops, etc.
* playing basic sound files.
* Scratch coordinate-plane layout: (0, 0) is in the center, with +x to the right, and +y up.
* displaying variables on-screen.
* setting the "depth" of sprites to control the layering of the display of sprites.

ScratchFoot does **not** currently support these features from Scratch:
* playing different instruments or drums.
* only the "ghost" effect of the graphics effects is implemented.
* pen size is always width 1.
* user ("cloud") variables.
* the video stuff
* the microphone stuff.

----------------------

#How to Convert a Scratch program to a ScratchFoot (i.e., Greenfoot) scenario.

The file s2g.py is a python3 program that will try to automatically convert a downloaded Scratch project into a Greenfoot scenario. 
NOTE NOTE NOTE: this only works for Greenfoot 2.4.2 at this time.  It does not work with Greenfoot 3 (yet).

In order to make this work, you need to install these programs on your computer:

* Greenfoot 2.4.2: you can get this older version from [here](http://www.greenfoot.org/download_old).
* ImageMagick: including the legacy command-line module (you select this when you are installing ImageMagick.)
* python3
* The files from this repository: Scratch.java, ScratchWorld.java, and s2g.py.  You can get these files by downloading the Zip file from here and unzipping them.

Procedure for converting your Scratch project to Greenfoot:

* Start up Scratch in your browser and find your project.  
  * Go into the editor so that you can see the code, etc.
* Choose File --> Download to your computer.  This will save the program as a .sb2 file.
* Start up Greenfoot 2.4.2
  * Choose Scenario --> New to create a new Scenario folder.
  * Exit Greenfoot.
* In a terminal window (command prompt), 
  * Copy your Scratch.java and ScratchWorld.java files to the new Greenfoot scenario folder that you just created.
  * run the python s2g.py conversion script:   `python s2g.py <scratch.sb2> <greenfootDir>`
    * replace `<scratch.sb2>` with the name of the .sb2 file you downloaded from Scratch
    * replace `<greenfootDir>` with the name of the folder you created for the new Greenfoot scenario.
* Start up Greenfoot again.  Compile.  Enjoy.


NOTE NOTE: This project has been most extensively tested on MacOS and on Ubuntu Linux.  I have just tested it on Windows 10 with Greenfoot 3.0.3 and it actually seems to work!  I tried it [this scenario](https://scratch.mit.edu/projects/44669322/#editor).

ScratchFoot has been created by [Victor Norman](mailto:vtn2@calvin.edu) at [Calvin College](http://www.calvin.edu).

