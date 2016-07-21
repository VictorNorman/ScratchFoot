
/*
 * Copyright (C) 2016  Victor T. Norman, Calvin College, Grand Rapids, MI, USA
 * 
 * ScratchFoot: a Scratch emulation layer for Greenfoot, along with a program
 * to convert a Scratch project to a Greenfoot scenario.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 * 
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>
 */

import greenfoot.*;  // (World, Actor, GreenfootImage, Greenfoot and MouseInfo)

import java.util.ArrayList;
import java.util.LinkedList;
import java.util.HashMap;
import java.lang.Class;
import java.awt.Color;
import java.lang.reflect.*;

/**
 * Write a description of class ScratchWorld here.
 * 
 * @author Victor Norman
 * @version 7/7/2016
 */
public class ScratchWorld extends World
{
    // Default sizes of the world for Scratch
    static public int SCRATCH_WIDTH = 480;
    static public int SCRATCH_HEIGHT = 360;

    // Keep track of the number of times act() is called here and in all the Actors.
    // This "frameNumber" is used for handling broadcast messages.
    private long frameNumber = 0L;

    // Record the time, in milliseconds, when the scenario was started, so that 
    // we can return the correct value when the built-in "timer" variable is referenced.
    private long startTime;

    // These private variables are used for displaying Scratch variables on
    // the screen.  In Scratch, you can choose to show a variable.  This
    // causes a little box to be displayed that shows the variable's name
    // and its value.  When multiple variables are displayed, they are
    // initially tiled along the left side from top to bottom.  We need to
    // keep track of this x,y pair so we can tile the variable-display
    // objects.  The values are the upper-left corner of the images.
    private int varXloc = 5;
    private int varYloc = 10;
    private final static int VAR_Y_OFFSET = 25;

    // These variables manage the list of backgrounds.
    private int currBackdrop = 0;

    // Maintain a mapping from spriteName (a String) to the sprite object.
    // TODO: need to test whether this works or should work with clones.
    HashMap<String, Scratch> sprites = new HashMap();

    // This variable tracks whether the mouse is pressed
    private boolean isMouseDown;

    /*
     * This class is just a pairing of backdrop image with its name.
     */
    private class Backdrop {
        GreenfootImage img;
        String name;

        public Backdrop(GreenfootImage img, String name) {
            this.img = img;
            this.name = name;
        }
    }
    private ArrayList<Backdrop> backdrops = new ArrayList<Backdrop>();

    /*
     * This is used for storing bcast message as a string object
     * for handling broadcasts, and for storing the sprite object
     * to clone in the handling cloning.
     */
    private class ObjectFrameNumPair {
        public Object obj;
        public long frameNum;   // the frame # this message should be sent in.

        public ObjectFrameNumPair(Object obj, long frame) {
            this.obj = obj;
            this.frameNum = frame;
        }
    }

    // A list of pending broadcast messages.
    private LinkedList<ObjectFrameNumPair> mesgs = new LinkedList<ObjectFrameNumPair>();

    // A list of pending clone objects that need to be activated.
    private LinkedList<ObjectFrameNumPair> clones2Activate = new LinkedList<ObjectFrameNumPair>();

    // Keep an array of the classes in this world in order to support
    // changing of the "paint order" -- which objects are painted on top of
    // others.  In Greenfoot, you can only specify this by class, not by
    // individual objects in a class.  Classes are added dynamically by
    // ScratchActor calling addClassToWorld() in its constructor or
    // addedToWorld() function.  Individual actors' code can call
    // goToFront(), etc., to change the paint order.
    private ArrayList<Class> clses4PaintOrder = new ArrayList<Class>();

    /**
     * Constructor for objects of class ScratchWorld.
     */
    public ScratchWorld(int width, int height, int cellSize)
    {    
        super(width, height, cellSize);
    }

    /**
     * Constructor that creates the default screen size for Scratch -- 480 by 360.
     */
    public ScratchWorld()
    {
        this(SCRATCH_WIDTH, SCRATCH_HEIGHT, 1);
    }

