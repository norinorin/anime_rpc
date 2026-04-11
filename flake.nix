{
  description = "Anime RPC - Discord Rich Presence integration";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };

  outputs = {
    self,
    nixpkgs,
  }: let
    systems = ["x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin"];
    forAllSystems = nixpkgs.lib.genAttrs systems;
  in {
    packages = forAllSystems (system: let
      pkgs = nixpkgs.legacyPackages.${system};
    in {
      default = pkgs.callPackage ./nix/package.nix {};
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
      anime_rpc = import ./nix/hm-module.nix self;
    };

    devShells = forAllSystems (system: let
      pkgs = nixpkgs.legacyPackages.${system};
      animeRpcPkg = pkgs.callPackage ./nix/package.nix {};
    in {
      default = pkgs.mkShell {
        inputsFrom = [animeRpcPkg];
        packages = with pkgs; [
          python3
          python3Packages.ruff
          python3Packages.pytest
          basedpyright
          uv

          cargo
          rustc
          rustfmt
          rust-analyzer
          clippy

          pkg-config
          vulkan-loader
          glib
          gtk3
          atk
          gdk-pixbuf
          cairo
          xdotool
        ];

        LD_LIBRARY_PATH =
          pkgs.lib.optionalString pkgs.stdenv.hostPlatform.isLinux
          (pkgs.lib.makeLibraryPath [
            pkgs.libgccjit
            pkgs.libmediainfo
            pkgs.alsa-lib
            pkgs.libpulseaudio
            pkgs.xorg.libX11
            pkgs.wayland
            pkgs.libxkbcommon
            pkgs.libayatana-appindicator
          ]);
      };
    });
  };
}
