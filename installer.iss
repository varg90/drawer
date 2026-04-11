#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppName=Drawer
AppVersion={#AppVersion}
AppPublisher=varg90
DefaultDirName={autopf}\Drawer
DefaultGroupName=Drawer
OutputDir=dist
OutputBaseFilename=Drawer_Setup
Compression=lzma2/ultra64
SolidCompression=yes
SetupIconFile=drawer.ico
UninstallDisplayIcon={app}\drawer.ico
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern

[Files]
Source: "dist\onedir\Drawer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\Drawer"; Filename: "{app}\Drawer.exe"; IconFilename: "{app}\drawer.ico"
Name: "{autodesktop}\Drawer"; Filename: "{app}\Drawer.exe"; IconFilename: "{app}\drawer.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\Drawer.exe"; Description: "Launch Drawer"; Flags: nowait postinstall skipifsilent
