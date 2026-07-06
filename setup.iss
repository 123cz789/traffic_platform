; setup.iss
; Inno Setup configuration script for Traffic Platform

[Setup]
AppName=交通工程设施全生命周期运维平台
AppVersion=1.0.0
DefaultDirName={autopf}\TrafficPlatform
DefaultGroupName=TrafficPlatform
OutputDir=installer_output
OutputBaseFilename=TrafficPlatform_Setup_x64
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
DisableProgramGroupPage=yes

[Files]
; Copy all compiled files and folders from PyInstaller output, maintaining dynamic directory structures
Source: "dist\TrafficPlatform\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
; Create shortcuts in Start Menu and Desktop
Name: "{autoprograms}\交通工程设施运维平台"; Filename: "{app}\TrafficPlatform.exe"
Name: "{autodesktop}\交通工程设施运维平台"; Filename: "{app}\TrafficPlatform.exe"

[Run]
; Run the app automatically after installation finishes
Filename: "{app}\TrafficPlatform.exe"; Description: "启动 交通工程设施全生命周期运维平台"; Flags: postinstall nowait skipifsilent