/*
 * Decompiled with CFR 0.152.
 * 
 * Could not load the following classes:
 *  hec.appInterface.Application
 *  hec.appInterface.ApplicationFrame
 *  hec.appInterface.ApplicationModule
 *  hec.appInterface.ToolBarButtonManager
 *  hec.appInterface.Workspace
 *  hec.heclib.util.HecTime
 *  hec.io.Identifier
 *  hec.lang.NamedType
 *  hec.map.LocalPt
 *  hec.map.MapGlyph
 *  hec.map.appInterface.MapApplicationModule
 *  hec.map.appInterface.MapWorkspace
 */
package hms;

import hec.appInterface.Application;
import hec.appInterface.ApplicationFrame;
import hec.appInterface.ApplicationModule;
import hec.appInterface.ToolBarButtonManager;
import hec.appInterface.Workspace;
import hec.heclib.util.HecTime;
import hec.io.Identifier;
import hec.lang.NamedType;
import hec.map.LocalPt;
import hec.map.MapGlyph;
import hec.map.appInterface.MapApplicationModule;
import hec.map.appInterface.MapWorkspace;
import hms.ErrorDestination;
import hms.ErrorLevel;
import hms.ErrorProcessor;
import hms.a_0;
import hms.b_0;
import hms.c_0;
import hms.command.HmsCommandServerImpl;
import hms.e_0;
import hms.f.g_0;
import hms.f.v;
import hms.gui.UpdateAvailableDialog;
import hms.gui.bz_0;
import hms.gui.h.i_0;
import hms.gui.k.z_0;
import hms.m;
import hms.model.JythonHms;
import hms.model.ProjectManager;
import hms.model.data.h;
import hms.model.o_0;
import hms.model.project.e;
import hms.n;
import hms.p_0;
import hms.s_0;
import hms.w_0;
import java.awt.Dimension;
import java.awt.Point;
import java.awt.event.ActionEvent;
import java.rmi.RemoteException;
import java.util.logging.LogManager;
import javax.swing.JWindow;

