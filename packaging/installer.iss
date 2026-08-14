; DocTools 安装器（Inno Setup 6）
; 构建入口：packaging\build_installer.ps1（自动传递 /DSourceDir /DOutputDir /DAppVersion）
; 手动编译示例：
;   ISCC.exe packaging\installer.iss /DSourceDir=dist\DocTools-win-x64 /DOutputDir=dist /DAppVersion=1.1.0

#ifndef SourceDir
  #define SourceDir "..\dist\DocTools-win-x64"
#endif
#ifndef OutputDir
  #define OutputDir "..\dist"
#endif
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

#define MyAppName "DocTools"
#define MyAppExeName "DocTools.exe"

[Setup]
; 固定 AppId：升级安装时保持同一 GUID 才能覆盖旧版本
AppId={{C9D7E5B3-4A2F-4E8B-9C1D-6F3A8B2E5D7C}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppPublisher=pyrrolys1ne
AppPublisherURL=https://github.com/pyrrolys1ne/DocTools
; 按用户安装到 LocalAppData，无需管理员权限，符合"本地工具"定位
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes
PrivilegesRequired=lowest
OutputDir={#OutputDir}
OutputBaseFilename=DocTools-Setup-{#AppVersion}-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
; zip 分发包保留解压即用；安装器负责快捷方式与卸载入口
CloseApplications=no

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务:"; Flags: unchecked
Name: "libreoffice"; Description: "下载便携版 LibreOffice（约 350MB，未安装 Office 时推荐，作 Word/PPT 转 PDF 兜底引擎）"; GroupDescription: "附加任务:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "download_libreoffice.ps1"; DestDir: "{app}\tools"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent
Filename: "powershell.exe"; Description: "下载便携版 LibreOffice"; Tasks: libreoffice; \
    Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\tools\download_libreoffice.ps1"" -Url ""https://mirrors.ustc.edu.cn/tdf/libreoffice/portable/26.2.4/LibreOfficePortable_26.2.4_MultilingualStandard.paf.exe"" -TargetDir ""{app}\libreoffice"""; \
    Flags: postinstall runhidden

[Code]
function IsOfficeInstalled(): Boolean;
begin
  Result := RegKeyExists(HKCR, 'Word.Application\CLSID') or
            RegKeyExists(HKCR, 'PowerPoint.Application\CLSID') or
            RegKeyExists(HKLM32, 'SOFTWARE\Classes\Word.Application\CLSID') or
            RegKeyExists(HKLM64, 'SOFTWARE\Classes\Word.Application\CLSID') or
            RegKeyExists(HKLM32, 'SOFTWARE\Classes\PowerPoint.Application\CLSID') or
            RegKeyExists(HKLM64, 'SOFTWARE\Classes\PowerPoint.Application\CLSID');
end;

procedure InitializeWizard();
begin
  if not IsOfficeInstalled() then
  begin
    MsgBox('未检测到 Microsoft Office。' + #13#10 +
           '建议在附加任务页勾选「下载便携版 LibreOffice」，' + #13#10 +
           '作为 Word/PPT 转 PDF 的兜底引擎。',
           mbInformation, MB_OK);
  end;
end;
