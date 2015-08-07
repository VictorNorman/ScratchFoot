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
* Scratch coordinate plane layout: (0, 0) is in the center, with +x to the left, and +y up.
* displaying variables on-screen.
* setting the "depth" of sprites to control the layering of the display of sprites.

ScratchFoot does **not** currently support these features from Scratch:
* playing different instruments or drums.
* only the "ghost" effect of the graphics effects is implemented.
* pen size is always width 1.
* user ("cloud") variables.
* the video stuff
* the microphone stuff.

Note that ScratchFoot does **NOT** automatically convert a Scratch project into a Greenfoot project.  This must (currently) 
be done by hand.  The ScratchFoot wiki will contain guidance for how to do this systematically.

ScratchFoot has been created by [Victor Norman](mailto:vtn2@calvin.edu) at [Calvin College](http://www.calvin.edu).

