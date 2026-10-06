{
  description = "Anime RPC - Discord Rich Presence integration";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = {
    self,
    nixpkgs,
    uv2nix,
    pyproject-nix,
    pyproject-build-systems,
  }: let
    systems = ["x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin"];
    forAllSystems = nixpkgs.lib.genAttrs systems;
    workspace = uv2nix.lib.workspace.loadWorkspace {workspaceRoot = ./.;};
  in {
    packages = forAllSystems (system: let
      pkgs = nixpkgs.legacyPackages.${system};
      inherit (pkgs) lib;

      date = self.lastModifiedDate or "20261006000000";
      y = lib.substring 0 4 date; # "2026"
      m = toString (lib.toIntBase10 (lib.substring 4 2 date));
      d = toString (lib.toIntBase10 (lib.substring 6 2 date));
      dev =
        if self ? revCount
        then toString self.revCount
        else "0";
      gitHash =
        if self ? shortRev
        then "+g${self.shortRev}"
        else "+dirty";

      version = "${y}.${m}.${d}.0.dev${dev}${gitHash}";
      pythonSet = pkgs.callPackage ./nix/package.nix {
        inherit workspace pyproject-nix pyproject-build-systems version;
      };
      venv = pythonSet.mkVirtualEnv "anime-rpc-env" workspace.deps.default;
    in {
      default = pkgs.writeShellScriptBin "anime_rpc" ''
        exec ${venv}/bin/anime_rpc "$@"
      '';
    });

    overlays.default = final: prev: {
      mpvScripts =
        prev.mpvScripts
        // {
          simple-mpv-webui = prev.mpvScripts.simple-mpv-webui.overrideAttrs (old: {
            postPatch =
              (old.postPatch or "")
              + ''
                substituteInPlace main.lua \
                  --replace 'local values = {' \
                            'local values = { ["working-dir"] = mp.get_property("working-directory") or "",'
              '';
          });
        };
    };

    homeModules = {
      default = self.homeModules.anime_rpc;
      anime_rpc = {...}: {
        imports = [./nix/hm-module.nix];
        _module.args = {inherit self;};
      };
    };

    devShells = forAllSystems (system: let
      pkgs = nixpkgs.legacyPackages.${system};
      animeRpcPkg = self.packages.${system}.default;
    in {
      default = pkgs.mkShell {
        inputsFrom = [animeRpcPkg];
        packages = with pkgs; [
          python3
          python3Packages.ruff
          python3Packages.pytest
          basedpyright
          uv
        ];

        LD_LIBRARY_PATH =
          pkgs.lib.optionalString pkgs.stdenv.hostPlatform.isLinux
          (pkgs.lib.makeLibraryPath [
            pkgs.stdenv.cc.cc.lib
            pkgs.libmediainfo
            pkgs.alsa-lib
            pkgs.libpulseaudio
            pkgs.libX11
          ]);
      };
    });
  };
}
