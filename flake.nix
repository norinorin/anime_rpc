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
      y = toString (pkgs.lib.toIntBase10 (pkgs.lib.substring 2 2 self.lastModifiedDate));
      m = toString (pkgs.lib.toIntBase10 (pkgs.lib.substring 4 2 self.lastModifiedDate));
      d = toString (pkgs.lib.toIntBase10 (pkgs.lib.substring 6 2 self.lastModifiedDate));
      version = "${y}.${m}.${d}.0.dev${
        if self ? shortRev
        then "0+${self.shortRev}"
        else "0"
      }";
    in {
      default = pkgs.callPackage ./nix/package.nix {inherit version;};
      ui = pkgs.callPackage ./nix/ui.nix {};
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
        ];
      };
    });
  };
}
