/*
 * Decompiled with CFR 0.152.
 * 
 * Could not load the following classes:
 *  org.python.core.Py
 *  org.python.core.PyException
 *  org.python.core.PyInteger
 *  org.python.core.PyObject
 *  org.python.util.PythonInterpreter
 */
package hms.model;

import hec.heclib.util.HecDouble;
import hec.heclib.util.HecTime;
import hms.C;
import hms.ErrorDestination;
import hms.ErrorLevel;
import hms.ErrorProcessor;
import hms.a.q;
import hms.model.ProjectManager;
import hms.model.a;
import hms.model.b.Q;
import hms.model.b.an_0;
import hms.model.b.ax;
import hms.model.b.l_0;
import hms.model.b.m_0;
import hms.model.basin.V;
import hms.model.basin.a.a_0;
import hms.model.basin.a.c;
import hms.model.basin.a.f_0;
import hms.model.basin.a.h_0;
import hms.model.basin.a.t_0;
import hms.model.basin.a.u_0;
import hms.model.basin.a.z;
import hms.model.basin.ag;
import hms.model.basin.d.h;
import hms.model.basin.d.l;
import hms.model.basin.g_0;
import hms.model.m;
import java.io.File;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.List;
import java.util.Properties;
import java.util.Vector;
import org.python.core.Py;
import org.python.core.PyException;
import org.python.core.PyInteger;
import org.python.core.PyObject;
import org.python.util.PythonInterpreter;

public class JythonHms {
    private static boolean a = false;
    private static ProjectManager b = null;
    private String c;

    public JythonHms() {
    }

    public JythonHms(ProjectManager projectManager) {
        b = projectManager;
    }

    public static void setProjectManager(ProjectManager projectManager) {
        b = projectManager;
    }

    public void setScriptFileName(String string) {
        this.c = string;
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
        a = true;
    }

    public int runScript() {
        return JythonHms.runScript(this.c);
    }

    public static int runScript(String string) {
        Object[] objectArray;
        File file;
        int n2 = 0;
        if (b == null) {
            b = new ProjectManager(false);
        }
        if (!(file = new File(string)).exists()) {
            objectArray = new PythonInterpreter[]{string};
            ErrorProcessor.notifyError(12578, objectArray, ErrorLevel.d, ErrorDestination.c);
            n2 = -1;
        } else if (!file.canRead()) {
            objectArray = new Object[]{string};
            ErrorProcessor.notifyError(12579, objectArray, ErrorLevel.d, ErrorDestination.c);
            n2 = -1;
        }
        if (n2 != 0) {
            return n2;
        }
        if (!a) {
            JythonHms.a();
        }
        objectArray = new PythonInterpreter();
        try {
            objectArray.execfile(string);
        }
        catch (PyException pyException) {
            if (pyException.type.equals((Object)Py.SystemExit)) {
                Object[] objectArray2 = new Object[]{string, "0"};
                ErrorProcessor.notifyError(12573, objectArray2, ErrorLevel.b, ErrorDestination.c);
                n2 = 0;
            }
            Object[] objectArray3 = new Object[]{string};
            ErrorProcessor.notifyError(12550, objectArray3, ErrorLevel.d, ErrorDestination.c);
            pyException.printStackTrace();
            n2 = -1;
        }
        return n2;
    }

