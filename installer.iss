; Script de Inno Setup para Companion Advisor (LLM Voice Advisor)
; Genera el instalador profesional ejecutable con registro en Windows,
; ruta personalizable por defecto en C:\CompanionAdvisor, desinstalador integrado
; y accesos directos opcionales (desmarcados por defecto).

#define MyAppName "Companion Advisor"
#define MyAppVersion "0.2.0"
#define MyAppPublisher "Reaper"
#define MyAppURL "https://github.com/reaper1067MSX/llm-voice-advisor"
#define MyAppExeName "game-advisor.exe"

[Setup]
; Identificador único de la aplicación (GUID)
AppId={{8B49E71F-32A1-4C5D-91BC-7A2F08D64F12}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Ruta por defecto y selector de carpeta interactivo
DefaultDirName=C:\CompanionAdvisor
DisableDirPage=no
AppendDefaultDirName=no

; Grupo en el Menú Inicio
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=no

; Directorio y nombre de salida del instalador
OutputDir=dist\installer
OutputBaseFilename=CompanionAdvisor-Installer-v{#MyAppVersion}
SetupIconFile=assets\app_icon.ico

; Configuración de compresión óptima LZMA2
Compression=lzma2/ultra64
SolidCompression=yes

; Nombres limpios para el Registro de Windows y Panel de Control
UninstallDisplayName={#MyAppName} (Tactical Voice Copilot) v{#MyAppVersion}
UninstallDisplayIcon={app}\{#MyAppExeName}

; No forzar elevación admin si el usuario instala en su propia carpeta (compatible con Windows 10 y 11)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Visualización moderna
WizardStyle=modern

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; Acceso directo en escritorio: OPCIONAL y DESMARCADO por defecto para no invadir el escritorio
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Binarios principales generados por PyInstaller (carpeta onedir)
Source: "dist\game-advisor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Icono del sistema
Source: "assets\app_icon.ico"; DestDir: "{app}\assets"; Flags: ignoreversion

; Archivos de configuración del usuario: NUNCA se sobreescriben si ya existen
Source: "keys.env.example"; DestDir: "{app}"; DestName: "keys.env"; Flags: onlyifdoesntexist
Source: "config.yaml"; DestDir: "{app}"; Flags: onlyifdoesntexist

[Icons]
; Acceso directo en Menú Inicio para abrir el copiloto
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app_icon.ico"

; Acceso directo en Menú Inicio para desinstalar limpiamente con nombre amigable
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"

; Acceso directo en Escritorio (solo si el usuario lo marca explícitamente)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app_icon.ico"; Tasks: desktopicon

[Run]
; Opción para iniciar la aplicación al finalizar el asistente
Filename: "{app}\{#MyAppExeName}"; Description: "Iniciar {#MyAppName} ahora"; Flags: nowait postinstall skipifsilent

[Code]
// Procedimiento interactivo al desinstalar: pregunta al usuario si desea conservar sus claves y memorias
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    if MsgBox('¿Deseas conservar tu archivo keys.env y las memorias de juego para futuras instalaciones?', mbConfirmation, MB_YESNO) = IDNO then
    begin
      // Si el usuario elige "NO", borra las claves y la base de datos de datos
      DeleteFile(ExpandConstant('{app}\keys.env'));
      DelTree(ExpandConstant('{app}\data'), True, True, True);
    end;
  end;
end;
