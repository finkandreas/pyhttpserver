import json
import dbus
import sys
import os
from gi.repository import GObject
from dbus.mainloop.glib import DBusGMainLoop


class DbusProxyIface(object):
  def __init__(self, proxy, iface):
    self.proxy = proxy;
    self.iface = iface;

  def GetProperty(self, property):
    return self.proxy.Get(self.iface, property, dbus_interface=dbus.PROPERTIES_IFACE)

  def SetProperty(self, property, value):
    self.proxy.Set(self.iface, property, value, dbus_interface=dbus.PROPERTIES_IFACE)

  def CallMethod(self, method, *args):
    return self.proxy.get_dbus_method(method, dbus_interface=self.iface)(*args)


class DbusKeyring(object):
  def __init__(self):
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    self.bus = dbus.SessionBus()
    self.secretsProxy = DbusProxyIface(self.bus.get_object("org.freedesktop.secrets", "/org/freedesktop/secrets"), "org.freedesktop.Secret.Service")
    self.loop = GObject.MainLoop()
    self.session = None

  def __del__(self):
    if (self.session): DbusProxyIface(self.bus.get_object("org.freedesktop.secrets", self.session), "org.freedesktop.Secret.Session").CallMethod("Close")
    self.bus.close()

  def SetSecret(self, item, password):
    secret = self.ToDbusSecret(password)
    DbusProxyIface(self.bus.get_object("org.freedesktop.secrets", item), "org.freedesktop.Secret.Item").CallMethod("SetSecret", secret)

  def GetSecret(self, item):
    if self.session == None: (_, self.session) = self.secretsProxy.CallMethod("OpenSession", "plain", "")
    secret = DbusProxyIface(self.bus.get_object("org.freedesktop.secrets", item), "org.freedesktop.Secret.Item").CallMethod("GetSecret", self.session)
    return bytearray(secret[2]).decode('utf-8')

  def ToDbusSecret(self, password):
    if self.session == None: (_, self.session) = self.secretsProxy.CallMethod("OpenSession", "plain", "");
    return (self.session, bytearray(), bytearray(password, 'utf-8'), "text/plain; charset=utf8")

  def GetCollections(self):
    return self.secretsProxy.GetProperty("Collections")

  def UnlockItem(self, item):
    (unlocked, prompt) = self.secretsProxy.CallMethod("Unlock", [item])
    if item not in unlocked: return self.WaitForPrompt(prompt)
    return True

  def CreateItem(self, attributes, password):
    allcollections = self.GetCollections()
    notLoginCollections = [ x for x in allcollections if str(x).find("session")==-1 ]
    collection = notLoginCollections[0] if len(notLoginCollections) else allcollections[0] # select first collection which does not have session in its name, otherwise select the very first collection
    self.UnlockItem(collection)
    secret = self.ToDbusSecret(password)
    attributes.update({'xdg:schema': 'org.freedesktop.Secret.Generic'})
    attribs = { "org.freedesktop.Secret.Item.Label": 'pyhttpserver', "org.freedesktop.Secret.Item.Attributes": attributes }
    (objPath, prompt) = DbusProxyIface(self.bus.get_object("org.freedesktop.secrets", collection), "org.freedesktop.Secret.Collection").CallMethod("CreateItem", attribs, secret, False)
    if (objPath == "/"): self.WaitForPrompt(prompt)

  def WaitForPrompt(self, prompt):
    self.bus.add_signal_receiver(handler_function=self._received_pw, signal_name="Completed", dbus_interface="org.freedesktop.Secret.Prompt")
    DbusProxyIface(self.bus.get_object("org.freedesktop.secrets", prompt), "org.freedesktop.Secret.Prompt").CallMethod("Prompt", "")
    self.loop.run()
    return not self.PromptDismissed

  def _finditem(self, attributesToMatch):
    (unlockedItems, lockedItems) = self.secretsProxy.CallMethod("SearchItems", attributesToMatch)
    if len(unlockedItems) > 0:
      return unlockedItems[0]
    elif len(lockedItems) > 0:
      self.UnlockItem(lockedItems[0])
      return lockedItems[0]
    else:
      return None

  def FindItem(self, attributesToMatch):
    (unlockedItems, lockedItems) = self.secretsProxy.CallMethod("SearchItems", attributesToMatch)
    item = self._finditem(attributesToMatch)
    if item == None: return (None, None)
    allAttribs = DbusProxyIface(self.bus.get_object("org.freedesktop.secrets", item), "org.freedesktop.Secret.Item").GetProperty("Attributes")
    return (allAttribs, self.GetSecret(item))

  def UpdateOrInsertItem(self, attributesToMatch, password):
    item = self._finditem(attributesToMatch)
    if item != None: self.SetSecret(item, password)
    else: self.CreateItem(attributesToMatch, password)

  def _received_pw(self, dismissed, objectPath):
    self.bus.remove_signal_receiver(self._received_pw, signal_name="Completed", dbus_interface="org.freedesktop.Secret.Prompt")
    self.PromptDismissed = dismissed
    self.loop.quit()
