/*
 * Decompiled with CFR 0.152.
 * 
 * Could not load the following classes:
 *  hec.heclib.util.HecDouble
 *  org.python.core.Py
 *  org.python.core.PyException
 *  org.python.core.PyInteger
 *  org.python.core.PyObject
 *  org.python.util.PythonInterpreter
 */
package hms.model;

import hec.heclib.util.HecDouble;
import hms.ErrorDestination;
import hms.ErrorLevel;
import hms.ErrorProcessor;
import hms.f.b.ad;
import hms.f.b.bj;
import hms.f.b.bv;
import hms.f.v_0;
import hms.model.Project;
import hms.model.ProjectManager;
import hms.model.basin.a.d;
import hms.model.basin.a.h_0;
import hms.model.basin.b.a;
import hms.model.basin.b.c;
import hms.model.basin.b.g;
import hms.model.basin.bp;
import hms.model.basin.h.am;
import hms.model.basin.h.ar;
import hms.model.basin.h.av;
import hms.model.basin.h.b;
import hms.model.basin.h.h;
import hms.model.basin.h.l;
import hms.model.basin.h.z_0;
import hms.model.basin.x;
import hms.model.c.r;
import hms.model.g.f;
import hms.model.project.a_0;
import hms.model.project.u;
import java.io.File;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.Properties;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Future;
import java.util.logging.Level;
import java.util.logging.Logger;
import org.python.core.Py;
import org.python.core.PyException;
import org.python.core.PyInteger;
import org.python.core.PyObject;
import org.python.util.PythonInterpreter;

public class JythonHms {
    private static final Logger a = Logger.getLogger(JythonHms.class.getName());
    private static boolean b = false;
    private static ProjectManager c = null;
    private String d;
    private static x e;

    public JythonHms() {
    }

    public JythonHms(ProjectManager projectManager) {
        c = projectManager;
    }

    public static void setProjectManager(ProjectManager projectManager) {
        c = projectManager;
    }

    public void setScriptFileName(String string) {
        this.d = string;
    }

    private static void a() {
        Properties properties = new Properties();
        Properties properties2 = System.getProperties();
        Enumeration<?> enumeration = properties2.propertyNames();
        while (enumeration.hasMoreElements()) {
            String string = (String)enumeration.nextElement();
            if (!string.startsWith("python.")) continue;
            properties.put(string, properties2.getProperty(string));
        }
        PythonInterpreter.initialize((Properties)properties2, (Properties)properties, (String[])new String[0]);
        b = true;
    }

    public int runScript() {
        return JythonHms.runScript(this.d);
    }

    public static int runScript(String string) {
        Object[] objectArray;
        File file;
        int n2 = 0;
        if (c == null) {
            c = new ProjectManager(false);
        }
        if (!(file = new File(string)).exists()) {
            objectArray = new PythonInterpreter[]{string};
            ErrorProcessor.notifyError(12578, objectArray, ErrorLevel.ERROR, ErrorDestination.DISPLAYLIST);
            n2 = -1;
        } else if (!file.canRead()) {
            objectArray = new Object[]{string};
            ErrorProcessor.notifyError(12579, objectArray, ErrorLevel.ERROR, ErrorDestination.DISPLAYLIST);
            n2 = -1;
        }
        if (n2 != 0) {
            return n2;
        }
        if (!b) {
            JythonHms.a();
        }
        objectArray = new PythonInterpreter();
        try {
            objectArray.execfile(string);
        }
        catch (PyException pyException) {
            a.log(Level.WARNING, pyException, () -> ((PyException)pyException).getMessage());
            if (pyException.type.equals((Object)Py.SystemExit)) {
                Object[] objectArray2 = new Object[]{string, "0"};
                ErrorProcessor.notifyError(12573, objectArray2, ErrorLevel.NOTE, ErrorDestination.DISPLAYLIST);
                n2 = 0;
            }
            Object[] objectArray3 = new Object[]{string};
            ErrorProcessor.notifyError(12550, objectArray3, ErrorLevel.ERROR, ErrorDestination.DISPLAYLIST);
            pyException.printStackTrace();
            n2 = -1;
        }
        return n2;
    }

