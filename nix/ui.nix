{
  lib,
  rustPlatform,
  pkg-config,
  wrapGAppsHook3,
  copyDesktopItems,
  makeDesktopItem,
  gtk3,
  glib,
  cairo,
  pango,
  atk,
  gdk-pixbuf,
  vulkan-loader,
  wayland,
  libxkbcommon,
  xorg,
  xdotool,
  libayatana-appindicator,
}:
rustPlatform.buildRustPackage {
  pname = "anime_rpc_ui";
  version = "0.1.0";

  src = ../ui;

  cargoLock = {
    lockFile = ../ui/Cargo.lock;
  };

  nativeBuildInputs = [
    pkg-config
    wrapGAppsHook3
    copyDesktopItems
  ];

  buildInputs = [
    gtk3
    glib
    cairo
    pango
    atk
    gdk-pixbuf
    vulkan-loader
    wayland
    libxkbcommon
    xdotool
    xorg.libX11
    xorg.libXcursor
    xorg.libXi
    xorg.libXrandr
  ];

  desktopItems = [
    (makeDesktopItem {
      name = "anime-rpc"; # FIXME: either use dash or underscore
      desktopName = "Anime RPC";
      exec = "anime_rpc_ui";
      icon = "anime-rpc";
      comment = "Configure Anime Rich Presence";
      categories = ["Utility" "Settings"];
      startupNotify = true;
    })
  ];

  postInstall = ''
    install -Dm644 assets/icon.png $out/share/icons/anime-rpc.png
  '';

  postFixup = ''
    wrapProgram $out/bin/anime_rpc_ui \
      --prefix LD_LIBRARY_PATH : ${lib.makeLibraryPath [
      vulkan-loader
      wayland
      libxkbcommon
      libayatana-appindicator
    ]}
  '';

  meta = with lib; {
    description = "Configuration UI for Anime RPC";
    license = licenses.mit;
    mainProgram = "anime_rpc_ui";
    platforms = platforms.linux;
  };
}
