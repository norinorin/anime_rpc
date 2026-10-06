{
  pkgs,
  lib,
  stdenv,
  version,
  workspace,
  pyproject-nix,
  pyproject-build-systems,
  libmediainfo,
  autoPatchelfHook ? null,
  alsa-lib ? null,
  libpulseaudio ? null,
  libX11 ? null,
}: let
  overlay = workspace.mkPyprojectOverlay {
    sourcePreference = "wheel";
  };

  pyprojectOverrides = final: prev: {
    anime-rpc = prev.anime-rpc.overrideAttrs (old: {
      SETUPTOOLS_SCM_PRETEND_VERSION_FOR_ANIME_RPC = version;

      nativeBuildInputs =
        (old.nativeBuildInputs or [])
        ++ lib.optionals stdenv.hostPlatform.isLinux [pkgs.autoPatchelfHook];

      buildInputs =
        (old.buildInputs or [])
        ++ [libmediainfo]
        ++ lib.optionals stdenv.hostPlatform.isLinux [
          alsa-lib
          libpulseaudio
          libX11
        ];
    });
  };

  pythonSet = (pkgs.callPackage pyproject-nix.build.packages
    {
      python = pkgs.python3;
    }).overrideScope (
    lib.composeManyExtensions [
      pyproject-build-systems.overlays.default
      overlay
      pyprojectOverrides
    ]
  );
in
  pythonSet
