; Inno Setup Script — Suivi Commandes SPACE
; https://jrsoftware.org/ishelp/

#define AppName      "Suivi Commandes SPACE"
#define AppVersion   "1.0.0"
#define AppPublisher "Paul Molusson"
#define AppExeName   "SuiviCommandes.exe"

[Setup]
AppId={{A7B3C2D1-E4F5-6789-ABCD-EF0123456789}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://github.com/pillix17/paulmolusson
DefaultDirName={localappdata}\{#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=Output
OutputBaseFilename=SuiviCommandes_Setup_Windows
SetupIconFile=icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardSmallImageFile=icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
; Pas besoin de droits admin — installation dans AppData
PrivilegesRequiredOverridesAllowed=commandline

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; \
  Description: "Créer une icône sur le {commondesktop}"; \
  GroupDescription: "Icônes supplémentaires :"; \
  Flags: checked

[Files]
Source: "dist\{#AppExeName}"; \
  DestDir: "{app}"; \
  Flags: ignoreversion

[Icons]
; Bureau
Name: "{commondesktop}\{#AppName}"; \
  Filename: "{app}\{#AppExeName}"; \
  Tasks: desktopicon

; Menu Démarrer
Name: "{userprograms}\{#AppName}\{#AppName}"; \
  Filename: "{app}\{#AppExeName}"
Name: "{userprograms}\{#AppName}\Désinstaller {#AppName}"; \
  Filename: "{uninstallexe}"

[Run]
; Proposer de lancer l'app à la fin de l'installation
Filename: "{app}\{#AppExeName}"; \
  Description: "Lancer {#AppName}"; \
  Flags: nowait postinstall skipifsilent

[UninstallRun]
; Fermer l'application avant désinstallation
Filename: "taskkill"; \
  Parameters: "/F /IM {#AppExeName}"; \
  Flags: runhidden waituntilterminated

[Code]
// Personnalisation optionnelle (vide pour l'instant)
