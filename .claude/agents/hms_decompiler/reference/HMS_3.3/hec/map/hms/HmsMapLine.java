/*
 * Decompiled with CFR 0.152.
 */
package hec.map.hms;

import hec.map.WorldRect;
import java.io.Serializable;

public class HmsMapLine
implements Serializable {
    private double a;
    private double b;
    private double c;
    private double d;
    private double[] e;
    private double[] f;
    private boolean g = false;

    public boolean isPolygon() {
        return this.g;
    }

    public double[] gete() {
        return this.e;
    }

    public double[] getn() {
        return this.f;
    }

    public WorldRect getExtent() {
        return new WorldRect(this.b, this.a, this.c, this.d);
    }

    public int getNumberOfPoints() {
        return this.e.length;
    }

    public HmsMapLine(double[] dArray, double[] dArray2, int n2, boolean bl2) {
        this.e = new double[n2];
        this.f = new double[n2];
        int n3 = 0;
        while (n3 < n2) {
            this.e[n3] = dArray[n3];
            this.f[n3] = dArray2[n3];
            ++n3;
        }
        this.g = bl2;
        this.b = this.e[0];
        this.a = this.e[0];
        this.c = this.f[0];
        this.d = this.f[0];
        n3 = 0;
        while (n3 < n2) {
            this.b = Math.min(this.e[n3], this.b);
            this.a = Math.max(this.e[n3], this.a);
            this.c = Math.min(this.f[n3], this.c);
            this.d = Math.max(this.f[n3], this.d);
            ++n3;
        }
    }
}

