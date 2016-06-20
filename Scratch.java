import greenfoot.*;  // (getWorld(), Actor, GreenfootImage, Greenfoot and MouseInfo)

import java.util.ArrayList;
import java.util.ListIterator;
import java.util.Calendar;
import java.awt.Color;
import java.lang.String;
import java.lang.reflect.*;
import javax.swing.JOptionPane;
import java.awt.geom.RoundRectangle2D;

/**
 * class Scratch
 * 
 * @author Victor Norman 
 * @version 0.1
 */
public class Scratch extends Actor
{
    // These are the 200 numbered colors used in Scratch.
    private static String numberedColors[] = {
            "#FF0000", "#FF0700", "#FF0F00", "#FF1600", "#FF1E00",        // indices 0 - 4
            "#FF2600", "#FF2D00", "#FF3500", "#FF3D00", "#FF4400",        // indices 5 - 9
            "#FF4C00", "#FF5400", "#FF5B00", "#FF6300", "#FF6B00",        // indices 10 - 14   
            "#FF7200", "#FF7A00", "#FF8200", "#FF8900", "#FF9100",        // indices 15 - 19
            "#FF9900", "#FFA000", "#FFA800", "#FFAF00", "#FFB700",        // indices 20 - 24
            "#FFBF00", "#FFC600", "#FFCE00", "#FFD600", "#FFDD00",        // indices 25 - 29
            "#FFE500", "#FFED00", "#FFF400", "#FFFC00", "#F9FF00",        // indices 30 - 34
            "#F2FF00", "#EAFF00", "#E2FF00", "#DBFF00", "#D3FF00",        // indices 35 - 39
            "#CCFF00", "#C4FF00", "#BCFF00", "#B5FF00", "#ADFF00",        // indices 40 - 44
            "#A5FF00", "#9EFF00", "#96FF00", "#8EFF00", "#87FF00",        // indices 45 - 49
            "#7FFF00", "#77FF00", "#70FF00", "#68FF00", "#60FF00",        // indices 50 - 54
            "#59FF00", "#51FF00", "#49FF00", "#42FF00", "#3AFF00",        // indices 55 - 59
            "#32FF00", "#2BFF00", "#23FF00", "#1CFF00", "#14FF00",        // indices 60 - 64
            "#0CFF00", "#05FF00", "#00FF02", "#00FF0A", "#00FF11",        // indices 65 - 69
            "#00FF19", "#00FF21", "#00FF28", "#00FF30", "#00FF38",        // indices 70 - 74
            "#00FF3F", "#00FF47", "#00FF4F", "#00FF56", "#00FF5E",        // indices 75 - 79
            "#00FF65", "#00FF6D", "#00FF75", "#00FF7C", "#00FF84",        // indices 80 - 84
            "#00FF8C", "#00FF93", "#00FF9B", "#00FFA3", "#00FFAA",        // indices 15 - 19
            "#00FFB2", "#00FFBA", "#00FFC1", "#00FFC9", "#00FFD1",        // indices 90 - 94
            "#00FFD8", "#00FFE0", "#00FFE8", "#00FFEF", "#00FFF7",        // indices 95 - 99
            "#00FFFF", "#00F7FF", "#00EFFF", "#00E8FF", "#00E0FF",        // indices 100 - 104
            "#00D8FF", "#00D1FF", "#00C9FF", "#00C1FF", "#00BAFF",        // indices 15 - 19
            "#00B2FF", "#00AAFF", "#00A3FF", "#0098FF", "#0093FF",        // indices 110 - 114
            "#008CFF", "#0084FF", "#007CFF", "#0075FF", "#006DFF",        // indices 115 - 119
            "#0065FF", "#005EFF", "#0056FF", "#004FFF", "#0047FF",        // indices 120 - 124
            "#003FFF", "#0038FF", "#0030FF", "#0028FF", "#0021FF",        // indices 125 - 129
            "#0019FF", "#0011FF", "#000AFF", "#0002FF", "#0500FF",        // indices 130 - 134
            "#0C00FF", "#1400FF", "#1C00FF", "#2300FF", "#2B00FF",        // indices 135 - 139
            "#3300FF", "#3A00FF", "#4200FF", "#4900FF", "#5100FF",        // indices 140 - 144
            "#5900FF", "#6000FF", "#6800FF", "#7000FF", "#7700FF",        // indices 145 - 149
            "#7F00FF", "#8700FF", "#8E00FF", "#9600FF", "#9E00FF",        // indices 150 - 154
            "#A500FF", "#AD00FF", "#B500FF", "#BC00FF", "#C400FF",        // indices 155 - 159
            "#CB00FF", "#D300FF", "#D800FF", "#E200FF", "#EA00FF",        // indices 160 - 164
            "#F200FF", "#F900FF", "#FF00FC", "#FF00F4", "#FF00ED",        // indices 165 - 169
            "#FF00E5", "#FF00DD", "#FF00D6", "#FF00CE", "#FF00C6",        // indices 170 - 174
            "#FF00BF", "#FF00B7", "#FF00AF", "#FF00A8", "#FF00A0",        // indices 175 - 179
            "#FF0098", "#FF0091", "#FF0089", "#FF0082", "#FF007A",        // indices 180 - 184
            "#FF0072", "#FF006B", "#FF0063", "#FF005B", "#FF0054",        // indices 185 - 189
            "#FF004C", "#FF0044", "#FF003D", "#FF0035", "#FF002D",        // indices 190 - 194
            "#FF0026", "#FF001E", "#FF0016", "#FF000F", "#FF0007",        // indices 195 - 199
        };

    private boolean isPenDown = false;
    private Color penColor = Color.RED;
    private int penColorNumber = 0;         // an integer that is mod 200 -- 0 to 199.
    private int penSize = 1;
    private int currCostume = 0;
    private GreenfootImage lastImg = getImage();
    private boolean isFlipped = false;      // tracks whether the image is flipped due to LEFT_RIGHT rotation.
    
    /*
     * this class is just a pairing of costume image with its name.
     */
    private class Costume {
        GreenfootImage img;
        String name;

        public Costume(GreenfootImage img, String name) {
            this.img = img;
            this.name = name;
        }
    }
    private ArrayList<Costume> costumes = new ArrayList<Costume>();

    // costumesCopy holds the original unaltered costume images.  So, if
    // the code alters the costume by, e.g., scaling it, the copy stays
    // unchanged.
    
    // TODO TODO: need to figure out if this is really necessary.
    private ArrayList<GreenfootImage> costumesCopy = new ArrayList<GreenfootImage>();   

    private boolean isShowing = true;  // do we show the image or not?
    private int ghostEffect;           // image transparency.

    // The layer this object (actually all objects of this class) is painted in.
    // Layer 0 is on top.  ScratchWorld object keeps a list of the overall paint
    // order.
    private int currentLayer;

    // Note that the scale of a sprite in Scratch is a property of the sprite,
    // not a property of the image.  In Greenfoot it is just a property of
    // the image, so if you scale one image and then change to another image
    // the scaling is not applied.  So, here we have to store the current
    // scaling factor to be applied to all costumes/images.
    private int costumeSize = 100;   // percentage of original size

    // The direction the sprite is set to move in.  Due to the 
    // rotationStyle that is set, the image may not be pointing in that
    // direction.  This value is in Scratch orientation (which is GF 
    // orientation + 90).
    private int currDirection = 90; 

    private int lastMouseX;
    private int lastMouseY;

    // Remember if this object is a clone or not.  It is not, by default.
    private boolean isClone = false;

    // Note if the code being run is in a callback script -- i.e., being
    // run in a Sequence. This needs to be noted so that if stopThisScript() is 
    // called it can check if the code is in the script.
    private boolean inCbScript = false;

    // Actor that is showing what is being said OR thought by this sprite.
    Sayer sayActor = null;
    
    /**
     *  Turn the sprite to face the direction depending on the rotation style:
     *   o if ALL_AROUND: rotate to face the direction.
     *   o if LEFT_RIGHT: face left if direction is -1 to -179 or 181 - 359
     *   o if DONT_ROTATE: don't change the sprite.
     */
    public enum RotationStyle {
        LEFT_RIGHT, ALL_AROUND, DONT_ROTATE
    }
    private RotationStyle rotationStyle = RotationStyle.ALL_AROUND;

    private class StopScriptException extends RuntimeException {
        public StopScriptException() {
            super();
        }
    }

    private class CloneStartCb {
        public String className;
        public String method;