    public final void act() 
    {
        // Record the time in milliseconds when the world is started, so
        // that the "timer" variable can get the correct time in seconds
        // and 1/10th of seconds since the scenario started.
        if (frameNumber == 0) {
            startTime = System.currentTimeMillis();
        }

        // System.out.println("-------------------------------------");
        frameNumber++;
        // System.out.println("ScratchWorld: starting frame " + frameNumber);

        if (mesgs.size() != 0) {
            // Go through the messages in the bcast message list and remove the
            // first ones that are old -- with frameNumber in the past.
            while (true) {
                ObjectFrameNumPair bcmsg = mesgs.peekFirst();
                if (bcmsg != null && bcmsg.frameNum < frameNumber) {
                    mesgs.removeFirst();
                } else {
                    // The list is empty or the pending messages are for the next
                    // iteration.
                    break;
                }
            }
        }
        if (clones2Activate.size() != 0) {
            // Go through the messages in the bcast message list and remove the
            // first ones that are old -- with frameNumber in the past.
            while (true) {
                ObjectFrameNumPair spr = clones2Activate.peekFirst();
                if (spr != null && spr.frameNum < frameNumber) {
                    /* System.out.println("Removing " + spr.obj + " from c2A with frame # " + spr.frameNum +
                    " (curr Framenumber " + frameNumber + ")"); */
                    clones2Activate.removeFirst();
                } else {
                    // The list is empty or the pending clones are for the next
                    // iteration.
                    break;
                }
            }
        }

        // This tracks whether the mouse is pressed by using the fact that 
        // mouseClickCount is > 0 when the mouse is released, and drag ended works 
        // outside the greenfoot window. 
        MouseInfo mi = Greenfoot.getMouseInfo();
        boolean dragEnd = Greenfoot.mouseDragEnded(null);
        boolean pressed = Greenfoot.mousePressed(null);
        // Iterate through all on-screen objects to check if they have been clicked
        if (mi != null) {
            if (mi.getClickCount() > 0 || dragEnd) {
                isMouseDown = false;
            }
        } else if (dragEnd) {
            isMouseDown = false;
        }
        if (pressed) {
            isMouseDown = true;
        }
    }

    /**
     * Not to be called by users.
     */
    public boolean bcastPending(String message)
    {
        for (ObjectFrameNumPair bcmsg : mesgs) {
            // Look for the correct message, to be triggered in the frame.
            if ((String) (bcmsg.obj) == message && bcmsg.frameNum == frameNumber) {
                return true;
            }
        }
        return false;
    }

    /**
     * Not to be called by the user: register a bcast message, to be sent to all 
     * Scratch Actors during the next frame.
     */
    public void registerBcast(String message)
    {
        // Create a new StringFrameNumPair object, saving the message string, and the
        // frame in which the actor's registered to receive this message
        // should execute their methods.  This frame is the *next* time
        // around -- thus we add 1 to the current frame number. 
        /* System.out.println("Adding message " + message +
        " to bcastList with frame " + (frameNumber + 1));  */
        ObjectFrameNumPair msg = new ObjectFrameNumPair(message, frameNumber + 1);
        mesgs.addLast(msg);
    }

    /**
     * Not to be called by users -- only by Scratch.
     * return true if there is a clone pending for the given sprite name.
     */
    public boolean clonePending(Object sprite)
    {
        // System.out.print("clonePending(" + sprite + "): (frameNum " + frameNumber + ") returns ");
        for (ObjectFrameNumPair pair : clones2Activate) {
            // Look for the correct sprite name, to be triggered in the frame.
            if (pair.obj == sprite && pair.frameNum == frameNumber) {
                // System.out.println("true");
                return true;
            }
        }
        // System.out.println("false");
        return false;
    }

