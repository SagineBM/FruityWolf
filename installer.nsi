; FruityWolf NSIS Installer Script
; Creates a Windows installer with proper shortcuts and registry entries

!include "MUI2.nsh"
!include "FileFunc.nsh"

; Custom Icon
!define MUI_ICON "assets\icon.ico"
!define MUI_UNICON "assets\icon.ico"

; App Info
Name "FruityWolf"
OutFile "dist\FruityWolf-Installer\FruityWolf-Setup.exe"
InstallDir "$PROGRAMFILES\FruityWolf"
RequestExecutionLevel admin
Unicode True

; Version Info
VIProductVersion "2.0.0.0"
VIAddVersionKey "ProductName" "FruityWolf"
VIAddVersionKey "ProductVersion" "2.0.0"
VIAddVersionKey "FileDescription" "FruityWolf - FL Studio Library Manager"
VIAddVersionKey "FileVersion" "2.0.0"
VIAddVersionKey "CompanyName" "FruityWolf Team"
VIAddVersionKey "LegalCopyright" "© 2024 FruityWolf Team"

; Installer Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Uninstaller Pages
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; Languages
!insertmacro MUI_LANGUAGE "English"

; Installer Section
Section "Install" SecInstall
    SetOutPath "$INSTDIR"
    
    ; Copy all files from dist/FruityWolf-Folder
    File /r "dist\FruityWolf-Folder\*.*"
    
    ; Create Start Menu shortcuts
    CreateDirectory "$SMPROGRAMS\FruityWolf"
    CreateShortCut "$SMPROGRAMS\FruityWolf\FruityWolf.lnk" "$INSTDIR\FruityWolf.exe"
    CreateShortCut "$SMPROGRAMS\FruityWolf\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
    
    ; Create Desktop shortcut
    CreateShortCut "$DESKTOP\FruityWolf.lnk" "$INSTDIR\FruityWolf.exe"
    
    ; Write uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    
    ; Registry entries for Add/Remove Programs
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\FruityWolf" "DisplayName" "FruityWolf"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\FruityWolf" "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\FruityWolf" "DisplayVersion" "2.0.0"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\FruityWolf" "Publisher" "FruityWolf Team"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\FruityWolf" "InstallLocation" "$INSTDIR"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\FruityWolf" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\FruityWolf" "NoRepair" 1
    
    ; File associations (optional - for .flp files if desired)
    ; WriteRegStr HKCR ".flp" "" "FruityWolf.Project"
    ; WriteRegStr HKCR "FruityWolf.Project" "" "FL Studio Project"
    ; WriteRegStr HKCR "FruityWolf.Project\DefaultIcon" "" "$INSTDIR\FruityWolf.exe,0"
    ; WriteRegStr HKCR "FruityWolf.Project\shell\open\command" "" '"$INSTDIR\FruityWolf.exe" "%1"'
SectionEnd

; Uninstaller Section
Section "Uninstall"
    ; Remove files
    RMDir /r "$INSTDIR"
    
    ; Remove shortcuts
    Delete "$SMPROGRAMS\FruityWolf\FruityWolf.lnk"
    Delete "$SMPROGRAMS\FruityWolf\Uninstall.lnk"
    RMDir "$SMPROGRAMS\FruityWolf"
    Delete "$DESKTOP\FruityWolf.lnk"
    
    ; Remove registry entries
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\FruityWolf"
    
    ; Remove file associations (if added)
    ; DeleteRegKey HKCR ".flp"
    ; DeleteRegKey HKCR "FruityWolf.Project"
SectionEnd