        // Store the method to call, and also the class in which the method exists.
        // When we invoke this (here in Scratch), we don't know the actual subclass, so
        // we have to reference it by the stored name.
        public CloneStartCb(String className, String method) 
        {
            this.className = className;
            this.method = method;
        }
        // obj is the (new) clone object to call the method on.
        public void invoke(Object obj)
        {
            try {
                Class clazz = Class.forName(className);
                Method m = clazz.getMethod(method);
                m.invoke(obj);
            } catch (Exception e) {
                System.err.println("Scratch.cloneCb: exception when invoking callback method '" + 
                    method + "': " + e);
                e.printStackTrace();
            }
        }
    }
    private ArrayList<CloneStartCb> cloneStartCbs = new ArrayList<CloneStartCb>();
    

    /**
     * A Sequence is an executable thread of code that will be run.  
     * It can be paused via a wait() call, like in Scratch, etc.
     */
    public class Sequence extends Thread
    {
        private Object sequenceLock;
        private boolean doneSequence;
        private boolean terminated;
        // active records if the registered sequence should continue to be run in the future.
        // It is set to false when stopThisScript() or stopOtherScriptsForSprite() has been called.
        private boolean active;
        // isRunning records if this sequence is being run now.  It is used only in stopOtherScriptsForSprite.
        // This is similar to the variable above called inForeverloop, which is set to true if *any* sequence is
        // being run at the time.
        private boolean isRunning;
        // triggered is true indicates if this sequence is running.  It is false when the condition to 
        // run the sequence has not been met yet.  E.g., a key press sequence will have triggered false when
        // the key has not by hit by the user yet.
        protected boolean triggered; 

        private Object objToCall;
        private String methodToCall;

        /**
         * Constructor for objects of class Sequence
         */
        public Sequence(Object obj, String method)
        {
            this.sequenceLock = this;
            doneSequence = true;
            terminated = false;
            active = true;
            isRunning = false;
            triggered = true;      // override this in subclasses for non-automatically triggered sequences.
            this.objToCall = obj;
            this.methodToCall = method;
            // System.out.println("Sequence ctor: obj " + obj + " method " + method);
        }

        public String toString() {
            return "Sequence: obj " + objToCall + " method " + methodToCall + " doneSeq " + doneSequence;
        }

        // These are needed only for copy constructors.
        public Object getObj() { return objToCall; }

        public String getMethod() { return methodToCall; }

        public boolean isTerminated() { return terminated; }

        public void run()
        {
            try {
                synchronized (sequenceLock) {

                    while (doneSequence) {
                        // System.out.println(methodToCall + ": run(): Calling seqLock.wait");
                        sequenceLock.wait();
                        // System.out.println(methodToCall + ": run(): done with seqLock.wait");
                    }

                    java.lang.reflect.Method m = objToCall.getClass().getMethod(methodToCall, 
                            Class.forName("Scratch$Sequence"));
                    // System.out.println(methodToCall + ": run(): invoking callback");
                    inCbScript = true;
                    isRunning = true;
                    m.invoke(objToCall, this);

                    // System.out.println(methodToCall + ": run(): done invoking callback");

                }
            } catch (InvocationTargetException i) {
                if (i.getCause() instanceof StopScriptException) {
                    System.out.println("Sequence.invoke: got StopScriptException: making script inactive");
                    active = false;
                } else {
                    // We had a problem with invoke(), but it wasn't the StopScript exception, so
                    // just print out the info.
                    i.printStackTrace();
                }
            } catch (InterruptedException ie) {
            } catch (Throwable t) {
                t.printStackTrace();
            }
            System.out.println(methodToCall + ": run(): done");
            inCbScript = false;
            isRunning = false;

            terminated = true;
            doneSequence = true;
        }

        /**
         * Call this to relinquish control and wait for the next sequence.
         */
        public void waitForNextSequence() throws InterruptedException
        {
            doneSequence = true;
            sequenceLock.notify();

            while (doneSequence) {
                // System.out.println(methodToCall + ": waitForNextSequence(): calling seqLock.wait()");
                sequenceLock.wait();
                // System.out.println(methodToCall + ": waitForNextSequence(): done with seqLock.wait()");
            }
        }

        /**
         * The controller calls this when a sequence should be executed. The sequence thread
         * will be notified, and allowed to run until it relinquishes control, at which point
         * this method will return.
         */
        public void performSequence()
        {
            try {
                synchronized (sequenceLock) {
                    if (terminated) {
                        System.out.println(methodToCall + ": terminated already.");

                        return;
                    }

                    doneSequence = false;
                    // System.out.println(methodToCall + ": perfSeq: calling notify()");
                    sequenceLock.notify();  // Thread now continues

                    while (! doneSequence) {
                        // System.out.println(methodToCall + ": perfSeq: calling wait()");
                        sequenceLock.wait(); // Wait for thread to notify us it's done
                        // System.out.println(methodToCall + ": perfSeq: done with wait()");
                    }
                }
            }
            catch (InterruptedException ie) {
            }
            // System.out.println(methodToCall + ": perfSeq: done");
        }

        // This is a Template Method.  Each subclass returns true if the condition has
        // been met for the sequence to be invoked.  E.g., for an act-like method, there
        // is no condition -- it is run.  For a keypress method, it returns true if
        // the user has typed the specified key.
        protected boolean invoke()
        {
            return true;
        }
    }
    // Keep a list of all the "plain" sequences.
    private ArrayList<Sequence> sequences = new ArrayList<Sequence>();

    /* -------- End of Sequence definition --------- */

    public class KeyPressSeq extends Sequence {
        private String key;

        public KeyPressSeq(String key, Object obj, String method)
        {
            super(obj, method);
            this.key = key;
            // A key press sequence is not triggered until the key is hit.
            this.triggered = false;
        }

        public KeyPressSeq(KeyPressSeq other) {
            this(other.key, other.getObj(), other.getMethod());
        }

        public boolean isTriggered() {
            if (Greenfoot.isKeyDown(this.key)) {
                if (! triggered) {
                    System.out.println("keySeq: for key " + this.key + " changing from NOT triggered to triggered.");
                }
                triggered = true;
            }
            return triggered;
        }
    }
    private ArrayList<KeyPressSeq> keySeqs = new ArrayList<KeyPressSeq>();

    private class ActorOrStageClickedSeq extends Sequence {

        public ActorOrStageClickedSeq(Object obj, String method)
        {
            super(obj, method);
            // A clicked sequence is not triggered until the sprite or backdrop is clicked.
            this.triggered = false;
        }

        public ActorOrStageClickedSeq(ActorOrStageClickedSeq other) {
            this(other.getObj(), other.getMethod());
        }

    }

    private class ActorClickedSeq extends ActorOrStageClickedSeq {
        ActorClickedSeq(Object obj, String method) {
            super(obj, method);
        }
        public ActorClickedSeq(ActorClickedSeq other) {
            this(other.getObj(), other.getMethod());
        }

        public boolean isTriggered() {
            if (Greenfoot.mouseClicked(this.getObj())) {
                if (! triggered) {
                    System.out.println("ActorClickedSeq: for actor " + this.getObj() + " changing from NOT triggered to triggered.");
                }
                triggered = true;
            }
            return triggered;
        }
    }
    private ArrayList<ActorClickedSeq> actorClickedSeqs = new ArrayList<ActorClickedSeq>();
    
    private class StageClickedSeq extends ActorOrStageClickedSeq {
        StageClickedSeq(Object obj, String method) {
            super(obj, method);
        }        
        public StageClickedSeq(StageClickedSeq other) {
            this(other.getObj(), other.getMethod());
        }
        public boolean isTriggered() {
            if (Greenfoot.mouseClicked(null)) {
                if (! triggered) {
                    System.out.println("stageClickedSeq: changing from NOT triggered to triggered.");
                }
                triggered = true;
            }
            return triggered;
        }
    }
    private ArrayList<StageClickedSeq> stageClickedSeqs = new ArrayList<StageClickedSeq>();
    
    private class MesgRecvdSeq extends Sequence {
        private String mesg;

        public MesgRecvdSeq(String mesg, Object obj, String method) {
            super(obj, method);
            this.mesg = mesg;
            // A message received sequence is not triggered until the message is received.
            this.triggered = false;
        }
        public MesgRecvdSeq(MesgRecvdSeq other) {
            this(other.mesg, other.getObj(), other.getMethod());
        }
        public boolean isTriggered() {
            if (((ScratchWorld) getWorld()).bcastPending(mesg)) {
                if (! triggered) {
                    System.out.println("mesgRecvdSeq: for mesg " + mesg + " changing from NOT triggered to triggered.");
                }
                triggered = true;
            }
            return triggered;
        }
    }
    private ArrayList<MesgRecvdSeq> mesgRecvdSeqs = new ArrayList<MesgRecvdSeq>();

    /* -------------------  Variables ------------------------ */
    private ArrayList<Variable> varsToDisplay = new ArrayList<Variable>();

    /**
     * Create an integer variable whose value will be displayed on the screen.
     */
    public IntVar createIntVariable(String varName, int initVal)
    {
        IntVar newVar = new IntVar(varName, initVal);
        varsToDisplay.add(newVar);
        return newVar; 
    }

