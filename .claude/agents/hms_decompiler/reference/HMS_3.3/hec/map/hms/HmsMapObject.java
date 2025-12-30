/*
 * Decompiled with CFR 0.152.
 */
package hec.map.hms;

import hec.map.WorldRect;
import hec.map.hms.HmsMapLine;
import java.io.Serializable;
import java.util.Vector;

public class HmsMapObject
implements Serializable {
    private double a;
    private double b;
    private double c;
    private double d;
    private String e = "";
    private Vector f = new Vector();

    public HmsMapObject() {
    }

    public HmsMapObject(String string) {
        this.e = string;
    }

    public WorldRect getExtent() {
        return new WorldRect(this.b, this.a, this.d, this.c);
    }

    public void setName(String string) {
        this.e = string;
    }

    public void addLine(double[] dArray, double[] dArray2, int n2, boolean bl2) {
        HmsMapLine hmsMapLine = new HmsMapLine(dArray, dArray2, n2, bl2);
        this.f.addElement(hmsMapLine);
        if (this.f.size() == 1) {
            this.a = hmsMapLine.getExtent().e;
            this.b = hmsMapLine.getExtent().w;
            this.d = hmsMapLine.getExtent().s;
            this.c = hmsMapLine.getExtent().n;
        } else {
            this.a = Math.max(hmsMapLine.getExtent().e, this.a);
            this.b = Math.min(hmsMapLine.getExtent().w, this.b);
            this.d = Math.min(hmsMapLine.getExtent().s, this.d);
            this.c = Math.max(hmsMapLine.getExtent().n, this.c);
        }
    }

    public void trimLine() {
        this.f.trimToSize();
    }

    public int getNumberOfLines() {
        return this.f.size();
    }

    public String getName() {
        return this.e;
    }

    public HmsMapLine getLine(int n2) {
        return (HmsMapLine)this.f.elementAt(n2);
    }
}

