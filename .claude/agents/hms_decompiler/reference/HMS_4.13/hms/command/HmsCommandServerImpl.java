/*
 * Decompiled with CFR 0.152.
 * 
 * Could not load the following classes:
 *  hec.client2.ClientCheckInService
 *  hec.csinterface.ClientCheckInServer
 *  hec.heclib.util.HecTime
 *  hms.command.CallbackMessenger
 *  hms.command.CommandStatus
 *  hms.command.HmsCommandServer
 *  hms.command.MfpCommand
 *  hms.command.RtsCommand
 *  hms.command.WatCommand
 *  org.jdom.Attribute
 *  org.jdom.Document
 *  org.jdom.Element
 *  org.jdom.JDOMException
 *  org.jdom.input.SAXBuilder
 *  org.jdom.output.XMLOutputter
 */
package hms.command;

import hec.client2.ClientCheckInService;
import hec.csinterface.ClientCheckInServer;
import hec.heclib.util.HecTime;
import hms.ErrorProcessor;
import hms.command.CallbackMessenger;
import hms.command.CommandStatus;
import hms.command.HmsCommandServer;
import hms.command.MfpCommand;
import hms.command.RtsCommand;
import hms.command.WatCommand;
import hms.command.a;
import hms.command.h_0;
import hms.command.i;
import hms.command.j;
import hms.command.p;
import hms.command.q;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;
import java.net.InetAddress;
import java.net.MalformedURLException;
import java.net.UnknownHostException;
import java.rmi.Naming;
import java.rmi.NotBoundException;
import java.rmi.Remote;
import java.rmi.RemoteException;
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;
import java.rmi.server.UnicastRemoteObject;
import org.jdom.Attribute;
import org.jdom.Document;
import org.jdom.Element;
import org.jdom.JDOMException;
import org.jdom.input.SAXBuilder;
import org.jdom.output.XMLOutputter;

