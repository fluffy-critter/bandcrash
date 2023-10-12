""" Bandcrash GUI """
# pylint:disable=invalid-name,too-few-public-methods,too-many-ancestors
import wx
import wx.adv

from . import __version__, args


class AboutBox(wx.adv.AboutDialogInfo):
    """ Simple about box """

    def __init__(self, parent):
        super().__init__()


class PreferencesDialog(wx.Dialog):
    """ preferences panel """

    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "Preferences")


class AlbumEditor(wx.Frame):
    """ Album editor frame """

    def __init__(self, parent, open_file = None):
        wx.Frame.__init__(self, parent, -1, "New Album")

        self.album = None # Currently open album specification
        self.unsaved = False # Are there unsaved changes?

        self.SetupMenu()

        # self.Bind(wx.EVT_MENU, self.open_preferences, id=wx.ID_PREFERENCES)
        self.Bind(wx.EVT_MENU, self.ShowAbout, id=wx.ID_ABOUT)
        self.Bind(wx.EVT_MENU, self.OpenDialog, id=wx.ID_OPEN)

    def SetupMenu(self):
        menu_bar = wx.MenuBar()

        menu = wx.Menu()
        menu.Append(wx.ID_NEW, "&New\tCtrl-N", "Create a new album")
        menu.Append(wx.ID_OPEN, "&Open...\tCtrl-O", "Open an existing album")
        menu.Append(wx.ID_SAVE, "&Save\tCtrl-S", "Save the current album")
        menu.Append(wx.ID_SAVEAS, "Save &As...\tCtrl-Shift-S", "Save to a new filename")
        menu.Append(wx.ID_REVERT_TO_SAVED, "&Revert", "Undo all changes")
        menu.AppendSeparator()
        menu.Append(wx.ID_EXIT, "&Quit\tCtrl-Q", "Quit the app")
        menu_bar.Append(menu, "&File")

        menu = wx.Menu()
        menu.Append(wx.ID_PREFERENCES, "&Preferences", "Open application preferences")
        menu_bar.Append(menu, "&Edit")

        menu = wx.Menu()
        menu.Append(wx.ID_ABOUT, "&About...", "About Bandcrash")
        menu_bar.Append(menu, "&Help")

        wx.MenuBar.MacSetCommonMenuBar(menu_bar)
        self.SetMenuBar(menu_bar)

    def OpenDialog(self, event):
        """ Open a file through a dialog """

    def ShowAbout(self, event):
        """ Show the about box """
        info = wx.adv.AboutDialogInfo()
        info.SetName("Bandcrash")
        info.SetWebSite("https://github.com/fluffy-critter/bandcrash",
            "Github Repository")
        info.SetVersion(__version__.__version__)
        info.SetCopyright("© 2022—2023 j. \"fluffy\" shagam")

        info.SetLicense("""MIT License

Copyright (c) 2022—2023 j. shagam <fluffy@beesbuzz.biz>

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
""")
        wx.adv.AboutBox(info)


class BandcrashApp(wx.App):
    """ app instance """

    def OnInit(self):
        """ set up the app """
        self.SetAppName("Bandcrash")
        self.SetVendorName("biz.beesbuzz.bandcrash")

        self.InitConfig()

        frame = AlbumEditor(None)
        frame.Show(True)
        self.SetTopWindow(frame)
        return True

    def InitConfig(self):
        """ Initialize the application configuration """
        cfg = wx.ConfigBase.Get()
        defaults = vars(args.parse_args())
        for item in ('num_threads', 'lame_path', 'oggenc_path', 'flac_path',
            'butler_path',
            'preview_encoder_args', 'mp3_encoder_args', 'ogg_encoder_args', 'flac_encoder_args'):
            if not cfg.Exists(item) and item in defaults:
                if isinstance(defaults[item], str):
                    cfg.Write(item, defaults[item])
                elif isinstance(defaults[item], int):
                    cfg.WriteInt(item, defaults[item])
                else:
                    raise RuntimeError("Got unexpected type %s for key %s", type(defaults[item]), item)

        cfg.Flush()


def main():
    """ instantiate an app """
    app = BandcrashApp()
    app.MainLoop()


if __name__ == '__main__':
    main()
