/*
 * Decompiled with CFR 0.152.
 */
package hms;

import hec.appInterface.Application;
import hec.appInterface.ApplicationFrame;
import hec.appInterface.ApplicationModule;
import hec.appInterface.ToolBarButtonManager;
import hec.appInterface.Workspace;
import hec.io.Identifier;
import hec.lang.NamedType;
import hec.map.LocalPt;
import hec.map.MapGlyph;
import hms.ErrorDestination;
import hms.ErrorLevel;
import hms.ErrorProcessor;
import hms.a.a;
import hms.a.e;
import hms.a.q;
import hms.b;
import hms.gui.g;
import hms.gui.gs_0;
import hms.h_0;
import hms.i;
import hms.j_0;
import hms.l_0;
import hms.m;
import hms.model.JythonHms;
import hms.model.ProjectManager;
import hms.model.b.ac_0;
import hms.model.data.S;
import hms.n;
import hms.o;
import hms.p;
import hms.r;
import hms.s;
import hms.t;
import java.awt.Container;
import java.awt.Frame;
import java.awt.GridLayout;
import java.awt.event.ActionEvent;
import java.util.HashMap;
import java.util.HashSet;
import java.util.concurrent.Callable;
import javax.swing.JButton;
import javax.swing.JFrame;
import javax.swing.SwingUtilities;
import javax.swing.UIManager;
import javax.swing.UnsupportedLookAndFeelException;