    // add the given sprite object to the list of pending clone requests.
    public void registerActivateClone(Object clone)
    {
        // Create a new ObjectFrameNumPair object, saving the sprite
        // and the frame in which the clone should be activated.
        // This frame is the *next* time around -- thus we add 1 to the
        // current frame number.  
        /* System.out.println("Adding sprite " + clone +
        " to clones2Activate with frame " + (frameNumber + 1)); */
        ObjectFrameNumPair pair = new ObjectFrameNumPair(clone, frameNumber + 1);
        clones2Activate.addLast(pair);
    }

    /**
     *  return whether or not the mouse is currently pressed on this world
     */
    public boolean isMouseDown() 
    {
        return isMouseDown;
    }

    /**
     * return the current number of times each Scratch Actor has had its
     * registered callbacks called. 
     * (i.e., how many times each act() has been called.)
     */
    public long getFrameNumber() 
    {
        return frameNumber;
    }

    /**
     * Not to be called by users.
     */
    public int getDisplayVarYLoc()
    {
        int t = varYloc;
        varYloc += VAR_Y_OFFSET;
        return t;
    }

    /**
     * Not to be called by users.
     */
    public int getDisplayVarXLoc()
    {
        return varXloc;
    }

    /**
     * redisplay the backdrop, without any modifications to it.
     * Not available in Scratch.
     */
    public void clearBackdrop()
    {
        if (backdrops.size() > 0) {
            setBackground(new GreenfootImage(backdrops.get(currBackdrop).img));
        } else {
            setBackground(new GreenfootImage(getWidth() - 1, getHeight() - 1));
        }
    }

    /**
     * add a new backdrop, with the given name.
     * Many backdrops come with Greenfoot, but can be tough to find.  On my
     * Mac, they are at /Applications/Greenfoot\
     * 2.4.2/Greenfoot.app/Contents/Resources/Java/greenfoot/imagelib/backgrounds/ 
     */
    public void addBackdrop(String backdropFile, String backdropName)
    {
        backdrops.add(new Backdrop(new GreenfootImage(backdropFile), backdropName));
    }

    /**
     * switch to the next backdrop.
     */
    public void nextBackdrop()
    {
        currBackdrop = (currBackdrop + 1) % backdrops.size();
        setBackground(new GreenfootImage(backdrops.get(currBackdrop).img));
    }

    /**
     * switch to the previous backdrop.
     */
    public void previousBackdrop()
    {
        currBackdrop--;
        if (currBackdrop < 0) {
            currBackdrop = backdrops.size() - 1;
        }
        setBackground(new GreenfootImage(backdrops.get(currBackdrop).img));
    }

    /**
     * return the index of the current backdrop.
     */
    public int getBackdropNumber() 
    {
        return currBackdrop;
    }

    /**
     * set the current backdrop number to the given value.
     */
    public void setBackdropNumber(int num)
    {
        currBackdrop = num;
        // TODO: check num to make sure it is valid before setting it.
        setBackground(new GreenfootImage(backdrops.get(currBackdrop).img));
    }

    /**
     * return the name of the current backdrop
     */
    public String getBackdropName()
    {
        return backdrops.get(currBackdrop).name;
    }

    /**
     * switch backdrop to the one with the given name.
     */
    public void switchBackdropTo(String backdropName)
    {
        for (int i = 0; i < backdrops.size(); i++) {
            if (backdrops.get(i).name.equals(backdropName)) {
                currBackdrop = i;
                setBackground(new GreenfootImage(backdrops.get(currBackdrop).img));
                return;
            }
        }
        // Do nothing if the given backdropName is not found.  (Should
        // perhaps issue a warning/error?) 
    }
    
    /**
     * switch backdrop to the one with the given number, loops.
     */
    public void switchBackdropTo(int num)
    {
        num = Math.floorMod(num, backdrops.size());
        currBackdrop = num;
        setBackground(new GreenfootImage(backdrops.get(currBackdrop).img));
    }

    /**
     * rename the default backdrop.  (Only available through the GUI in scratch.)
     */
    public void renameDefaultBackdrop(String newName) 
    {
        backdrops.get(0).name = newName;
    }

    /* 
     * Paint order stuff.
     */