public class Hms
implements Application,
ApplicationModule,
MapApplicationModule {
    protected static bz_0 a;
    protected static z_0 b;
    protected static b_0 c;
    protected static ProjectManager d;
    protected static boolean e;
    protected static boolean f;

    public Hms(boolean bl2, boolean bl3) {
        b = null;
        c = new b_0();
        e = bl2;
        f = false;
        w_0.a();
        s_0.a();
        if (!e) {
            c_0.a();
            if (bl3) {
                g_0.a();
            } else {
                g_0.b();
            }
        } else {
            ErrorProcessor.setShowPopups(false);
        }
        new n(this);
        d = new ProjectManager(false);
        a = new bz_0();
        if (!e) {
            int n2 = Integer.parseInt(a_0.a());
            if (d.programSettings().r() < n2) {
                d.programSettings().d(false);
                d.programSettings().c(false);
            }
            if (a_0.e().matches("(?i).*(alpha|beta).*") && !d.programSettings().t()) {
                new p_0();
            }
            if (!d.programSettings().u()) {
                new e_0();
            } else {
                d.programSettings().d(true);
                Hms.launchInterface(false);
                if (d.programSettings().q()) {
                    Object object;
                    String string = "";
                    if (d.recentProjectList().size() > 0) {
                        object = d.recentProjectList().get(0);
                        string = ((e)object).c();
                    } else if (d.projectList().size() > 0) {
                        object = d.projectList().get(0);
                        string = ((e)object).c();
                    }
                    if (string.length() > 0) {
                        object = new o_0();
                        ((o_0)object).a(Hms.hmsFrame(), string);
                    }
                }
            }
        }
    }

    public static boolean launchInterface(boolean bl2) {
        if (d != null && !f) {
            v.a();
            d.programSettings().d(true);
            b = new z_0(d);
            JWindow jWindow = null;
            if (bl2) {
                i_0 i_02 = new i_0("hms.images/splash3.jpg");
                jWindow = new JWindow();
                jWindow.add(i_02);
                jWindow.setAlwaysOnTop(true);
                jWindow.setSize(570, 380);
                Point point = b.az();
                Dimension dimension = b.ay();
                int n2 = point.x + dimension.width / 2 - 285;
                int n3 = point.y + dimension.height / 2 - 190;
                jWindow.setLocation(n2, n3);
                jWindow.setVisible(true);
                try {
                    Thread.sleep(2500L);
                }
                catch (InterruptedException interruptedException) {
                    // empty catch block
                }
            }
            b.e();
            f = true;
            ErrorProcessor.setShowPopups(true);
            if (bl2) {
                try {
                    Thread.sleep(2500L);
                }
                catch (InterruptedException interruptedException) {
                    // empty catch block
                }
                jWindow.dispose();
            }
            new UpdateAvailableDialog();
            return true;
        }
        return false;
    }

    public static void shutdownInterface() {
        f = false;
        if (e) {
            b.g(false);
        } else {
            b.g(true);
        }
        b = null;
        ErrorProcessor.setShowPopups(false);
        if (!e) {
            Hms.shutdownEngine();
        }
    }

    public static void shutdownEngine() {
        System.exit(0);
    }

    public static bz_0 hmsDialogManager() {
        return a;
    }

    public static z_0 hmsFrame() {
        return b;
    }

    public static synchronized ProjectManager hmsEngine() {
        if (d == null) {
            Hms.refreshManager();
        }
        return d;
    }

    public Workspace getWorkspace() {
        return c;
    }

    public MapWorkspace getMapWorkspace() {
        return c;
    }

    public static b_0 getHmsWorkspace() {
        return c;
    }

    public static void refreshManager() {
        d = new ProjectManager(false);
    }

    public ApplicationFrame getFrame() {
        return b;
    }

    public String getUser() {
        return new String("hmsUser");
    }

    public String getAppType() {
        return new String("HMS");
    }

    public int getClientUnitSystem() {
        return 2;
    }

    public Identifier downLoadParameterFile() {
        return null;
    }

    public Identifier downLoadUnitsFile() {
        return null;
    }

    public void postError(String string, String string2) {
    }

    public boolean isNetworked() {
        return false;
    }

    public String getWorkingDir() {
        if (h.d() != null) {
            return h.d().projectDirectory();
        }
        return null;
    }

    public String getApplicationProperty(String string) {
        return null;
    }

    public static void main(String[] stringArray) {
        Object object;
        boolean bl2 = false;
        boolean bl3 = true;
        boolean bl4 = false;
        String string = null;
        int n2 = 0;
        boolean bl5 = false;
        for (int i2 = 0; i2 < stringArray.length; ++i2) {
            if (stringArray[i2].compareTo("-d") == 0) {
                bl4 = true;
                continue;
            }
            if (stringArray[i2].compareTo("-debug") == 0) {
                bl4 = true;
                continue;
            }
            if (stringArray[i2].compareTo("-l") == 0) {
                bl2 = true;
                continue;
            }
            if (stringArray[i2].compareTo("-lite") == 0) {
                bl2 = true;
                continue;
            }
            if (stringArray[i2].compareTo("CommandServer") == 0) {
                bl5 = true;
                continue;
            }
            if (stringArray[i2].startsWith("port=")) {
                object = stringArray[i2].substring(5).trim();
                n2 = Integer.parseInt((String)object);
                continue;
            }
            if (stringArray[i2].compareTo("-s") == 0) {
                string = stringArray[++i2];
                continue;
            }
            if (stringArray[i2].compareTo("-script") == 0) {
                string = stringArray[++i2];
                continue;
            }
            if (stringArray[i2].compareTo("-disableprint") == 0) {
                bl3 = false;
                continue;
            }
            if (stringArray[i2].compareTo("-info") != 0) continue;
            object = "Version: " + a_0.e();
            object = ((String)object).concat("   Build: " + a_0.a());
            object = ((String)object).concat("   Date: " + a_0.d());
            System.out.println((String)object);
            return;
        }
        if (string != null && string.length() > 0) {
            w_0.a();
            s_0.a();
            if (bl4) {
                h.a(true);
            }
            String string2 = "HEC-HMS";
            string2 = string2.concat(" " + a_0.a(3));
            if (a_0.b().length() > 0) {
                string2 = string2.concat(" " + a_0.b());
            }
            string2 = string2.concat(" " + a_0.c());
            ErrorProcessor.notifyError("Begin " + string2, ErrorLevel.UNKNOWN, ErrorDestination.DISPLAYLIST);
            object = new HecTime(0);
            object.setCurrent();
            ErrorProcessor.notifyError("   Start time: " + object.dateAndTime(7), ErrorLevel.UNKNOWN, ErrorDestination.DISPLAYLIST);
            Object[] objectArray = new Object[]{string};
            ErrorProcessor.notifyError(14650, objectArray, ErrorLevel.NOTE, ErrorDestination.DISPLAYLIST);
            int n3 = JythonHms.runScript(string);
            String string3 = "End " + string2 + "; Exit status = " + Integer.toString(n3);
            ErrorProcessor.notifyError(string3, ErrorLevel.UNKNOWN, ErrorDestination.DISPLAYLIST);
            object.setCurrent();
            ErrorProcessor.notifyError("   End time: " + object.dateAndTime(7), ErrorLevel.UNKNOWN, ErrorDestination.DISPLAYLIST);
            System.exit(n3);
        }
        if (!bl4) {
            LogManager.getLogManager().reset();
        }
        if (bl5) {
            try {
                new HmsCommandServerImpl(n2);
            }
            catch (RemoteException remoteException) {
                remoteException.printStackTrace();
            }
        } else {
            new Hms(bl2, bl3);
            if (bl4) {
                h.a(true);
                System.out.println("HEC-HMS Started With PID: " + h.b());
            }
        }
    }

    public String getName() {
        return "HMS";
    }

    public boolean hasWriteLock(MapGlyph mapGlyph) {
        return true;
    }

    public ToolBarButtonManager getToolBarButtonManager() {
        return null;
    }

    public boolean objectPopupMenu(NamedType[] namedTypeArray, LocalPt localPt) {
        return true;
    }

    public boolean objectPopupMenu(NamedType namedType, LocalPt localPt) {
        return true;
    }

    public boolean objectDoubleClick(NamedType namedType, LocalPt localPt) {
        return true;
    }

    public void actionPerformed(ActionEvent actionEvent) {
    }

    static {
        m.a();
    }
}

