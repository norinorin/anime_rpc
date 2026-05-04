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
  darwin ? null, # FIXME
}: let
  linuxNativeDeps = [
    autoPatchelfHook
  ];
  linuxSystemDeps = [
    alsa-lib
    libpulseaudio
    xorg.libX11
  ];
  darwinSystemDeps = [
    # FIXME
  ];
  libEnvVar =
    if stdenv.hostPlatform.isDarwin
    then "DYLD_LIBRARY_PATH"
    else "LD_LIBRARY_PATH";
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
      ++ lib.optionals stdenv.hostPlatform.isLinux linuxSystemDeps
      ++ lib.optionals stdenv.hostPlatform.isDarwin darwinSystemDeps;

    makeWrapperArgs = [
      "--prefix ${libEnvVar} : ${lib.makeLibraryPath [libmediainfo]}"
      "--set SETUPTOOLS_SCM_PRETEND_VERSION ${version}"
    ];

    meta = with lib; {
      description = "Anime Rich Presence integration";
      license = licenses.mit;
      mainProgram = "anime_rpc";
      platforms = platforms.all;
    };
  }
