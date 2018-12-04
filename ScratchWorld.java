
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
import java.util.List;
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
    
    // This variable tracks which frame the last backdrop switch happened.
    // This allows the backdropSwitch sequence to tell if it's switched
    private long backdropSwitchFrame;
    
    // A random id generated when the world is constructed
    // Any thread with a different id to this will destroy itself
    protected static int id;

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

    static ThreadGroup threadGroup = new ThreadGroup("Sequences");
    
    // This static initializer will be called whenever this class is loaded.
    // this will happen whenever the greenfoot project is recompiled.
    // When this happens, the static reference to the threadgroup is lost,
    // so we instead search for threads with the name "Sequence" and
    // terminate them individually.
    static {
        // get a group of all running threads in the current group
        ThreadGroup rootGroup = Thread.currentThread().getThreadGroup();
        // create an array to hold the threads in the current group
        Thread[] threads = new Thread[rootGroup.activeCount()];
        // dump all the threads from the current group into the array
        while (rootGroup.enumerate(threads, true) == threads.length) {
            // if the array wasn't big enough to hold them all, increase its size
            threads = new Thread[threads.length * 2];
        }
        
        // Iterate through all running threads, terminating any started by scratch.java
        for (Thread t : threads) {
            if (t != null) {
                // The threads ScratchFoot can spawn are "ScratchSequence" and "ScratchSound"
                if (t.getName().equals("ScratchSequence") || t.getName().equals("ScratchSound")) {
                    // Interrupt all threads we've made, causing them to stop running
                    t.interrupt();
                }
            }
        }
    }

    /**
     * Constructor for objects of class ScratchWorld.
     */
    public ScratchWorld(int width, int height, int cellSize)
    {    
        super(width, height, cellSize);
        
        // If the threadGroup has been created, we must first close all existing threads
        // otherwise they will continue to run, taking up resources
        if (threadGroup != null) {
            threadGroup.interrupt();
        }
    }

    /**
     * Constructor that creates the default screen size for Scratch -- 480 by 360.
     */
    public ScratchWorld()
    {
        this(SCRATCH_WIDTH, SCRATCH_HEIGHT, 1);
    }
    
    /**
     * Constructor that creates a custom screen size
     */
    public ScratchWorld(int w, int h)
    {
        this(w, h, 1);
        Stage.bgImg = new GreenfootImage(w, h);
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
     * Not to be called by the user: go through all Scratch actors and look
     * at all their MesgRecvdSeq's.  Return a list of all that are for the
     * given message.
     */
    public ArrayList<Scratch.MesgRecvdSeq> getAllMessageScripts(String message)
    {
        ArrayList<Scratch.MesgRecvdSeq> resSeq = new ArrayList<Scratch.MesgRecvdSeq>();
        List<Scratch> allScr = getObjects(Scratch.class);
        for (Scratch scr : allScr) {
            ArrayList<Scratch.MesgRecvdSeq> seqs = scr.getMesgRecvdSeqs();
            for (Scratch.MesgRecvdSeq s: seqs) {
                if (s.getMesg() == message) {
                    resSeq.add(s);
                }
            }
        }
        return resSeq;
    }

    /**
     * Not to be called by the user: register a bcast message, to be sent to all 
     * Scratch Actors during the next frame.
     */
    public void registerBcast(String message)
    {
        // Create a new ObjectFrameNumPair object, saving the message string, and the
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
    public int getDisplayListYLoc(int length)
    {
        int t = varYloc;
        varYloc += (length + 1) * 18 + 12;
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
        backdropSwitchFrame = frameNumber;
    }

    /**
     * switch to the previous backdrop.
     */
    public void previousBackdrop()
    {
        currBackdrop--;
        if (currBackdrop <= 0) {
            currBackdrop = backdrops.size();
        }
        setBackground(new GreenfootImage(backdrops.get(currBackdrop - 1).img));
        backdropSwitchFrame = frameNumber;
    }

    /**
     * return the index of the current backdrop.
     */
    public int getBackdropNumber() 
    {
        return currBackdrop + 1;
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
     * If "next backdrop" or "previous backdrop" is put as the name,
     * switch to that backdrop instead of looking for one with the
     * same name.
     */
    public void switchBackdropTo(String backdropName)
    {
        if (backdropName.equals("next backdrop")) {
            nextBackdrop();
        } else if (backdropName.equals("previous backdrop")) {
            previousBackdrop();
        } else {
            for (int i = 0; i < backdrops.size(); i++) {
                if (backdrops.get(i).name.equals(backdropName)) {
                    currBackdrop = i;
                    setBackground(new GreenfootImage(backdrops.get(currBackdrop).img));
                    backdropSwitchFrame = frameNumber;
                    return;
                }
            }
        }
        // Do nothing if the given backdropName is not found.  (Should
        // perhaps issue a warning/error?) 
    }
    
    /**
     * switch backdrop to the one with the given number, wrapping around the extents like scratch
     */
    public void switchBackdropTo(int num)
    {
        num = Math.floorMod(num - 1, backdrops.size());
        backdropSwitchFrame = frameNumber;
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
    
    /**
     * Checks if the background has switched to the provided index this frame
     * Used with SwitchedToBackdropSeqs
     */
    public boolean switchedToBackdrop(int index)
    {
        if (backdropSwitchFrame == frameNumber && getBackdropNumber() == index) {
            return true;
        }
        return false;
    }
    
    /**
     * Checks if the background has switched to the provided name this frame
     * Used with SwitchedToBackdropSeqs
     */
    public boolean switchedToBackdrop(String name)
    {
        if (backdropSwitchFrame == frameNumber && getBackdropName().equals(name)) {
            return true;
        }
        return false;
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
        moveClassToLayerN(cls, 0);
    }

    public void moveClassToBack(Class cls)
    {
        if (! clses4PaintOrder.contains(cls)) {
            System.err.println("Error: moveClassToBack: class " + cls + " not found");
            return;
        }
        moveClassToLayerN(cls, 1000);   // end
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
            System.err.println("Error: moveClassForwardNLayers: class " + cls + " not found");
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
            System.err.println("Error: moveClassToLayerN: class " + cls + " not found");
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
        startTime = System.currentTimeMillis();
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
        sprites.put(spriteClass.toUpperCase(), sprite);
    }

    // TODO: override remove() to remove objects from the sprites hashmap.

    /**
     * return the Scratch object identified by the given name, or null if 
     * it does not exist.
     */
    public Scratch getActorByName(String name) 
    {
        return sprites.get(name.toUpperCase());
    }
}
