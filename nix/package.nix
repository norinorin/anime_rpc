{
  lib,
  stdenv,
  python3Packages,
  libmediainfo,
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
    version = "0.0.0+git";

    src = ../.;
    format = "pyproject";

    nativeBuildInputs = with python3Packages;
      [
        setuptools
        setuptools-scm
      ]
      ++ lib.optionals stdenv.hostPlatform.isLinux linuxNativeDeps;

    propagatedBuildInputs = with python3Packages; [
      aiohttp
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

    postInstall = ''
      site_packages=$out/${python3Packages.python.sitePackages}

      mkdir -p $site_packages/lib
      mkdir -p $site_packages/include

      cp -r lib/* $site_packages/lib/
      cp -r include/* $site_packages/include/
    '';

    makeWrapperArgs = [
      "--prefix ${libEnvVar} : ${lib.makeLibraryPath [libmediainfo]}"
    ];

    meta = with lib; {
      description = "Anime Rich Presence integration";
      license = licenses.mit;
      mainProgram = "anime_rpc";
      platforms = platforms.all;
    };
  }