    // Convert ArrayList of classes into array and call setPaintOrder in Greenfoot.World.
    private void setPaintOrderInGF()
    {
        Class[] temp = new Class[clses4PaintOrder.size()];
        for (int i = 0; i < clses4PaintOrder.size(); i++) {
            temp[i] = clses4PaintOrder.get(i);
        }
        setPaintOrder(temp);
    }

    //
    // Called by Scratch Actor from addedToWorld() to register the actor's class 
    // in the paint order.
    //

    public int getLayer(Class cls)
    {
        return clses4PaintOrder.indexOf(cls);
    }

    public void addToPaintOrder(Class cls)
    {
        // System.out.println("addToClasses called with class " + cls);
        if (clses4PaintOrder.contains(cls)) {
            return;
        }

        clses4PaintOrder.add(cls);
        // System.out.println("addToClasses: clses list is now " + clses4PaintOrder);
        setPaintOrderInGF();
    }

    public void moveClassToFront(Class cls)
    {
        if (! clses4PaintOrder.contains(cls)) {
            System.err.println("Error: moveClassToFront: class " + cls + " not found");
            return;
        }
        clses4PaintOrder.remove(cls);
        clses4PaintOrder.add(0, cls);
        setPaintOrderInGF();
    }

    public void moveClassBackNLayers(Class cls, int n)
    {
        int idx = clses4PaintOrder.indexOf(cls);
        if (idx < 0) {
            System.err.println("Error: moveClassBackNLayers: class " + cls + " not found");
            return;
        }
        clses4PaintOrder.remove(idx);
        if (idx + n <= clses4PaintOrder.size()) {
            clses4PaintOrder.add(idx + n, cls);    // insert it.
        } else {
            clses4PaintOrder.add(cls);   // append it.
        }

        setPaintOrderInGF();
    }

    public void moveClassForwardNLayers(Class cls, int n)
    {
        int idx = clses4PaintOrder.indexOf(cls);
        if (idx < 0) {
            System.err.println("Error: moveClassBackNLayers: class " + cls + " not found");
            return;
        }
        clses4PaintOrder.remove(idx);
        if (idx - n <= clses4PaintOrder.size()) {
            clses4PaintOrder.add(idx - n, cls);    // insert it.
        } else {
            clses4PaintOrder.add(0, cls);
        }

        setPaintOrderInGF();
    }

    public void moveClassToLayerN(Class cls, int n)
    {
        int idx = clses4PaintOrder.indexOf(cls);
        if (idx < 0) {
            System.err.println("Error: moveClassBackNLayers: class " + cls + " not found");
            return;
        }
        if (idx == n) {
            return;  // don't have to move it at all.
        }
        clses4PaintOrder.remove(idx);
        if (n < 0) {
            clses4PaintOrder.add(0, cls);
        } else if (n >= clses4PaintOrder.size()) {
            clses4PaintOrder.add(cls);            // put it at the end.
        } else {
            clses4PaintOrder.add(n, cls);         // insert it.
        }

        setPaintOrderInGF();
    }

    /**
     * Get the time, in seconds and tenths of seconds, from when the scenario started.
     */
    public double getTimer() 
    {
        long diff = System.currentTimeMillis() - startTime;
        // divide by 100 (integer division) to get number of tenths of
        // seconds. Then divide by 10.0 to get floating point result in seconds.
        return (diff / 100) / 10.0;
    }

    /**
     * Reset the timer to 0.0
     */
    public void resetTimer() 
    {
        startTime = 0;
    }    

    /* -------------------  Global Variables ------------------------ */
    /* This code is almost an exact copy from the Scratch.java class, but
    I don't want to move it to a separate class because I want to keep only
    two classes -- one a subclass of World and one a subclass of Actor. -- author */

    private class Variable extends Actor 
    {
        private final Color textColor = Color.black;
        private final Color bgColor = Color.gray;

        private Object value;
        private String text;
        private boolean valChanged = true;
        private boolean display = true;           // is the variable supposed to be displayed or hidden?
        private boolean addedToWorld = false;     // has this object been added to the world yet?
        private int xLoc, yLoc;                   // current location of the image: the upper-lefthand
        // corner.

