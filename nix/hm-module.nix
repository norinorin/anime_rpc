self: {
  config,
  lib,
  pkgs,
  ...
}: let
  cfg = config.services.anime_rpc;
  pkg = self.packages.${pkgs.system}.default;
in {
  options.services.anime_rpc = {
    enable = lib.mkEnableOption "Anime RPC Service";

    enableWebserver = lib.mkEnableOption "the webserver for browser userscripts (extension integration)";

    clearOnPause = lib.mkEnableOption "clearing rich presence on media pause";

    useOAuth2 = lib.mkEnableOption "authentication via OAuth2 (no Discord client required)";

    fetchEpisodeTitles = lib.mkEnableOption "fetching episode titles from MyAnimeList";

    verbose = lib.mkEnableOption "verbose logging";

    interval = lib.mkOption {
      type = lib.types.int;
      default = 0;
      description = ''
        Specify the interval in seconds for periodic updates.
        Defaults to 0, meaning updates occur only on play/stop events.
      '';
    };

    pollers = lib.mkOption {
      type = lib.types.listOf (lib.types.strMatching "^(mpc|mpv-ipc|mpv-webui)(:[0-9]+)?$");
      default = ["mpv"];
      example = ["mpv" "mpc:13579"];
      description = ''
        List of pollers to enable (e.g., mpc, mpv-ipc, mpv-webui).
        You can specify ports using the format 'name:port'.
      '';
    };

    extraArgs = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [];
      description = "Extra arguments to pass directly to the anime_rpc binary.";
    };
  };

  config = lib.mkIf cfg.enable {
    home.packages = [pkg];

    systemd.user.services.anime_rpc = {
      Unit = {
        Description = "Anime RPC Daemon";
        After = ["graphical-session.target"];
        PartOf = ["graphical-session.target"];
      };

      Service = {
        ExecStart = let
          args = lib.concatLists [
            (lib.optional cfg.enableWebserver "--enable-webserver")
            (lib.optional cfg.clearOnPause "--clear-on-pause")
            (lib.optional cfg.useOAuth2 "--use-oauth2")
            (lib.optional cfg.fetchEpisodeTitles "--fetch-episode-titles")
            (lib.optional cfg.verbose "--verbose")
            (lib.optionals (cfg.interval != 0) ["--interval" (toString cfg.interval)])
            (lib.optionals (cfg.pollers != []) ["--pollers" (lib.concatStringsSep "," cfg.pollers)])
            cfg.extraArgs
          ];
        in "${pkg}/bin/anime_rpc ${lib.escapeShellArgs args}";

        Restart = "on-failure";
        RestartSec = 5;
      };

      Install = {
        WantedBy = ["graphical-session.target"];
      };
    };
  };
}
