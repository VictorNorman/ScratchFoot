import greenfoot.*;  // (World, Actor, GreenfootImage, Greenfoot and MouseInfo)

import java.util.ArrayList;
import java.util.LinkedList;
import java.lang.Class;

/**
 * Write a description of class ScratchWorld here.
 * 
 * @author (your name) 
 * @version (a version number or a date)
 */
public class ScratchWorld extends World
{

    // Keep track of the number of times act() is called here and in all the Actors.
    // This "frameNumber" is used for handling broadcast messages.
    private long frameNumber = 0L;
    
    // Record the time, in milliseconds, when the scenario was started, so that 
    // we can return the correct value when the built-in "timer" variable is referenced.
    private long startTime;

    // These private variables are used for displaying Scratch variables on the 
    // screen.  In Scratch, you can choose to show a variable.  This causes a little
    // box to be displayed that shows the variable's name and its value.  When multiple
    // variables are displayed, they are initially tiled along the left side from top to bottom.
    // We need to keep track of this x,y pair so we can tile the variable-display objects.
    private int varXloc = 5;
    private int varYloc = 10;
    private final static int VAR_Y_OFFSET = 25;
    
    // These variable manage the list of backgrounds.
    private int currBackdrop = 0;
    private ArrayList<GreenfootImage> backdrops = new ArrayList<GreenfootImage>();
    private ArrayList<String> backdropNames = new ArrayList<String>();
    
    private class BcastMsg {
        public String message;
        public long frameNum;   // the frame # this message should be sent in.
        
        public BcastMsg(String msg, long frame) {
            this.message = msg;
            this.frameNum = frame;
        }
    }
    private LinkedList<BcastMsg> mesgs = new LinkedList<BcastMsg>();
    
    // Keep an array of the classes in this world in order to support changing of the 
    // "paint order" -- which objects are painted on top of others.  In Greenfoot, you can
    // only specify this by class, not by individual objects in a class.
    // Classes are added dynamically by ScratchActor calling addClassToWorld() in its
    // constructor or addedToWorld() function.  Individual actors' code can call goToFront(), 
    // etc., to change the paint order.
    private ArrayList<Class> clses4PaintOrder = new ArrayList<Class>();

    /**
     * Constructor for objects of class ScratchWorld.
     * 
     */
    public ScratchWorld(int width, int height, int cellSize)
    {    
        super(width, height, cellSize);
        
        // make a copy of the background image.
        backdrops.add(new GreenfootImage(getBackground()));
        backdropNames.add("backdrop1");    // this is what it is called in Scratch, by default.
    }
    
    /**
     * Greenfoot requires that a default constructor exist.  However, 
     * users of Scratchfoot should call the 3-parameter constructor, which
     * takes care of some details, like recording the backdrop that was set
     * via the GUI.
     */
    public ScratchWorld()
    {
        this(600, 400, 1);
        // System.out.println("Called default constructor ScratchWorld... shouldn't do this...");
    }
    
    public void act() 
    {
        // Record the time in milliseconds when the world is started, so that the "timer" variable
        // can get the correct time in seconds and 1/10th of seconds since the scenario started.
        if (frameNumber == 0) {
            startTime = System.currentTimeMillis();
        }
        
        System.out.println("-------------------------------------");
        frameNumber++;
        System.out.println("ScratchWorld: starting frame " + frameNumber);
        
        if (mesgs.size() != 0) {
            // Go through the messages in the bcast message list and remove the
            // first ones that are old -- with frameNumber in the past.
            while (true) {
                BcastMsg bcmsg = mesgs.peekFirst();
                if (bcmsg != null && bcmsg.frameNum < frameNumber) {
                    mesgs.removeFirst();
                } else {
                    // The list is empty or the pending messages are for the next
                    // iteration.
                    break;
                }
            }
        }
        

    }
    
    // Not to be called by users.
    public boolean bcastPending(String message)
    {
        for (BcastMsg bcmsg : mesgs) {
            // Look for the correct message, to be triggered in the frame.
            if (bcmsg.message == message && bcmsg.frameNum == frameNumber) {
                return true;
            }
        }
        return false;
    }
    
    /**
     * return the current number of times each Actor has had its registered callbacks called.
     * (i.e., how many times each act() has been called.)
     */
    public long getFrameNumber() 
    {
        return frameNumber;
    }
    
    public int getDisplayVarYLoc()
    {
        int t = varYloc;
        varYloc += VAR_Y_OFFSET;
        return t;
    }
    
    public int getDisplayVarXLoc()
    {
        return varXloc;
    }
    
    // Not available in Scratch.
    public void clearBackdrop()
    {
        setBackground(new GreenfootImage(backdrops.get(currBackdrop)));
    }
    
    public void addBackdrop(String backdropFile, String backdropName)
    {
        backdrops.add(new GreenfootImage(backdropFile));
        backdropNames.add(backdropName);
    }
    
    public void nextBackdrop()
    {
        currBackdrop = (currBackdrop + 1) % backdrops.size();
        setBackground(new GreenfootImage(backdrops.get(currBackdrop)));
    }
    
    public void previousBackdrop()
    {
        currBackdrop--;
        if (currBackdrop < 0) {
            currBackdrop = backdrops.size() - 1;
        }
        setBackground(new GreenfootImage(backdrops.get(currBackdrop)));
    }
    
    public int getBackdropNumber() 
    {
        return currBackdrop;
    }
    
    public String getBackdropName()
    {
        return backdropNames.get(currBackdrop);
    }
    
    public void switchBackdropTo(String backdropName)
    {
        // Do nothing if the given backdropName is not legal.  (Should perhaps issue a warning/error?)
        int res = backdropNames.indexOf(backdropName);
        if (res == -1) {
            return;
        }
        
        currBackdrop = res;
        setBackground(new GreenfootImage(backdrops.get(currBackdrop)));
    }
    
    public void renameDefaultBackdrop(String newName) 
    {
        backdropNames.set(0, newName);
    }

    /**
     * Not to be called by the user: register a bcast message, to be sent to all 
     * Scratch Actors during the next frame.
     */
    public void registerBcast(String message)
    {
        // Create a new BcastMsg object, saving the message string, and the frame in which
        // the actor's registered to receive this message should execute their methods.  This
        // frame is the *next* time around -- thus we add 1 to the current frame number.
        System.out.println("Adding message " + message + " to bcastList with frame " + (frameNumber + 1));
        BcastMsg msg = new BcastMsg(message, frameNumber + 1);
        mesgs.addLast(msg);
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
        System.out.println("addToClasses called with class " + cls);
        if (clses4PaintOrder.contains(cls)) {
            return;
        }
        
        clses4PaintOrder.add(cls);
        System.out.println("addToClasses: clses list is now " + clses4PaintOrder);
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
        // divide by 100 (integer division) to get number of tenths of seconds.  Then divide by 10.0 to 
        // get floating point result in seconds.
        return (diff / 100) / 10.0;
    }
    
    /**
     * Reset the timer to 0.0
     */
    public void resetTimer() 
    {
        startTime = 0;
    }    
    
}