        public Variable(String varName, Object val)
        {
            text = varName;
            value = val;
            valChanged = true;

            // Get the initial upperleft-hand corner coordinates for this variable.
            xLoc = getDisplayVarXLoc();
            yLoc = getDisplayVarYLoc();
        }

        public void act()
        {
            updateImage();
        }

        /**
         * Update the value.  The value on the screen will be updated next time act()
         * is called for this object.
         */
        public void set(Object newVal)
        {
            value = newVal;
            valChanged = true;
        }

        /**
         * @return the value.
         */
        public Object get()
        {
            return value;
        }

        public int getXLoc() { return xLoc; }

        public int getYLoc() { return yLoc; }

        /**
         * Update the image being displayed.
         */
        private void updateImage()
        {
            if (! display) {
                getImage().clear();
                return;
            }
            if (valChanged) {
                // To support the user pausing the scenario and moving the Variable display box
                // to a new location, we will read the actual xLoc and yLoc from the actor,
                // but also subtract the current width/height, since
                // Greenfoot's image reference point is the center of the
                // image.  (Note: this has to be done before recomputing
                // a possible new width/height in the code below.)
                if (addedToWorld) {
                    // getX() and getY() get the actual current location.
                    // System.out.println("AddedToWorld is TRUE: getX, getY = " + getX() + " " + getY());
                    xLoc = getX() - getImage().getWidth() / 2;
                    yLoc = getY() - getImage().getHeight() / 2;
                    // System.out.println("AddedToWorld is TRUE: xLoc, yLoc = " + xLoc + " " + yLoc);
                } 

                String dispStr = text + value;
                int stringLength = (dispStr.length() + 2) * 7;
                // Create a gray background under the variable's name.
                GreenfootImage image = new GreenfootImage(stringLength, 20);
                image.setColor(bgColor);
                image.setFont(new java.awt.Font("Courier", java.awt.Font.PLAIN, 12));
                image.fill();
                // Create orange background under the variable's value.
                image.setColor(Color.decode("#EE7D16"));
                image.fillRect((int) ((text.length() + 1 )* 7), 3, ((value + "").length()) * 7 + 3, 15);

                image.setColor(textColor);
                // System.out.println("Variable.updateImage: creating with value " + text + " " + value);
                image.drawString(text + " " + value, 1, 15);
                setImage(image);

                // Because the size of the image may have changed (to accommodate a longer
                // or shorter string to display), and because we want all images tiled nicely
                // along the left side of the screen, and because Greenfoot places images based
                // on the center of the image, we have to calculate a new location for
                // each image, each time.
                setLocation(xLoc + getImage().getWidth() / 2, yLoc + getImage().getHeight() / 2);
                // System.out.println("setLocation done: set to x, y = " + (xLoc + getImage().getWidth() / 2) +
                //                   " " + (yLoc + getImage().getHeight() / 2));
                valChanged = false;
                addedToWorld = true;
            }
        }

        /**
         * mark that this variable's value should be displayed on the Scratch screen.
         */
        public void show()
        {
            display = true;
            valChanged = true;      // make sure we display the value in next act() iteration.
        }

        /**
         * mark that this variable's value should not be displayed on the Scratch screen.
         */
        public void hide()
        {
            display = false;
            valChanged = true;  // make sure we don't display the value in next act() iteration.
        }
    }

    public class IntVar extends Variable {

        public IntVar(String name, int initVal) {
            super(name, (Object) initVal);
        }

        public Integer get() { return (Integer) super.get(); }
    }
    public class StringVar extends Variable {

        public StringVar(String name, String initVal) {
            super(name, (Object) initVal);
        }

        public String get() { return (String) super.get(); }
    }
    public class DoubleVar extends Variable {

        public DoubleVar(String name, double initVal) {
            super(name, (Object) initVal);
        }

        public Double get() { return (Double) super.get(); }
    }
    public class BooleanVar extends Variable {