    public static void OpenBasinModel(String string) {
        V v2 = JythonHms.c().n(string);
        if (v2 == null) {
            Object[] objectArray = new Object[]{string};
            int n2 = 12551;
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string2 = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.ValueError, string2);
        }
    }

    public static void OpenProject(String string, String string2) {
        HashMap hashMap = new HashMap();
        m m2 = b.openProject(string, string2, "", hashMap);
        if (m2 == null) {
            Object[] objectArray = new Object[]{string};
            int n2 = 12552;
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string3 = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.ValueError, string3);
        }
        b.addProject();
    }

    public static void Compute(String string) {
        m m2;
        int n2;
        if (ErrorProcessor.numberOfMessages() > 0) {
            ErrorProcessor.clearMessageList();
        }
        if ((n2 = (m2 = JythonHms.c()).b(string, m.x)) >= 0) {
            n2 = m2.j(true);
        }
        if (n2 < 0) {
            Object[] objectArray = new Object[]{string};
            int n3 = 12553;
            ErrorProcessor.notifyError(n3, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string2 = ErrorProcessor.getMessage(n3, objectArray);
            throw new PyException(Py.ValueError, string2);
        }
    }

    public static void MoveResults(String string, String string2) {
        ax ax2 = JythonHms.d();
        int n2 = ax2.a(string, string2);
        if (n2 < 0) {
            Object[] objectArray = new Object[]{string, string2};
            int n3 = 12584;
            ErrorProcessor.notifyError(n3, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string3 = ErrorProcessor.getMessage(n3, objectArray);
            throw new PyException(Py.ValueError, string3);
        }
    }

    public static void SaveAllProjectComponents() {
        m m2 = JythonHms.c();
        int n2 = m2.T();
        if (n2 != 0) {
            int n3 = 12585;
            Object[] objectArray = null;
            ErrorProcessor.notifyError(n3, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string = ErrorProcessor.getMessage(n3, objectArray);
            throw new PyException(Py.ValueError, string);
        }
    }

    public static void SaveBasinModel() {
        m m2 = JythonHms.c();
        int n2 = m2.L();
        if (n2 != 0) {
            int n3 = 12574;
            Object[] objectArray = null;
            ErrorProcessor.notifyError(n3, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string = ErrorProcessor.getMessage(n3, objectArray);
            throw new PyException(Py.ValueError, string);
        }
    }

    public static void SaveBasinModelAs(String string) {
        m m2 = JythonHms.c();
        V v2 = m2.x();
        if (v2 == null) {
            int n2 = 12580;
            Object[] objectArray = new Object[]{string};
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string2 = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.ValueError, string2);
        }
        V v3 = m2.b(string, true);
        if (v3 == null) {
            int n3 = 12581;
            Object[] objectArray = new Object[]{string};
            ErrorProcessor.notifyError(n3, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string3 = ErrorProcessor.getMessage(n3, objectArray);
            throw new PyException(Py.ValueError, string3);
        }
        int n4 = m2.L();
        if (n4 != 0) {
            int n5 = 12574;
            Object[] objectArray = null;
            ErrorProcessor.notifyError(n5, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string4 = ErrorProcessor.getMessage(n5, objectArray);
            throw new PyException(Py.ValueError, string4);
        }
    }

    public static void SelectOptimizationTrial(String string, String string2, int n2) {
        an_0 an_02 = JythonHms.e();
        List list = an_02.g().b();
        int n3 = list.size();
        m_0 m_02 = null;
        int n4 = 0;
        while (n4 < n3) {
            m_02 = (m_0)list.get(n4);
            String string3 = String.valueOf(string) + "_" + Integer.toString(n2);
            if (m_02.j().equalsIgnoreCase(string) && m_02.i().equalsIgnoreCase(string2) && m_02.g().equalsIgnoreCase(string3)) {
                an_02.a(m_02);
                break;
            }
            m_02 = null;
            ++n4;
        }
        if (m_02 == null) {
            Object[] objectArray = new Object[]{string, string2, Integer.toString(n2)};
            int n5 = 12575;
            ErrorProcessor.notifyError(n5, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string4 = ErrorProcessor.getMessage(n5, objectArray);
            throw new PyException(Py.ValueError, string4);
        }
    }

    public static void SelectOptimizationTrial(String string) {
        an_0 an_02 = JythonHms.e();
        List list = an_02.g().b();
        int n2 = list.size();
        m_0 m_02 = null;
        int n3 = 0;
        while (n3 < n2) {
            m_02 = (m_0)list.get(n3);
            if (m_02.g().equalsIgnoreCase(string)) {
                an_02.a(m_02);
                break;
            }
            m_02 = null;
            ++n3;
        }
        if (m_02 == null) {
            Object[] objectArray = new Object[]{string};
            int n4 = 12577;
            ErrorProcessor.notifyError(n4, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string2 = ErrorProcessor.getMessage(n4, objectArray);
            throw new PyException(Py.ValueError, string2);
        }
    }

    public static void SetParameterLock(String string, String string2, String string3) {
        l_0 l_02 = JythonHms.e().h();
        if (l_02 == null) {
            Object[] objectArray = null;
            int n2 = 12557;
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string4 = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.RuntimeError, string4);
        }
        Vector vector = l_02.r();
        int n3 = vector.size();
        boolean bl2 = false;
        int n4 = 0;
        while (n4 < n3) {
            Q q2 = (Q)vector.get(n4);
            if (q2.b().equalsIgnoreCase(string) && q2.d().equalsIgnoreCase(string2)) {
                bl2 = true;
                if (string3.equalsIgnoreCase("yes")) {
                    q2.b(true);
                    break;
                }
                q2.b(false);
                break;
            }
            ++n4;
        }
        if (!bl2) {
            Object[] objectArray = new Object[2];
            objectArray[0] = string2;
            objectArray[0] = string;
            int n5 = 12558;
            ErrorProcessor.notifyError(n5, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string5 = ErrorProcessor.getMessage(n5, objectArray);
            throw new PyException(Py.ValueError, string5);
        }
    }

    public static void SetPercentMissingAllowed(double d2) {
        l_0 l_02 = JythonHms.e().h();
        if (l_02 == null) {
            Object[] objectArray = null;
            int n2 = 12557;
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.RuntimeError, string);
        }
        l_02.a(new HecDouble(d2));
    }

    public static void SetObjectiveFunctionTime(String string, String string2, String string3) {
        an_0 an_02 = JythonHms.e();
        l_0 l_02 = an_02.h();
        if (l_02 == null) {
            Object[] objectArray = null;
            int n2 = 12557;
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string4 = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.RuntimeError, string4);
        }
        int n3 = 0;
        HecTime hecTime = new HecTime();
        n3 = hecTime.setDate(string2);
        if (n3 != 0) {
            Object[] objectArray = new Object[]{string2};
            int n4 = 12560;
            ErrorProcessor.notifyError(n4, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string5 = ErrorProcessor.getMessage(n4, objectArray);
            throw new PyException(Py.ValueError, string5);
        }
        n3 = hecTime.setTime(string3);
        if (n3 != 0) {
            Object[] objectArray = new Object[]{string3};
            int n5 = 12561;
            ErrorProcessor.notifyError(n5, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string6 = ErrorProcessor.getMessage(n5, objectArray);
            throw new PyException(Py.ValueError, string6);
        }
        if (string.equalsIgnoreCase("start")) {
            l_02.i(string2);
            l_02.j(string3);
        } else if (string.equalsIgnoreCase("end")) {
            l_02.k(string2);
            l_02.l(string3);
        } else {
            Object[] objectArray = new Object[]{string};
            int n6 = 12559;
            ErrorProcessor.notifyError(n6, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string7 = ErrorProcessor.getMessage(n6, objectArray);
            throw new PyException(Py.ValueError, string7);
        }
    }

    public static void Optimize(String string, String string2, int n2) {
        if (ErrorProcessor.numberOfMessages() > 0) {
            ErrorProcessor.clearMessageList();
        }
        int n3 = 0;
        an_0 an_02 = JythonHms.e();
        List list = an_02.g().b();
        int n4 = list.size();
        int n5 = 0;
        while (n5 < n4) {
            m_0 m_02 = (m_0)list.get(n5);
            String string3 = String.valueOf(string) + "_" + Integer.toString(n2);
            if (m_02.j().equalsIgnoreCase(string) && m_02.i().equalsIgnoreCase(string2) && m_02.g().equalsIgnoreCase(string3)) {
                an_02.a(m_02);
                n3 = 0;
                break;
            }
            n3 = -1;
            ++n5;
        }
        if (n3 >= 0) {
            n3 = an_02.d(true);
        }
        if (n3 < 0) {
            Object[] objectArray = new Object[]{string, string2, Integer.toString(n2)};
            int n6 = 12562;
            ErrorProcessor.notifyError(n6, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string4 = ErrorProcessor.getMessage(n6, objectArray);
            throw new PyException(Py.RuntimeError, string4);
        }
    }

    public static void Optimize() {
        an_0 an_02;
        int n2;
        if (ErrorProcessor.numberOfMessages() > 0) {
            ErrorProcessor.clearMessageList();
        }
        if ((n2 = (an_02 = JythonHms.e()).d(true)) < 0) {
            Object[] objectArray = new Object[1];
            m_0 m_02 = an_02.d();
            objectArray[0] = m_02.g();
            int n3 = 12576;
            ErrorProcessor.notifyError(n3, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string = ErrorProcessor.getMessage(n3, objectArray);
            throw new PyException(Py.RuntimeError, string);
        }
    }

    public static void UseOptimizerTrialResults(String string, String string2, int n2) {
        Object object;
        int n3 = 0;
        an_0 an_02 = JythonHms.e();
        List list = an_02.g().b();
        int n4 = list.size();
        if (n4 == 0) {
            n3 = -1;
        }
        int n5 = 0;
        while (n5 < n4) {
            m_0 m_02 = (m_0)list.get(n5);
            object = String.valueOf(string) + "_" + Integer.toString(n2);
            if (m_02.j().equalsIgnoreCase(string) && m_02.i().equalsIgnoreCase(string2) && m_02.g().equalsIgnoreCase((String)object)) {
                an_02.a(m_02);
                n3 = 0;
                break;
            }
            n3 = -1;
            ++n5;
        }
        if (n3 < 0) {
            Object[] objectArray = new Object[]{string, string2, Integer.toString(n2)};
            int n6 = 12563;
            ErrorProcessor.notifyError(n6, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string3 = ErrorProcessor.getMessage(n6, objectArray);
            throw new PyException(Py.ValueError, string3);
        }
        l_0 l_02 = an_02.h();
        object = JythonHms.b();
        Vector vector = l_02.r();
        int n7 = vector.size();
        int n8 = 0;
        while (n8 < n7) {
            Q q2 = (Q)vector.get(n8);
            if (q2.u().a()) {
                Object[] objectArray;
                Q q3 = new Q(((V)object).a());
                ag ag2 = ((V)object).d(q2.b());
                if (ag2 != null) {
                    q3.a(ag2);
                    n3 = q3.a(q2.d(), false);
                    if (n3 == 0) {
                        objectArray = new C(q3.r());
                        objectArray.a(q2.u());
                        q3.a((C)objectArray);
                    }
                } else {
                    objectArray = new Object[]{q2.c(), ((a)object).l()};
                    int n9 = 12564;
                    ErrorProcessor.notifyError(n9, objectArray, ErrorLevel.d, ErrorDestination.c);
                    String string4 = ErrorProcessor.getMessage(n9, objectArray);
                    throw new PyException(Py.RuntimeError, string4);
                }
            }
            ++n8;
        }
    }

    private static V b() {
        V v2 = JythonHms.c().x();
        if (v2 == null) {
            Object[] objectArray = null;
            int n2 = 12565;
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.RuntimeError, string);
        }
        return v2;
    }

    private static m c() {
        m m2;
        if (b == null) {
            b = new ProjectManager(true);
        }
        if ((m2 = b.project()) == null) {
            Object[] objectArray = null;
            int n2 = 12566;
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.RuntimeError, string);
        }
        return m2;
    }

    private static ax d() {
        m m2 = JythonHms.c();
        ax ax2 = m2.B();
        if (ax2 == null) {
            Object[] objectArray = null;
            int n2 = 12583;
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.RuntimeError, string);
        }
        return ax2;
    }

    private static an_0 e() {
        m m2 = JythonHms.c();
        an_0 an_02 = m2.W();
        if (an_02 == null) {
            Object[] objectArray = new Object[]{m2.l()};
            int n2 = 12567;
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.RuntimeError, string);
        }
        return an_02;
    }

    public static void SetBasinUnitSystem(String string) {
        if (!(string.equalsIgnoreCase("English") || string.equalsIgnoreCase("SI") || string.equalsIgnoreCase("Metric"))) {
            Object[] objectArray = new Object[]{string};
            int n2 = 12568;
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string2 = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.ValueError, string2);
        }
        JythonHms.b().i(string);
    }

    public static void SetBlendMethod(String string, String string2) {
        ag ag2 = JythonHms.b().d(string);
        if (ag2 == null) {
            Object[] objectArray = new Object[]{string};
            int n2 = 12569;
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string3 = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.ValueError, string3);
        }
        g_0 g_02 = g_0.a(string2);
        if (g_02.equals(g_0.a)) {
            Object[] objectArray = new Object[]{string2, string};
            int n3 = 12570;
            ErrorProcessor.notifyError(n3, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string4 = ErrorProcessor.getMessage(n3, objectArray);
            throw new PyException(Py.ValueError, string4);
        }
        ag2.a(g_02);
    }

    public static void SetBlendMethod(String string, String string2, String string3) {
        try {
            double d2 = Double.parseDouble(string3);
            JythonHms.SetBlendMethod(string, string2, d2);
        }
        catch (NumberFormatException numberFormatException) {
            Object[] objectArray = new Object[]{string3};
            int n2 = 12582;
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string4 = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.ValueError, string4);
        }
    }

    public static void SetBlendMethod(String string, String string2, double d2) {
        JythonHms.SetBlendMethod(string, string2);
        ag ag2 = JythonHms.b().d(string);
        if (ag2 != null && ag2.aZ().equals(g_0.d)) {
            ag2.ba().a(new HecDouble(d2));
        }
    }

    public static void SetBaseflowValue(String string, String string2, String string3) {
        try {
            double d2 = Double.parseDouble(string3);
            JythonHms.SetBaseflowValue(string, string2, d2);
        }
        catch (NumberFormatException numberFormatException) {
            Object[] objectArray = new Object[]{string3};
            int n2 = 12582;
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string4 = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.ValueError, string4);
        }
    }

    public static void SetBaseflowValue(String string, String string2, double d2) {
        Object object;
        hms.model.basin.l l2 = (hms.model.basin.l)JythonHms.b().d(string);
        if (l2 == null) {
            Object[] objectArray = new Object[]{string};
            int n2 = 12569;
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string3 = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.ValueError, string3);
        }
        HecDouble hecDouble = new HecDouble(d2);
        boolean bl2 = true;
        String string4 = q.a(new StringBuffer(string2));
        if (string4.equalsIgnoreCase("RecessionFactor")) {
            if (l2.y().equals(h.c) || l2.y().equals(h.f)) {
                object = (Object[])l2.s();
                ((l)object).a(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("InitialBaseflow")) {
            if (l2.y().equals(h.c) || l2.y().equals(h.f)) {
                object = (l)l2.s();
                ((l)object).b(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("Flow/AreaRatio")) {
            if (l2.y().equals(h.c) || l2.y().equals(h.f)) {
                object = (l)l2.s();
                ((l)object).c(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("ThresholdFlow")) {
            if (l2.y().equals(h.c)) {
                object = (l)l2.s();
                ((l)object).d(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("FlowToPeakRatio") && l2.y().equals(h.c)) {
            object = (l)l2.s();
            ((l)object).e(hecDouble);
            bl2 = false;
        }
        if (bl2) {
            object = new Object[]{string2, string};
            int n3 = 12571;
            ErrorProcessor.notifyError(n3, (Object[])object, ErrorLevel.d, ErrorDestination.c);
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
            Object[] objectArray = new Object[]{string3};
            int n2 = 12582;
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string4 = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.ValueError, string4);
        }
    }

    public static void SetLossRateValue(String string, String string2, double d2) {
        Object object;
        hms.model.basin.l l2 = (hms.model.basin.l)JythonHms.b().d(string);
        if (l2 == null) {
            Object[] objectArray = new Object[]{string};
            int n2 = 12569;
            ErrorProcessor.notifyError(n2, objectArray, ErrorLevel.d, ErrorDestination.c);
            String string3 = ErrorProcessor.getMessage(n2, objectArray);
            throw new PyException(Py.ValueError, string3);
        }
        HecDouble hecDouble = new HecDouble(d2);
        boolean bl2 = true;
        String string4 = q.a(new StringBuffer(string2));
        if (string4.equalsIgnoreCase("InitialLoss")) {
            if (l2.w().equals(f_0.d)) {
                object = (t_0)l2.p();
                ((t_0)object).a(hecDouble);
                bl2 = false;
            } else if (l2.w().equals(f_0.e)) {
                object = (a_0)l2.p();
                ((a_0)object).a(hecDouble);
                bl2 = false;
            } else if (l2.w().equals(f_0.i)) {
                object = (z)l2.p();
                ((z)object).a(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("MoistureDeficit")) {
            if (l2.w().equals(f_0.e)) {
                object = (a_0)l2.p();
                ((a_0)object).b(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("WettingFrontSuction")) {
            if (l2.w().equals(f_0.e)) {
                object = (a_0)l2.p();
                ((a_0)object).c(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("HydraulicConductivity")) {
            if (l2.w().equals(f_0.e)) {
                object = (a_0)l2.p();
                ((a_0)object).d(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("ConstantLossRate")) {
            if (l2.w().equals(f_0.i)) {
                object = (z)l2.p();
                ((z)object).b(hecDouble);
                bl2 = false;
            } else if (l2.w().equals(f_0.c)) {
                object = (h_0)l2.p();
                ((h_0)object).c(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("RecoveryFactor")) {
            if (l2.w().equals(f_0.c)) {
                object = (h_0)l2.p();
                ((h_0)object).d(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("PrecipExponent")) {
            if (l2.w().equals(f_0.d)) {
                object = (t_0)l2.p();
                ((t_0)object).c(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("LossCoefficientRatio")) {
            if (l2.w().equals(f_0.d)) {
                object = (t_0)l2.p();
                ((t_0)object).b(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("StartLossCoefficient")) {
            if (l2.w().equals(f_0.d)) {
                object = (t_0)l2.p();
                ((t_0)object).d(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("SCSCurveNumber")) {
            if (l2.w().equals(f_0.k)) {
                object = (u_0)l2.p();
                ((u_0)object).a(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("SCSInitialAbstraction")) {
            if (l2.w().equals(f_0.k)) {
                object = (u_0)l2.p();
                ((u_0)object).b(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("InitialDeficit")) {
            if (l2.w().equals(f_0.c)) {
                object = (h_0)l2.p();
                ((h_0)object).a(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("MaximumDeficit")) {
            if (l2.w().equals(f_0.c)) {
                object = (h_0)l2.p();
                ((h_0)object).b(hecDouble);
                bl2 = false;
            }
        } else if (string4.equalsIgnoreCase("PercentImperviousArea")) {
            object = l2.p();
            ((c)object).e(hecDouble);
            bl2 = false;
        }
        if (bl2) {
            object = new Object[]{string2, string};
            int n3 = 12572;
            ErrorProcessor.notifyError(n3, (Object[])object, ErrorLevel.d, ErrorDestination.c);
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