    public static void OpenBasinModel(String string) {
        x x2 = JythonHms.c().getBasinProxy(string);
        if (x2 == null) {
            Object[] objectArray = new Object[]{string};
            int n2 = 12551;
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.ERROR, ErrorDestination.DISPLAYLIST);
            String string2 = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.ValueError, string2);
        }
        e = x2;
    }

    public static void OpenProject(String string, String string2) {
        HashMap<String, String> hashMap = new HashMap<String, String>();
        Project project = c.openProject(string, string2, "", hashMap);
        if (project == null) {
            Object[] objectArray = new Object[]{string};
            int n2 = 12552;
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.ERROR, ErrorDestination.DISPLAYLIST);
            String string3 = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.ValueError, string3);
        }
        c.addProject();
    }

    public static void SetTimeWindow(String string, String string2, String string3, String string4) {
        Project project = JythonHms.c();
        u u2 = project.control();
        if (u2 == null) {
            Object[] objectArray = new Object[]{};
            int n2 = 12587;
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.ERROR, ErrorDestination.DISPLAYLIST);
            String string5 = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.ValueError, string5);
        }
        u2.c(string);
        u2.b(string2);
        u2.e(string3);
        u2.d(string4);
    }

    public static void ComputeRun(String string) {
        bj bj2 = new bj(string, false);
        Future<?> future = hms.f.h.a(bj2);
        try {
            Object obj = future.get();
            Integer n2 = (Integer)obj;
            if (n2 != 0) {
                Object[] objectArray = new Object[]{string};
                String string2 = ErrorProcessor.getMessage(12598, objectArray);
                throw new PyException(Py.ValueError, string2);
            }
        }
        catch (ExecutionException executionException) {
            a.log(Level.WARNING, executionException, executionException::getMessage);
            Object[] objectArray = new Object[]{string};
            String string3 = ErrorProcessor.getMessage(12598, objectArray);
            throw new PyException(Py.ValueError, string3);
        }
        catch (InterruptedException interruptedException) {
            a.log(Level.WARNING, interruptedException, interruptedException::getMessage);
            Object[] objectArray = new Object[]{string};
            String string4 = ErrorProcessor.getMessage(12598, objectArray);
            throw new PyException(Py.ValueError, string4);
        }
    }

    public static void ComputeTrial(String string) {
        bv bv2 = new bv(string, false);
        Future<?> future = hms.f.h.a(bv2);
        try {
            Object obj = future.get();
            Integer n2 = (Integer)obj;
            if (n2 != 0) {
                Object[] objectArray = new Object[]{string};
                String string2 = ErrorProcessor.getMessage(12599, objectArray);
                throw new PyException(Py.ValueError, string2);
            }
        }
        catch (ExecutionException executionException) {
            a.log(Level.WARNING, executionException, executionException::getMessage);
            Object[] objectArray = new Object[]{string};
            String string3 = ErrorProcessor.getMessage(12599, objectArray);
            throw new PyException(Py.ValueError, string3);
        }
        catch (InterruptedException interruptedException) {
            a.log(Level.WARNING, interruptedException, interruptedException::getMessage);
            Object[] objectArray = new Object[]{string};
            String string4 = ErrorProcessor.getMessage(12599, objectArray);
            throw new PyException(Py.ValueError, string4);
        }
    }

    public static void ComputeForecast(String string) {
        ad ad2 = new ad(string, "", false);
        Future<?> future = hms.f.h.a(ad2);
        try {
            Object obj = future.get();
            Integer n2 = (Integer)obj;
            if (n2 != 0) {
                Object[] objectArray = new Object[]{string};
                String string2 = ErrorProcessor.getMessage(12600, objectArray);
                throw new PyException(Py.ValueError, string2);
            }
        }
        catch (ExecutionException executionException) {
            a.log(Level.WARNING, executionException, executionException::getMessage);
            Object[] objectArray = new Object[]{string};
            String string3 = ErrorProcessor.getMessage(12600, objectArray);
            throw new PyException(Py.ValueError, string3);
        }
        catch (InterruptedException interruptedException) {
            a.log(Level.WARNING, interruptedException, interruptedException::getMessage);
            Object[] objectArray = new Object[]{string};
            String string4 = ErrorProcessor.getMessage(12600, objectArray);
            throw new PyException(Py.ValueError, string4);
        }
    }

    @Deprecated
    public static void Compute(String string) {
        JythonHms.ComputeRun(string);
    }

    public static void CopyRunResults(String string, String string2, String string3) {
        int n2;
        a_0 a_02 = JythonHms.c().getRunManager().a(string);
        if (a_02 != null && (n2 = a_02.a(string2, string3)) < 0) {
            Object[] objectArray = new Object[]{string2, string3};
            int n3 = 12584;
            ErrorProcessor.notifyError(n3, objectArray, ErrorLevel.ERROR, ErrorDestination.DISPLAYLIST);
            String string4 = ErrorProcessor.getMessage(n3, objectArray);
            throw new PyException(Py.ValueError, string4);
        }
    }

    public static void CopyForecastResults(String string, String string2, String string3) {
        int n2;
        r r2 = JythonHms.c().getForecastManager().b(string);
        if (r2 != null && (n2 = r2.a(string2, string3)) < 0) {
            Object[] objectArray = new Object[]{string2, string3};
            int n3 = 12584;
            ErrorProcessor.notifyError(n3, objectArray, ErrorLevel.ERROR, ErrorDestination.DISPLAYLIST);
            String string4 = ErrorProcessor.getMessage(n3, objectArray);
            throw new PyException(Py.ValueError, string4);
        }
    }

    public static void CopyTrialResults(String string, String string2, String string3) {
        int n2;
        f f2 = JythonHms.c().getOptimizationManager().d(string);
        if (f2 != null && (n2 = f2.a(string2, string3)) < 0) {
            Object[] objectArray = new Object[]{string2, string3};
            int n3 = 12584;
            ErrorProcessor.notifyError(n3, objectArray, ErrorLevel.ERROR, ErrorDestination.DISPLAYLIST);
            String string4 = ErrorProcessor.getMessage(n3, objectArray);
            throw new PyException(Py.ValueError, string4);
        }
    }

    public static void RenameStateGridBPart(String string) {
        int n2;
        a_0 a_02 = JythonHms.d();
        if (a_02 != null && (n2 = a_02.h(string)) < 0) {
            Object[] objectArray = new Object[]{string};
            int n3 = 12589;
            ErrorProcessor.notifyError(n3, objectArray, ErrorLevel.ERROR, ErrorDestination.DISPLAYLIST);
            String string2 = ErrorProcessor.getMessage(n3, objectArray);
            throw new PyException(Py.ValueError, string2);
        }
    }

    public static void SaveAllProjectComponents() {
        Project project = JythonHms.c();
        int n2 = project.saveAll();
        if (n2 != 0) {
            int n3 = 12585;
            Object[] objectArray = null;
            ErrorProcessor.notifyError(n3, objectArray, ErrorLevel.ERROR, ErrorDestination.DISPLAYLIST);
            String string = ErrorProcessor.getMessage(n3, objectArray);
            throw new PyException(Py.ValueError, string);
        }
    }

    public static void SaveBasinModel() {
        if (e == null) {
            return;
        }
        int n2 = e.g();
        if (n2 != 0) {
            int n3 = 12574;
            Object[] objectArray = null;
            ErrorProcessor.notifyError(n3, objectArray, ErrorLevel.ERROR, ErrorDestination.DISPLAYLIST);
            String string = ErrorProcessor.getMessage(n3, objectArray);
            throw new PyException(Py.ValueError, string);
        }
    }

    public static void SaveBasinModelAs(String string) {
        if (e == null) {
            return;
        }
        Project project = JythonHms.c();
        hms.model.basin.u u2 = e.f();
        if (u2 == null) {
            int n2 = 12580;
            Object[] objectArray = new Object[]{string};
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.ERROR, ErrorDestination.DISPLAYLIST);
            String string2 = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.ValueError, string2);
        }
        e.h();
        x x2 = project.copyBasin(e, string, true);
        if (x2 == null) {
            int n3 = 12581;
            Object[] objectArray = new Object[]{string};
            ErrorProcessor.notifyError(n3, objectArray, ErrorLevel.ERROR, ErrorDestination.DISPLAYLIST);
            String string3 = ErrorProcessor.getMessage(n3, objectArray);
            throw new PyException(Py.ValueError, string3);
        }
        e = x2;
        int n4 = e.g();
        if (n4 != 0) {
            int n5 = 12574;
            Object[] objectArray = null;
            ErrorProcessor.notifyError(n5, objectArray, ErrorLevel.ERROR, ErrorDestination.DISPLAYLIST);
            String string4 = ErrorProcessor.getMessage(n5, objectArray);
            throw new PyException(Py.ValueError, string4);
        }
    }

    public static void SelectOptimizationTrial(String string) {
        Object[] objectArray = null;
        String string2 = ErrorProcessor.getMessage(12593, objectArray);
        throw new PyException(Py.ValueError, string2);
    }

    public static void SetParameterLock(String string, String string2, String string3) {
        Object[] objectArray = null;
        String string4 = ErrorProcessor.getMessage(12595, objectArray);
        throw new PyException(Py.ValueError, string4);
    }

    public static void SetPercentMissingAllowed(double d2) {
        Object[] objectArray = null;
        String string = ErrorProcessor.getMessage(12596, objectArray);
        throw new PyException(Py.ValueError, string);
    }

    public static void SetObjectiveFunctionTime(String string, String string2, String string3) {
        Object[] objectArray = null;
        String string4 = ErrorProcessor.getMessage(12594, objectArray);
        throw new PyException(Py.ValueError, string4);
    }

    @Deprecated
    public static void Optimize() {
        Object[] objectArray = null;
        String string = ErrorProcessor.getMessage(12592, objectArray);
        throw new PyException(Py.ValueError, string);
    }

    public static void UseOptimizerTrialResults(String string, String string2, int n2) {
        Object[] objectArray = null;
        String string3 = ErrorProcessor.getMessage(12597, objectArray);
        throw new PyException(Py.ValueError, string3);
    }

    private static hms.model.basin.u b() throws PyException {
        if (e == null) {
            Object[] objectArray = null;
            int n2 = 12565;
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.ERROR, ErrorDestination.DISPLAYLIST);
            String string = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.RuntimeError, string);
        }
        hms.model.basin.u u2 = e.f();
        if (u2 == null) {
            Object[] objectArray = null;
            int n3 = 12565;
            ErrorProcessor.notifyError(n3, objectArray, ErrorLevel.ERROR, ErrorDestination.DISPLAYLIST);
            String string = ErrorProcessor.getMessage(n3, objectArray);
            throw new PyException(Py.RuntimeError, string);
        }
        return u2;
    }

    private static Project c() throws PyException {
        Project project;
        if (c == null) {
            c = new ProjectManager(true);
        }
        if ((project = c.project()) == null) {
            Object[] objectArray = null;
            int n2 = 12566;
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.ERROR, ErrorDestination.DISPLAYLIST);
            String string = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.RuntimeError, string);
        }
        return project;
    }

    private static a_0 d() throws PyException {
        Project project = JythonHms.c();
        a_0 a_02 = project.getRunManager().g();
        if (a_02 == null) {
            Object[] objectArray = null;
            int n2 = 12583;
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.ERROR, ErrorDestination.DISPLAYLIST);
            String string = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.RuntimeError, string);
        }
        return a_02;
    }

    public static void SetBasinUnitSystem(String string) {
        if (!(string.equalsIgnoreCase("English") || string.equalsIgnoreCase("SI") || string.equalsIgnoreCase("Metric"))) {
            Object[] objectArray = new Object[]{string};
            int n2 = 12568;
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.ERROR, ErrorDestination.DISPLAYLIST);
            String string2 = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.ValueError, string2);
        }
        JythonHms.b().setUnitSystem(string);
    }

    public static void SetBlendMethod(String string, String string2) {
        hms.model.basin.d d2 = JythonHms.b().c(string);
        if (d2 == null) {
            Object[] objectArray = new Object[]{string};
            int n2 = 12569;
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.ERROR, ErrorDestination.DISPLAYLIST);
            String string3 = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.ValueError, string3);
        }
        c c2 = hms.model.basin.b.c.a(string2);
        if (c2.equals(hms.model.basin.b.c.UNSPECIFIED_BLEND)) {
            Object[] objectArray = new Object[]{string2, string};
            int n3 = 12570;
            ErrorProcessor.notifyError(n3, objectArray, ErrorLevel.ERROR, ErrorDestination.DISPLAYLIST);
            String string4 = ErrorProcessor.getMessage(n3, objectArray);
            throw new PyException(Py.ValueError, string4);
        }
        d2.a(c2);
    }

    public static void SetBlendMethod(String string, String string2, String string3) {
        try {
            double d2 = Double.parseDouble(string3);
            JythonHms.SetBlendMethod(string, string2, d2);
        }
        catch (NumberFormatException numberFormatException) {
            a.log(Level.WARNING, numberFormatException, numberFormatException::getMessage);
            Object[] objectArray = new Object[]{string3};
            int n2 = 12582;
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.ERROR, ErrorDestination.DISPLAYLIST);
            String string4 = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.ValueError, string4);
        }
    }

    public static void SetBlendMethod(String string, String string2, double d2) {
        a a2;
        JythonHms.SetBlendMethod(string, string2);
        hms.model.basin.d d3 = JythonHms.b().c(string);
        if (d3 != null && (a2 = d3.az()).g().equals(hms.model.basin.b.c.LINEAR_TAPER_BLEND)) {
            ((g)a2).c(new HecDouble(d2));
        }
    }

    public static void SetBaseflowValue(String string, String string2, String string3) {
        try {
            double d2 = Double.parseDouble(string3);
            JythonHms.SetBaseflowValue(string, string2, d2);
        }
        catch (NumberFormatException numberFormatException) {
            a.log(Level.WARNING, numberFormatException, numberFormatException::getMessage);
            Object[] objectArray = new Object[]{string3};
            int n2 = 12582;
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.ERROR, ErrorDestination.DISPLAYLIST);
            String string4 = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.ValueError, string4);
        }
    }

    public static void SetBaseflowValue(String string, String string2, double d2) {
        Object object;
        bp bp2 = (bp)JythonHms.b().c(string);
        if (bp2 == null) {
            Object[] objectArray = new Object[]{string};
            int n2 = 12569;
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.ERROR, ErrorDestination.DISPLAYLIST);
            String string3 = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.ValueError, string3);
        }
        HecDouble hecDouble = new HecDouble(d2);
        boolean bl2 = true;
        String string4 = v_0.a(new StringBuffer(string2));
        if (string4.equalsIgnoreCase("RecessionFactor")) {
            if (bp2.cx().equals(hms.model.basin.a.d.RECESSION) || bp2.cx().equals(hms.model.basin.a.d.BOUNDED_RECESSION)) {
                object = (Object[])bp2.cq();
                ((h_0)object).b(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("InitialBaseflow")) {
            if (bp2.cx().equals(hms.model.basin.a.d.RECESSION) || bp2.cx().equals(hms.model.basin.a.d.BOUNDED_RECESSION)) {
                object = (h_0)bp2.cq();
                ((h_0)object).c(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("Flow/AreaRatio")) {
            if (bp2.cx().equals(hms.model.basin.a.d.RECESSION) || bp2.cx().equals(hms.model.basin.a.d.BOUNDED_RECESSION)) {
                object = (h_0)bp2.cq();
                ((h_0)object).d(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("ThresholdFlow")) {
            if (bp2.cx().equals(hms.model.basin.a.d.RECESSION)) {
                object = (h_0)bp2.cq();
                ((h_0)object).e(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("FlowToPeakRatio") && bp2.cx().equals(hms.model.basin.a.d.RECESSION)) {
            object = (h_0)bp2.cq();
            ((h_0)object).f(hecDouble);
            bl2 = false;
        }
        if (bl2) {
            object = new Object[]{string2, string};
            int n3 = 12571;
            ErrorProcessor.notifyError(n3, (Object[])object, ErrorLevel.ERROR, ErrorDestination.DISPLAYLIST);
            String string5 = ErrorProcessor.getMessage(n3, (Object[])object);
            throw new PyException(Py.ValueError, string5);
        }
    }

    public static void SetLossRateValue(String string, String string2, String string3) {
        try {
            double d2 = Double.parseDouble(string3);
            JythonHms.SetLossRateValue(string, string2, d2);
        }
        catch (NumberFormatException numberFormatException) {
            a.log(Level.WARNING, numberFormatException, numberFormatException::getMessage);
            Object[] objectArray = new Object[]{string3};
            int n2 = 12582;
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.ERROR, ErrorDestination.DISPLAYLIST);
            String string4 = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.ValueError, string4);
        }
    }

    public static void SetLossRateValue(String string, String string2, double d2) {
        Object object;
        bp bp2 = (bp)JythonHms.b().c(string);
        if (bp2 == null) {
            Object[] objectArray = new Object[]{string};
            int n2 = 12569;
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.ERROR, ErrorDestination.DISPLAYLIST);
            String string3 = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.ValueError, string3);
        }
        HecDouble hecDouble = new HecDouble(d2);
        boolean bl2 = true;
        String string4 = v_0.a(new StringBuffer(string2));
        if (string4.equalsIgnoreCase("InitialLoss")) {
            if (bp2.cv().equals(ar.EXPONENTIAL)) {
                object = (h)bp2.cn();
                ((h)object).a(hecDouble);
                bl2 = false;
            } else if (bp2.cv().equals(ar.GREEN_AMPT)) {
                object = (l)bp2.cn();
                ((l)object).a(hecDouble);
                bl2 = false;
            } else if (bp2.cv().equals(ar.INITIAL_CONSTANT)) {
                object = (z_0)bp2.cn();
                ((z_0)object).a(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("MoistureDeficit")) {
            if (bp2.cv().equals(ar.GREEN_AMPT)) {
                object = (l)bp2.cn();
                ((l)object).d(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("WettingFrontSuction")) {
            if (bp2.cv().equals(ar.GREEN_AMPT)) {
                object = (l)bp2.cn();
                ((l)object).e(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("HydraulicConductivity")) {
            if (bp2.cv().equals(ar.GREEN_AMPT)) {
                object = (l)bp2.cn();
                ((l)object).g(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("ConstantLossRate")) {
            if (bp2.cv().equals(ar.INITIAL_CONSTANT)) {
                object = (z_0)bp2.cn();
                ((z_0)object).b(hecDouble);
                bl2 = false;
            } else if (bp2.cv().equals(ar.DEFICIT_CONSTANT)) {
                object = (b)bp2.cn();
                ((b)object).c(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("PercolationRate")) {
            if (bp2.cv().equals(ar.DEFICIT_CONSTANT)) {
                object = (b)bp2.cn();
                ((b)object).c(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("RecoveryFactor")) {
            if (bp2.cv().equals(ar.DEFICIT_CONSTANT)) {
                object = (b)bp2.cn();
                ((b)object).d(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("PrecipExponent")) {
            if (bp2.cv().equals(ar.EXPONENTIAL)) {
                object = (h)bp2.cn();
                ((h)object).c(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("LossCoefficientRatio")) {
            if (bp2.cv().equals(ar.EXPONENTIAL)) {
                object = (h)bp2.cn();
                ((h)object).b(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("StartLossCoefficient")) {
            if (bp2.cv().equals(ar.EXPONENTIAL)) {
                object = (h)bp2.cn();
                ((h)object).d(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("SCSCurveNumber")) {
            if (bp2.cv().equals(ar.SCS_LOSS)) {
                object = (av)bp2.cn();
                ((av)object).a(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("SCSInitialAbstraction")) {
            if (bp2.cv().equals(ar.SCS_LOSS)) {
                object = (av)bp2.cn();
                ((av)object).b(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("InitialDeficit")) {
            if (bp2.cv().equals(ar.DEFICIT_CONSTANT)) {
                object = (b)bp2.cn();
                ((b)object).a(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("MaximumDeficit")) {
            if (bp2.cv().equals(ar.DEFICIT_CONSTANT)) {
                object = (b)bp2.cn();
                ((b)object).b(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("PercentImperviousArea")) {
            object = bp2.cn();
            ((am)object).p(hecDouble);
            bl2 = false;
        }
        if (bl2) {
            object = new Object[]{string2, string};
            int n3 = 12572;
            ErrorProcessor.notifyError(n3, (Object[])object, ErrorLevel.ERROR, ErrorDestination.DISPLAYLIST);
            String string5 = ErrorProcessor.getMessage(n3, (Object[])object);
            throw new PyException(Py.ValueError, string5);
        }
    }

    public static void Exit(int n2) {
        throw new PyException(Py.SystemExit, (PyObject)new PyInteger(n2));
    }

    public static void HMSExit(int n2) {
        throw new PyException(Py.SystemExit, (PyObject)new PyInteger(n2));
    }
}