        public BooleanVar(String name, boolean initVal) {
            super(name, (Object) initVal);
        }

        public Boolean get() { return (Boolean) super.get(); }
    }

    /**
     * Create an integer variable whose value will be displayed on the screen.
     */
    public IntVar createIntVariable(String varName, int initVal)
    {
        IntVar newVar = new IntVar(varName, initVal);
        addObject(newVar, newVar.getXLoc(), newVar.getYLoc());
        // Call act() so that it calls updateImage() which creates/computes
        // the image that displays the variable, and places in the correct location.
        newVar.act();
        return newVar; 
    }

    /**
     * Create a String variable whose value will be displayed on the screen.
     */
    public StringVar createStringVariable(String varName, String val)
    {
        StringVar newVar = new StringVar(varName, val);
        addObject(newVar, newVar.getXLoc(), newVar.getYLoc());
        // Call act() so that it calls updateImage() which creates/computes
        // the image that displays the variable, and places in the correct location.
        newVar.act();
        return newVar; 
    }

    /**
     * Create a double variable whose value will be displayed on the screen.
     */
    public DoubleVar createDoubleVariable(String varName, double val)
    {
        DoubleVar newVar = new DoubleVar(varName, val);
        addObject(newVar, newVar.getXLoc(), newVar.getYLoc());
        // Call act() so that it calls updateImage() which creates/computes
        // the image that displays the variable, and places in the correct location.
        newVar.act();
        return newVar; 
    }

    /**
     * Create a boolean variable whose value will be displayed on the screen.
     */
    public BooleanVar createBooleanVariable(String varName, boolean val)
    {
        BooleanVar newVar = new BooleanVar(varName, val);
        addObject(newVar, newVar.getXLoc(), newVar.getYLoc());
        // Call act() so that it calls updateImage() which creates/computes
        // the image that displays the variable, and places in the correct location.
        newVar.act();
        return newVar; 
    }

    private int translateToGreenfootX(int x) 
    {
        return x + getWidth() / 2;
    }

    /*
     * Scratch's (0, 0) is in the middle, with y increasing y up, while greenfoot's 0, 0 is in 
     * the upper-left corner with y increasing downward.
     */
    private int translateToGreenfootY(int y) 
    {
        return getHeight() / 2 - y;
    }

    /**
     * Add a new Sprite to the world, given the Sprite's class name.
     * (This simplifies Greenfoot's standard addObject() call.)
     * Note that initX and initY are in the Scratch coordinate system
     * (0, 0 = middle).
     */
    public void addSprite(String spriteClass, int initX, int initY) 
    {
        /*
         * 1. convert classname to class instance.
         * 2. call addObject() on the new instance at 0, 0.
         * 3. record mapping of class name -> object, so that sprites can do stuff like
         *    isTouching(objectName), not having to have a reference to the actual object.
         */
        Class clazz;

        try {
            clazz = Class.forName(spriteClass);
        } catch (ClassNotFoundException x) {
            x.printStackTrace();
            return;
        }
        Scratch sprite;
        try {
            Constructor ctor = clazz.getDeclaredConstructor();
            ctor.setAccessible(true);

            // Call the Scratch constructor here.
            sprite = (Scratch) ctor.newInstance();
        } catch (InstantiationException x) {
            x.printStackTrace();
            return;
        } catch (InvocationTargetException x) {
            x.printStackTrace();
            return;
        } catch (IllegalAccessException x) {
            x.printStackTrace();
            return;
        } catch (java.lang.NoSuchMethodException x) {
            x.printStackTrace();
            return;
        }

        // Tell the Greenfoot world about this new sprite.
        addObject(sprite, translateToGreenfootX(initX), translateToGreenfootY(initY));

        // Add to the hashmap.
        sprites.put(spriteClass, sprite);
    }

    // TODO: override remove() to remove objects from the sprites hashmap.

    /**
     * return the Scratch object identified by the given name, or null if 
     * it does not exist.
     */
    public Scratch getActorByName(String name) 
    {
        return sprites.get(name);
    }
}
