@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
title TikTok Live Recorder
cd /d "%~dp0"

echo ================================================
echo   TikTok Live Recorder
echo ================================================
echo.

rem -----------------------------------------------------------------
rem 0) Se o projeto ainda nao estiver nesta pasta, baixa do GitHub.
rem    Isso permite enviar SOMENTE este arquivo .bat para um amigo:
rem    ao clicar, ele baixa o resto sozinho.
rem -----------------------------------------------------------------
if exist "%~dp0src\main.py" goto PROJECT_OK

echo Primeira execucao: baixando o programa, aguarde...
powershell -NoProfile -ExecutionPolicy ByPass -Command "$ErrorActionPreference='Stop'; $zip = Join-Path $env:TEMP 'tlr_download.zip'; $dest = Join-Path $env:TEMP 'tlr_download_extract'; if (Test-Path $zip) { Remove-Item $zip -Force }; if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }; try { $release = Invoke-RestMethod -UseBasicParsing -Uri 'https://api.github.com/repos/Michele0303/tiktok-live-recorder/releases/latest'; $downloadUrl = $release.zipball_url } catch { $downloadUrl = 'https://github.com/Michele0303/tiktok-live-recorder/archive/refs/heads/main.zip' }; Invoke-WebRequest -UseBasicParsing -Uri $downloadUrl -OutFile $zip; Expand-Archive -Path $zip -DestinationPath $dest -Force; $inner = Get-ChildItem -Path $dest -Directory | Select-Object -First 1; Copy-Item -Path (Join-Path $inner.FullName '*') -Destination '%~dp0' -Recurse -Force; Remove-Item $zip -Force; Remove-Item $dest -Recurse -Force"

if not exist "%~dp0src\main.py" (
    echo.
    echo Nao foi possivel baixar o programa. Verifique sua conexao com a internet
    echo e tente novamente. Se o problema continuar, baixe manualmente em:
    echo https://github.com/Michele0303/tiktok-live-recorder
    pause
    exit /b 1
)

echo Download concluido.
echo.

:PROJECT_OK

rem -----------------------------------------------------------------
rem 1) Verifica/instala o "uv" (cuida do Python e das dependencias)
rem -----------------------------------------------------------------
where uv >nul 2>nul
if errorlevel 1 (
    echo "uv" nao encontrado. Instalando agora, aguarde...
    powershell -NoProfile -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    echo.
    echo Instalacao concluida.
    echo IMPORTANTE: feche esta janela e clique DUAS VEZES neste arquivo de novo para continuar.
    pause
    exit /b 0
)
echo [OK] uv encontrado.

rem -----------------------------------------------------------------
rem 2) Verifica/instala o FFmpeg
rem -----------------------------------------------------------------
where ffmpeg >nul 2>nul
if not errorlevel 1 goto FFMPEG_OK

where winget >nul 2>nul
if errorlevel 1 goto FFMPEG_MANUAL

echo FFmpeg nao encontrado. Instalando via winget, aguarde...
winget install -e --id Gyan.FFmpeg --silent --accept-package-agreements --accept-source-agreements
echo.
echo Instalacao concluida.
echo IMPORTANTE: feche esta janela e clique DUAS VEZES neste arquivo de novo para continuar.
pause
exit /b 0

:FFMPEG_MANUAL
echo.
echo FFmpeg nao encontrado e nao foi possivel instalar automaticamente
echo ^(o winget nao esta disponivel neste computador^).
echo.
echo Abrindo a pagina de download do FFmpeg no navegador...
start https://www.gyan.dev/ffmpeg/builds/
echo Baixe o arquivo "ffmpeg-release-essentials.zip", extraia-o em qualquer
echo pasta e adicione a subpasta "bin" dele as Variaveis de Ambiente ^(PATH^)
echo do Windows. Depois, feche esta janela e clique neste arquivo de novo.
pause
exit /b 1

:FFMPEG_OK
echo [OK] FFmpeg encontrado.
echo.

rem -----------------------------------------------------------------
rem 3) Instala/atualiza as dependencias do programa
rem -----------------------------------------------------------------
echo Preparando o programa, aguarde...
uv sync --no-dev
if errorlevel 1 (
    echo.
    echo Falha ao instalar as dependencias. Verifique sua conexao com a internet.
    pause
    exit /b 1
)
echo.

:MENU
echo ================================================
echo   Quem voce quer gravar?
echo ================================================
set "PERFIS="
set /p "PERFIS=Perfil(is) do TikTok, sem @ (varios: separe por virgula): "
if "!PERFIS!"=="" (
    echo Voce nao digitou nenhum perfil.
    echo.
    goto MENU
)

echo.
echo Modo de gravacao:
echo   1 - Gravar AGORA ^(a pessoa ja precisa estar ao vivo^)
echo   2 - Esperar a pessoa entrar ao vivo ^(recomendado^)
set "MODOOPT="
set /p "MODOOPT=Escolha 1 ou 2 [padrao 2]: "
if "!MODOOPT!"=="1" (
    set "MODO=manual"
) else (
    set "MODO=automatic"
)

if not exist "%~dp0Downloads" mkdir "%~dp0Downloads"

echo.
echo Iniciando... pressione CTRL+C uma vez para parar a gravacao.
echo.

uv run python src\main.py -user "!PERFIS!" -mode !MODO! -output "%~dp0Downloads"

echo.
set "OUTRO="
set /p "OUTRO=Gravar outro perfil agora? (S/N): "
if /i "!OUTRO!"=="S" goto MENU

echo.
echo Ate a proxima!
pause
