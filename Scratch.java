
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

import greenfoot.*;  // (getWorld(), Actor, GreenfootImage, Greenfoot and MouseInfo)

import java.io.File;
import java.util.ArrayList;
import java.util.List;
import java.util.LinkedList;
import java.util.ListIterator;
import java.util.Calendar;
import java.util.HashMap;
import java.util.Hashtable;
import java.util.concurrent.LinkedTransferQueue;
import java.util.Stack;
import java.util.stream.*;
import java.awt.Color;
import java.awt.image.BufferedImage;
import java.awt.image.AffineTransformOp;
import java.awt.geom.AffineTransform;
import java.awt.image.Raster;
import java.awt.image.WritableRaster;
import java.lang.String;
import java.lang.reflect.*;
import javax.swing.JOptionPane;
import javax.sound.sampled.*;
import javax.sound.midi.*;
import java.awt.geom.RoundRectangle2D;

/**
 * class Scratch
 * 
 * @author Victor Norman 
 * @version 0.1
 */
public class Scratch extends Actor implements Comparable<Scratch>
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
            "#00FF8C", "#00FF93", "#00FF9B", "#00FFA3", "#00FFAA",        // indices 85 - 89
            "#00FFB2", "#00FFBA", "#00FFC1", "#00FFC9", "#00FFD1",        // indices 90 - 94
            "#00FFD8", "#00FFE0", "#00FFE8", "#00FFEF", "#00FFF7",        // indices 95 - 99
            "#00FFFF", "#00F7FF", "#00EFFF", "#00E8FF", "#00E0FF",        // indices 100 - 104
            "#00D8FF", "#00D1FF", "#00C9FF", "#00C1FF", "#00BAFF",        // indices 105 - 109
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
        
    // These are the images to be used for saying
    static final GreenfootImage saySrc = new GreenfootImage("say.png");
    static final GreenfootImage sayExt = new GreenfootImage("say2.png");
    static final GreenfootImage sayEnd = new GreenfootImage("say3.png");
    static final GreenfootImage sayThink = new GreenfootImage("think.png");
    
    // Instrument and Drum patch numbers
    static final int[] scratchInstruments = {0, 0, 2, 19, 24, 27, 32, 45, 42, 57, 71, 64, 
                                             73, 75, 70, 91, 11, 10, 114, 12, 82, 90};
    static final int[] scratchDrums = {0, 38, 36, 37, 49, 46, 42, 54, 39, 75,
                                       77, 56, 81, 61, 64, 69, 74, 58, 79};
    private boolean isPenDown = false;
    private Color penColor = Color.BLUE;
    private int penColorNumber = 133;         // an integer that is mod 200 -- 0 to 199.
    private float penSize = 1;
    private int currCostume = 0;
    private String name;                    // Sprite's class name, for sound lookup
    private long deferredWait; // What time the next deferred yield should take place
    
    /**
     * This class holds a Greenfoot 'baseImage' as well as several fields that dictate
     * how the image should be modified. Whenever these fields are changed, the image will
     * update itself, storing the result in 'image'. 
     */
    public class ScratchImage {
        public RotationStyle style;
        // original image from file, but centered in a field big enough to
        // allow rotation. 
        private GreenfootImage baseImage;   
        public GreenfootImage image;        // modified by rotation, scaling, etc.
        private int ghost;
        private double color;
        private double fisheye;
        private double whirl;
        private double pixelate;
        private double mosaic;
        private double brightness;
        private int rotation;
        private double size;
        private boolean flipped;
        public boolean genQuadTree = false;
        private int pixelWidth, pixelHeight;
        public Node root;
        public ScratchImage(GreenfootImage img) {
            // In order to rotate the image properly, we must make it big enough to rotate fully
            // without resizing
            style = RotationStyle.ALL_AROUND;
            ghost = 0;
            pixelate = 0;
            rotation = 0;
            size = 100;
            flipped = false;
            BufferedImage bi = img.getAwtImage();
            int minx = 0, miny = 0;
            int maxx = bi.getWidth();
            int maxy = bi.getHeight();
            root = new Node();
            // First we have to crop and center the image
            for (int x = 0; x < bi.getWidth(); x++) {
                for (int y = 0; y < bi.getHeight(); y++) {
                    if ((bi.getRGB(x, y) >> 24) != 0x00) {
                        // Find the smallest rectangle that contains the entire image
                        if (x < minx) minx = x;
                        if (x > maxx) maxx = x;
                        if (y < miny) miny = y;
                        if (y > maxy) maxy = y;
                    }
                }
            }
            // Store the extents of the image.
            pixelWidth = maxx - minx;
            pixelHeight = maxy - miny;
            // Slide the image to the upper left hand corner, then make the image big enough to
            // fully rotate the object without cutting off any corners.
            AffineTransformOp ato = new AffineTransformOp(AffineTransform.getTranslateInstance(-minx, -miny),
                              AffineTransformOp.TYPE_BILINEAR);
            // + 2 at end to deal with rounding issues.
            int newDim = (int)Math.sqrt(Math.pow(bi.getWidth(), 2) + Math.pow(bi.getHeight(), 2)) + 2;
            baseImage = new GreenfootImage(newDim, newDim);
            // Move image pixels from bi to baseImage to the upper-left corner.
            ato.filter(bi, baseImage.getAwtImage());
            // Now slide the image from the upper left corner to the center
            AffineTransformOp ato2 = new AffineTransformOp(AffineTransform.getTranslateInstance(((newDim - img.getWidth()) / 4),
                ((newDim - img.getHeight()) / 4)), AffineTransformOp.TYPE_BILINEAR);
            bi = baseImage.getAwtImage();
            baseImage = new GreenfootImage(newDim, newDim);
            // Use setData because you can't use a filter and have both
            // sides be the same thing.  So, take result of ato2.filter()
            // and store in baseImage.
            baseImage.getAwtImage().setData(ato2.filter(bi.getData(), null));
            updateImage();
        }
        public ScratchImage(GreenfootImage img, RotationStyle rs) {
            this(img);
            style = rs;
        }
        // TODO: make a way to set all fields at once, then call updateImage() to avoid 
        // uneccessary recalculations
        public void setRotation(int val) {
            if (rotation == val) {
                return;
            }
            rotation = val;
            updateImage();
        }
        public void setGhost(int val) {
            if (val > 100) {
                ghost = 100;
            } else if (val < 0) {
                ghost = 0;
            } else if (ghost == val) {
                return;
            } else {
                ghost = val;
            }
            updateImage();
        }
        public void setPixelate(double val) {
            pixelate = val;
            updateImage();
        }
        public void setWhirl(double val) {
            whirl = val;
            updateImage();
        }
        public void setFisheye(double val) {
            fisheye = val;
            updateImage();
        }
        public void setMosaic(double val) {
            mosaic = val;
            updateImage();
        }
        public void setColor(double val) {
            color = val;
            updateImage();
        }
        public void setBrightness(double val) {
            brightness = val;
            updateImage();
        }
        public void setSize(Number percent) {
            size = percent.doubleValue();
            updateImage();
        }
        public void setAll(int rot, int ghost, double pix, double whirl, double fish, double mos, double color, double bright, double size) {
            rotation = rot;
            this.ghost = ghost;
            pixelate = pix;
            this.whirl = whirl;
            fisheye = fish;
            mosaic = mos;
            this.color = color;
            brightness = bright;
            this.size = size;
            updateImage();
        }
        private void updateImage() {
            // Apply all graphic effects and rotation
            // The order of these may affect the resulting image
            GreenfootImage trans = new GreenfootImage(baseImage);
            trans = updateRotation(trans);
            trans = updateSize(trans);
            trans = updateGhost(trans);
            trans = updateWhirl(trans);
            trans = updateFisheye(trans);
            trans = updatePixelate(trans);
            trans = updateMosaic(trans);
            trans = updateHSV(trans);
            image = trans;
            
            root = null;
        }
        private GreenfootImage updateGhost(GreenfootImage trans) {
            trans.setTransparency((int)((-1 * ghost + 100) * 2.55));
            return trans;
        }
        // The algorithms for these image filters were obtained from 
        // https://github.com/LLK/scratch-flash/tree/develop/src/filters
        private GreenfootImage updatePixelate(GreenfootImage trans) {
            double size = Math.abs(pixelate / 10d) + 1;
            if (size == 1) {
                return trans;
            }
            BufferedImage img = trans.getAwtImage();
            // Get the raster data (array of pixels)
            Raster src = img.getData();
            
            // Create an identically-sized output raster
            WritableRaster dest = src.createCompatibleWritableRaster();
            // Loop through all pixels in the output
            IntStream.range(0, src.getHeight()).parallel().forEach(y->{
                for (int x = 0; x < src.getWidth(); x++) {
                    double dx = Math.floor(x / size) * size;
                    double dy = Math.floor(y / size) * size;
                    if (dy < src.getHeight() && dx < src.getWidth()) {
                        dest.setPixel(x, y, src.getPixel((int)Math.round(dx), (int)Math.round(dy), new double[4]));
                    }
                }
            });
            img.setData(dest);
            return trans;
        }
        private GreenfootImage updateWhirl(GreenfootImage trans) {
            if (whirl == 0) {
                return trans;
            }
            
            BufferedImage img = trans.getAwtImage();
            // Get the raster data (array of pixels)
            Raster src = img.getData();
            
            // Create an identically-sized output raster
            WritableRaster dest = src.createCompatibleWritableRaster();
            // Get center coords, whirl radius, and scale factors
            double cx = src.getWidth() / 2;
            double cy = src.getHeight() / 2;
            double radius = Math.min(src.getWidth(), src.getHeight()) / 2;
            double sx = (src.getWidth() > src.getHeight()) ? (src.getHeight() / src.getWidth()) : 1;
            double sy = (src.getWidth() > src.getHeight()) ? 1 : (src.getWidth() / src.getHeight());
            // Loop through all pixels in the output
            IntStream.range(0, src.getHeight()).parallel().forEach(y->{
                for (int x = 0; x < src.getWidth(); x++) {
                    double dx = sx * (x - cx);
                    double dy = sy * (y - cy);
                    double length = Math.sqrt((dx * dx) + (dy * dy));
                    double factor = 1.0d - (length / radius);
                    double a = (Math.PI * whirl / 180) * factor * factor;
                    double sin = Math.sin(a);
                    double cos = Math.cos(a);
                    double px = (((cos * dx) + (-sin * dy)) / sx) + cx;
                    double py = (((sin * dx) + (cos * dy)) / sy) + cy;
                    if (length > radius) {
                        dest.setPixel(x, y, src.getPixel(x, y, new double[4]));
                    } else if (py > 0 && py < src.getHeight() - 1 && px > 0 && px < src.getWidth() - 1) {
                        dest.setPixel(x, y, src.getPixel((int)Math.round(px), (int)Math.round(py), new double[4]));
                    }
                }
            });
            img.setData(dest);
            return trans;
        }
        private GreenfootImage updateFisheye(GreenfootImage trans) {
            double power = (fisheye + 100) / 100;
            if (power <= 0 || fisheye == 0) {
                return trans;
            }
            
            BufferedImage img = trans.getAwtImage();
            // Get the raster data (array of pixels)
            Raster src = img.getData();
            
            // Create an identically-sized output raster
            WritableRaster dest = src.createCompatibleWritableRaster();
            // Get center coords, whirl radius, and scale factors
            double cx = src.getWidth() / 2;
            double cy = src.getHeight() / 2;
            // Loop through all pixels in the output
            IntStream.range(0, src.getHeight()).parallel().forEach(y->{
                for (int x = 0; x < src.getWidth(); x++) {
                    double dx = (x - cx) / cx;
                    double dy = (y - cy) / cy;
                    double length = Math.sqrt((dx * dx) + (dy * dy));
                    double r = Math.pow(length, power);
                    double angle = Math.atan2(dx, -dy) - Math.PI / 2;
                    double px = cx + (r * Math.cos(angle) * cx);
                    double py = cy + (r * Math.sin(angle) * cy);
                    if (r > 1.0d) {
                        px = x;
                        py = y;
                    } else if (py > 0 && py < src.getHeight() - 1 && px > 0 && px < src.getWidth() - 1) {
                        dest.setPixel(x, y, src.getPixel((int)Math.round(px), (int)Math.round(py), new double[4]));
                    }
                }
            });
            img.setData(dest);
            return trans;
        }
        private GreenfootImage updateMosaic(GreenfootImage trans) {
            if (mosaic <= 1) {
                return trans;
            }
            
            BufferedImage img = trans.getAwtImage();
            // Get the raster data (array of pixels)
            Raster src = img.getData();
            
            // Create an identically-sized output raster
            WritableRaster dest = src.createCompatibleWritableRaster();
            // Loop through all pixels in the output
            IntStream.range(0, src.getHeight()).parallel().forEach(y->{
                for (int x = 0; x < src.getWidth(); x++) {
                    double px = (x * Math.round((mosaic + 10) / 10)) % src.getWidth();
                    double py = (y * Math.round((mosaic + 10) / 10)) % src.getHeight();
                    if (py > 0 && py < src.getHeight() - 1 && px > 0 && px < src.getWidth() - 1) {
                        dest.setPixel(x, y, src.getPixel((int)Math.round(px), (int)Math.round(py), new double[4]));
                    }
                }
            });
            img.setData(dest);
            return trans;
        }
        private GreenfootImage updateHSV(GreenfootImage trans) {
            if (color == 0 && brightness == 0) {
                return trans;
            }
            
            BufferedImage img = trans.getAwtImage();
            // Get the raster data (array of pixels)
            Raster src = img.getData();
            
            // Create an identically-sized output raster
            WritableRaster dest = src.createCompatibleWritableRaster();
            // Loop through all pixels in the output
            double colorShift = (color / 200) % 360;
            IntStream.range(0, src.getHeight()).parallel().forEach(y->{
                for (int x = 0; x < src.getWidth(); x++) {
                    // Get the previous color at this pixel
                    Color old = new Color(img.getRGB(x, y));
                    // Convert it to HSB color model
                    float[] hsb = Color.RGBtoHSB(old.getRed(), old.getGreen(), old.getBlue(), null);
                    // Adjust color mod 360
                    hsb[0] = (hsb[0] + (float)colorShift) % 360;
                    // Adjust brightness, keeping it within the bounds of 0 and 1
                    hsb[2] = Math.max(Math.min(hsb[2] + (float)brightness / 100, 1f), 0);
                    // Turn the new color back into rgb
                    Color rgb = new Color(Color.HSBtoRGB(hsb[0], hsb[1], hsb[2]));
                    // Add in the alpha component from the old image
                    int[] rgba = {rgb.getRed(), rgb.getGreen(), rgb.getBlue(), src.getPixel(x, y, new int[4])[3]};
                    // Set the pixel
                    dest.setPixel(x, y, rgba);
                }
            });
            img.setData(dest);
            return trans;
        }
        private GreenfootImage updateRotation(GreenfootImage trans) {
            if (style == RotationStyle.ALL_AROUND) {
                int w = baseImage.getWidth(), h = baseImage.getHeight();
                double rads = Math.toRadians(rotation);
                GreenfootImage rot = new GreenfootImage(w, h);
                AffineTransform at = new AffineTransform();
                at.rotate(rads, w / 2, h / 2);
                AffineTransformOp ato = new AffineTransformOp(at, AffineTransformOp.TYPE_BILINEAR);
                ato.filter(trans.getAwtImage(), rot.getAwtImage());
                return rot;
            } else if (style == RotationStyle.LEFT_RIGHT && rotation > 90 && rotation < 270) {
                trans.mirrorHorizontally();
                return trans;
            } else {
                return trans;
            }
        }
        private GreenfootImage updateSize(GreenfootImage trans) {
            double perc = size / 100.0d;
            // Now scale it, store it and display it.
            trans.scale((int) (trans.getWidth() * perc), (int) (trans.getHeight() * perc));
            return trans;
        }
        /**
         * Returns the image with all modifications applied to it. Note that this image will
         * be re-created from baseImage every time a field is updated, so modifying this image is
         * not necessarily useful.
         */
        public GreenfootImage getDisplay() {
            return image;
        }
        /**
         * Returns a copy of baseImage. This image will be as it was when the ScratchImage 
         * was constructed, and should never change.
         */
        public GreenfootImage getBase() {
            return new GreenfootImage(baseImage);
        }
        /**
         * Returns the distance from the leftmost pixel to the rightmost 
         * (Of base image. TODO account for effects such as rotation)
         */
        public int pixelWidth() {
            return pixelWidth;
        }
        /**
         * Returns the distance from the highest pixel to the lowest
         * (Of base image. TODO account for effects such as rotation)
         */
        public int pixelHeight() {
            return pixelHeight;
        }
        public void generateQuadTree() {
            GreenfootImage trans = getDisplay();
            root = new Node();
            root.w = trans.getWidth();
            root.h = trans.getHeight();
            // An array of the alpha values. Getting it is relatively expensive, so we do it outside of the recursion
            
            int[] data = ((java.awt.image.DataBufferInt) trans.getAwtImage().getAlphaRaster().getDataBuffer()).getData();
            buildQuadTree(root, data, trans.getWidth(), trans.getHeight());
        }
        private void buildQuadTree(Node parent, int[] data, int w, int h) {
            boolean trans = false, opaque = false;
            // if either w or h is out of bounds, move it back in bounds
            if (parent.x + parent.w > w) {
                parent.w--;
            }
            if (parent.y + parent.h > h) {
                parent.h--;
            }
            //int[] quadrant = bim.getRGB(parent.x, parent.y, parent.w, parent.h, null, 0, parent.w);
            for (int x = parent.x; x < parent.x + parent.w; x++) {
                for (int y = parent.y; y < parent.y + parent.h; y++) {
                    //double[] pixel = r.getPixel(x, y, (double[])null);
                    if (data[y * h + x] >= 0) {
                        // If the sector contains a transparent pixel, record it
                        trans = true;
                    } else {
                        // If the sector has any opaque pixels, record it
                        opaque = true;
                    }
                    // If we've already found one of each, exit the loop
                    if (trans && opaque) {
                        break;
                    }
                }
                // If we've already found one of each, exit the loop
                if (trans && opaque) {
                    break;
                }
            }
            // Now check whether it's all opaque, all transparent, or both
            parent.fill = 0; // A value of 0 means it's partial
            if (trans) {
                parent.fill--; // A value of -1 means it's fully transparent
            }
            if (opaque) {
                parent.fill++; // A value of 1 means it's fully opaque
            }
            // Recursively build the rest of the tree
            if (parent.fill == 0 && parent.w > 1 && parent.h > 1) {
                parent.nw = new Node(parent, 0);
                buildQuadTree(parent.nw, data, w, h);
                parent.ne = new Node(parent, 1);
                buildQuadTree(parent.ne, data, w, h);
                parent.sw = new Node(parent, 2);
                buildQuadTree(parent.sw, data, w, h);
                parent.se = new Node(parent, 3);
                buildQuadTree(parent.se, data, w, h);
            }
            
        }
        /**
         * Draws a visual representation of the quad tree of a given sprite
         * This has little practical use, but it is neat!
         */
        public void drawQuadTree(Node parent) {
            if (parent.nw == null || parent.ne == null || parent.sw == null || parent.se == null) {
                BufferedImage bim = getDisplay().getAwtImage();
                int[] quadrant = bim.getRGB(parent.x, parent.y, parent.w, parent.h, null, 0, parent.w);
                java.util.Arrays.fill(quadrant, 0xFF0000FF);
                bim.setRGB(parent.x, parent.y, parent.w, parent.h, quadrant, 0, parent.w);
                if (parent.fill == 0) 
                    java.util.Arrays.fill(quadrant, 0xFF00FF00);
                if (parent.fill == 1) 
                    java.util.Arrays.fill(quadrant, 0xFFFF0000);
                if (parent.fill == -1) 
                    java.util.Arrays.fill(quadrant, 0x00000000);
                
                bim.setRGB(parent.x + 1, parent.y + 1, parent.w - 1, parent.h - 1, quadrant, 0, parent.w);
            }
            if (parent.nw != null)
                drawQuadTree(parent.nw);
            if (parent.ne != null)
                drawQuadTree(parent.ne);
            if (parent.sw != null)
                drawQuadTree(parent.sw);
            if (parent.se != null)
                drawQuadTree(parent.se);
        }
        private class Node {
            Node nw, ne, sw, se;
            byte fill;
            int x, y, w, h;
            public Node() {
                x = 0;
                y = 0;
                fill = 0;
            }
            public Node(Node parent, int dir) {
                w = (parent.w / 2);
                h = (parent.h / 2);
                // If w or h are odd, round up. This is more time efficeint
                // than Math.ceil().
                if (parent.w % 2 == 1)
                    w++;
                if (parent.h % 2 == 1)
                    h++;
                switch(dir) { // Northwest Corner
                    case 0:
                        x = parent.x;
                        y = parent.y;
                        break;
                    case 1: // Northeast Corner
                        x = parent.x + w;
                        y = parent.y;
                        break;
                    case 2: // Southwest Corner
                        x = parent.x;
                        y = parent.y + h;
                        break;
                    case 3: // Southeast Corner
                        x = parent.x + w;
                        y = parent.y + h;
                        break;
                }
            }
        }
    }
        
    /*
     * this class is just a pairing of costume image with its name.
     */
    private class Costume {
        ScratchImage image;
        String name;

        public Costume(GreenfootImage img, String name) {
            image = new ScratchImage(img);
            this.name = name;
        }
    }
    /**
     * This is an empty interface that serves to mark certain subclasses of scratch that should
     * not be accessible by basic scratch functions such as isTouching.
     * 
     * Classes that implement this will still be displayed, and may be changed through a direct
     * reference, but will not be returned by getIntersectingActors
     */
    public interface nonInteractive {
    }
    
    private ArrayList<Costume> costumes = new ArrayList<Costume>();

    // costumesCopy holds the original unaltered costume images.  So, if
    // the code alters the costume by, e.g., scaling it, the copy stays
    // unchanged.
 

    private boolean isShowing = true;  // do we show the image or not?
    private int ghostEffect;           // image transparency.
    private double pixelateEffect;     // image pixelation.
    private double whirlEffect;        // amount of whirl
    private double fisheyeEffect;      // amount of fisheye
    private double mosaicEffect;       // amount of clones
    private double colorEffect;        // Change to hue
    private double brightnessEffect;   // Change to brightness
    private boolean updateImage = true;// If this is set to true, the image will be 
                                       // recalculated at the end of the frame.

    // The layer this object (actually all objects of this class) is painted in.
    // Layer 0 is on top.  ScratchWorld object keeps a list of the overall paint
    // order.
    private int currentLayer;

    // Note that the scale of a sprite in Scratch is a property of the sprite,
    // not a property of the image.  In Greenfoot it is just a property of
    // the image, so if you scale one image and then change to another image
    // the scaling is not applied.  So, here we have to store the current
    // scaling factor to be applied to all costumes/images.
    private double costumeSize = 100;   // percentage of original size

    // The direction the sprite is set to move in.  Due to the 
    // rotationStyle that is set, the image may not be pointing in that
    // direction.  This value is in Scratch orientation (which is GF 
    // orientation + 90).
    private int currDirection = 90; 

    private int lastMouseX;
    private int lastMouseY;

    // Track the actor's subpixel location
    // this makes angled movement more robust when moving small distances

    private double subX;
    private double subY;

    // Remember if this object is a clone or not.  It is not, by default.
    private boolean isClone = false;

    // Note if the code being run is in a callback script -- i.e., being
    // run in a Sequence. This needs to be noted so that if stopThisScript() is 
    // called it can check if the code is in the script.
    private boolean inCbScript = false;

    // Actor that is showing what is being said OR thought by this sprite.
    private Sayer sayActor = null;

    // If this object is a clone, the parent is set to the object that was cloned.
    // This is needed because we need to get the values of the parent's local
    // variables and set them in the variables in the clone.
    private Scratch parent = null;

    // A mapping of variable name to the Variable itself.  This is needed only
    // when a clone is made and the clone has local variables.  During initialization
    // the code has to get the values of the parent's local variables to initialize
    // the new copies.
    private HashMap<String, Variable> variables = new HashMap<String, Variable>();

    // Declare the SoundPlayer, since it is static, it won't be redeclared when
    // the scenario is reset. The SoundPlayer can play Clips and Midi notes.
    private static SoundPlayer soundPlayer = new SoundPlayer();
    
    

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

    /**
     * A Sequence is an executable thread of code that will be run.  
     * It can be paused via a wait() call, like in Scratch, etc.
     */
    protected class Sequence extends Thread
    {
        private Object sequenceLock;
        private boolean doneSequence;
        private boolean terminated;
        // triggered is true indicates if this sequence is running.  It is false when the condition to 
        // run the sequence has not been met yet.  E.g., a key press
        // sequence will have triggered false when the key has not by hit by the user yet.
        protected boolean triggered; 
        // isReady tracks whether the sequence has been told to begin or not
        // since it must wake up to check if greenfoot has been reset, this
        // will tell the thread if it has timed out or been notified
        protected boolean isReady;
        
        private Object objToCall;
        private String methodToCall;

        /**
         * Constructor for objects of class Sequence
         */
        public Sequence(Object obj, String method)
        {
            // Give this thread the name "ScratchSequence" and add it to the thread group
            super(ScratchWorld.threadGroup, "ScratchSequence"); 
            this.sequenceLock = this;
            doneSequence = true;
            terminated = false;
            triggered = true;      // override this for non-automatically triggered sequences.
            this.objToCall = obj;
            this.methodToCall = method;
            isReady = false;
            // System.out.println("Sequence ctor: obj " + obj + " method " + method);
        }

        //        public String toString() {
        //            return "Sequence (": obj " + objToCall + " method " + methodToCall + " doneSeq " + doneSequence;
        //         }

        // These are needed only for copy constructors.
        public Object getObj() { return objToCall; }

        public String getMethod() { return methodToCall; }

        public boolean isTerminated() { return terminated; }

        public void run()
        {
            try {
                synchronized (sequenceLock) {

                    while (doneSequence) {
                        //System.out.println(methodToCall + ": run(): Calling seqLock.wait");
                        while (!isReady) {
                            sequenceLock.wait(100);
                            if (interrupted()) {
                                terminated = true;
                                return;
                            }
                            //System.out.println("thread running: " + this.getName());
                            //System.out.println("Comparing: " + id + " against: " + ScratchWorld.id);
                        }
                        //System.out.println(methodToCall + ": run(): done with seqLock.wait, donesequence: " + doneSequence);
                    }

                    java.lang.reflect.Method m = objToCall.getClass().getMethod(methodToCall, 
                            Class.forName("Scratch$Sequence"));
                    System.out.println(methodToCall + ": run(): invoking callback");
                    inCbScript = true;
                    m.invoke(objToCall, this);

                    // System.out.println(methodToCall + ": run(): done invoking callback");

                }
            } catch (InvocationTargetException i) {
                if (i.getCause() instanceof StopScriptException) {
                } else {
                    // We had a problem with invoke(), but it wasn't the StopScript exception, so
                    // just print out the info.
                    i.printStackTrace();
                }
            } catch (InterruptedException ie) {
                terminated = true;
                return;
            } catch (Throwable t) {
                t.printStackTrace();
            }
            System.out.println(methodToCall + ": run(): done");
            inCbScript = false;

            terminated = true;
            doneSequence = true;
        }

        /**
         * Call this to relinquish control and wait for the next sequence.
         */
        public void waitForNextSequence() throws InterruptedException
        {
            doneSequence = true;
            isReady = true;
            sequenceLock.notify();

            while (doneSequence) {
                // System.out.println(methodToCall + ": waitForNextSequence(): calling seqLock.wait()");
                try {
                    sequenceLock.wait();
                } catch (InterruptedException e) {
                    // If the wait is interrupted, the script should stop
                    throw new StopScriptException();
                }
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
                    isReady = true;
                    sequenceLock.notify();  // Thread now continues

                    while (! doneSequence) {
                        // System.out.println(methodToCall + ": perfSeq: calling wait() " + doneSequence);
                        sequenceLock.wait(); // Wait for thread to notify us it's done
                        // System.out.println(methodToCall + ": perfSeq: done with wait()");
                    }
                }
            }
            catch (InterruptedException ie) {
                System.out.println("PerfSeq exiting");
                return;
            }
            // System.out.println(methodToCall + ": perfSeq: done");
        }
    }
    // Keep a list of all the "plain" sequences.
    private ArrayList<Sequence> sequences = new ArrayList<Sequence>();

    /* -------- End of Sequence definition --------- */

    private class KeyPressSeq extends Sequence {
        private String key;
        public boolean retrigger;
        public int waitframes;
        public KeyPressSeq(String key, Object obj, String method)
        {
            super(obj, method);
            this.key = key;
            // A key press sequence is not triggered until the key is hit.
            triggered = false;
            retrigger = true;
            waitframes = 0;
        }

        public KeyPressSeq(KeyPressSeq other) {
            this(other.key, other.getObj(), other.getMethod());
            retrigger = other.retrigger;
            waitframes = other.waitframes;
        }

        // Called from act().
        public boolean isTriggered() {
            if (Greenfoot.isKeyDown(this.key)) {
                if (! triggered) {
                    System.out.println("keySeq: for key " + this.key +
                        " changing from NOT triggered to triggered.");
                }
                triggered = true;
            } else {
                retrigger = true;
                triggered = false;
                waitframes = -1;
            }
            return triggered;
        }
    }
    private ArrayList<KeyPressSeq> keySeqs = new ArrayList<KeyPressSeq>();

    abstract private class ActorOrStageClickedSeq extends Sequence {

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
                    System.out.println("ActorClickedSeq: for actor " + this.getObj() +
                        " changing from NOT triggered to triggered.");
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

    public class MesgRecvdSeq extends Sequence {
        private String mesg;

        public String getMesg() { return mesg; }

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
            if (getWorld().bcastPending(mesg)) {
                if (! triggered) {
                    System.out.println("mesgRecvdSeq: for mesg " + mesg +
                        " changing from NOT triggered to triggered.");
                }
                triggered = true;
            }
            return triggered;
        }
    }
    private ArrayList<MesgRecvdSeq> mesgRecvdSeqs = new ArrayList<MesgRecvdSeq>();
    public ArrayList<MesgRecvdSeq> getMesgRecvdSeqs() { return mesgRecvdSeqs; }

    private class CloneStartSeq extends Sequence {
        public CloneStartSeq(Object obj, String method) 
        {
            super(obj, method);
            this.triggered = false;
            /* System.out.println("CloneStartSeq (" + System.identityHashCode(this) +
            "): for sprite " + this.getObj() +
            " created.");
            try {
            new Exception().printStackTrace();
            } catch (Exception e) {
            }
             */
        }

        public CloneStartSeq(CloneStartSeq other) {
            this(other.getObj(), other.getMethod());
            // System.out.println("After CloneSSeq copy constructor: triggered is " + triggered);
        }

        // called from act()
        public boolean isTriggered() {
            /*System.out.println("CloneStartSeq (" + System.identityHashCode(this) +
            "): for sprite " + this.getObj() +
            " calling clonePending.");
             */
            // If the world is null, this object has been deleted
            if (getWorld() == null) {
                throw new StopScriptException();
            }
            if (getWorld().clonePending(getObj())) {
                /* if (! triggered) {
                    System.out.println("CloneStartSeq (" + System.identityHashCode(this) +
                        "): for sprite " + this.getObj() +
                        " changing from NOT triggered to triggered.");
                } */
                triggered = true;
            }
            return triggered;
        }
    }
    private ArrayList<CloneStartSeq> cloneStartSeqs = new ArrayList<CloneStartSeq>();
    
    private class SwitchToBackdropSeq extends Sequence {
        int index;
        String name;
        public SwitchToBackdropSeq(Number index, Object obj, String method)
        {
            super(obj, method);
            this.triggered = false;
            this.index = index.intValue();
            this.name = null;
        }
        
        public SwitchToBackdropSeq(String name, Object obj, String method)
        {
            super(obj, method);
            this.triggered = false;
            this.name = name;
        }
        
        public SwitchToBackdropSeq(SwitchToBackdropSeq other)
        {
            this(other.index, other.getObj(), other.getMethod());
            this.name = other.name;
        }
        
        public boolean isTriggered() {
            if (name == null) {
                if (getWorld().switchedToBackdrop(index)) {
                    triggered =  true;
                }
            } else if (getWorld().switchedToBackdrop(name)) {
                triggered = true;
            }
            return triggered;
        }
    }
    private ArrayList<SwitchToBackdropSeq> switchToBackdropSeqs = new ArrayList<SwitchToBackdropSeq>();

    /* -------------------  Variables ------------------------ */

    private class Variable extends Scratch implements nonInteractive
    {
        private final greenfoot.Color textColor = greenfoot.Color.BLACK;
        private final greenfoot.Color bgColor = greenfoot.Color.GRAY;
        private final java.awt.Font awtfont = new java.awt.Font("Arial", java.awt.Font.PLAIN, 12);
        private final greenfoot.Font font = new greenfoot.Font("Arial", false, false, 12);
        
        private Object value;
        private ScratchList container = null;     // Store the list that contains this variable. If null
                                                  // The variable is standalone and should display normally
                                                  // otherwise it should determine its location and visibility
                                                  // from the containing List
        private String text;
        private boolean valChanged = true;
        private boolean display = true;           // is the variable supposed to be displayed or hidden?
        private boolean addedToWorld = false;     // has this object been added to the world yet?
        private int xLoc, yLoc;                   // current location of the image: the upper-lefthand
                                                  // corner.

        public Variable(ScratchWorld w, String varName, Object val)
        {
            text = varName;
            value = val;
            valChanged = true;

            // Get the initial upperleft-hand corner coordinates for this variable.
            xLoc = w.getDisplayVarXLoc();
            yLoc = w.getDisplayVarYLoc();
        }
        // This constructor is to be used when creating lists.
        public Variable(ScratchList container, int index, Object val)
        {
            text = String.valueOf(index);
            value = val;
            valChanged = true;
            display = true;
            this.container = container;
            
            xLoc = 0;
            yLoc = 0;
            
            updateImage();
        }
        
        /**
         * Sets this variables display text
         */
        public void setText(String s)
        {
            text = s;
            valChanged = true;
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
                    // getX() and getY() get the actual current location -- in Scratch coords.
                    // System.out.println("AddedToWorld is TRUE: var, getX, getY = " + text + " " + translateToGreenfootX(getX()) + " " + translateToGreenfootY(getY()));
                    xLoc = translateToGreenfootX(getX()) - getImage().getWidth() / 2;
                    yLoc = translateToGreenfootY(getY()) - getImage().getHeight() / 2;
                    // System.out.println("AddedToWorld is TRUE: xLoc, yLoc = " + xLoc + " " + yLoc);
                } else {
                    // System.out.println("addedToWorld is FALSE: var, xLoc, yLoc = " + text + " " + xLoc + " " + yLoc);
                }
                Object v;
                if (value instanceof Double) {
                    v = new java.text.DecimalFormat("#.######").format((Double)value);
                } else {
                    v = value;
                }
                java.awt.FontMetrics fm = new BufferedImage(1, 1, BufferedImage.TYPE_INT_ARGB).getGraphics().getFontMetrics(awtfont);
                
                String dispStr = text + v;
                int stringLength = fm.stringWidth(dispStr);
                int textLength = fm.stringWidth(text);
                int valLength = fm.stringWidth(v.toString());
                // Create a gray background under the variable's name.
                GreenfootImage image = new GreenfootImage(stringLength + 8, 20);
                if (this instanceof CloudVar) {
                    image.setColor(toGFColor(Color.decode("#66FFFF")));
                } else  if (container != null) { // If part of list match background colors
                    image.setColor(greenfoot.Color.LIGHT_GRAY);
                } else {
                    image.setColor(bgColor);
                }
                image.setFont(font);
                image.fill();
                // Create orange background under the variable's value.
                image.setColor(toGFColor(Color.decode("#EE7D16")));
                image.fillRect(textLength + 4, 3, valLength + 2, 15);

                image.setColor(textColor);
                // System.out.println("Variable.updateImage: creating with value " + text + " " + value);
                image.drawString(text + " " + v, 1, 15);
                setImage(image);

                // Because the size of the image may have changed (to accommodate a longer
                // or shorter string to display), and because we want all images tiled nicely
                // along the left side of the screen, and because Greenfoot places images based
                // on the center of the image, we have to calculate a new location for
                // each image, each time.
                setLocation(xLoc + getImage().getWidth() / 2, yLoc + getImage().getHeight() / 2);
                // System.out.println("setLocation done: set to x, y = " + (xLoc + getImage().getWidth() / 2) +
                //     " " + (yLoc + getImage().getHeight() / 2));
                // System.out.println("    image width, height is " + getImage().getWidth() + " " + getImage().getHeight());
                valChanged = false;
                if (container == null) {// If the variable is part of a list it will never be added to world
                    addedToWorld = true;
                }
            }
        }

        /**
         * mark that this variable's value should be displayed on the Scratch screen.
         */
        public void show()
        {
            display = true;
            valChanged = true;      // make sure we display the value in next act() iteration.
            act();
        }

        /**
         * mark that this variable's value should not be displayed on the Scratch screen.
         */
        public void hide()
        {
            display = false;
            valChanged = true;  // make sure we don't display the value in next act() iteration.
            act();
        }
    }

    public class IntVar extends Variable {

        public IntVar(ScratchWorld w, String name, int initVal) {
            super(w, name, (Object) initVal);
        }
        public IntVar(ScratchList container, int index, Object val) {
            super(container, index, val);
        }

        public Integer get() { return (Integer) super.get(); }
        public void set(Number newVal) { super.set(newVal.intValue()); }
    }
    public class StringVar extends Variable {

        public StringVar(ScratchWorld w, String name, String initVal) {
            super(w, name, (Object) initVal);
        }
        public StringVar(ScratchList container, int index, Object val) {
            super(container, index, val.toString());
        }

        public String get() { return (String) super.get(); }
        public void set(Object newVal) { super.set(newVal.toString()); }
    }
    public class DoubleVar extends Variable {

        public DoubleVar(ScratchWorld w, String name, double initVal) {
            super(w, name, (Object) initVal);
        }
        public DoubleVar(ScratchList container, int index, Object val) {
            super(container, index, (Double) val);
        }

        public Double get() { return (Double) super.get(); }
        public void set(Number newVal) { super.set(newVal.doubleValue()); }
    }
    public class BooleanVar extends Variable {

        public BooleanVar(ScratchWorld w, String name, boolean initVal) {
            super(w, name, (Object) initVal);
        }
        public BooleanVar(ScratchList container, int index, Object val) {
            super(container, index, (Boolean) val);
        }

        public Boolean get() { return (Boolean) super.get(); }
        public void set(Object newVal) { super.set((Boolean) newVal); }
    }
    public class CloudVar extends Variable {
        int id;
        public CloudVar(ScratchWorld w, String name, int id) {
            super(w, name, (Object)new Integer(0));
            if (UserInfo.isStorageAvailable()) {
                super.set(UserInfo.getMyInfo().getInt(id));
            }
            this.id = id;
        }
        
        public Integer get() { return ((Integer)super.get()).intValue(); }
        public void set(Number val) { 
            super.set(val);
            if (UserInfo.isStorageAvailable()) {
                UserInfo.getMyInfo().setInt(id, val.intValue());
                UserInfo.getMyInfo().store();
            }
        }
    }

    /**
     * Create an integer variable whose value will be displayed on the screen.
     * If this variable "belongs" to a clone, then hide it and update its value
     * to the value from its parent.  This is how Scratch operates.
     */
    public IntVar createIntVariable(ScratchWorld w, String varName, int initVal)
    {
        IntVar newVar = new IntVar(w, varName, initVal);
        w.addObject(newVar, newVar.getXLoc(), newVar.getYLoc());
        // Call act() so that it calls updateImage() which creates/computes
        // the image that displays the variable, and places in the correct location.
        newVar.act();
        variables.put(varName, newVar);
        if (this.isClone) {
            newVar.set(((Scratch.IntVar) parent.getVariable(varName)).get());
            newVar.hide();
        }
        return newVar;
    }

    /**
     * Create a String variable whose value will be displayed on the screen.
     */
    public StringVar createStringVariable(ScratchWorld w, String varName, String val)
    {
        StringVar newVar = new StringVar(w, varName, val);
        w.addObject(newVar, newVar.getXLoc(), newVar.getYLoc());
        // Call act() so that it calls updateImage() which creates/computes
        // the image that displays the variable, and places in the correct location.
        newVar.act();
        variables.put(varName, newVar);
        if (this.isClone) {
            newVar.set(((Scratch.StringVar) parent.getVariable(varName)).get());
            newVar.hide();
        }
        return newVar; 
    }

    /**
     * Create a double variable whose value will be displayed on the screen.
     */
    public DoubleVar createDoubleVariable(ScratchWorld w, String varName, double val)
    {
        DoubleVar newVar = new DoubleVar(w, varName, val);
        w.addObject(newVar, newVar.getXLoc(), newVar.getYLoc());
        // Call act() so that it calls updateImage() which creates/computes
        // the image that displays the variable, and places in the correct location.
        newVar.act();
        variables.put(varName, newVar);
        if (this.isClone) {
            newVar.set(((Scratch.DoubleVar) parent.getVariable(varName)).get());
            newVar.hide();
        }
        return newVar; 
    }

    /**
     * Create a boolean variable whose value will be displayed on the screen.
     */
    public BooleanVar createBooleanVariable(ScratchWorld w, String varName, boolean val)
    {
        BooleanVar newVar = new BooleanVar(w, varName, val);
        w.addObject(newVar, newVar.getXLoc(), newVar.getYLoc());
        // Call act() so that it calls updateImage() which creates/computes
        // the image that displays the variable, and places in the correct location.
        newVar.act();
        variables.put(varName, newVar);
        if (this.isClone) {
            newVar.set(((Scratch.BooleanVar) parent.getVariable(varName)).get());
            newVar.hide();
        }
        return newVar;
    }
    
    /**
     * Create an cloud variable whose value will be displayed on the screen.
     * The id must be an int between 0 and 9. Each cloud varaible should be given
     * a different id, as the id determines which 'slot' to store the data in
     */
    public CloudVar createCloudVariable(ScratchWorld w, String varName, int id)
    {
        CloudVar newVar = new CloudVar(w, varName, id);
        w.addObject(newVar, newVar.getXLoc(), newVar.getYLoc());
        // Call act() so that it calls updateImage() which creates/computes
        // the image that displays the variable, and places in the correct location.
        newVar.act();
        variables.put(varName, newVar);
        // Cloud variables can never be local, so they will never be cloned
        return newVar;
    }
    
    public class ScratchList extends Scratch implements nonInteractive
    {
        private final greenfoot.Font font = new greenfoot.Font("Arial", false, false, 12);
        private ArrayList<Variable> contents;
        private String name;
        int xLoc, yLoc;
        private boolean display = true;
        private boolean addedToWorld = false;
        public ScratchList(String name)
        {
            this.contents = new ArrayList<Variable>();
            this.name = name;
        }
        public ScratchList(String name, Object... contents)
        {
            this(name);
            int i = 1; // Scratch lists start with index 1
            for (Object o : contents) {
                // This code is very similar to 2 other methods, but slightly different. Maybe condensable? TODO
                if (o instanceof Integer) this.contents.add(new IntVar(this, i, o));
                else if (o instanceof Double) this.contents.add(new DoubleVar(this, i, o));
                else if (o instanceof String) this.contents.add(new StringVar(this, i, o));
                else if (o instanceof Boolean) this.contents.add(new BooleanVar(this, i, o));
                else throw new RuntimeException("Tried to create list element of invalid type");
                i++;
            }
        }
        private void updateIndex() // Make sure all elements display text matches their index
        {                          // TODO this currently does nothing as the variables
            for (int i = 0; i < contents.size(); i++) {
                contents.get(i).setText(String.valueOf(i + 1));
                contents.get(i).act();
            }
        }
        public void act()
        {
            updateDisplay();
        }
        private void updateDisplay() {
            if (!display) {
                getImage().clear();
                return;
            }
            if (addedToWorld) {
                xLoc = translateToGreenfootX(getX()) - getImage().getWidth() / 2;
                yLoc = translateToGreenfootY(getY()) - getImage().getHeight() / 2;
            }
            java.awt.FontMetrics fm = new BufferedImage(1, 1, BufferedImage.TYPE_INT_ARGB).getGraphics().getFontMetrics(new java.awt.Font("Arial", java.awt.Font.PLAIN, 12));
            int width = fm.stringWidth(name);
            int height = (length() + 1) * 18 + 8;
            for (Variable v : contents) {
                int varWidth = v.getImage().getWidth();
                if (varWidth > width) {
                    width = varWidth;
                }
            }
            width += 8;
            if (width > 150) {
                width = 150;
            }
            
            GreenfootImage img = new GreenfootImage(width, height);
            img.setColor(greenfoot.Color.LIGHT_GRAY);
            img.fill();
            img.setColor(greenfoot.Color.BLACK);
            img.drawString(name, 4, 12);
            for (int i = 0; i < length(); i++) {
                img.drawImage(contents.get(i).getImage(), 4, (i + 1) * 18);
            }
            img.drawShape(new java.awt.Rectangle(0, 0, img.getWidth() - 1, img.getHeight() - 1));
            setImage(img);
            
            
            setLocation(xLoc + getImage().getWidth() / 2, yLoc + getImage().getHeight() / 2);
            addedToWorld = true;
        }
        public void add(Object o)
        {
            if (o instanceof Integer) contents.add(new IntVar(this, contents.size(), o));
            else if (o instanceof Double) contents.add(new DoubleVar(this, contents.size(), o));
            else if (o instanceof String) contents.add(new StringVar(this, contents.size(), o));
            else if (o instanceof Boolean) contents.add(new BooleanVar(this, contents.size(), o));
            else throw new RuntimeException("Tried to create list element of invalid type");
        }
        public void delete(int index)
        {
            index--;
            contents.remove(index);
            updateIndex();
        }
        public void delete(String key)
        {
            int index = 0;
            if (key.equals("last")) {
                index = length();
                delete(index);
            } else if (key.equals("all")) {
                contents.clear();
                updateIndex(); 
            }
            
        }
        public void insert(int index, Object o)
        {
            index--;
            if (o instanceof Integer) contents.add(index, new IntVar(this, index + 1, o));
            else if (o instanceof Double) contents.add(index, new DoubleVar(this, index + 1, o));
            else if (o instanceof String) contents.add(index, new StringVar(this, index + 1, o));
            else if (o instanceof Boolean) contents.add(index, new BooleanVar(this, index + 1, o));
            else throw new RuntimeException("Tried to create list element of invalid type");
            
        }
        public void insert(String key, Object o)
        {
            int index = 0;
            if (key.equals("last")) {
                index = length();
            } else if (key.equals("random")) {
                index = pickRandom(1, length());
            } else {
                System.err.println("Unknow list key: " + key);
            }
            insert(index, o);
        }
        public void replaceItem(int index, Object o)
        {
            insert(index, o);
            delete(index + 1);
        }
        public void replaceItem(String key, Object o)
        {
            int index = 0;
            if (key.equals("last")) {
                index = length();
            } else if (key.equals("random")) {
                index = pickRandom(1, length());
            } else {
                System.err.println("Unknow list key: " + key);
            }
            replaceItem(index, o);
        }
        private Object get(int index)
        {
            index--;
            return contents.get(index).get();
        }
        // Use in strExpr, will get the item as a string.
        public String itemAt(int index)
        {
            return get(index).toString();
        }
        public String itemAt(String key)
        {
            int index = 0;
            if (key.equals("last")) {
                index = length();
            } else if (key.equals("random")) {
                index = pickRandom(1, length());
            } else {
                System.err.println("Unknow list key: " + key);
            }
            return itemAt(index);
        }
        // Use in mathExpr
        public Double numberAt(int index)
        {
            if (get(index) instanceof String) { 
                return Double.valueOf(index); 
            } else { 
                return ((Number)get(index)).doubleValue();
            } 
        }
        public Double numberAt(String key)
        {
            int index = 0;
            if (key.equals("last")) {
                index = length();
            } else if (key.equals("random")) {
                index = pickRandom(1, length());
            } else {
                index = Double.valueOf(key).intValue();
            }
            return numberAt(index);
        }
        // For use by user if an int is required
        public int intAt(int index)
        {
            return numberAt(index).intValue();
        }
        public int intAt(String key)
        {
            int index = 0;
            if (key.equals("last")) {
                index = length();
            } else if (key.equals("random")) {
                index = pickRandom(1, length());
            } else {
                index = Double.valueOf(key).intValue();
            }
            return intAt(index);
        }
        public int length()
        {
            return contents.size();
        }
        public boolean contains(Object o) // TODO this needs testing
        {
            for (Variable v : contents) {
                if (v.get().equals(o)) return true;
            }
            return false;
        }
        public void show()
        {
            display = true;
            updateDisplay();
        }
        public void hide()
        {
            display = false;
            updateDisplay();
        }
    }
    
    public ScratchList createList(ScratchWorld w, String name, Object...contents)
    {
        ScratchList l = new ScratchList(name, contents);
        w.addObject(l, 0, 0); // TODO display right position
        
        l.xLoc = w.getDisplayVarXLoc();
        l.yLoc = w.getDisplayListYLoc(l.length());
        l.act();
        return l;
    }
    

    /*
     * Start of code!
     */

    public Scratch()
    {
        super();
        
        
        // put the first costume in our array of costumes.
        costumes.add(new Costume(getImage(), "Sprite1"));
        displayCostume();
        // System.out.println("item from getImage is " + System.identityHashCode(getImage()));
        // System.out.println("item in costumes array is " + System.identityHashCode(costumes.get(0)));

        // System.out.println("item in costumesCopy array is " + System.identityHashCode(costumesCopy.get(0)));
        // System.out.println("Scratch(): constructor finished for object " + System.identityHashCode(this));
        
        // Get this class's name
        name = this.getClass().getName();
        // Load sounds in this class's directory
        if (!isClone && !(this instanceof Sayer)) {
            if (!soundPlayer.isAlive()) {
                soundPlayer.start(); // Start the soundPlayer if it hasn't been started yet
            }
            loadSounds();
        }
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
        isShowing = other.isShowing;
        ghostEffect = other.ghostEffect;
        currentLayer = other.currentLayer;
        costumeSize = other.costumeSize;
        currDirection = other.currDirection;
        lastMouseX = other.lastMouseX;
        lastMouseY = other.lastMouseY;
        subX = other.subX;
        subY = other.subY;
        
        name = other.name;

        rotationStyle = other.rotationStyle;

        /* Copy the keyPress sequences.  whenKeyPressed does the work. */
        for (KeyPressSeq k: other.keySeqs) {
            whenKeyPressed(k.key, k.getMethod());
        }

        /* Copy the actorClicked sequences from the previous sprite, but for this one.
           Easiest to do this just by calling whenSpriteClicked. */
        for (ActorClickedSeq a: other.actorClickedSeqs) {
            whenSpriteClicked(a.getMethod());
        }
        
        for (StageClickedSeq s: other.stageClickedSeqs) {
            whenStageClicked(s.getMethod());
        }
        
        for (MesgRecvdSeq m: other.mesgRecvdSeqs) {
            whenRecvMessage(m.mesg, m.getMethod());
        }

        /* Copy the CloneStart sequences from the previous sprite, but for this one.
           Easiest to do this just by calling whenIStartAsAClone. */
        for (CloneStartSeq css : other.cloneStartSeqs) {
            whenIStartAsAClone(css.getMethod());
        }

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

        // Set the parent reference to the original Scratch object.
        parent = other;
        
        // Ensure all graphic effects are applied before it displays
        displayCostume();
        /*
        // System.out.println("Scratch: copy constructor finished for object " + System.identityHashCode(this));
        System.out.println("Copy constructor finished for object " + System.identityHashCode(this));
        System.out.println("cloneStartSeqs has this in it:");
        for (CloneStartSeq s: cloneStartSeqs) {
        System.out.println("    " + System.identityHashCode(s));
        }
        System.out.println("----------");
        System.out.println("OTHER'S cloneStartSeqs has this in it:");
        for (CloneStartSeq s: other.cloneStartSeqs) {
        System.out.println("    " + System.identityHashCode(s));
        }
        System.out.println("----------");
         */
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
    }

    /*
     * act - first look for keypresses and call any registered methods on them.  Then, call each 
     * method registered as an 'act' callback -- e.g., a "whenFlagClicked" callback.
     * Users must NOT override act() in this system.
     */
    public void act()
    {
        // Call all the registered "whenFlagClicked" scripts.
        
        // Remove all terminated sequences from the main sequences list.
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
            // If the keyseq is ready, that means it is currently waiting on a yield
            // statement. We should allow it to continue running even if the key has
            // been released.
            if (seq.isReady) {
                seq.performSequence();
                continue;
            }
            // Prevents the sequence from being repeated until 30 frames after the initial
            // press. Releasing the button will reset this.
            if (seq.waitframes > 0) {
                seq.waitframes--;
                seq.retrigger = false;
            } else {
                seq.retrigger = true;
            }
            // isTriggered returns true if a sequence has seen its key press done already, or
            // if the sequence is seeing its key press done right now.
            if (seq.isTriggered() && seq.retrigger) {
                // If this is the first frame of a press, wait 30 frames, 1/2 a second.
                // TODO: To match scratch, this should be based on the OS keypress repeat delay/speed.
                // TODO: To isolate from the "speed" bar, this should use millisecond timing rather than frames.
                if (seq.waitframes == -1) {
                    seq.waitframes = 30;
                }
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
            if (seq.isTriggered()) {
                seq.performSequence();
            }
        }

        /* ---------- Repeat, but for clone requests. ------------- */

        for (ListIterator<CloneStartSeq> iter = cloneStartSeqs.listIterator(); iter.hasNext(); ) {
            CloneStartSeq seq = iter.next();
            if (seq.isTerminated()) {
                CloneStartSeq n = new CloneStartSeq(seq);
                iter.remove();   // remove old one
                iter.add(n);     // add new one that is reset to the beginning.
                n.start();
            }
        }

        /* Loop through sequences that have been invoked already. */
        for (CloneStartSeq seq : cloneStartSeqs) {
            try { 
                if (seq.isTriggered()) {
                    seq.performSequence();
                } 
            } catch (StopScriptException e) {
                // If the script belongs to an object that has been deleted, stop i
                seq.interrupt();
            }
        }
        
        for (ListIterator<SwitchToBackdropSeq> iter = switchToBackdropSeqs.listIterator(); iter.hasNext(); ) {
            SwitchToBackdropSeq seq = iter.next();
            if (seq.isTerminated()) {
                SwitchToBackdropSeq n = new SwitchToBackdropSeq(seq);
                iter.remove();   // remove old one
                iter.add(n);     // add new one that is reset to the beginning.
                n.start();
            }
        }
        
        for (SwitchToBackdropSeq seq : switchToBackdropSeqs) {
            if (seq.isTriggered()) {
                seq.performSequence();
            } 
        }
        

        if (sayActor != null) {
            sayActorUpdateLocation();
        }
        
        if (updateImage) {
            displayCostume();
            updateImage = false;
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
     * There will be a 30 second window where holding a key will be ignored
     * before repeatedly calling the method every frame.
     */
    public void whenKeyPressed(String keyName, String methodName)
    {
        KeyPressSeq k = new KeyPressSeq(keyName, this, methodName);
        keySeqs.add(k);
        k.start();
        // System.out.println("whenKeyPressed: thread added for key " + keyName);
    }
    
    /**
     * register a method to be called whenever the backdrop switches to the
     * provided one.
     */
    public void whenSwitchToBackdrop(int index, String methodName)
    {
        SwitchToBackdropSeq s = new SwitchToBackdropSeq(index, this, methodName);
        switchToBackdropSeqs.add(s);
        s.start();
    }
    
    /**
     * register a method to be called whenever the backdrop switches to the
     * provided one.
     */
    public void whenSwitchToBackdrop(String name, String methodName)
    {
        SwitchToBackdropSeq s = new SwitchToBackdropSeq(name, this, methodName);
        switchToBackdropSeqs.add(s);
        s.start();
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
     * register a method to be called when a new clone starts up.  The method
     * has no parameters.
     */
    public void whenIStartAsAClone(String methodName)
    {
        CloneStartSeq cb = new CloneStartSeq(this, methodName);
        cloneStartSeqs.add(cb);
        cb.start();
        // System.out.println("whenIStartAsAClone: method registered for class " +
        //     this.getClass().getName() + "; sequence obj created.");
    }

    /**
     * broadcast a message to all sprites.
     */
    public void broadcast(String message)
    {
        getWorld().registerBcast(message);
    }


    /**
     * broadcast a message to all sprites and wait until the scripts
     * waiting for that message complete.  Then, continue.
     */
    public void broadcastAndWait(Sequence s, String message)
    {
        /* Make a copy of all sequences from all Scratch Actors that are
         * waiting for this message. */
        ArrayList<MesgRecvdSeq> mesgScriptSeqs = getWorld().getAllMessageScripts(message);

        /* Send the broadcast */
        getWorld().registerBcast(message);

        while (true) {
            int countActive = 0;
            for (MesgRecvdSeq m: mesgScriptSeqs) {
                if (! m.isTerminated()) {
                    countActive++;
                }
            }
            if (countActive == 0) {
                break;
            }
            yield(s);
        }
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
        createCloneOf(this);
    }

    /**
     * createCloneOf: create a clone of the given Scratch actor.
     */
    public void createCloneOf(String spriteName)
    {
        createCloneOf(getWorld().getActorByName(spriteName));
    }

    /**
     * createCloneOf: create a clone of the given Scratch actor.
     */
    public void createCloneOf(Scratch actor)
    {
        // Create a new Object, which is a subclass of Scratch (the same class as "this").
        Object clone = callConstructor(actor);

        // System.out.println("createCloneOfMyself: called copy constructor to get object of type " + 
        //     clone.getClass().getName() + ". Now, calling addObject()");
        getWorld().addObject((Scratch)clone, translateToGreenfootX(actor.getX()), translateToGreenfootY(actor.getY()));

        getWorld().registerActivateClone(clone);
        // System.out.println("Clone added");        
    }

    private Object callConstructor(Scratch obj)
    {
        try {
            Constructor ctor = obj.getClass().getDeclaredConstructor(obj.getClass(), int.class, int.class);

            ctor.setAccessible(true);
            return ctor.newInstance(obj, translateToGreenfootX(obj.getX()), translateToGreenfootY(obj.getY()));
        } catch (InstantiationException x) {
            x.printStackTrace();
        } catch (InvocationTargetException x) {
            x.printStackTrace();
        } catch (IllegalAccessException x) {
            x.printStackTrace();
        } catch (java.lang.NoSuchMethodException x) {
            try {
                // This can happen if a Scratch script calls createClone() but the Sprite does
                // not have a whenIStartAsAClone script defined.  In this case, we do want to
                // create a clone, but no copy constructor exists.  So, find the copy constructor
                // in Scratch (the super class) and call that.
                Constructor ctor = obj.getClass().getSuperclass().getDeclaredConstructor(obj.getClass().getSuperclass(), int.class, int.class);

                ctor.setAccessible(true);
                return ctor.newInstance(obj, translateToGreenfootX(obj.getX()), translateToGreenfootY(obj.getY()));
            } catch (InstantiationException y) {
                y.printStackTrace();
            } catch (InvocationTargetException y) {
                y.printStackTrace();
            } catch (IllegalAccessException y) {
                y.printStackTrace();
            } catch (java.lang.NoSuchMethodException y) {
                y.printStackTrace();
            }
        }
        return null;
    }

    private Object callConstructor()
    {
        return callConstructor(this);
    }

    /**
     * remove this clone from the world.
     */
    public void deleteThisClone()
    {
        if (isClone) {        
            getWorld().removeObject(this);
            Thread.currentThread().interrupt();
        }
    }

    /**
     * Not to be called by users.  For internal use only.  May return null.
     */
    public Variable getVariable(String name) {
        return variables.get(name);
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
        // Iterate through all of this sprite's sequences, interrupting them
        // if they are not the currently running thread.
        for (Sequence s : sequences) {
            if (Thread.currentThread() != s) {
                s.interrupt();
            }
        }
        for (Sequence s : keySeqs) {
            if (Thread.currentThread() != s) {
                s.interrupt();
            }
        }
        for (Sequence s : actorClickedSeqs) {
            if (Thread.currentThread() != s) {
                s.interrupt();
            }
        }
        for (Sequence s : stageClickedSeqs) {
            if (Thread.currentThread() != s) {
                s.interrupt();
            }
        }
        for (Sequence s : mesgRecvdSeqs) {
            if (Thread.currentThread() != s) {
                s.interrupt();
            }
        }
        for (Sequence s : cloneStartSeqs) {
            if (Thread.currentThread() != s) {
                s.interrupt();
            }
        }
        for (Sequence s : switchToBackdropSeqs) {
            if (Thread.currentThread() != s) {
                s.interrupt();
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
        penColorNumber = Math.floorMod(c, 200);
        penColor = Color.decode(numberedColors[penColorNumber]);
    }

    /**
     * change the pen color number by the given amount.
     */
    public void changePenColorBy(Number n)
    {
        penColorNumber = (penColorNumber + n.intValue()) % 200;
        penColor = Color.decode(numberedColors[penColorNumber]);
    }

    /**
     * set the pen size to the given value.  If pen size is set to 0 or negative,
     * a size of 1 is used. 
     */
    public void setPenSize(Number size)
    {
        penSize = size.floatValue();
    }

    /**
     * change pen size by the given amount.  If pen size is set to 0 or negative,
     * a size of 1 is used.
     */
    public void changePenSizeBy(Number size)
    {
        penSize += size.floatValue();
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
        Stage.getBackground().clear();
    }

    /**
     * copy the actor's image onto the screen.
     */
    public void stamp()
    {
        // Get the upper left corner of the sprite
        int cx = super.getX() - (getCurrImage().getWidth() / 2);
        int cy = super.getY() - (getCurrImage().getHeight() / 2);
        // Draw a copy of the current image to the background
        Stage.getBackground().drawImage(getCurrImage(), cx, cy);
    }

    /*
     * ---------------------------------------------------------------------
     * Motion commands.
     * ---------------------------------------------------------------------
     */
    
    /**
     * Override for Greenfoot method. Call the general method.
     */
    public void move(int distance) {
        move(new Double(distance));
    }

    /**
     * move the given distance in the direction the sprite is facing.
     */
    public void move(Number distance) 
    {
        int oldX = super.getX();
        int oldY = super.getY();

        // We don't use the move() function provided by greenfoot because
        // it rounds x and y to integer values.  If we use it, we end up
        // with a limited number of angles that can actually be achieved.
        // So, instead we move the actor using setLocation() with subpixels.

        int GFdir = (currDirection - 90) % 360;

        // This code copied from Greenfoot source.
        double radians = Math.toRadians(GFdir);

        // Calculate the cartesian movement from polar
        double dx = (Math.cos(radians) * distance.doubleValue());
        double dy = (Math.sin(radians) * distance.doubleValue());

        // Update subpixel locations with the decimal portion of dx and dy
        subX += dx - Math.round(dx);
        subY += dy - Math.round(dy);

        // If a subpixel amount is greater than 1, change that movement to standard pixel
        // movement
        if (Math.abs(subX) > 1) {
            // add the integer portion of subX to dx, then wrap subX
            dx += (int)subX;
            subX %= 1;
        }
        if (Math.abs(subY) > 1) {
            // add the integer portion of subY to dy, then wrap subY
            dy += (int)subY;
            subY %= 1;
        }
        // Set the location to the integer portion of dx and dy, as the decimal part is
        // tracked in subX and subY
        super.setLocation(oldX + (int)Math.round(dx), oldY + (int)Math.round(dy));

        /* pen is down, so we need to draw a line from the current point to the new point */
        if (isPenDown) {
            java.awt.Graphics2D g = Stage.getBackground().getAwtImage().createGraphics();
            g.setColor(penColor);
            g.setStroke(new java.awt.BasicStroke(penSize, java.awt.BasicStroke.CAP_ROUND, java.awt.BasicStroke.JOIN_ROUND));
            g.draw(new java.awt.geom.Line2D.Float(oldX, oldY, super.getX(), super.getY()));
        }
    }

    /**
     * glide the sprite to the given x, y coordinates over the given time period.
     */
    public void glideTo(Sequence s, Number duration, Number x, Number y)
    {
        if (duration.doubleValue() < .02) {
            goTo(x, y);
            return;
        }
        duration = 1000.0 * duration.doubleValue();   // convert to milliseconds.
        int begX = super.getX();  // get original X, Y in Greenfoot coordinates
        int begY = super.getY();
        int endX = translateToGreenfootX(x.intValue());   // get end destination in GF coordinates.
        int endY = translateToGreenfootY(y.intValue());
        // System.out.println("glideTo: beg " + begX + ", " + begY + " end " + endX + ", " + endY);
        double begTime = System.currentTimeMillis();
        double endTime = begTime + duration.doubleValue();
        double currTime;
        while ((currTime = System.currentTimeMillis()) < endTime) {
            try {
                s.waitForNextSequence();
            } catch (InterruptedException ie) {
                ie.printStackTrace();
            }
            // Compute how far along we are in the duration time.
            double diff = (currTime - begTime) / duration.doubleValue();
            int gfX = begX + (int) ((endX - begX) * diff);
            int gfY = begY + (int) ((endY - begY) * diff);
            goToGF(gfX, gfY);
        }
    }

    /**
     * glide the sprite to a random position onscreen over the given time period.
     */
    public void glideToRandomPosition(Sequence s, Number duration)
    {
        int w = getWorld().getWidth();
        int h = getWorld().getHeight();
        Number x = pickRandom(-w / 2, w / 2);
        Number y = pickRandom(-h / 2, h / 2);
        glideTo(s, duration, x, y);
    }

    /**
     * glide the sprite to where the mouse is.
     */
    public void glideToMouse(Sequence s, Number duration)
    {
        MouseInfo mi = Greenfoot.getMouseInfo();
        if (mi == null) {
            return;
        }
        Number x = mi.getX();
        Number y = mi.getY();
        glideTo(s, duration, translateGFtoScratchX(x.intValue()), translateGFtoScratchY(y.intValue()));
    }

    /**
     * glide the sprite to the location of another sprite
     */
    public void glideToSprite(Sequence s, String name, Number duration)
    {
        Scratch other = getWorld().getActorByName(name);
        glideTo(s, duration, other.getX(), other.getY());
    }

    /**
     * move the sprite to the location on the screen, where (0, 0) is the center and x increases
     * to the right and y increases up.
     */
    public void goTo(Number x, Number y) 
    {
        int newX = translateToGreenfootX(x.intValue());
        int newY = translateToGreenfootY(y.intValue());
        // Call goToGF() which assumes greenfoot coordinates.
        goToGF(newX, newY);
        subX = x.doubleValue() % 1;
        subY = y.doubleValue() % 1;
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
     * move to the location of another sprite
     */
    public void goTo(String name)
    {
        Scratch other = getWorld().getActorByName(name);
        goTo(other.getX(), other.getY());
    }

    /**
     * move to a random position on the stage.
     */
    public void goToRandomPosition()
    {
        int w = getWorld().getWidth();
        int h = getWorld().getHeight();
        goTo(pickRandom(-w / 2, w / 2), pickRandom(-h / 2, h / 2));
    }

    /**
     * set the sprite's x position.  (left or right)
     */
    public void setXTo(Number x) { 
        goTo(x.doubleValue(), getY()); 
    }

    /**
     * set the sprite's y position.  (up or down)
     */
    public void setYTo(Number y) 
    { 
        goTo(getX(), y.doubleValue()); 
    }
    
    /**
     * change the x position of the sprite by the given value.
     */
    public void changeXBy(Number val) 
    { 
        goTo(getX() + val.intValue(), getY()); 
        subX += val.doubleValue() % 1;
        if (Math.abs(subX) > 1) {
            changeXBy((int) subX);
            subX %= 1;
        }
    }
    
    /**
     * change the y position of the sprite by the given value.
     */
    public void changeYBy(Number val) 
    { 
        goTo(getX(), getY() + val.intValue()); 
        subY += val.doubleValue() % 1;
        if (Math.abs(subY) > 1) {
            changeXBy((int) subY);
            subY %= 1;
        }
    }

    /**
     * turn the sprite clockwise by the given degrees.
     */
    public void turnRightDegrees(Number degrees) {
        currDirection += degrees.intValue();
        setRotation(currDirection);
    }

    /**
     * turn the sprite counter-clockwise by the given degrees.
     */
    public void turnLeftDegrees(Number degrees) { 
        currDirection -= degrees.intValue();
        setRotation(currDirection);
    }

    /**
     * point the sprite in the given direction.  0 is up, 
     * 90 is to the right, -90 to the left, 180 is down.
     */
    public void pointInDirection(Number dir) 
    {
        currDirection = dir.intValue();
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
        costumes.get(currCostume).image.setRotation(rotation - 90);
        updateImage = true;
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
     * turn the sprite to point toward the direction of the given sprite
     */
    public void pointToward(String spriteName)
    {
        Scratch other = getWorld().getActorByName(spriteName);
        pointToward(other);
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
        ScratchImage img = costumes.get(currCostume).image;
        int w = (int)((double)(img.pixelWidth() / 2) * (costumeSize / 100d));
        int h = (int)((double)(img.pixelHeight() / 2) * (costumeSize / 100d));
        if (super.getX() + w >= getWorld().getWidth() - 1) {
            // hitting right edge
            currDirection = (360 - currDirection) % 360;
            setRotation(currDirection);
            // prevent actor from getting stuck on the edge by pushing it out
            changeXBy(-((super.getX() + w) - (getWorld().getWidth() - 1)) - 1); 
        } else if (super.getX() - w <= 0) {
            // hitting left edge
            currDirection = (360 - currDirection) % 360;
            setRotation(currDirection);
            // prevent actor from getting stuck on the edge by pushing it out
            changeXBy(-(super.getX() - w) + 1);
        }
        if (super.getY() + h >= getWorld().getHeight() - 1) {
            // hitting top
            currDirection = (180 - currDirection) % 360;
            setRotation(currDirection);
            // prevent actor from getting stuck on the edge by pushing it out
            changeYBy(((super.getY() + h) - (getWorld().getHeight() - 1)) + 1);
        } else if (super.getY() - h <= 0) {
            // hitting bottom
            currDirection = (180 - currDirection) % 360;
            setRotation(currDirection);
            // prevent actor from getting stuck on the edge by pushing it out
            changeYBy((super.getY() - h) - 1);
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
        costumes.get(currCostume).image.style = rs;
        updateImage = true;
    }
    
    /**
     * Get the current rotation style
     */
    public RotationStyle getRotationStyle()
    {
        return rotationStyle;
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
    
    /**
     * return x coordinate of this sprite in the Greenfoot system.
     */
    public int getGFX() 
    {
        // System.out.println("x in GF is " + super.getX(); + " but in scratch is " + translateGFtoScratchX(super.getX()));
        return super.getX();
    }

    /**
     * return the y coordinate of this sprite in the Greenfoot system.
     */
    public int getGFY() 
    {
        // System.out.println("y in GF is " + super.getY() + " but in scratch is " + translateGFtoScratchY(super.getY()));
        return super.getY();
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
        java.awt.Graphics2D g = Stage.getBackground().getAwtImage().createGraphics();
        g.setColor(penColor);
        g.setStroke(new java.awt.BasicStroke(penSize, java.awt.BasicStroke.CAP_ROUND, java.awt.BasicStroke.JOIN_ROUND));
        g.draw(new java.awt.geom.Line2D.Float(oldX, oldY, super.getX(), super.getY()));
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
     * Will get the image as it is displayed
     */
    public GreenfootImage getCurrImage()
    {
        return costumes.get(currCostume).image.getDisplay();
    }

    /**
     * Will get the image as it is displayed
     */
    public ScratchImage getScratchImage()
    {
        return costumes.get(currCostume).image;
    }

    /**
     * display the given string next to the sprite.
     */
    public void say(Object speech)
    {
        String str = speech.toString();
        if (str == "") {
            return;
        }
        if (sayActor != null) {
            if (str == null) {
                // saying nothing means remove the sayActor
                getWorld().removeObject(sayActor);
                sayActor = null;
            } else {
                sayActor.setString(str);
                if (!isShowing()) {
                    sayActor.hide();
                }
            }
            return;
        }

        GreenfootImage mySprite = getCurrImage();

        int width = mySprite.getWidth();
        int height = mySprite.getHeight();

        sayActor = new Sayer(str);
        sayActor.think = false;
        sayActor.update();
        getWorld().addObject(sayActor, super.getX() + width + 10, super.getY() - height - 5);
        if (!isShowing) {
            sayActor.hide();
        }
        getWorld().moveClassToFront(sayActor.getClass());
    }
    
    /**
     * display the given string next to the sprite in a thought bubble.
     */
    public void think(Object speech)
    {
        say(speech);
        sayActor.think = true;
        sayActor.update();
    }
    
    /**
     * display the given string for <n> seconds next to the sprite.
     */
    public void sayForNSeconds(Sequence s, Object speech, Number duration)
    {
        String str = speech.toString();
        GreenfootImage mySprite = getCurrImage();

        int width = mySprite.getWidth();
        int height = mySprite.getHeight();

        sayActor = new Sayer(str);
        getWorld().addObject(sayActor, super.getX() + width + 10, super.getY() - height - 5);

        if (!isShowing) {
            sayActor.hide();
        }
        getWorld().moveClassToFront(sayActor.getClass());

        wait(s, duration.doubleValue());

        getWorld().removeObject(sayActor);
        sayActor = null;
    }
    
    /**
     * display the given string for <n> seconds next to the sprite.
     */
    public void thinkForNSeconds(Sequence s, Object speech, Number duration)
    {
        String str = speech.toString();
        GreenfootImage mySprite = getCurrImage();

        int width = mySprite.getWidth();
        int height = mySprite.getHeight();

        sayActor = new Sayer(str);
        sayActor.think = true;
        sayActor.update();
        getWorld().addObject(sayActor, super.getX() + width + 10, super.getY() - height - 5);

        if (!isShowing) {
            sayActor.hide();
        }
        getWorld().moveClassToFront(sayActor.getClass());

        wait(s, duration.doubleValue());

        getWorld().removeObject(sayActor);
        sayActor = null;
    }

    // called from act() above to update the location of the say/think actor.
    private void sayActorUpdateLocation()
    {
        ScratchImage mySprite = getScratchImage();
        int width = (int)(((float)mySprite.pixelWidth / 2f) * costumeSize / 100f);
        int height = (int)(((float)mySprite.pixelHeight / 2f) * costumeSize / 100f);
        sayActor.updateLocation(getX() + width + 4, getY() + height + 4);
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
        updateImage = true;
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
        updateImage = true;
    }

    /**
     * switch to the costume with the given number, loops.
     */
    public void switchToCostume(int costumeNum)
    {
        costumeNum--;
        costumeNum = Math.floorMod(costumeNum, costumes.size() - 1);
        costumeNum++;
        currCostume = costumeNum;
        
        updateImage = true;
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
    public int costumeNumber()
    {
        return currCostume;
    }
    
    /**
     * return the name of the current costume.
     */
    public String costumeName()
    {
        return costumes.get(currCostume).name;
    }

    /**
     * hide this sprite -- don't show it.
     */
    public void hide()
    {
        isShowing = false;
        if (sayActor != null) {
            sayActor.hide();
        }
        updateImage = true;
    }

    /**
     * show this sprite in the world.
     */
    public void show()
    {
        isShowing = true;
        if (sayActor != null) {
            sayActor.show();
            sayActor.update();
        }
        updateImage = true;
    }
    
    /**
     * Returns true if the object is showing, false if hidden
     */
    public boolean isShowing()
    {
        return isShowing;
    }

    /**
     * set the ghost effect (transparency) to a value from 0 to 100.  
     * 0 is fully visible; 100 is completely invisible.
     */
    public void setGhostEffectTo(Number amount)
    {
        if (amount.intValue() < 0) {
            amount = 0;
        } else if (amount.intValue() > 100) {
            amount = 100;
        }
        ghostEffect = amount.intValue();
        updateImage = true;
    }

    /**
     * change the ghost effect (transparency) by the given amount.
     * 0 is full visible; 100 is fully invisible.
     */
    public void changeGhostEffectBy(Number amount)
    {
        setGhostEffectTo(ghostEffect + amount.intValue());
    }
    
    /**
     * set the pixelate effect to a value
     */
    public void setPixelateEffectTo(Number amount)
    {
        amount = amount.doubleValue();
        pixelateEffect = amount.doubleValue();
        updateImage = true;
    }

    /**
     * change the pixelate effect of this sprite by the given amount.
     */
    public void changePixelateEffectBy(Number amount)
    {
        pixelateEffect += amount.doubleValue();
        updateImage = true;
    }
    
    /**
     * set the whril effect to a value
     */
    public void setWhirlEffectTo(Number amount)
    {
        whirlEffect = amount.doubleValue();
        updateImage = true;
    }

    /**
     * change the whirl effect of this sprite by the given amount.
     */
    public void changeWhirlEffectBy(Number amount)
    {
        whirlEffect += amount.doubleValue();
        updateImage = true;
    }
    
    /**
     * set the fisheye effect to a value
     */
    public void setFisheyeEffectTo(Number amount)
    {
        fisheyeEffect = amount.doubleValue();
        updateImage = true;
    }

    /**
     * change the fisheye effect of this sprite by the given amount.
     */
    public void changeFisheyeEffectBy(Number amount)
    {
        fisheyeEffect += amount.doubleValue();
        updateImage = true;
    }
    
    /**
     * set the mosaic effect to a value
     */
    public void setMosaicEffectTo(Number amount)
    {
        mosaicEffect = amount.doubleValue();
        updateImage = true;
    }

    /**
     * change the mosaic effect of this sprite by the given amount.
     */
    public void changeMosaicEffectBy(Number amount)
    {
        mosaicEffect += amount.doubleValue();
        updateImage = true;
    }
    
    /**
     * set the color effect to a value
     */
    public void setColorEffectTo(Number amount)
    {
        colorEffect = amount.doubleValue();
        updateImage = true;
    }

    /**
     * change the color effect of this sprite by the given amount.
     */
    public void changeColorEffectBy(Number amount)
    {
        colorEffect += amount.doubleValue();
        updateImage = true;
    }
    
    /**
     * set the brightness effect to a value
     */
    public void setBrightnessEffectTo(Number amount)
    {
        brightnessEffect = amount.doubleValue();
        updateImage = true;
    }

    /**
     * change the brightness effect of this sprite by the given amount.
     */
    public void changeBrightnessEffectBy(Number amount)
    {
        brightnessEffect += amount.doubleValue();
        updateImage = true;
    }

    /**
     * change the size of this sprite by the given percent.
     */
    public void changeSizeBy(Number percent)
    {
        setSizeTo(costumeSize + percent.intValue());
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
    public double size() 
    {
        return costumeSize;
    }

    /**
     * Set the sprite size to a percentage of the original size.
     */
    public void setSizeTo(Number percent)
    {
        costumeSize = percent.intValue();
        updateImage = true;
    }

    // private helper function
    private void displayCostume()
    {
        // Prevent the stage from updating its image
        if (this instanceof Stage || this instanceof nonInteractive) {
            return;
        }
        Costume cost = costumes.get(currCostume);
        cost.image.setAll(currDirection - 90, ghostEffect, pixelateEffect, whirlEffect, fisheyeEffect, 
                          mosaicEffect, colorEffect, brightnessEffect, costumeSize);              
        if (isShowing) {
            setImage(cost.image.getDisplay());
        } else {
            setImage((GreenfootImage) null);
        }
    }

    /**
     * return the current backdrop name being shown in the world.
     */
    public String backdropName()
    {
        return getWorld().getBackdropName();
    }
    
    /**
     * return the current backdrop number being shown in the world.
     */
    public int getBackdropNumber()
    {
        return getWorld().getBackdropNumber();
    }
    
    /**
     * Switches to the provided backdrop number
     */
    public void switchBackdropTo(int num) {
        getWorld().switchBackdropTo(num);
    }
    
    /**
     * Switches to the backdrop with the given name
     */
    public void switchBackdropTo(String name) {
        getWorld().switchBackdropTo(name);
    }
    
    /**
     * Switches to the backdrop with the given name
     */
    public void nextBackdrop() {
        getWorld().nextBackdrop();
    }

    /*
     * ---------------------------------------------------------------------
     * Sensing blocks.
     * ---------------------------------------------------------------------
     */

    /**
     * Returns the containing scratchworld
     */
    public ScratchWorld getWorld()
    {
        return (ScratchWorld)super.getWorld();
    }
    
    /**
     * Returns true if this object's tree overlaps another in the
     * list of actors given.
     */
    public boolean treeOverlap(List<Scratch> others, Color rgb) {
        ScratchImage.Node n = costumes.get(currCostume).image.root;
        if (n == null) {
            costumes.get(currCostume).image.generateQuadTree();
            n = costumes.get(currCostume).image.root;
        }
        GreenfootImage im = getCurrImage();
        // Get the upper left corner of the sprite's image
        int cx = getGFX() - (n.w / 2);
        int cy = getGFY() - (n.h / 2);
        // Queues for the BFS
        LinkedList<ScratchImage.Node> q = new LinkedList();
        LinkedList<ScratchImage.Node> q2 = new LinkedList();
        for (Scratch other : others) {
            if (!other.isShowing()) {
                // If the other isn't displaying, we can't collide with it.
                continue;
            }
            ScratchImage.Node root2 = other.costumes.get(other.currCostume).image.root;
            if (root2 == null) {
                other.costumes.get(currCostume).image.generateQuadTree();
                root2 = other.costumes.get(currCostume).image.root;
            }
            // Get the queue ready for a new BFS
            q.clear();
            q.add(n);
            // Get the coordinates of the upper left corner of the other's sprite
            int ocx = other.getGFX() - (root2.w / 2);
            int ocy = other.getGFY() - (root2.h / 2);
            // Do a breadth first search of the object's tree
            while (!q.isEmpty()) {
                ScratchImage.Node self = q.poll();
                if (self == null)
                    continue;
                if (self.fill == 1) {
                    // If this is opaque, if it overlaps an opaque square from the other sprite
                    // Find the absolute coordinates of the corner of this node
                    int absx = cx + self.x;
                    int absy = cy + self.y;
                    // Get the second queue ready for another BFS
                    q2.clear();
                    q2.add(root2);
                    while (!q2.isEmpty()) {
                        ScratchImage.Node oth = q2.poll();
                        // Find the absolute coordinates of the corner of this node
                        int absx2 = ocx + oth.x;
                        int absy2 = ocy + oth.y;
                        if (absx + self.w < absx2 || absx2 + oth.w < absx || absy + self.h < absy2 || absy2 + oth.h < absy) {
                            // If it does not overlap, skip it, and don't add any of its children to the queue
                            continue;
                        }
                        if (oth.fill == 1) {
                            // If it's filled, that means two opaque squares are overlapping
                            return true;
                        } else if (oth.fill == -1) {
                            // If it's transparent, there can't be a collision in this square, so skip
                            continue;
                        } else {
                            // If it's partial, recurse to find its components
                            q2.add(oth.nw);
                            q2.add(oth.ne);
                            q2.add(oth.sw);
                            q2.add(oth.se);
                        }
                    }
                } else if (self.fill == -1) {
                    // If this is transparent, it cannot collide, so this branch is finished
                    continue;
                } else {
                    // If this is partially filled, recurse
                    q.add(self.nw);
                    q.add(self.ne);
                    q.add(self.sw);
                    q.add(self.se);
                }
            }
        }
        return false;
    }
    
    /**
     * Returns true if this sprite overlaps the specified color in other.
     * Passing color as 'null' will check all non-transparent pixels.
     */
    private boolean pixelOverlap(List<Scratch> others, Color rgb)
    {
        // Get this image's data
        // The image from getCurrImage is already rotated/resized, so we don't have to do that here
        GreenfootImage im = getCurrImage();
        int height = im.getHeight();
        int width = im.getWidth();
        // get the coordinates of the upper left corners for awt interaction
        int cx = getX() - (width / 2);
        int cy = getY() + (height / 2);
        // get world width and height to avoid constant calls to world
        int worldH = getWorld().getHeight();
        int worldW = getWorld().getWidth();
        // declare lists to iterate through each intersecting object
        ArrayList<GreenfootImage> oim = new ArrayList<GreenfootImage>();
        ArrayList<Integer> ocx = new ArrayList<Integer>();
        ArrayList<Integer> ocy = new ArrayList<Integer>();
        // Get the other image's data
        for (Scratch other : others) {
            if (other.isShowing()) {  // Objects that arent showing shouldnt be checked 
                GreenfootImage img = other.getCurrImage();
                oim.add(img);
                ocx.add(other.getX() - (img.getWidth() / 2));
                ocy.add(other.getY() + (img.getHeight() / 2));
            }
        }
        for (int x = 0; x < width; x++) {
            for (int y = 0; y < height; y++) {
                if (im.getAwtImage().getRGB(x, y) >> 24 == 0x00) {
                    continue;
                }
                boolean checkBackdrop = rgb != null; // If no sprite is found and a color is selected, check the backdrop too
                for (int i = 0; i < oim.size(); i++) {
                    int fx = changeRelativePoint(x, cx, ocx.get(i));
                    int fy = changeRelativePoint(y, -cy, -ocy.get(i));
                    if (fx < 0 || fy < 0 || fx >= oim.get(i).getWidth() || fy >= oim.get(i).getHeight()) {
                        continue;
                    }
                    greenfoot.Color pixel = oim.get(i).getColorAt(fx, fy);
                    if (rgb == null) {
                        if (pixel.getAlpha() != 0) {
                            return true;
                        }
                    } else {
                        if (Math.abs(pixel.getRed() - rgb.getRed()) < 8 // Compare the top 5 bits of red/green and top 4 of blue
                            && Math.abs(pixel.getGreen() - rgb.getGreen()) < 8
                            && Math.abs(pixel.getBlue() - rgb.getBlue()) < 16
                            && pixel.getAlpha() > 240) {
                            return true;
                        } else if (pixel.getAlpha() == 0) {
                            checkBackdrop = true;
                            break;
                        } else {
                            checkBackdrop = false;
                            break;
                        }
                    }
                }
                // If there is nothing else to check on this pixel, check the backdrop
                if (checkBackdrop) {
                    // Catching exceptions is very slow, so instead we skip iterations that might throw one.
                    if (translateToGreenfootX(cx + x) < 0 || translateToGreenfootX(cx + x) >= worldW || translateToGreenfootY(cy - y) >= worldH || translateToGreenfootY(cy - y) < 0) {
                        continue;
                    }
                    // See if the pixel at this location in the background is of the given color.
                    greenfoot.Color bkg = getWorld().getBackground().getColorAt(translateToGreenfootX(cx + x), translateToGreenfootY(cy - y));
                    
                    if (Math.abs(bkg.getRed() - rgb.getRed()) < 8 // Compare the top 5 bits of red/green and top 4 of blue
                        && Math.abs(bkg.getGreen() - rgb.getGreen()) < 8
                        && Math.abs(bkg.getBlue() - rgb.getBlue()) < 16
                        && bkg.getAlpha() > 240) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    /**
     * return true if this sprite is touching a sprite that is an instance of
     * other's class.  This includes the "original" sprite and any clones.
     * return false otherwise.
     */
    public boolean isTouching(Scratch other)
    {
        if (!isShowing) {
            return false;
        }
        /* Get all intersecting objects of other's class.  To Greenfoot, "intersecting" means
           the images' bounding boxes overlap.  */
        java.lang.Class clazz = other.getClass();
        List<Scratch> nbrs = getIntersectingActors(clazz);

        /* Scratch's definition of "intersecting" (or "touching") is that the images'
           non-transparent pixels overlap.  So, we need to go through each neighbor
           and find the first with this criterion. */
        if (treeOverlap(nbrs, null)) {
            return true;
        }
        return false;
    }

    /**
     * return true if this sprite is touching another sprite, with the given name.
     */
    public boolean isTouching(String spriteName) 
    {
        Scratch other = getWorld().getActorByName(spriteName);
        if (other == null) { 
            System.err.println("isTouching() could not find sprite " + spriteName); 
            return false; 
        } 
        return isTouching(other);
    }

    /**
     * return true if this sprite is touching the mouse, 
     * false otherwise.
     */
    public boolean isTouchingMouse()
    {
        // Get the image and rotate it to the proper orientation. TODO The rotation code is
        // copied from stamp(), possibility for refactoring.
        GreenfootImage oldImg = getCurrImage();
        int w = oldImg.getWidth(), h = oldImg.getHeight();
        int newDim = w > h ? w : h;
        GreenfootImage image = new GreenfootImage(newDim, newDim);  
        image.drawImage(oldImg, (newDim - w) / 2, (newDim - h) / 2);
        int rot = getRotation();
        image.rotate(rot);

        BufferedImage bIm = image.getAwtImage();
        try {
            // This line gets the pixel color at x and y of the mouse relative to
            // the actor's position. The y value must be reversed because the y axis
            // is different for buffered images. 
            int pixel = bIm.getRGB(getMouseX() - getX() + (bIm.getWidth() / 2),
                    bIm.getHeight() - (getMouseY() - getY() + (bIm.getHeight() / 2)));
            if ((pixel >> 24) == 0x00) {
                return false;   // transparent pixel: doesn't count.
            } else {
                return true;
            }

        } catch (ArrayIndexOutOfBoundsException e) {
            return false;   // pixel out of bounds of image
        } 
    }

    /**
     * return true if this sprite is touching the edge of the world,
     * false otherwise.
     */
    public boolean isTouchingEdge()
    {
        ScratchImage img = costumes.get(currCostume).image;
        return (super.getX() + img.pixelWidth() / 2 >= getWorld().getWidth() - 1 || super.getX() - img.pixelWidth() / 2 <= 0 || 
            super.getY() + img.pixelHeight() / 2 >= getWorld().getHeight() - 1 || super.getY() - img.pixelHeight() / 2 <= 0);
    }

    /**
     * return true if this sprite is touching the given color in the background.
     */
    public boolean isTouchingColor(Color color)
    {
        List<Scratch> nbrs = getIntersectingActors(null);
        java.util.Collections.sort(nbrs);
        if (pixelOverlap(nbrs, color)) {
            return true;
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
        return getWorld().isMouseDown();
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
     * return the distance in pixels to the other sprite.
     */
    public int distanceTo(String spriteName)
    {
        return distanceTo(getWorld().getActorByName(spriteName));
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
        return getWorld().getTimer();
    }

    /**
     * reset the built-in timer to 0.0.
     */
    public void resetTimer()
    {
        getWorld().resetTimer();
    }

    /**
     * return the x position of the given sprite.
     */
    public int xPositionOf(Scratch other)
    {
        return translateGFtoScratchX(other.getX());
    }

    /**
     * return the x position of the given sprite.
     */
    public int xPositionOf(String spriteName)
    {
        return xPositionOf(getWorld().getActorByName(spriteName));
    }

    /**
     * return the y position of the given sprite.
     */
    public int yPositionOf(Scratch other)
    {
        return translateGFtoScratchY(other.getY());
    }

    /**
     * return the x position of the given sprite.
     */
    public int yPositionOf(String spriteName)
    {
        return yPositionOf(getWorld().getActorByName(spriteName));
    }

    /**
     * return the direction the given sprite is pointing to.
     */
    public int directionOf(Scratch other)
    {
        return other.getDirection();
    }

    /**
     * return the direction the given sprite is pointing to.
     */
    public int directionOf(String spriteName)
    {
        Scratch other = getWorld().getActorByName(spriteName);
        return other.getDirection();
    }

    /**
     * return the costume number of the given sprite
     */
    public int costumeNumberOf(Scratch other)
    {
        return other.costumeNumber();
    }

    /**
     * return the costume name of the given sprite
     */
    public String costumeNameOf(String spriteName)
    {
        Scratch other = getWorld().getActorByName(spriteName);
        return other.costumeName();
    }
    
    /**
     * return the costume name of the given sprite
     */
    public String costumeNameOf(Scratch other)
    {
        return other.costumeName();
    }

    /**
     * return the costume number of the given sprite
     */
    public int costumeNumberOf(String spriteName)
    {
        Scratch other = getWorld().getActorByName(spriteName);
        return other.costumeNumber();
    }

    /**
     * return the size (in percentage of the original) of the given sprite
     */
    public double sizeOf(Scratch other)
    {
        return other.size();
    }

    /**
     * return the size (in percentage of the original) of the given sprite
     */
    public double sizeOf(String spriteName)
    {
        Scratch other = getWorld().getActorByName(spriteName);
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
     * return the number of days since January 1 2000 as a decimal
     */
    public double daysSince2000()
    {
        return ((double)new java.util.GregorianCalendar().getTimeInMillis() - (double)new java.util.GregorianCalendar(2000, 1, 0).getTimeInMillis()) / 86400000D;
    }

    /**
     * askStringAndWait
     */
    public String askStringAndWait(String message)
    {
        return JOptionPane.showInputDialog(message);
    }

    /*
     * Sound stuff.
     */
   
    /**
     * Add all sounds in the "proj/sounds/[spritename]" directory to the sound dictionary. Uses filename as key.
     * Not to be called by users
     */
    public void loadSounds()
    {
        soundPlayer.loadSounds(name);
    }

    /**
     * Plays a sound until it has finished
     */
    public void playSoundUntilDone(String clipName)
    {
        soundPlayer.playSoundUntilDone(name, clipName);
    }

    /**
     * Plays a sound, restarting it if it is currently playing
     * This currently works the same as playUntilDone because greenfoot does not restart sounds
     * that are stopped and replayed on the same frame, and doing so causes massive performance drops.
     */
    public void playSound(String clipName)
    {
        soundPlayer.playSound(name, clipName);
    }

    /**
     * Stops all currently playing sounds
     */
    public void stopAllSounds()
    {
        soundPlayer.stopAllSounds();
    }
    
    /**
     * Plays the given note using the currently selected instrument
     * if this sprite already has a note playing, it will wait for that
     * one to finish first. Note that this uses the Scratch drumset,
     * not the GM drumset.
     */
    public void playNote(Sequence s, int pitch, double length) 
    {
        // Ensure the pitch is valid
        if (pitch > 127) {
            pitch = 127;
        } else if (pitch < 1) {
            pitch = 1;
        }
        //int volume = 255 * 
        while (!soundPlayer.playNote(pitch, 255, 0, length, name)) {
            yield(s); // Yield until the note is successfully played
        }
    }
    
    /**
     * sets the Instrument to the given one. Note that this uses the
     * Scratch instrment set, not the GM instrument set.
     */
    public void changeInstrument(int instrument) 
    {
        // Ensure the instrument will not go out of bounds
        if (instrument > 21) {
            instrument = 21;
        } else if (instrument < 1) {
            instrument = 1;
        }
        soundPlayer.setInstrument(scratchInstruments[instrument], 0);
    }
    
    /**
     * Plays the given drum using the currently selected instrument
     * if this sprite already has a drum playing, it will wait for that
     * one to finish first.
     */
    public void playDrum(Sequence s, int drum, double length) {
        long start = System.currentTimeMillis();
        // Ensure the drum is valid
        if (drum > 18) {
            drum = 18;
        } else if (drum < 1) {
            drum = 1;
        }
        while (!soundPlayer.playNote(scratchDrums[drum], 255, 9, length, name)) {
            yield(s); // Yield until the note is successfully played
        }
    }
    
    /**
     * Plays a silent note for the given time, delaying its other notes
     * if this sprite already has a drum/instrument playing, it will wait for that
     * one to finish first.
     */
    public void rest(Sequence s, double length) {
        while (!soundPlayer.playNote(0, 0, 16, length, name)) {
            yield(s); // Yield until the note is successfully played
        }
    }
    
    /**
     * Sets the tempo to the provided value
     */
    public void setTempo(int bpm)
    {
        if (bpm <= 0) {
            return; // if bpm is negative or 0 do nothing
        }
        soundPlayer.setTempo(bpm);
    }
    
    /**
     * Adds the provided value to the current tempo
     */
    public void changeTempoBy(int bpm)
    {
        if (soundPlayer.tempo + bpm < 0) {
            return; // if bpm is negative do nothing
        }
        soundPlayer.setTempo(soundPlayer.tempo + bpm);
    }
    
    static class SoundPlayer extends Thread 
    {
        Synthesizer synth;
        int tempo = 60;
        double whole; // Length in ms of 1 beat
        
        // Stores pending notes that are to be played
        LinkedTransferQueue<Note> notes = new LinkedTransferQueue<Note>();
        // Stores currently playing notes
        Stack<Note> activeNotes = new Stack<Note>();
        // Store the names of sprites that are currently playing notes
        ArrayList<String> active = new ArrayList<String>();
        // List of this sprites sounds
        private Hashtable<String, Clip> soundList = new Hashtable<String, Clip>();
        
        public SoundPlayer() {
            // Set this threads name to ScratchSound, so we can find it later
            super("ScratchSound");
            whole = (double)tempo * 1000 / 60;
            try {
                synth = MidiSystem.getSynthesizer();
                synth.open();
            } catch (MidiUnavailableException e) {
                System.out.println("Midi synthesizer could not be initialized, instruments and drums won't work");
            }
            setTempo(tempo);
        }
        
        public void run() {
            int p = 0;
            while (true) {
                // Pull a note off the stack if one exists
                try {
                    // Poll for any new notes to play for 100micros
                    Note note = notes.poll(1, java.util.concurrent.TimeUnit.MILLISECONDS);
                    if (interrupted()) {
                        // Release all resources held by this thread
                        close();
                        return;
                    }
                    if (note != null) { // If a note was found
                        // Play the new note
                        System.out.println("note channel" + note.channel);
                        synth.getChannels()[note.channel].noteOn(note.pitch, note.vel);
                        // Set the note to active
                        activeNotes.push(note);
                    }
                    // The midi will be interrupted when scratch is recompiled
                } catch (InterruptedException e) {
                    // Release all resources held by this thread
                    close();
                    return;
                }
                // Check all active notes and end any that have passed their end time
                for (int i = 0; i < activeNotes.size(); i++) { 
                    Note n = activeNotes.pop(); 
                    if (System.currentTimeMillis() > n.start + n.length) {
                        // If the note has ended, remove its caller from the active list
                        active.remove(n.caller);
                        // Turn the note off. This will not immediately stop the sound,
                        // different instruments react differently to noteOff messages
                        synth.getChannels()[n.channel].noteOff(n.pitch, n.vel);
                    } else {
                        // If the note has not finished, put it back on the stack
                        activeNotes.push(n);
                    }
                }
            }
        }
        
        synchronized public boolean playNote(int pitch, int vel, int channel, double length, String caller) {
            length *= whole; // Adjust beat time to milliseconds
            long start = System.currentTimeMillis(); // get appropriate start time
            // Ensure exclusive access to active and notes arrays
            if (active.contains(caller)) { // if the caller has a note active, return false
                return false;              // Caller should retry until it succeeds
            }
            active.add(caller); // Activate this caller
            notes.add(new Note(pitch, vel, channel, length, start, caller)); // Add the note as pending

            return true; // Note was successfully played, return to normal execution
        }
        
        synchronized public void setTempo(int bpm) {
            tempo = bpm;
            whole = tempo * 1000 / 60; // Length in ms of 1 beat
        }
        
        synchronized public void setInstrument(int instrument, int channel) {
            synth.getChannels()[channel].programChange(instrument);
        }
        
        synchronized public void soundOff() {
            for (int i = 0; i < 16; i++) { // loop through all midi channels
                synth.getChannels()[i].allSoundOff(); // Immediately cut sound
            }
        }
        
        private class Note {
            public int pitch, vel, channel;
            public double length;
            public long start;
            public String caller;
            public Note(int p, int v, int c, double l, long s, String C) {
                pitch = p;
                vel = v;
                channel = c;
                length = l;
                start = s;
                caller = C;
            }
        }
        
        /**
         * Add all sounds in the "proj/sounds/[spritename]" 
         * directory to the sound dictionary. Uses "[spritename]/filename" as key.
         */
        private void loadSounds(String name)
        {
            close(name);
            // Access sound directory
            File soundDir = new File("sounds/" + name);
            //System.out.println("Looking for sounds in: " + soundDir.getAbsolutePath());
            AudioInputStream aIn = null;
            File[] ls = soundDir.listFiles();
            
            if (ls != null) {
                for (File f : ls) {
                    try {
                        // Get the input stream from the found file
                        AudioInputStream fileIn = AudioSystem.getAudioInputStream(f);
                        // Try to convert it to PCM, if possible
                        aIn = AudioSystem.getAudioInputStream(AudioFormat.Encoding.PCM_SIGNED, fileIn);
                        // Create an empty clip object
                        Clip clip = AudioSystem.getClip();
                        // Load the sound file into the clip
                        clip.open(aIn);
                        // Add the clip to the list of sounds
                        soundList.put(name + "/" + f.getName(), clip);
                        System.out.println("Added sound clip: " + f.getName() + " for sprite: " + name);
                    } catch (UnsupportedAudioFileException e) {
                        System.err.println("Only pcm .wav filetypes are acceptable: " + f.getName());
                        //e.printStackTrace();
                    } catch (LineUnavailableException e) {
                        System.err.println("Sounds did not unload properly, Please restart Greenfoot");
                    } catch (Exception e) {
                        e.printStackTrace();
                    } finally {
                        try {
                            aIn.close();
                        } catch (java.io.IOException e) {
                            System.err.println("couldn't close Ain");
                        }
                    }
                }
            }
        }
    
        /**
         * Plays a sound until it has finished
         */
        public void playSoundUntilDone(String sprite, String name)
        {
            String clipName = sprite + "/" + name + ".wav";
            Clip toPlay = soundList.get(clipName);
            if (toPlay != null) {
                if (!toPlay.isActive()) {
                    toPlay.setFramePosition(0);
                }
                toPlay.start();
            } else {
                System.err.println("Attempted to play non-existent sound");
            }
        }
    
        /**
         * Plays a sound, restarting it if it is currently playing
         * This currently works the same as playUntilDone because greenfoot does not restart sounds
         * that are stopped and replayed on the same frame, and doing so causes massive performance drops.
         */
        public void playSound(String sprite, String name)
        {
            String clipName = sprite + "/" + name + ".wav";
            Clip toPlay = soundList.get(clipName);
            if (toPlay != null) {
                toPlay.setFramePosition(0);
                if (!toPlay.isActive()) {
                    toPlay.start();
                }
            } else {
                System.err.println("Attempted to play non-existent sound");
            }
        }
    
        /**
         * Stops all currently playing sounds
         */
        public void stopAllSounds()
        {
            for (Clip clip : soundList.values()) {
                clip.stop();
            }
            soundList.clear();
            soundPlayer.soundOff();
        }
        
        /**
         * Closes down the player, releasing all held resources
         */
        public void close() {
            soundPlayer.soundOff();
            synth.close();
            for (Clip c : soundList.values()) {
                c.close();
                //System.out.println("Closing sound on shutdown");
            }
        }
        
        /**
         * Closes all clips for a specific sprite
         * This is used to release resources held by the sprites
         * when greenfoot is reloaded.
         */
        public void close(String name) {
            soundPlayer.soundOff();
            //System.out.println("Closing sound for sprite: " + name);
            ArrayList<String> keysToRemove = new ArrayList<String>();
            for (String key : soundList.keySet()) {
                // If the first part of the name of the sound is this sprites name
                // then the sound belongs to that sprite, and it should be removed
                if (key.split("/")[0].equals(name)) {
                    // Close the clip, releasing any resources it has
                    soundList.get(key).stop();
                    soundList.get(key).close();
                    // Store the keys we need to remove from the hash table
                    // removing them here would throw a concurrentModificationException
                    keysToRemove.add(key);
                }
            }
            for (String key : keysToRemove) {
                // remove all the closed clips from the table
                soundList.remove(key);
            }
        }

    }

    /*
     * Miscellaneous stuff.
     */
    /**
     * Allows sorting scratch objects by paint order
     */
    @Override
    public int compareTo(Scratch o)
    {
        return getLayer() - o.getLayer();
    }
    
    /**
     * Determines whether two objects have intersecting bounding boxes
     */
    public boolean intersects(Scratch other)
    {
        int w = getCurrImage().getWidth()/2;
        int h = getCurrImage().getHeight()/2;
        int ow = other.getCurrImage().getWidth()/2;
        int oh = other.getCurrImage().getHeight()/2;
        // 1st rectangle's lower left point coords
        int l1x = getX() - w;
        int l1y = getY() - h;
        // 1st rect's upper left point
        int r1x = getX() + w;
        int r1y = getY() + h;
        // 2nd rect's lower left
        int l2x = other.getX() - ow;
        int l2y = other.getY() - oh;
        // 2nd rect's upper right
        int r2x = other.getX() + ow;
        int r2y = other.getY() + oh;
        
        if (l1x > r2x || l2x > r1x) {
            return false;
        }
        if (l1y > r2y || l2y > r1y) {
            return false;
        }
        return true;
    }
    
    /**
     * Determines whether two objects have intersecting bounding boxes
     */
    public boolean intersects(String name)
    {
        return intersects(getWorld().getActorByName(name));
    }
    
    /**
     * Returns a list of all intersecting actors of the given class.
     * Use the class Scratch to get all actors.
     */
    public List<Scratch> getIntersectingActors(Class type) {
        List<? extends Scratch> actors = getWorld().getObjects(type);
        List<Scratch> ret = new ArrayList<Scratch>();
        actors.remove(this);
        for (Scratch actor : actors) {
            if (intersects(actor) && !(actor instanceof nonInteractive)) {
                ret.add(actor);
            }
        }
        return ret;
    }
    
    /**
     * Takes a coordinate r relative to an absolute coordinate p and returns the relative
     * coordinate to the new absolute coordinate p
     */
    private int changeRelativePoint(int r, int p, int n)
    {
        return absToRel(relToAbs(r, p), n);
    }
    
    /**
     * Takes an absolute coordinate a and returns the relative position to the coordinate p.
     */
    private int absToRel(int a, int p)
    {
        return a - p;
    }
    
    /**
     * Takes a coordinate r relative to the absolute coordinate p and returns the absolute position 
     */
    private int relToAbs(int r, int p)
    {
        return r + p;
    }

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
     * offer the CPU to other Sequences, but only every half second
     */
    public void deferredYield(Sequence s)
    {
        // If this is the first deferredyeild then get the time 500ms from now
        if (deferredWait == -1) {
            deferredWait = System.currentTimeMillis() + 500;
        // If the time has passed the original time
        } else if (deferredWait < System.currentTimeMillis()) {
            try {
                // Allow other sequences to run
                s.waitForNextSequence();
                // Reset the timer
                deferredWait = -1;
            } catch (InterruptedException ie) {
                ie.printStackTrace();
            }
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
    public void wait(Sequence s, Number duration) 
    {
        double endTime = System.currentTimeMillis() + duration.doubleValue() * 1000.0;
        while (System.currentTimeMillis() < endTime) {
            try {
                s.waitForNextSequence();
            } catch (InterruptedException ie) {
                ie.printStackTrace();
            }
        }
    }

    /*
     * --------------------------------------------------------------
     * Operator Blocks
     * --------------------------------------------------------------
     */

    public String join(Object a, Object b) { return a.toString() + b.toString(); }

    public String letterNOf(Object o, int n) 
    {
        String s = o.toString();
        if (n < 0) {
            return "";
        }
        if (n >= s.length()) {
            return "";
        }
        return "" + s.charAt(n);
    }

    public int lengthOf(Object o) 
    {
        String s = o.toString();
        return s.length();
    }

    /**
     * return a random number between low and high, inclusive (for both).
     */
    public int pickRandom(int low, int high)
    {
        // getRandomNumber gets a number between 0 (inclusive) and high (exclusive).
        // so we have add low to the value.
        return Greenfoot.getRandomNumber(high - low + 1) + low;
    }
    
    /**
     * return a random number between low and high, inclusive (for both).
     */
    public double pickRandom(double low, double high)
    {
        // getRandomNumber gets a number between 0 (inclusive) and high (exclusive).
        // so we have add low to the value.
        return low + (high - low) * new java.util.Random().nextDouble();
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
    
    /*
     * toGFColor - converts a java.awt.Color to a greenfoot.Color object 
     */
    public greenfoot.Color toGFColor(Color awtcolor)
    {
        return new greenfoot.Color(awtcolor.getRed(), awtcolor.getGreen(), awtcolor.getBlue(), awtcolor.getAlpha());
    }

    /**
     * Sayer: a bubble that follows a Scratch actor around, displaying what
     * they are saying or thinking.
     */
    public class Sayer extends Scratch implements nonInteractive
    {
        private String str;
        boolean think = false;
        int x, y;             // in Greenfoot coordinates.
        public Sayer(String str)
        {
            super();
            this.str = str;
            // this.x = x;
            // this.y = y;
            update();
        }
        public Sayer(String str, boolean think)
        {
            super();
            this.str = str;
            this.think = think;
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
            java.awt.Graphics g = new BufferedImage(1, 1, BufferedImage.TYPE_INT_ARGB).getGraphics();
            int strLength = g.getFontMetrics(new java.awt.Font("Arial", java.awt.Font.BOLD, 14)).stringWidth(str);
            // These integer literals have been calculated based on the width of the various regions of
            // the say actor graphic.
            int imgW = (strLength < 39) ? 57 : 57 + strLength - 39;
            int imgH = 45;
            
            GreenfootImage img = new GreenfootImage(imgW, imgH);
            if (think) img.drawImage(sayThink, 0, 0);
            else img.drawImage(saySrc, 0, 0);
            for (int i = 45; i < imgW - 7; i++) {
                img.drawImage(sayExt, i, 0);
            }
            img.drawImage(sayEnd, imgW - 8, 0);
            img.setFont(new greenfoot.Font("Arial", true, false, 14));
            img.drawString(str, 8, 20);
            setImage(img);
        }

        /**
         * update the location of the box that shows what is being said.
         * x and y are in Greenfoot coordinates.  Should not be called explicitly.
         */
        public void updateLocation(int x, int y)
        {
            goTo(x, y);
        }

    }
}


