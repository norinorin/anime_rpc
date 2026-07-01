{
  lib,
  stdenv,
  python3Packages,
  libmediainfo,
  version ? "0.0.0+unknown",
  autoPatchelfHook ? null,
  alsa-lib ? null,
  libpulseaudio ? null,
  libX11 ? null,
}: let
  linuxNativeDeps = [
    autoPatchelfHook
  ];
  linuxSystemDeps = [
    alsa-lib
    libpulseaudio
    libX11
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

    postPatch = ''
      # TODO: Remove once nixpkgs ships aiohttp >= 3.14.1.
      # We don't rely on features introduced in 3.14, and the CVE addressed in
      # 3.14.1 concerns unbounded HTTP/1 pipelined request queues in aiohttp's
      # server implementation. We bind to loopback only so exposure to untrusted
      # clients is limited.
      substituteInPlace pyproject.toml \
        --replace-fail "aiohttp>=3.14.1" "aiohttp>=3.13.5"
    '';

    meta = with lib; {
      description = "Anime Rich Presence integration";
      license = licenses.mit;
      mainProgram = "anime_rpc";
      platforms = platforms.linux ++ platforms.darwin;
    };
  }
