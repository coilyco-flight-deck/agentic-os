@echo off
REM git-credential-forgejo-ssm.cmd - Windows entry point for git credential.helper.
REM Wraps the bash helper so native git.exe can fetch the Forgejo token from SSM.

"C:\Program Files\Git\usr\bin\bash.exe" "%~dp0git-credential-forgejo-ssm.sh" %*
