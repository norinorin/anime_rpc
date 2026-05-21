{
  lib,
  stdenv,
  python3Packages,
  libmediainfo,
  version ? "0.0.0+unknown",
  autoPatchelfHook ? null,
  alsa-lib ? null,
  libpulseaudio ? null,
  xorg ? null,
}: let
  linuxNativeDeps = [
    autoPatchelfHook
  ];
  linuxSystemDeps = [
    alsa-lib
    libpulseaudio
    xorg.libX11
  ];
in
  python3Packages.buildPythonApplication {
    pname = "anime_rpc";
    inherit version;

    src = ../.;
    format = "pyproject";

    nativeBuildInputs = with python3Packages;
      [
        setuptools
        setuptools-scm
      ]
      ++ lib.optionals stdenv.hostPlatform.isLinux linuxNativeDeps;

    propagatedBuildInputs = with python3Packages; [
      setuptools-scm
      aiohttp
      aiohttp-cors
      pymediainfo
      beautifulsoup4
      coloredlogs
      platformdirs
      watchdog
      cffi
      keyring
    ];

    buildInputs =
      [
        libmediainfo
      ]
      ++ lib.optionals stdenv.hostPlatform.isLinux linuxSystemDeps;

    makeWrapperArgs = [
      "--set SETUPTOOLS_SCM_PRETEND_VERSION ${version}"
    ];

    meta = with lib; {
      description = "Anime Rich Presence integration";
      license = licenses.mit;
      mainProgram = "anime_rpc";
      platforms = platforms.linux ++ platforms.darwin;
    };
  }
