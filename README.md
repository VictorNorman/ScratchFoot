# ScratchFoot v0.3 
(7 July 2016)

## A Scratch emulation layer for Greenfoot.

ScratchFoot provides a subclass of World and subclass of Actor which make available much of the functionality of Scratch in Greenfoot.  
Using ScratchFoot, you should be able to convert many Scratch programs to use Greenfoot.  This may be useful for

* overcoming limitations of Scratch.  E.g., when the Scratch canvas is just too small for your application, or when Scratch starts 
running too slowly because you have so many scripts running.
* making the transition from the simple (and wonderful) world of Scratch to the more real world of Java programming.

ScratchFoot emulates the following nice features from Scratch:
* multiple scripts can be created for a Sprite.  Specifically, you can create multiple forever loops, multiple "when I receive message" scripts,
multiple "when key clicked" scripts, etc.  These scripts all seemingly run in parallel (just as in Scratch).
* clone sprites.
* ask for user input.
* do all the math, if statements, etc., but in Java syntax, which is much more compact.
* use wait(), glideTo(), etc.
* use multiple costumes, multiple backdrops, etc.
* play basic sound files.
* Scratch coordinate-plane layout: (0, 0) is in the center, with +x to the right, and +y up.
* displaying variables on-screen.
* setting the "depth" of sprites to control the layering of the display of sprites.

### ScratchFoot limitations: 
* Playing different instruments or drums is not supported.
* Only the "ghost" effect of the graphics effects is implemented.
* The video stuff and microphone stuff are not supported.
* Does not handle rotating images around a non-center point.
* broadcastAndWait() is not supported.

----------------------

## How to Convert a Scratch program to a ScratchFoot (i.e., Greenfoot) scenario.

The file s2g.py is a python3 program that will try to automatically convert a downloaded Scratch project into a Greenfoot scenario. 

In order to make this work, you need to install these programs on your computer:

* Greenfoot 3
* ImageMagick: including the legacy command-line module (you select this when you are installing ImageMagick.)
* python 3.x
* The files from this repository: Scratch.java, ScratchWorld.java, s2g.py, and the various .png files.  You can get these files by downloading the Zip file from here and unzipping them.

Procedure for converting your Scratch project to Greenfoot:

* Start up Scratch in your browser and find your project.  
  * Go into the editor so that you can see the code, etc.
* Choose File --> Download to your computer.  This will save the program as a .sb2 file.
* In a terminal window (command prompt), 
  * run the python s2g.py conversion script:   `python s2g.py <scratch.sb2> <greenfootDir>`
    * replace `<scratch.sb2>` with the name of the .sb2 file you downloaded from Scratch
    * replace `<greenfootDir>` with the name of a folder where your new Greenfoot scenario will be created.
* Start up Greenfoot and open the new Greenfoot scenario.  Enjoy.


#### For more information about the API provided by ScratchFoot and what to expect when you convert a Scratch project to a Greenfoot scenario, see [this wiki page](https://github.com/VictorNorman/ScratchFoot/wiki/Mapping-between-Scratch-Block-and-ScratchFoot-generated-Code).



#### ScratchFoot has been created by [Victor Norman](mailto:vtn2@calvin.edu) at [Calvin College](http://www.calvin.edu) with great help from student Jordan Doorlag.

