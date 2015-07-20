import greenfoot.*;  // (World, Actor, GreenfootImage, Greenfoot and MouseInfo)
import java.awt.Color;
import java.awt.Graphics;

/**
 * An IntegerVar holds a single integer and, optinally, displays its value on the
 * Scratch background.
 * Thanks to Michael Kolling for Counter.java, from which this borrows heavily.
 * 
 * @author Victor Norman
 * @version July 10, 2014
 */

/**
 * IntegerVar that displays a variable's name and its value.
 * 
 * This is heavily based off of Michael Kolling's Counter class.
 * 
 * @author Victor Norman
 * @version 0.1
 */
public class IntegerVar extends Actor
{
    private static final Color textColor = Color.black;
    private static final Color bgColor = Color.gray;

    private int value;
    private String text;
    private boolean valChanged = true;
    private boolean display = true;    // is the variable supposed to be displayed or hidden?
    private boolean addedToWorldYet = false;  // has this object been added to the world yet?
    private int xLoc, yLoc;            // initial location of the image.
    
    /**
     * Create a variable with the given name and given initial value.
     */
    public IntegerVar(String varName, int initVal)
    {
        text = varName;
        value = initVal;
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
    public void set(int newVal)
    {
        value = newVal;
        valChanged = true;
    }

    /**
     * @return the value.
     */
    public int get()
    {
        return value;
    }

    /**
     * Update the image being displayed.
     */
    private void updateImage()
    {
        if (display && valChanged) {
            String dispStr = text + value;
            int stringLength = (dispStr.length() + 1) * 7;
            GreenfootImage image = new GreenfootImage(stringLength, 20);
            image.setColor(bgColor);
            image.fill();
            image.setColor(Color.decode("#EE7D16"));
            image.fillRect((int) (text.length() * 6.5 + 1), 3, (value + "").length() * 10, 15);
            image.setColor(textColor);
            // System.out.println("IV.updateImage: creating with value " + text + " " + value);
            image.drawString(text + " " + value, 1, 15);
            setImage(image);
            
            // Because the size of the image may have changed (to accommodate a longer
            // or shorter string to display), and because we want all images tiled nicely
            // along the left side of the screen, and because Greenfoot places images based
            // on the center of the image, we have to calculate a new location for
            // each image, each time.
            setLocation(xLoc + getImage().getWidth() / 2, yLoc + getImage().getHeight() / 2);
            valChanged = false;
        } else {
            // System.out.println("IV.updateImage: calling clear");
            getImage().clear();
        }
    }

    /**
     * Add the IntegerVar actor to the world so that it can be displayed.
     * This must be called after the ScratchWorld has been fully constructed -- e.g., 
     * the first time from act() of the object that stores/updates this variable.
     */
    public void addToWorld(ScratchWorld sw)
    {
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
