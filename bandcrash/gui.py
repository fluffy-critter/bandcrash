""" Bandcrash GUI """
# pylint:disable=invalid-name,too-few-public-methods,too-many-ancestors
import wx


class MainFrame(wx.Frame):
    """ main window for the app """

    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, "Bandcrash", size=(800, 600),
                          style=wx.DEFAULT_FRAME_STYLE)


class BandcrashApp(wx.App):
    """ app instance """

    def OnInit(self):
        """ set up the app """
        frame = MainFrame(None)
        frame.Show(True)
        self.SetTopWindow(frame)
        return True


def main():
    """ instantiate an app """
    app = BandcrashApp()
    app.MainLoop()


if __name__ == '__main__':
    main()