public class Hms
implements Application,
ApplicationModule {
    protected static g a;
    protected static h_0 b;
    protected static ProjectManager c;
    protected static boolean d;
    protected static boolean e;

    static {
        System.loadLibrary("jniLibHydro");
    }

    public Hms(boolean bl2) {
        a = null;
        b = new h_0();
        d = bl2;
        e = false;
        hms.a.a.a();
        j_0.a();
        i.a();
        try {
            UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
        }
        catch (ClassNotFoundException classNotFoundException) {
        }
        catch (InstantiationException instantiationException) {
        }
        catch (IllegalAccessException illegalAccessException) {
        }
        catch (UnsupportedLookAndFeelException unsupportedLookAndFeelException) {
            // empty catch block
        }
        new hms.a(this);
        c = new ProjectManager(false);
        if (!d) {
            int n2 = Integer.parseInt(hms.b.a());
            if (c.programSettings().e() < n2) {
                c.programSettings().b(false);
            }
            if (!c.programSettings().f()) {
                Hms hms = this;
                SwingUtilities.invokeLater(new o(this, hms));
            } else {
                c.programSettings().b(true);
                Hms.launchInterface();
                if (c.programSettings().d()) {
                    Object object;
                    String string = "";
                    String string2 = "";
                    String string3 = "";
                    if (c.recentProjectList().size() > 0) {
                        object = (ac_0)c.recentProjectList().get(0);
                        string = ((ac_0)object).a();
                        string3 = ((ac_0)object).b();
                        string2 = q.f(((ac_0)object).c());
                    } else if (c.projectList().size() > 0) {
                        object = (ac_0)c.projectList().get(0);
                        string = ((ac_0)object).a();
                        string3 = ((ac_0)object).b();
                        string2 = q.f(((ac_0)object).c());
                    }
                    if (string.length() > 0 && string2.length() > 0) {
                        Object object2;
                        object = S.a(string, string2);
                        HashMap<String, String> hashMap = new HashMap<String, String>();
                        if (((HashSet)object).size() > 0) {
                            object2 = ((HashSet)object).iterator();
                            while (object2.hasNext()) {
                                String string4 = (String)object2.next();
                                gs_0 gs_02 = new gs_0((Frame)a, string, string4);
                                gs_02.a(false);
                                String string5 = gs_02.a();
                                if (string5.length() <= 0) continue;
                                hashMap.put(string4, string5);
                            }
                        }
                        object2 = new hms.a.a.p(string, string2, string3, hashMap);
                        hms.a.e.a((Callable)object2);
                    }
                }
            }
        }
    }

    public static boolean launchInterface() {
        if (c != null && !e) {
            c.programSettings().b(true);
            a = new g(c);
            a.a();
            e = true;
            return true;
        }
        return false;
    }

    public static void shutdownInterface() {
        a.setVisible(false);
        e = false;
        if (d) {
            a.a(false);
        } else {
            a.a(true);
        }
        a.dispose();
        a = null;
        if (!d) {
            Hms.shutdownEngine();
        }
    }

    public static void shutdownEngine() {
        System.exit(0);
    }

    public static void launchDebug() {
        JButton jButton = new JButton();
        if (a == null) {
            jButton.setText("Start Interface");
        } else {
            jButton.setText("Stop Interface");
        }
        jButton.addActionListener(new p());
        JButton jButton2 = new JButton("Test 1");
        jButton2.addActionListener(new s());
        JButton jButton3 = new JButton("Test 2");
        jButton3.addActionListener(new t());
        JButton jButton4 = new JButton("Test 3");
        jButton4.addActionListener(new hms.q());
        JButton jButton5 = new JButton("Test 4");
        jButton5.addActionListener(new r());
        JButton jButton6 = new JButton("Test 5");
        jButton6.addActionListener(new m());
        JButton jButton7 = new JButton("Test 6");
        jButton7.addActionListener(new l_0());
        JFrame jFrame = new JFrame();
        jFrame.setDefaultCloseOperation(0);
        jFrame.addWindowListener(new n());
        Container container = jFrame.getContentPane();
        container.setLayout(new GridLayout(7, 1));
        container.add(jButton);
        container.add(jButton2);
        container.add(jButton3);
        container.add(jButton4);
        container.add(jButton5);
        container.add(jButton6);
        container.add(jButton7);
        jFrame.pack();
        jFrame.setVisible(true);
    }

    public static g hmsFrame() {
        return a;
    }

    public static ProjectManager hmsEngine() {
        return c;
    }

    @Override
    public Workspace getWorkspace() {
        return b;
    }

    public static h_0 getHmsWorkspace() {
        return b;
    }

    @Override
    public ApplicationFrame getFrame() {
        return a;
    }

    @Override
    public String getUser() {
        return new String("hmsUser");
    }

    @Override
    public String getAppType() {
        return new String("HMS");
    }

    @Override
    public int getClientUnitSystem() {
        return 2;
    }

    @Override
    public Identifier downLoadParameterFile() {
        return null;
    }

    @Override
    public Identifier downLoadUnitsFile() {
        return null;
    }

    @Override
    public void postError(String string, String string2) {
    }

    @Override
    public boolean isNetworked() {
        return false;
    }

    @Override
    public String getWorkingDir() {
        if (S.c() != null) {
            return S.c().D();
        }
        return null;
    }

    @Override
    public String getApplicationProperty(String string) {
        return null;
    }

    public static void main(String[] stringArray) {
        boolean bl2 = false;
        boolean bl3 = false;
        String string = null;
        int n2 = 0;
        while (n2 < stringArray.length) {
            if (stringArray[n2].compareTo("-d") == 0) {
                bl3 = true;
            } else if (stringArray[n2].compareTo("-debug") == 0) {
                bl3 = true;
            } else if (stringArray[n2].compareTo("-l") == 0) {
                bl2 = true;
            } else if (stringArray[n2].compareTo("-lite") == 0) {
                bl2 = true;
            } else if (stringArray[n2].compareTo("-s") == 0) {
                string = stringArray[++n2];
            } else if (stringArray[n2].compareTo("-script") == 0) {
                string = stringArray[++n2];
            }
            ++n2;
        }
        if (string != null && string.length() > 0) {
            j_0.a();
            String string2 = "HEC-HMS";
            string2 = string2.concat(" " + hms.b.a(3));
            if (hms.b.b().length() > 0) {
                string2 = string2.concat(" " + hms.b.b());
            }
            string2 = string2.concat(" " + hms.b.c());
            ErrorProcessor.notifyError("Begin " + string2, ErrorLevel.a, ErrorDestination.c);
            Object[] objectArray = new Object[]{string};
            ErrorProcessor.notifyError(14650, objectArray, ErrorLevel.b, ErrorDestination.c);
            int n3 = JythonHms.runScript(string);
            String string3 = "End " + string2 + "; Exit status = " + Integer.toString(n3);
            ErrorProcessor.notifyError(string3, ErrorLevel.a, ErrorDestination.c);
            System.exit(n3);
        }
        new Hms(bl2);
        if (bl3) {
            Hms.launchDebug();
            S.a(true);
        }
    }

    public String getName() {
        return "HMS";
    }

    @Override
    public boolean hasWriteLock(MapGlyph mapGlyph) {
        return true;
    }

    @Override
    public ToolBarButtonManager getToolBarButtonManager() {
        return null;
    }

    public boolean objectPopupMenu(NamedType[] namedTypeArray, LocalPt localPt) {
        return true;
    }

    @Override
    public boolean objectPopupMenu(NamedType namedType, LocalPt localPt) {
        return true;
    }

    @Override
    public boolean objectDoubleClick(NamedType namedType, LocalPt localPt) {
        return true;
    }

    @Override
    public void actionPerformed(ActionEvent actionEvent) {
    }
}