public class HmsCommandServerImpl
extends UnicastRemoteObject
implements HmsCommandServer {
    private static HmsCommandServerImpl a;
    private q b;
    private j c;
    private h_0 d;
    private CallbackMessenger e;
    private XMLOutputter f;
    private p g;
    private ClientCheckInService h;

    public HmsCommandServerImpl(int n2) throws RemoteException {
        this.a();
        this.a(n2);
        a = this;
        System.out.println("Finished starting HmsCommandServer");
        this.a("Finished starting HmsCommandServer");
    }

    private void a(int n2) {
        this.a("initPort " + n2);
        HmsCommandServerImpl.init(n2);
        this.a("finish initPort " + n2);
        String string = this.e();
        this.a("host " + string);
        String string2 = "rmi://" + string + ":" + n2 + "/HmsCommandServer";
        System.out.println("HmsCommandServerImpl: rebinding to " + string2);
        try {
            long l2 = System.currentTimeMillis();
            Naming.rebind(string2, this);
            long l3 = System.currentTimeMillis();
            System.out.println("timer: rebind(): " + (l3 - l2) + " millis");
            this.f();
        }
        catch (RemoteException remoteException) {
            System.out.println("HmsCommandServerImpl: RemoteException " + remoteException);
            remoteException.printStackTrace();
            this.a(remoteException);
            System.exit(5);
        }
        catch (MalformedURLException malformedURLException) {
            System.out.println("HmsCommandServerImpl: MalformedURLException " + malformedURLException);
            malformedURLException.printStackTrace();
            this.a(malformedURLException);
            System.exit(6);
        }
    }

    private void a() {
        this.g = null;
        String string = System.getProperty("hms.server.log");
        if (string != null) {
            File file = new File(string);
            System.out.println("log file: " + string);
            if (!file.exists()) {
                try {
                    file.createNewFile();
                }
                catch (IOException iOException) {
                    System.out.println("failed to create log file: " + string);
                }
            }
            if (file.canWrite()) {
                try {
                    this.g = new p(System.out, file);
                    HecTime hecTime = new HecTime(10);
                    hecTime.setCurrent();
                    this.a("Created server log: " + hecTime);
                    System.setOut(this.g);
                    System.setErr(this.g);
                }
                catch (FileNotFoundException fileNotFoundException) {
                    System.out.println("failed to create log writer: " + string);
                    this.g = null;
                }
            }
        }
    }

    private void a(String string) {
        if (this.g != null) {
            this.g.a(string);
        }
    }

    private void a(Exception exception) {
        if (this.g != null) {
            this.g.a(exception);
        }
    }

    private q b() {
        if (this.b == null) {
            this.b = new q();
        }
        return this.b;
    }

    private j c() {
        if (this.c == null) {
            this.c = new j(this.b());
        }
        return this.c;
    }

    private h_0 d() {
        if (this.d == null) {
            this.d = new h_0();
        }
        return this.d;
    }

    public String executeCommand(String string) {
        try {
            Document document;
            this.a("");
            this.a(string);
            SAXBuilder sAXBuilder = new SAXBuilder();
            try {
                Document document2 = sAXBuilder.build((Reader)new StringReader(string));
                document = this.a(document2);
            }
            catch (IOException iOException) {
                document = hms.command.a.a("UnrecognizedDocument", "-1", CommandStatus.Error_UnableToProcessDocument, "Error creating String Reader", iOException);
            }
            catch (JDOMException jDOMException) {
                document = hms.command.a.a("UnrecognizedDocument", "-1", CommandStatus.Error_UnableToProcessDocument, "Error parsing document string", (Exception)((Object)jDOMException));
            }
            String string2 = this.b(document);
            this.a(string2);
            return string2;
        }
        catch (Exception exception) {
            exception.printStackTrace();
            this.a(exception);
            Document document = hms.command.a.a("UncaughtException", "-1", CommandStatus.Error_CommandFailed, "Uncaught exception executing command", exception);
            String string3 = this.b(document);
            this.a(string3);
            return string3;
        }
    }

    private synchronized Document a(Document document) {
        Document document2 = null;
        String string = null;
        String string2 = null;
        try {
            Element element = document.getRootElement();
            if (!"Request".equalsIgnoreCase(element.getName())) {
                string = "UnrecognizedDocument";
            } else {
                string = element.getAttributeValue("command");
                if (string == null) {
                    string = "UndefinedCommand";
                }
            }
            Attribute attribute = element.getAttribute("id");
            string2 = attribute != null ? attribute.getValue() : "-1";
            if (string.equals("UnrecognizedDocument")) {
                String string3 = "Unable to process document: " + this.b(document);
                document2 = hms.command.a.a(string, string2, CommandStatus.Error_UnableToProcessDocument, string3);
                return document2;
            }
            if (string.equals("UndefinedCommand")) {
                String string4 = "Command is not defined: " + this.b(document);
                document2 = hms.command.a.a(string, string2, CommandStatus.Error_UndefinedCommand, string4);
                return document2;
            }
            String string5 = element.getAttributeValue("clientProgram");
            if (string5 == null) {
                String string6 = "Client program is not set: " + this.b(document);
                document2 = hms.command.a.a(string, string2, CommandStatus.Error_UndefinedProgram, string6);
                return document2;
            }
            boolean bl2 = false;
            if (string5.equals("RTS")) {
                q q2 = this.b();
                q2.a(this.e);
                RtsCommand rtsCommand = RtsCommand.fromString((String)string);
                document2 = q2.a(document, rtsCommand, string2);
                bl2 = q2.c();
            } else if (string5.equals("MFP")) {
                q q3 = this.b();
                q3.a(this.e);
                MfpCommand mfpCommand = MfpCommand.fromString((String)string);
                document2 = this.c().a(document, mfpCommand, string2);
                bl2 = q3.c();
            } else if (string5.equals("WAT")) {
                h_0 h_02 = this.d();
                h_02.a(this.e);
                WatCommand watCommand = WatCommand.fromString((String)string);
                document2 = h_02.a(document, watCommand, string2);
                bl2 = h_02.c();
            } else {
                String string7 = "Unknown client program: " + this.b(document);
                document2 = hms.command.a.a(string, string2, CommandStatus.Error_UndefinedProgram, string7);
            }
            if (bl2 && this.g != null) {
                this.g.close();
                this.g = null;
            }
        }
        catch (Exception exception) {
            ErrorProcessor.notifyError(exception);
            String string8 = "Exception while processing document: " + this.b(document);
            document2 = hms.command.a.a(string == null ? "UnrecognizedDocument" : string, string2 == null ? "-1" : string2, CommandStatus.Error_UnableToProcessDocument, string8, exception);
        }
        return document2;
    }

    private String b(Document document) {
        if (this.f == null) {
            this.f = new XMLOutputter();
        }
        return this.f.outputString(document);
    }

    public static void init(int n2) {
        if (n2 < 0) {
            System.out.println("HmsCommandServerImpl.init: Invalid RMI Port specified " + n2);
            System.exit(2);
        }
        System.out.println("HmsCommandServerImpl.init: Starting registry on port " + n2);
        Registry registry = null;
        long l2 = System.currentTimeMillis();
        try {
            registry = LocateRegistry.getRegistry(n2);
            String[] stringArray = registry.list();
            if (registry == null || stringArray == null) {
                l2 = System.currentTimeMillis();
                registry = LocateRegistry.createRegistry(n2);
                long l3 = System.currentTimeMillis();
                System.out.println("timer: createRegistry(): " + (l3 - l2) + " millis");
            }
            System.out.println("HmsCommandServerImpl.init: found existing registry on port " + n2);
        }
        catch (RemoteException remoteException) {
            System.out.println("HmsCommandServerImpl.init: RemoteException on finding registry " + remoteException);
            long l4 = System.currentTimeMillis();
            System.out.println("timer: createRegistry(): " + (l4 - l2) + " millis");
            try {
                l2 = System.currentTimeMillis();
                registry = LocateRegistry.createRegistry(n2);
                l4 = System.currentTimeMillis();
                System.out.println("timer: createRegistry(): " + (l4 - l2) + " millis");
                System.out.println("HmsCommandServerImpl.init: created new registry on port " + n2);
            }
            catch (RemoteException remoteException2) {
                System.out.println("HmsCommandServerImpl.init: RemoteException creating registy on " + n2 + " Exception: " + remoteException2);
                System.exit(3);
            }
        }
        System.out.println("HmsCommandServerImpl.init: Registry is up " + registry);
    }

    private String e() {
        String string = "localhost";
        String string2 = System.getProperty("java.rmi.server.hostname");
        if (string2 != null) {
            return string2;
        }
        try {
            return InetAddress.getLocalHost().getHostName();
        }
        catch (UnknownHostException unknownHostException) {
            System.out.println("getHostname:UnknownHostException " + unknownHostException);
            return string;
        }
    }

    private void f() {
        Remote remote;
        String string = System.getProperty("ClientCheckInURL");
        if (string == null || string.isEmpty()) {
            System.out.println("HmsCommandServerImpl.startClientCheckIn: No ClientCheckInURL");
            return;
        }
        System.out.println("HmsCommandServerImpl.startClientCheckIn: ClientCheckInURL=" + string);
        try {
            remote = Naming.lookup(string);
        }
        catch (MalformedURLException | NotBoundException | RemoteException exception) {
            exception.printStackTrace();
            return;
        }
        if (remote instanceof ClientCheckInServer) {
            i i2 = null;
            i2 = new i(this);
            i2.setClientCheckInServer((ClientCheckInServer)remote);
            i2.startCheckInService();
            this.h = i2;
            if (this.h != null) {
                System.out.println("HmsCommandServerImpl.startClientCheckIn: created process killer");
            }
        } else {
            System.out.println("HmsCommandServerImpl.startClientCheckIn:failed to find check in server at URL " + string);
        }
    }

    public void setCallbackMessenger(CallbackMessenger callbackMessenger) {
        this.e = callbackMessenger;
    }

    public void ping() {
    }
}