    /**
     * Create a String variable whose value will be displayed on the screen.
     */
    public StringVar createStringVariable(String varName, String val)
    {
        StringVar newVar = new StringVar(varName, val);
        varsToDisplay.add(newVar);
        return newVar; 
    }

    /**
     * Create a double variable whose value will be displayed on the screen.
     */
    public DoubleVar createDoubleVariable(String varName, double val)
    {
        DoubleVar newVar = new DoubleVar(varName, val);
        varsToDisplay.add(newVar);
        return newVar; 
    }

    /**
     * Create a boolean variable whose value will be displayed on the screen.
     */
    public BooleanVar createBooleanVariable(String varName, boolean val)
    {
        BooleanVar newVar = new BooleanVar(varName, val);
        varsToDisplay.add(newVar);
        return newVar; 
    }

    protected class Variable extends Actor 
    {
        private final Color textColor = Color.black;
        private final Color bgColor = Color.gray;

        private Object value;
        private String text;
        private boolean valChanged = true;
        private boolean display = true;           // is the variable supposed to be displayed or hidden?
        private boolean addedToWorldYet = false;  // has this object been added to the world yet?
        private int xLoc, yLoc;                   // initial location of the image.

        public Variable(String varName, Object val)
        {
            text = varName;
            value = val;
            valChanged = true;

            String dispStr = text + value + 2;   // add 2 for padding.  Remove later...
            int stringLength = dispStr.length() * 10;
            setImage(new GreenfootImage(stringLength, 16));      // TODO: remove this?
            updateImage();
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

        /**
         * Update the image being displayed.
         */
        private void updateImage()
        {
            if (! display) {
                System.out.println("IV.updateImage: calling clear");
                getImage().clear();
                return;
            }
            if (valChanged) {
                String dispStr = text + value;
                int stringLength = (dispStr.length() + 1) * 7;
                // Create a gray background until the variable's name.
                GreenfootImage image = new GreenfootImage(stringLength, 20);
                image.setColor(bgColor);
                image.fill();
                // Create orange background under the variable's value.
                image.setColor(Color.decode("#EE7D16"));
                image.fillRect((int) (text.length() * 6.5 + 1), 3, (value + "").length() * 10, 15);

                image.setColor(textColor);
                System.out.println("IV.updateImage: creating with value " + text + " " + value);
                image.drawString(text + " " + value, 1, 15);
                setImage(image);

                // Because the size of the image may have changed (to accommodate a longer
                // or shorter string to display), and because we want all images tiled nicely
                // along the left side of the screen, and because Greenfoot places images based
                // on the center of the image, we have to calculate a new location for
                // each image, each time.
                setLocation(xLoc + getImage().getWidth() / 2, yLoc + getImage().getHeight() / 2);
                valChanged = false;
            }
        }

        /**
         * Add the Variable actor to the world so that it can be displayed.
         */
        public void addToWorld(ScratchWorld sw)
        {
            super.addedToWorld(sw);
            if (! addedToWorldYet) {
                // Insert into the world.  Need to compute the width of the object because
                // addObject() uses x, y as the center of the image, and we want all these
                // displayed variable images to be lined up along the left side of the 
                // screen.
                int w = getImage().getWidth();
                int h = getImage().getHeight();
                // store the original x and y locations of the image.  These are used later
                // when the image is resized, so that we can keep the image lined up along
                // the left side of the screen.
                xLoc = sw.getDisplayVarXLoc();
                yLoc = sw.getDisplayVarYLoc();
                sw.addObject(this, xLoc + (int) (w / 2.0), (int) (yLoc + (h / 2.0)));
                addedToWorldYet = true;
                show();
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

    /*
     * Start of code!
     */

    public Scratch()
    {
        super();
        
        // put the first costume in our array of costumes.
        costumes.add(new Costume(getImage(), "Sprite1"));

        // System.out.println("item from getImage is " + System.identityHashCode(getImage()));
        // System.out.println("item in costumes array is " + System.identityHashCode(costumes.get(0)));

        // make sure the copy is a new copy of the image.
        costumesCopy.add(new GreenfootImage(getImage()));  
        // System.out.println("item in costumesCopy array is " + System.identityHashCode(costumesCopy.get(0)));
        // System.out.println("Scratch(): constructor finished for object " + System.identityHashCode(this));
    }

    /**
     * Copy constructor used only for cloning.
     * This is automatically called when a clone is created.
     */
    public Scratch(Scratch other, int x, int y)
    {
        // copy fields from other to this.
        isPenDown = other.isPenDown;
        penColor = other.penColor;
        penColorNumber = other.penColorNumber;
        penSize = other.penSize;
        currCostume = other.currCostume;
        costumes = new ArrayList<Costume>(other.costumes);     
        costumesCopy = new ArrayList<GreenfootImage>(other.costumesCopy);
        isShowing = other.isShowing;
        ghostEffect = other.ghostEffect;
        currentLayer = other.currentLayer;
        costumeSize = other.costumeSize;
        currDirection = other.currDirection;
        lastMouseX = other.lastMouseX;
        lastMouseY = other.lastMouseY;

        rotationStyle = other.rotationStyle;

        keySeqs = new ArrayList<KeyPressSeq>(other.keySeqs);
        actorClickedSeqs = new ArrayList<ActorClickedSeq>(other.actorClickedSeqs);
        stageClickedSeqs = new ArrayList<StageClickedSeq>(other.stageClickedSeqs);
        mesgRecvdSeqs = new ArrayList<MesgRecvdSeq>(other.mesgRecvdSeqs);
        cloneStartCbs = new ArrayList<CloneStartCb>(other.cloneStartCbs);

        // Initialize everything for this new Actor in Greenfoot.
        super.setLocation(x, y);
        setSizeTo(costumeSize);
        pointInDirection(currDirection);

        // NOTE: we are assuming that when this copy constructor is called, it is to make a clone.
        isClone = true;
        // Record that this new clone is not operating inside a cb script at this time.
        inCbScript = false;
        // a cloned Scratch actor does not say or think anything even if its clonee was saying something.
        sayActor = null;
        
        // System.out.println("Scratch: copy constructor finished for object " + System.identityHashCode(this));
    }

    /** 
     * This method is called by Greenfoot each time an actor is added to the world.
     * In this method, we register this actor's Class in the world, so that paint order
     * can be manipulated.
     * Any subclass of Scratch Actor has to implement addedToWorld() and call this method 
     * if the program needs to manipulate paint order and/or display variables.
     */
    public void addedToWorld(World w)
    {
        ((ScratchWorld) w).addToPaintOrder(this.getClass());

        // Add variables to be displayed to the world automatically so that code doesn't have to do it.
        for (Variable v : varsToDisplay) {
            v.addToWorld(((ScratchWorld) w));
        }
    }

    /*
     * act - first look for keypresses and call any registered methods on them.  Then, call each 
     * method registered as an 'act' callback -- e.g., a "whenFlagClicked" callback.
     * Users do NOT override (and cannot override) act() in this system.
     */
    public final void act()
    {
        // Call all the registered "whenFlagClicked" scripts.

        // Remove all terminated sequences from the main sequences list.  Do this by
        // copying the non-terminated ones to temp, then reassigning sequences to refer to temp.
        for (ListIterator<Sequence> iter = sequences.listIterator(); iter.hasNext(); ) {
            if (iter.next().isTerminated()) {
                iter.remove();
            }
        }

        for (Sequence seq : sequences) {
            seq.performSequence();
        }

        /* Now handle keyPress sequences.  They get restarted if they terminated. */
        
        for (ListIterator<KeyPressSeq> iter = keySeqs.listIterator(); iter.hasNext(); ) {
            KeyPressSeq seq = iter.next();
            if (seq.isTerminated()) {
                KeyPressSeq n = new KeyPressSeq(seq);
                iter.remove();   // remove old one
                iter.add(n);     // add new one that is reset to the beginning.
                n.start();
            }
        }

        /* Loop through sequences that have been invoked already. */
        for (KeyPressSeq seq: keySeqs) {
            // isTriggered returns true if a sequence has seen its key press done already, or
            // if the sequence is seeing its key press done right now.
            if (seq.isTriggered()) {
                seq.performSequence();
            }
        }

        /* ---------- Repeat, but for Sprite being clicked. ------------- */

        for (ListIterator<ActorClickedSeq> iter = actorClickedSeqs.listIterator(); iter.hasNext(); ) {
            ActorClickedSeq seq = iter.next();
            if (seq.isTerminated()) {
                ActorClickedSeq n = new ActorClickedSeq(seq);
                iter.remove();   // remove old one
                iter.add(n);     // add new one that is reset to the beginning.
                n.start();
            }
        }

        /* Loop through sequences that have been invoked already. */
        for (ActorClickedSeq seq : actorClickedSeqs) {
            // isTriggered returns true if a sequence has seen its sprite clicked already, or
            // if the sequence is seeing its sprite click done right now.
            if (seq.isTriggered()) {
                seq.performSequence();
            }
        }
        
        /* ---------- Repeat, but for Stage being clicked. ------------- */

        for (ListIterator<StageClickedSeq> iter = stageClickedSeqs.listIterator(); iter.hasNext(); ) {
            StageClickedSeq seq = iter.next();
            if (seq.isTerminated()) {
                StageClickedSeq n = new StageClickedSeq(seq);
                iter.remove();   // remove old one
                iter.add(n);     // add new one that is reset to the beginning.
                n.start();
            }
        }

        /* Loop through sequences that have been invoked already. */
        for (StageClickedSeq seq : stageClickedSeqs) {
            // isTriggered returns true if a sequence has seen the stage click done already, or
            // if the sequence is seeing stage click done right now.
            if (seq.isTriggered()) {
                seq.performSequence();
            }
        }
        
        /* ---------- Repeat, but for message being received. ------------- */

        for (ListIterator<MesgRecvdSeq> iter = mesgRecvdSeqs.listIterator(); iter.hasNext(); ) {
            MesgRecvdSeq seq = iter.next();
            if (seq.isTerminated()) {
                MesgRecvdSeq n = new MesgRecvdSeq(seq);
                iter.remove();   // remove old one
                iter.add(n);     // add new one that is reset to the beginning.
                n.start();
            }
        }

        /* Loop through sequences that have been invoked already. */
        for (MesgRecvdSeq seq : mesgRecvdSeqs) {
            // isTriggered returns true if a sequence has seen the stage click done already, or
            // if the sequence is seeing stage click done right now.
            if (seq.isTriggered()) {
                seq.performSequence();
            }
        }        

        if (sayActor != null) {
            sayActorUpdateLocation();
        }
        // Update lastImg to current image
        if (getImage() != null) {
            lastImg = getImage();
        }
    }

    /**
     * register a method to be called when the Scenario starts -- ala When Green Flag Clicked.
     */
    public void whenFlagClicked(String methodName)
    {
        Sequence s = new Sequence(this, methodName);
        sequences.add(s);
        s.start();   // call run() on the sequence's thread.
    }

    /**
     * register a method to be called each time a key press is noticed.
     * Note that Greenfoot runs very quickly so a key press is often noticed multiple 
     * times in a row.
     */
    public void whenKeyPressed(String keyName, String methodName)
    {
        KeyPressSeq k = new KeyPressSeq(keyName, this, methodName);
        keySeqs.add(k);
        k.start();
        // System.out.println("whenKeyPressed: thread added for key " + keyName);
    }

    /**
     * register a method to be called when a sprite is clicked.
     */
    public void whenSpriteClicked(String methodName)
    {
        ActorClickedSeq a = new ActorClickedSeq(this, methodName);
        // Add to the array list of methods to be called when an actor is clicked.
        actorClickedSeqs.add(a);
        a.start();
    }

    /**
     * register a method to be called when a sprite is clicked.
     */
    public void whenStageClicked(String methodName)
    {
        StageClickedSeq s = new StageClickedSeq(this, methodName);
        // add to the array list of methods to be called when the stage is clicked.
        stageClickedSeqs.add(s);
        s.start();
    }

    /**
     * register a method to be called when a specific message is received.
     */
    public void whenRecvMessage(String messageName, String methodName)
    {
        MesgRecvdSeq m = new MesgRecvdSeq(messageName, this, methodName);
        mesgRecvdSeqs.add(m);
        m.start();
    }

    
    /**
     * broadcast a message to all sprites.
     */
    public void broadcast(String message)
    {
        ((ScratchWorld) getWorld()).registerBcast(message);
    }

    /*
     * ---------------------------------------------------------------------
     * Control commands (most are not necessary to implement in Greenfoot)
     * ---------------------------------------------------------------------
     */

    /**
     * Create a new clone of this Sprite.  If this sprite has registered a 
     * startAsClone callback, then that method will be called.  If not, the 
     * new clone is positioned on the screen at the same location as the original.
     * TODO: if the original is hidden, make the clone hidden as well.
     */
    public void createCloneOfMyself()
    {
        // Create a new Object, which is a subclass of Scratch (the same class as "this").
        Object clone = callConstructor();

        // System.out.println("createCloneOfMyself: called copy constructor to get object of type " + 
        //    clone.getClass().getName() + ". Now, calling addObject()");
        ((ScratchWorld) getWorld()).addObject((Scratch)clone, super.getX(), super.getY());

        // If there are methods registered to be called when a clone is created,
        // call the methods now.   TODO: should this be done in the next frame?
        // But, have the new object run the callbacks.
        ((Scratch)clone).runCloneCallbacks();

        // System.out.println("Clone added");
    }

    /**
     * createCloneOf: create a clone of the given Scratch actor.
     */
    public void createCloneOf(Scratch actor)
    {
        // Create a new Object, which is a subclass of Scratch (the same class as "this").
        Object clone = callConstructor(actor);

        // System.out.println("createCloneOfMyself: called copy constructor to get object of type " + 
        //    clone.getClass().getName() + ". Now, calling addObject()");
        ((ScratchWorld) getWorld()).addObject((Scratch)clone, translateToGreenfootX(actor.getX()), 
            translateToGreenfootY(actor.getY()));

        // NOTE: Scratch does NOT run the "when added as clone" block when a clone of another
        // Sprite is created, so we won't either.

        System.out.println("Clone added");        
    }

    // Run registered "WhenIStartAsAClone" callbacks.
    private void runCloneCallbacks()
    {
        for (CloneStartCb cb : cloneStartCbs) {
            cb.invoke(this);
        }
    }

    private Object callConstructor(Scratch obj)
    {
        try {
            Constructor ctor = obj.getClass().getDeclaredConstructor(obj.getClass(), int.class, int.class);

            ctor.setAccessible(true);
            return ctor.newInstance(obj, super.getX(), super.getY());
        } catch (InstantiationException x) {
            x.printStackTrace();
        } catch (InvocationTargetException x) {
            x.printStackTrace();
        } catch (IllegalAccessException x) {
            x.printStackTrace();
        } catch (java.lang.NoSuchMethodException x) {
            x.printStackTrace();
        }
        return null;
    }

    private Object callConstructor()
    {
        return callConstructor(this);
    }

    /**
     * register a method to be called when a new clone starts up.  The method
     * has no parameters.
     */
    public void whenStartAsClone(String methodName)
    {
        // Save the method name, and also the name of the class of the new clone after it
        // is created.
        CloneStartCb cb = new CloneStartCb(getClass().getName(), methodName);
        cloneStartCbs.add(cb);
    }

    /**
     * remove this clone from the world.
     */
    public void deleteThisClone()
    {
        if (isClone) {        
            getWorld().removeObject(this);
        }
    }

    /**
     * Stop all scripts. In Scratch, event blocks like "when <keypress> pressed" still work 
     * even after all scripts have been stopped.  So, what it really means is "stop all scripts 
     * for all objects."  However, I am going to implement this by stopping Greenfoot.
     */
    public void stopAll()
    {
        Greenfoot.stop();
    }

    /**
     * If this function is called from within a callback script, 
     * unregister it (so that this isn't called again).
     */
    public void stopThisScript() throws StopScriptException
    {
        if (! inCbScript) {
            System.out.println("stopThisScript: returning because not in callback script.");
            return;
        }
        System.out.println("stopThisScript: throwing StopScriptException");
        throw new StopScriptException();
    }

    /**
     * Stop all other callback script methods from running anymore.  
     * If this is called from NOT in a callback script,
     * then stop *all* callback scripts.
     */
    public void stopOtherScriptsInSprite()
    {

        if (! inCbScript) {
            // Just make all callback scripts methods inactive.
            for (Sequence seq : sequences) {
                seq.active = false;
            }
        } else {
            for (Sequence seq : sequences) {
                if (! seq.isRunning) {
                    seq.active = false;
                }
            }
        }
    }

    /*
     * ---------------------------------------------------------------------
     * Pen commands.
     * ---------------------------------------------------------------------
     */
    /**
     * put the pen down so that a line is drawn for all subsequent movements 
     * of the actor.
     */
    public void penDown() 
    {
        isPenDown = true;
    }

    /**
     * put the pen up so that nothing is drawn for all subsequent movements 
     * of the actor.
     */
    public void penUp()
    {
        isPenDown = false;
    }

    /**
     * set the color to be drawn if the pen is down.
     */
    public void setPenColor(Color c)
    {
        penColor = c;
    }

    /**
     * set the color to a color number, between 0 and 200.
     */
    public void setPenColor(int c)
    {
        // the colors are numbered between 0 and 199, and then wraparound: 200 is 0, etc.
        penColorNumber = c % 200;
        penColor = Color.decode(numberedColors[penColorNumber]);
    }

    /**
     * change the pen color number by the given amount.
     */
    public void changePenColorBy(int n)
    {
        penColorNumber = (penColorNumber + n) % 200;
        penColor = Color.decode(numberedColors[penColorNumber]);
    }

    /**
     * set the pen size to the given value.  If pen size is set to 0 or negative,
     * a size of 1 is used. 
     */
    public void setPenSize(int size)
    {
        penSize = size;
        // getWorld().getBackground().setPenWidth(size);

    }

    /**
     * change pen size by the given amount.  If pen size is set to 0 or negative,
     * a size of 1 is used.
     */
    public void changePenSizeBy(int size)
    {
        penSize += size;
        if (penSize <= 0) {
            penSize = 1;
        }
        setPenSize(penSize);
    }

    /**
     * clear the screen.
     */
    public void clear()
    {
        // This call actually rewrites the backdrop onto the background, without
        // all the pen drawing, stamping, etc.
        ((ScratchWorld) getWorld()).clearBackdrop();
    }

    /**
     * copy the actor's image onto the screen.
     */
    public void stamp()
    {
        // The image that we get will not be rotated the same as the current image, so 
        // we have to do that ourselves.  Also, getX() and getY() will get the center of
        // the image, but drawImage() wants the upper left corner of where to draw it.
        // So, have to do some some manipulation here before drawing the image onto the
        // background.

        // NOTE: we have to get the max of the width and height of the current image. 
        // Then, make a new empty image with both dimensions equal to that max value.
        // Then, draw the current image onto the new image.  Then, rotate it.

        // But, this is even more complicated: when you make the new big square image, now
        // the offset from the upperleft corner to the middle will have changed...
        GreenfootImage oldImg;
        // Use lastImg if actor is hidden, as getImage returns null.
        if (isShowing) {
            oldImg = getImage();
        } else {
            oldImg = lastImg;
        }
        int w = oldImg.getWidth(), h = oldImg.getHeight();
        // System.out.println("image width: " + w + " height " + h);
        int newDim = w > h ? w : h;
        GreenfootImage image = new GreenfootImage(newDim, newDim);  
        image.drawImage(oldImg, (newDim - w) / 2, (newDim - h) / 2);
        int rot = getRotation();
        image.rotate(rot);

        // System.out.println("stamp: x " + super.getX() + " y " + super.getY());
        getWorld().getBackground().drawImage(image, super.getX() - newDim / 2, 
            super.getY() - newDim / 2);
        // System.out.println("stamp: drawing at x " + (super.getX() - newDim / 2) +
        //     " y " + (super.getY() - newDim / 2));
    }

    /*
     * ---------------------------------------------------------------------
     * Motion commands.
     * ---------------------------------------------------------------------
     */

    /**
     * move the given distance in the direction the sprite is facing.
     */
    public void move(int distance) 
    {
        int oldX = super.getX();
        int oldY = super.getY();

        if (rotationStyle == RotationStyle.ALL_AROUND) {
            super.move(distance);
        } else {      // rotationStyle is LEFT_RIGHT || DONT_ROTATE

            // We don't use the move() function provided by greenfoot because
            // it moves in the direction the image is facing.  If we use it,
            // then we cannot do the setRotationStyle(LEFT_RIGHT) correctly.
            // So, instead we move the actor using setLocation().

            int GFdir = (currDirection - 90) % 360;

            // This code copied from Greenfoot source.
            double radians = Math.toRadians(GFdir);
            // We round to the nearest integer, to allow moving one unit at an angle
            // to actually move.
            int dx = (int) Math.round(Math.cos(radians) * distance);
            int dy = (int) Math.round(Math.sin(radians) * distance);
            setLocation(oldX + dx, oldY + dy);
        }

        /* pen is down, so we need to draw a line from the current point to the new point */
        if (isPenDown) {
            getWorld().getBackground().setColor(penColor);
            getWorld().getBackground().drawLine(oldX, oldY, super.getX(), super.getY());
        }
    }

    /**
     * glide the sprite to the given x, y coordinates over the given time period.
     */
    public void glideTo(Sequence s, double duration, int x, int y)
    {
        if (duration < .02) {
            goTo(x, y);
            return;
        }
        duration *= 1000.0;   // convert to milliseconds.
        int begX = super.getX();  // get original X, Y in Greenfoot coordinates
        int begY = super.getY();
        int endX = translateToGreenfootX(x);   // get end destination in GF coordinates.
        int endY = translateToGreenfootY(y);
        // System.out.println("glideTo: beg " + begX + ", " + begY + " end " + endX + ", " + endY);
        double begTime = System.currentTimeMillis();
        double endTime = begTime + duration;
        double currTime;
        while ((currTime = System.currentTimeMillis()) < endTime) {
            try {
                s.waitForNextSequence();
            } catch (InterruptedException ie) {
                ie.printStackTrace();
            }
            // Compute how far along we are in the duration time.
            double diff = (currTime - begTime) / duration;
            int newX = begX + (int) ((endX - begX) * diff);
            int newY = begY + (int) ((endY - begY) * diff);
            goToGF(newX, newY);
        }
    }

    /**
     * move the sprite to the location on the screen, where (0, 0) is the center and x increases
     * to the right and y increases up.
     */
    public void goTo(int x, int y) 
    {
        int newX = translateToGreenfootX(x);
        int newY = translateToGreenfootY(y);
        // Call goToGF() which assumes greenfoot coordinates.
        // System.out.println("goTo: got x, y = " + x + ", " + y + " which are " + newX + ", " + newY);
        goToGF(newX, newY);
    }

    /**
     * move the sprite to where the mouse is.
     */
    public void goToMouse() 
    {
        MouseInfo mi = Greenfoot.getMouseInfo();
        if (mi == null) {
            return;
        }
        goToGF(mi.getX(), mi.getY());
    }

    /**
     * move to the location of another sprite
     */
    public void goTo(Scratch other)
    {
        goTo(other.getX(), other.getY());
    }

    /**
     * set the sprite's x position.  (left or right)
     */
    public void setXTo(int x) { 
        goTo(x, getY()); 
    }

    /**
     * set the sprite's y position.  (up or down)
     */
    public void setYTo(int y) 
    { 
        goTo(getX(), y); 
    }

    /**
     * change the x position of the sprite by the given value.
     */
    public void changeXBy(int val) 
    { 
        goTo(getX() + val, getY()); 
    }

    /**
     * change the y position of the sprite by the given value.
     */
    // subtract val from y since y increases upward in Scratch
    public void changeYBy(int val) 
    { 
        goTo(getX(), getY() + val); 
    }

    /**
     * turn the sprite clockwise by the given degrees.
     */
    public void turnRightDegrees(int degrees) {
        currDirection += degrees;
        setRotation(currDirection);
    }

    /**
     * turn the sprite counter-clockwise by the given degrees.
     */
    public void turnLeftDegrees(int degrees) { 
        currDirection -= degrees;
        setRotation(currDirection);
    }

    /**
     * point the sprite in the given direction.  0 is up, 
     * 90 is to the right, -90 to the left, 180 is down.
     */
    public void pointInDirection(int dir) 
    {
        currDirection = dir;
        setRotation(currDirection);
    }
    
    /**
     * Override for setRotation to handle Rotation Styles more succinctly
     *
     */
    public void setRotation(int rotation)
    {
        // Ensure that rotation and currDirection are between 0 and 360
        if (rotation < 0) {
            rotation += 360;
        }
        if (currDirection < 0) {
            currDirection += 360;
        }
        rotation %= 360;
        currDirection %= 360;
        
        // rotation Style logic unified from all methods involving rotation
        if (rotationStyle == RotationStyle.ALL_AROUND) {
            super.setRotation(rotation - 90);
            isFlipped = false;
        } else if (rotationStyle == RotationStyle.LEFT_RIGHT) {
            if (isFacingLeft(currDirection)) {
                super.setRotation(180);
                // check if image should be flipped
                if (!isFlipped) {
                    // if image is null use lastImg instead so stamping works properly
                    if (getImage() != null) {
                        getImage().mirrorVertically();
                    } else {
                        lastImg.mirrorVertically();
                    }
                    isFlipped = true;
                }
            } else {
                super.setRotation(0);
                // check if image should be unflipped
                if (isFlipped) {
                    // if image is null use lastImg instead so stamping works properly
                    if (getImage() != null) {
                        getImage().mirrorVertically();
                    } else {
                        lastImg.mirrorVertically();
                    }
                    isFlipped = false;
                }
            }
        } else {
            super.setRotation(0);
            isFlipped = false;
        }
    }
    
    
    
    /**
     * return the direction the sprite is pointed in.  Note that the sprite/actor
     * may not look like it is facing this way, due to the rotation style that is set.
     */
    public int getDirection()
    {
        return currDirection;
    }

    /**
     * turn the sprite to point toward the direction of the given sprite
     */
    public void pointToward(Scratch other)
    {
        // deltaX and deltaY are in Greenfoot coordinates.
        double deltaX = translateToGreenfootX(other.getX()) - super.getX();
        double deltaY = translateToGreenfootY(other.getY()) - super.getY();
        double degrees = java.lang.Math.toDegrees(java.lang.Math.atan2(deltaY, deltaX));
        int oldDir = currDirection;
        currDirection = (int) degrees + 90;   // convert to Scratch orientation

        setRotation(currDirection);

        // TODO: need displayCostume() call?
    }

    /**
     * turn the sprite to point toward the mouse.
     */
    public void pointTowardMouse()
    {
        MouseInfo mi = Greenfoot.getMouseInfo();
        if (mi == null) {
            return;
        }
        double deltaX = mi.getX() - super.getX();
        double deltaY = mi.getY() - super.getY();
        double degrees = java.lang.Math.toDegrees(java.lang.Math.atan2(deltaY, deltaX));
        // NOTE: this code identical to code above, and very similar to code above that... refactor!
        int oldDir = currDirection;
        currDirection = (int) degrees + 90;   // convert to Scratch orientation

        setRotation(currDirection);
    }

    /**
     * if the sprite is on the edge of the Scenario, then changes its direction to point
     * as if it bounced against the edge.
     */
    public void ifOnEdgeBounce()
    {
        
        if (super.getX() + lastImg.getWidth() / 2 >= getWorld().getWidth() - 1) {
            // hitting right edge
            currDirection = (360 - currDirection) % 360;
            setRotation(currDirection);
            // prevent actor from getting stuck on the edge by pushing it out
            changeXBy(-((super.getX() + lastImg.getWidth() / 2) - (getWorld().getWidth() - 1)) - 1); 
        } else if (super.getX() - lastImg.getWidth() / 2 <= 0) {
            // hitting left edge
            currDirection = (360 - currDirection) % 360;
            setRotation(currDirection);
            // prevent actor from getting stuck on the edge by pushing it out
            changeXBy(-(super.getX() - lastImg.getWidth() / 2) + 1);
        }
        if (super.getY() + lastImg.getHeight() / 2 >= getWorld().getHeight() - 1) {
            // hitting top
            currDirection = (180 - currDirection) % 360;
            setRotation(currDirection);
            // prevent actor from getting stuck on the edge by pushing it out
            changeYBy(((super.getY() + lastImg.getHeight() / 2) - (getWorld().getHeight() - 1)) + 1);
        } else if (super.getY() - lastImg.getHeight() / 2 <= 0) {
            // hitting bottom
            currDirection = (180 - currDirection) % 360;
            setRotation(currDirection);
            // prevent actor from getting stuck on the edge by pushing it out
            changeYBy((super.getY() - lastImg.getHeight() / 2) - 1);
        }
    }

    /**
     * Set the rotation style to one of ALL_AROUND (default), LEFT_RIGHT, 
     * or DONT_ROTATE.
     */
    public void setRotationStyle(RotationStyle rs)
    {
        if (rs == rotationStyle) {
            return;    // no change
        }
        rotationStyle = rs;

        // Take the original image and make a new copy of it.
        GreenfootImage img = new GreenfootImage(costumesCopy.get(currCostume));
        // Now scale it.
        if (costumeSize != 100) {
            img.scale((int) (img.getWidth() * (costumeSize / 100.0F)),
                (int) (img.getHeight() * (costumeSize / 100.0F)));
        }

        // No need to rotate the image.  Rotation is a property of the Actor, not the image,
        // so when you switch images they are rotated automatically (just like Scratch as
        // it turns out).
        costumes.set(currCostume, new Costume(img, costumes.get(currCostume).name));
        displayCostume();
        setRotation(currDirection);
    }

    /**
     * return x coordinate of this sprite.
     */
    public int getX() 
    {
        // System.out.println("x in GF is " + super.getX(); + " but in scratch is " + translateGFtoScratchX(super.getX()));
        return translateGFtoScratchX(super.getX());
    }

    /**
     * return the y coordinate of this sprite.
     */
    public int getY() 
    {
        // System.out.println("y in GF is " + super.getY() + " but in scratch is " + translateGFtoScratchY(super.getY()));
        return translateGFtoScratchY(super.getY());
    }

    // private helper function
    private void goToGF(int x, int y)
    {
        if (! isPenDown) {
            super.setLocation(x, y);
            return;
        }
        /* pen is down, so we need to draw a line from the current point to the new point */
        int oldX = super.getX();
        int oldY = super.getY();
        super.setLocation(x, y);
        getWorld().getBackground().setColor(penColor);
        getWorld().getBackground().drawLine(oldX, oldY, super.getX(), super.getY());
    }

    // private helper function
    private boolean isFacingLeft(int dir)
    {
        return ((dir < 0 && dir > -180) || (dir > 180 && dir < 360));
    }

    /*
     * ---------------------------------------------------------------------
     * Commands from the Looks tab in Scratch.
     * ---------------------------------------------------------------------
     */

    /**
     * display the given string next to the sprite.
     */
    public void say(String str)
    {
        if (sayActor != null) {
            if (str == null) {
                // saying nothing means remove the sayActor
                getWorld().removeObject(sayActor);
                sayActor = null;
            } else {
                sayActor.setString(str);
            }
            return;
        }

        GreenfootImage mySprite;
        if (getImage() == null) {
            mySprite = lastImg;
        } else {
            mySprite = getImage();
        }
        
        int width = mySprite.getWidth();
        int height = mySprite.getHeight();

        sayActor = new Sayer(str);
        getWorld().addObject(sayActor, super.getX() + width + 10, super.getY() - height - 5);
    }

    /**
     * display the given string for <n> seconds next to the sprite.
     */
    public void sayForNSeconds(Sequence s, String str, double duration)
    {
        GreenfootImage mySprite;
        if (getImage() == null) {
            mySprite = lastImg;
        } else {
            mySprite = getImage();
        }
        
        int width = mySprite.getWidth();
        int height = mySprite.getHeight();

        sayActor = new Sayer(str);
        getWorld().addObject(sayActor, super.getX() + width + 10, super.getY() - height - 5);

        wait(s, duration);

        getWorld().removeObject(sayActor);
        sayActor = null;
    }

    // called from act() above to update the location of the say/think actor.
    private void sayActorUpdateLocation()
    {
        GreenfootImage mySprite;
        if (getImage() == null) {
            mySprite = lastImg;
        } else {
            mySprite = getImage();
        }
        
        int width = mySprite.getWidth();
        int height = mySprite.getHeight();
        sayActor.updateLocation(super.getX() + width + 10, super.getY() - height - 5);
    }

    /**
     * add new costume to the list of costumes for a sprite, given the
     * file name and the name of the costume.  Not available in Scratch.
     */
    public void addCostume(String costumeFile, String costumeName)
    {
        // Name the new costume with the # of items in the array: Sprite2, Sprite3, etc.
        GreenfootImage img = new GreenfootImage(costumeFile);
        costumes.add(new Costume(img, costumeName));
        costumesCopy.add(new GreenfootImage(costumeFile));
    }
  
    /**
     * add new costume to the list of costumes for a sprite, with the
     * name Sprite# (e.g., Sprite2, Sprite3, Sprite4, ...)
     * Not available in Scratch.
     */
    public void addCostume(String costumeFile) 
    {
        addCostume(costumeFile, "Sprite" + costumes.size());
    }

    /**
     * switch to the next costume
     */
    public void nextCostume() 
    {
        // System.out.println("nextCostume!");
        currCostume = (currCostume + 1) % costumes.size();
        displayCostume();
    }

    /**
     * switch to the previous costume
     */
    public void prevCostume()
    {
        // Note: this function is not offered in Scratch
        currCostume--;
        if (currCostume == -1) {
            currCostume = costumes.size() - 1;
        }
        displayCostume();
    }

    /**
     * switch to the costume with the given number.
     */
    public void switchToCostume(int costumeNum)
    {
        if (costumeNum < 0 || costumeNum > costumes.size() - 1) {
            return;     // can't switch to the desired costume, so do nothing.
        }
        currCostume = costumeNum;
        displayCostume();
    }
    
    /**
     * switch to the costume with the given name.  If the name is unknown,
     * no switch will happen.
     */
    public void switchToCostume(String costumeName)
    {
        for (int i = 0; i < costumes.size(); i++) {
            if (costumes.get(i).name.equals(costumeName)) {
                switchToCostume(i);
                return;
            }
        }
    }

    /**
     * return the number of the current costume.
     */
    public int getCostumeNumber()
    {
        return currCostume;
    }

    /**
     * hide this sprite -- don't show it.
     */
    public void hide()
    {
        isShowing = false;
        displayCostume();
    }

    /**
     * show this sprite in the world.
     */
    public void show()
    {
        isShowing = true;
        displayCostume();
        // ensure that image is oriented properly if rotation style was changed while invisible
        if (!lastImg.equals(getImage()) && isFlipped) {
            getImage().mirrorVertically();
        }
    }

    /**
     * set the ghost effect (transparency) to a value from 0 to 100.  
     * 0 is fully visible; 100 is completely invisible.
     */
    public void setGhostEffectTo(int amount)
    {
        if (amount < 0) {
            amount = 0;
        } else if (amount > 100) {
            amount = 100;
        }
        ghostEffect = amount;
        displayCostume();
    }

    /**
     * change the ghost effect (transparency) by the given amount.
     * 0 is full visible; 100 is fully invisible.
     */
    public void changeGhostEffectBy(int amount)
    {
        setGhostEffectTo(ghostEffect + amount);
    }

    /**
     * change the size of this sprite by the given percent.
     */
    public void changeSizeBy(int percent)
    {
        setSizeTo(costumeSize + percent);
    }

    /**
     * Move the sprite to the front in the paint order.
     */
    public void goToFront()
    {
        // move this object's class in the paint order.
        ((ScratchWorld) getWorld()).moveClassToFront(this.getClass());
    }

    /**
     * Move the sprite forward <n> layers in the paint order.
     */
    public void goForwardNLayers(int n)
    {
        // move this object's class in the paint order.
        ((ScratchWorld) getWorld()).moveClassForwardNLayers(this.getClass(), n);
    }

    /**
     * Move the sprite back <n> layers in the paint order.
     */
    public void goBackNLayers(int n)
    {
        // move this object's class in the paint order.
        ((ScratchWorld) getWorld()).moveClassBackNLayers(this.getClass(), n);
    }

    /**
     * Paint the sprite at layer n.
     */
    public void setLayer(int n)
    {
        // move this object's class in the paint order.
        ((ScratchWorld) getWorld()).moveClassToLayerN(this.getClass(), n);
    }

    /**
     * Return the current layer of this sprite in the paint order.
     */
    public int getLayer()
    {
        return ((ScratchWorld) getWorld()).getLayer(this.getClass());
    }

    /**
     * return the size (in percent) of the sprite.  (100% is the 
     * original size.)
     */
    public int size() 
    {
        return costumeSize;
    }

    /**
     * Set the sprite size to a percentage of the original size.
     */
    public void setSizeTo(int percent)
    {
        float perc = percent / 100.0F;
        // Take the original image and make a new copy of it.
        GreenfootImage img = new GreenfootImage(costumesCopy.get(currCostume));
        // System.out.println("sst: Making copy of the costumesCopy and scaling it.");
        // Now scale it, store it and display it.
        img.scale((int) (img.getWidth() * perc), (int) (img.getHeight() * perc));
        // No need to rotate the image.  Rotation is a property of the Actor, not the image, 
        // so when you switch images they are rotated automatically (just like Scratch as
        // it turns out).
        Costume tempCost = new Costume(img, costumes.get(currCostume).name);
        costumes.set(currCostume, tempCost);
        displayCostume();
        costumeSize = percent;

        /*System.out.println("sst: item from getImage is " + System.identityHashCode(getImage()));
        System.out.println("sst: item in costumes array is " + System.identityHashCode(costumes.get(currCostume)));
        System.out.println("sst: item in costumesCopy array is " + System.identityHashCode(costumesCopy.get(currCostume)));
        */
    }

    // private helper function
    private void displayCostume()
    {
        if (isShowing) {
            Costume cost = costumes.get(currCostume);
            // Greenfoot transparency is from 0 to 255, with 0 being fully visible and 255 being
            // fully transparent.  So, we need to do a transformation: (0, 100) -> (255, 0)
            int transparency = (int) (((-1 * ghostEffect)   // now from -100 to 0
                                          + 100)            // now from 0 to 100
                                           * 2.55);         // now from 0 to 255.
            cost.img.setTransparency(transparency);
            setImage(cost.img);
        } else {
            setImage((GreenfootImage) null);
        }
    }

    /**
     * return the current backdrop name being shown in the world.
     */
    public String backdropName()
    {
        return ((ScratchWorld) getWorld()).getBackdropName();
    }

    /*
     * ---------------------------------------------------------------------
     * Sensing blocks.
     * ---------------------------------------------------------------------
     */

    /**
     * return true if this sprite is touching the other given sprite,
     * false otherwise.
     */
    public boolean isTouching(Scratch other)
    {
        return intersects((Actor) other);
    }
    
    /**
     * return true if this sprite is touching another sprite, with the given name.
     */
    public boolean isTouching(String spriteName) 
    {
        Scratch other = ((ScratchWorld) getWorld()).getActorByName(spriteName);
        return isTouching(other);
    }

    /**
     * return true if this sprite is touching the mouse, 
     * false otherwise.
     */
    public boolean isTouchingMouse()
    {
        MouseInfo mi = Greenfoot.getMouseInfo();
        if (mi == null) {
            return false;
        }
        if (mi.getActor() == null) {
            return false;
        }
        return (mi.getActor() == this);
    }

    /**
     * return true if this sprite is touching the edge of the world,
     * false otherwise.
     */
    public boolean isTouchingEdge()
    {
        return (super.getX() + lastImg.getWidth() / 2 >= getWorld().getWidth() - 1 || super.getX() - lastImg.getWidth() / 2 <= 0 || 
            super.getY() + lastImg.getHeight() / 2 >= getWorld().getHeight() - 1 || super.getY() - lastImg.getHeight() / 2 <= 0);
    }

    /**
     * return true if this sprite is touching the given color in the background.
     */
    public boolean isTouchingColor(Color color)
    {
        GreenfootImage im = getImage();
        int height = im.getHeight();
        int width = im.getWidth();
        int x = getX();
        int y = getY();
        java.awt.image.BufferedImage bIm = im.getAwtImage();
        for (int w = 0; w < width; w++) {
            for (int h = 0; h < height; h++) {
                int pixel = bIm.getRGB(w, h);
                if ((pixel >> 24) == 0x00) {
                    continue;   // transparent pixel: skip it.
                }
                // See if the pixel at this location in the background is of the given color.
                if (getWorld().getColorAt(x + (w / 2), y + (h / 2)).equals(color)) {
                    // Not sure this is correct, as it checks the transparency value as well...
                    return true;
                }
            }
        }
        return false;
    }

    /**
     * return the x position of the mouse
     */
    public int getMouseX()
    {
        MouseInfo mi = Greenfoot.getMouseInfo();
        if (mi == null) {
            return translateGFtoScratchX(lastMouseX);
        }
        // squirrel away the x value so that every call to this function returns a x value, 
        // even if the mouse hasn't moved.
        lastMouseX = mi.getX();
        return translateGFtoScratchX(lastMouseX);
    }

    /**
     * return the y position of the mouse
     */
    public int getMouseY()
    {
        MouseInfo mi = Greenfoot.getMouseInfo();
        if (mi == null) {
            return translateGFtoScratchY(lastMouseY);
        }
        // squirrel away the y value so that every call to this function returns a y value, 
        // even if the mouse hasn't moved.
        lastMouseY = mi.getY();
        return translateGFtoScratchY(lastMouseY);
    }

    /**
     * return true if the mouse is pressed down right now, else false.
     */
    public boolean isMouseDown()
    {
        return Greenfoot.mousePressed(null) || Greenfoot.mouseDragged(null);
    }

    /**
     * return true if the given key is currently pressed, else false.
     */
    public boolean isKeyPressed(java.lang.String keyName)
    {
        return Greenfoot.isKeyDown(keyName);
    }

    /**
     * return the distance in pixels to the other sprite.
     */
    public int distanceTo(Scratch other)
    {
        int deltaX = super.getX() - other.getX();
        int deltaY = super.getY() - other.getY();
        return (int) java.lang.Math.sqrt(deltaX * deltaX + deltaY * deltaY);
    }

    /**
     * return the distance in pixels to the mouse pointer.
     */
    public int distanceToMouse()
    {
        int x, y;
        MouseInfo mi = Greenfoot.getMouseInfo();
        if (mi == null) {
            x = lastMouseX;
            y = lastMouseY;
        } else {
            x = mi.getX();
            y = mi.getY();
        }
        int deltaX = super.getX() - x;
        int deltaY = super.getY() - y;
        return (int) java.lang.Math.sqrt(deltaX * deltaX + deltaY * deltaY);
    }

    /**
     * return the time, in seconds and tenths of seconds, since the scenario started.
     */
    public double getTimer()
    {
        return ((ScratchWorld) getWorld()).getTimer();
    }

    /**
     * reset the built-in timer to 0.0.
     */
    public void resetTimer()
    {
        ((ScratchWorld) getWorld()).resetTimer();
    }

    /**
     * return the x position of the given sprite.
     */
    public int xPositionOf(Scratch other)
    {
        return translateGFtoScratchX(other.getX());
    }

    /**
     * return the y position of the given sprite.
     */
    public int yPositionOf(Scratch other)
    {
        return translateGFtoScratchY(other.getY());
    }

    /**
     * return the direction the given sprite is pointing to.
     */
    public int directionOf(Scratch other)
    {
        return other.getDirection();
    }

    /**
     * return the costume number of the given sprite
     */
    public int costumeNumberOf(Scratch other)
    {
        return other.getCostumeNumber();
    }

    /**
     * return the size (in percentage of the original) of the given sprite
     */
    public int sizeOf(Scratch other)
    {
        return other.size();
    }

    /**
     * return the current year.
     */
    public int getCurrentYear()
    {
        Calendar now = Calendar.getInstance();   // Gets the current date and time
        return now.get(Calendar.YEAR);
    }

    /**
     * return the current month.
     */
    public int getCurrentMonth()
    {
        Calendar now = Calendar.getInstance();   // Gets the current date and time
        return now.get(Calendar.MONTH) + 1;
    }

    /**
     * return the current date.
     */
    public int getCurrentDate()
    {
        Calendar now = Calendar.getInstance();   // Gets the current date and time
        return now.get(Calendar.DATE);
    }

    /**
     * return the current day of the week.
     */
    public int getCurrentDayOfWeek()
    {
        Calendar now = Calendar.getInstance();   // Gets the current date and time
        return now.get(Calendar.DAY_OF_WEEK);
    }

    /**
     * return the current hour.
     */
    public int getCurrentHour()
    {
        Calendar now = Calendar.getInstance();   // Gets the current date and time
        return now.get(Calendar.HOUR_OF_DAY);
    }

    /**
     * return the current minute.
     */
    public int getCurrentMinute()
    {
        Calendar now = Calendar.getInstance();   // Gets the current date and time
        return now.get(Calendar.MINUTE);
    }

    /**
     * return the current second.
     */
    public int getCurrentSecond()
    {
        Calendar now = Calendar.getInstance();   // Gets the current date and time
        return now.get(Calendar.SECOND);
    }

    /**
     * askStringAndWait
     */
    public String askStringAndWait(String message)
    {
        return JOptionPane.showInputDialog(message);
    }

    /*
     * Miscellaneous stuff.
     */

    /**
     * offer the CPU to other Sequences.
     */
    public void yield(Sequence s)
    {
        try {
            s.waitForNextSequence();
        } catch (InterruptedException ie) {
            ie.printStackTrace();
        }
    }

    /**
     * delay execution for "duration" seconds.
     * 
     * Note: this does not work if the duration is very short -- shorter than
     * the current frameRate that Greenfoot is running at.  
     * Also, note that this implementation is NOT dependent on the speed the simulation 
     * is running at: it tries to wait exactly duration seconds, regardless of how fast
     * the speed is set.
     */
    public void wait(Sequence s, double duration) 
    {
        double endTime = System.currentTimeMillis() + duration * 1000.0;
        while (System.currentTimeMillis() < endTime) {
            try {
                s.waitForNextSequence();
            } catch (InterruptedException ie) {
                ie.printStackTrace();
            }
        }
    }

    public void wait(Sequence s, int duration) {  wait(s, (double) duration); }

    public void wait(Sequence s, float duration) {  wait(s, (double) duration); }

    /*
     * --------------------------------------------------------------
     * Operator Blocks
     * --------------------------------------------------------------
     */

    public String join(String a, String b) { return a + b; }

    public String join(String a, int b) { return a + b; }

    public String join(String a, double b) { return a + b; }

    public String join(String a, float b) { return a + b; }

    public String join(int a, String b) { return Integer.toString(a) + b; }

    public String join(double a, String b) { return Double.toString(a) + b; }

    public String join(float a, String b) { return Float.toString(a) + b; }

    public String join(int a, int b) { return Integer.toString(a) + Integer.toString(b); }

    public String join(double a, double b) { return Double.toString(a) + Double.toString(b); }

    public String join(float a, float b) { return Float.toString(a) + Float.toString(b); }

    public String join(int a, double b) { return Integer.toString(a) + Double.toString(b); }

    public String join(int a, float b) { return Integer.toString(a) + Float.toString(b); }

    public String join(float a, int b) { return Float.toString(a) + Integer.toString(b); }

    public String join(double a, int b) { return Double.toString(a) + Integer.toString(b); }

    public String join(float a, double b) { return Float.toString(a) + Double.toString(b); }

    public String join(double a, float b) { return Double.toString(a) + Float.toString(b); }

    public String letterNOf(String s, int n) 
    {
        if (n < 0) {
            return "";
        }
        if (n >= s.length()) {
            return "";
        }
        return "" + s.charAt(n);
    }

    public String letterNOf(int i, int n) { return letterNOf(Integer.toString(i), n); }

    public String letterNOf(double d, int n) { return letterNOf(Double.toString(d), n); }

    public String letterNOf(float f, int n) { return letterNOf(Float.toString(f), n); }

    public int lengthOf(String s) 
    {
        return s.length();
    }

    public int lengthOf(int i) { return lengthOf(Integer.toString(i)); }

    public int lengthOf(double d) { return lengthOf(Double.toString(d)); }

    public int lengthOf(float f) { return lengthOf(Float.toString(f)); }

    /**
     * return a random number between low and high, inclusive (for both).
     */
    public int pickRandom(int low, int high)
    {
        // getRandomNumber gets a number between 0 (inclusive) and high (exclusive).
        // so we have add low to the value.
        return Greenfoot.getRandomNumber(high - low + 1) + low;
    }

    public int getWorldMinX()
    {
        return translateGFtoScratchX(0);
    }

    public int getWorldMaxX()
    {
        return translateGFtoScratchX(getWorld().getWidth() - 1);
    }

    public int getWorldMinY()
    {
        // subtract 1 because the world goes from 0 to Height - 1.
        return translateGFtoScratchY(getWorld().getHeight() - 1);
    }

    public int getWorldMaxY()
    {
        return translateGFtoScratchY(0);
    }

    /*
     * Scratch's (0, 0) is in the middle, with increase x to the right.  So, to translate
     * from scratch to greenfoot, add half the width of the world.
     */
    public int translateToGreenfootX(int x) 
    {
        return x + getWorld().getWidth() / 2;
    }

    /*
     * Scratch's (0, 0) is in the middle, with y increasing y up, while greenfoot's 0, 0 is in 
     * the upper-left corner with y increasing downward.
     */
    public int translateToGreenfootY(int y) 
    {
        return getWorld().getHeight() / 2 - y;
    }

    /*
     * translateGFToScratchX - translate greenfoot x coordinate to a Scratch coord.
     */
    public int translateGFtoScratchX(int x)
    {
        return x - getWorld().getWidth() / 2;
    }

    /*
     * translateGFToScratchY - translate greenfoot y coordinate to a Scratch coord.
     */
    public int translateGFtoScratchY(int y)
    {
        return getWorld().getHeight() / 2 - y;
    }

    /**
     * Sayer: a bubble that follows a Scratch actor around, displaying what
     * they are saying or thinking.
     */
    public class Sayer extends Scratch
    {
        private String str;
        int x, y;             // in Greenfoot coordinates.

        public Sayer(String str)
        {
            super();
            this.str = str;
            // this.x = x;
            // this.y = y;
            update();
        }

        /**
         * Set the string to display.
         */
        public void setString(String newStr)
        {
            if (newStr.equals(str)) {
                return;
            }
            str = newStr;
            update();
        }

        private void update() 
        {
            // use this image just to get the extents of the string.
            GreenfootImage junk = new GreenfootImage(str, 14, null, null);
            int imgW = junk.getWidth() + 4;
            int imgH = junk.getHeight() + 4;
            junk = null;    // release the image.

            GreenfootImage img = new GreenfootImage(imgW, imgH);
            img.setColor(Color.white);   // set background to white.
            img.fill();   
            img.setColor(Color.black);   // set text color to black.

            // Draw a rounded rectangle around the edge of the image.
            RoundRectangle2D.Float rect = 
                new RoundRectangle2D.Float(0, 0, imgW - 1, imgH - 1, 
                    10, 10);  // these are arc widths.
            img.drawShape(rect);

            img.drawString(str, 2, 13);
            setImage(img);
        }

        /**
         * update the location of the box that shows what is being said.
         * x and y are in Greenfoot coordinates.  Should not be called explicitly.
         */
        public void updateLocation(int x, int y)
        {
            setLocation(x, y);
        }

    }
}
