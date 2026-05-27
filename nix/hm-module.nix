{
  lib,
  config,
  pkgs,
  self,
  ...
}: let
  inherit
    (lib)
    mkEnableOption
    mkIf
    mkOption
    mkDefault
    types
    optional
    optionals
    concatLists
    concatMap
    ;

  cfg = config.programs.anime_rpc;

  minimumInterval = 5;

  enabledPollers =
    lib.filterAttrs (_: v: v.enable) cfg.settings.pollers;

  pollerArgs = let
    renameMap = {
      mpvIpc = "mpv-ipc";
      mpvWebui = "mpv-webui";
    };
  in
    lib.mapAttrsToList
    (
      name: v: let
        cliName = renameMap.${name} or name;
      in
        if (v ? port && v.port != null)
        then "${cliName}:${toString v.port}"
        else cliName
    )
    enabledPollers;

  args = concatLists [
    (optional cfg.settings.clearOnPause "--clear-on-pause")

    (optional cfg.settings.webserver.enable "--enable-webserver")

    (optional cfg.settings.useOAuth2 "--use-oauth2")

    (optional cfg.settings.fetchEpisodeTitles
      "--fetch-episode-titles")

    (optional cfg.settings.verbose "--verbose")

    (optionals (cfg.settings.interval > 0) [
      "--interval"
      (toString cfg.settings.interval)
    ])

    (concatMap (p: ["--poller" p]) pollerArgs)

    cfg.settings.extraArgs
  ];
in {
  options.programs.anime_rpc = {
    enable = mkEnableOption "Anime RPC";

    package = mkOption {
      type = types.package;
      default = self.packages.${pkgs.system}.default;
      description = "The anime_rpc executable package to use.";
    };

    ui = {
      enable = mkEnableOption "Anime RPC UI";
      package = mkOption {
        type = types.package;
        default = self.packages.${pkgs.system}.ui;
        description = "The anime_rpc_ui package to use.";
      };
    };

    settings = {
      clearOnPause =
        mkEnableOption "clearing rich presence on pause";

      webserver.enable =
        mkEnableOption "webserver integration";

      useOAuth2 =
        mkEnableOption "OAuth2 authentication";

      fetchEpisodeTitles =
        mkEnableOption "fetching episode titles from MAL";

      verbose =
        mkEnableOption "verbose logging";

      interval = mkOption {
        type = types.ints.unsigned;
        default = 0;

        description = ''
          Interval in seconds for periodic updates.

          Values between 1 and ${toString minimumInterval}
          are ignored by anime_rpc.
        '';
      };

      extraArgs = mkOption {
        type = types.listOf types.str;
        default = [];
      };

      pollers = mkOption {
        type = let
          pollerOpts = poller: hasPort:
            mkOption {
              type = types.submodule {
                options =
                  {
                    enable = mkEnableOption "whether to enable ${poller} or not";
                  }
                  // lib.optionalAttrs hasPort {
                    port = mkOption {
                      type = types.nullOr types.port;
                      default = null;
                    };
                  };
              };
            };
        in
          types.submodule {
            options = {
              mpc = pollerOpts "MPC" true;
              mpvIpc = pollerOpts "mpv-ipc" false;
              mpvWebui = pollerOpts "mpv-webui" true;
            };
          };

        default = {};
      };
    };
  };

  config = mkIf cfg.enable {
    assertions = [
      {
        assertion = enabledPollers != {} || cfg.settings.webserver.enable;
        message = ''
          programs.anime_rpc requires either at least one poller enabled under
          programs.anime_rpc.settings.pollers or webserver integration enabled
          via programs.anime_rpc.settings.webserver.enable.
        '';
      }
      {
        assertion =
          cfg.settings.interval
          == 0
          || cfg.settings.interval >= minimumInterval;

        message = ''
          programs.anime_rpc.settings.interval
          must be either 0 or >= ${toString minimumInterval}.
        '';
      }
    ];

    programs.anime_rpc.settings.webserver.enable =
      mkDefault cfg.ui.enable;

    home.packages =
      [cfg.package]
      ++ optional cfg.ui.enable cfg.ui.package;

    systemd.user.services.anime_rpc = {
      Unit = {
        Description = "Anime RPC";
        After = ["graphical-session.target"];
        PartOf = ["graphical-session.target"];
      };

      Service = {
        ExecStart = "${cfg.package}/bin/anime_rpc ${lib.escapeShellArgs args}";

        Restart = "on-failure";
        RestartSec = 5;
      };

      Install.WantedBy = ["graphical-session.target"];
    };
  };
}
