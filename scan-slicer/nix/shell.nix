#TODO currently using system nixgl 
let pkgs = import (import ./sources.nix {}).nixpkgs-unstable {}; in
with pkgs;
(poetry2nix.mkPoetryEnv {
  projectDir = ../.;
  preferWheels = true;
  overrides = poetry2nix.overrides.withDefaults (self: super: {
    tesseract = super.tesseract.overridePythonAttrs (old: {
      nativeBuildInputs = (old.nativeBuildInputs or [ ]) ++ [ self.setuptools-scm ];
      });
    pyqt6 = super.pyqt6.overridePythonAttrs (o: {
      #autoPatchelfIgnoreMissingDeps = true;
      propagatedBuildInputs = (o.propagatedBuildInputs or [ ]) ++ [ qt6.full ];
      });
    pyqt6-qt6 = (super.pyqt6-qt6.override (o: {}))
      .overridePythonAttrs (o: {
      autoPatchelfIgnoreMissingDeps = true; #TODO

      #TODO WTF?
      propagatedBuildInputs = (o.buildInputs or [ ]) ++ [
        libxkbcommon
        xorg.libXrandr
        xorg.libxcb
        xorg.xcbutilwm
        xorg.xcbutil
        xorg.xcbutilimage
        xorg.xcbutilcursor
        xorg.xcbutilkeysyms
        xorg.xcbutilrenderutil
      ];

      });
    });
  }).env
.overrideAttrs (o: { 
    buildInputs = [
      jetbrains.pycharm-community
      ((qt6.callPackage (pkgs.path + "/pkgs/development/tools/gammaray") { }).overrideAttrs (o: { buildInputs = o.buildInputs ++ [ qt6.qtbase ]; src = fetchFromGitHub { owner = "KDAB"; repo = "gammaray"; rev = "master"; hash = "sha256-qhhtbNjX/sPMqiTPRW+joUtXL9FF0KjX00XtS+ujDmQ="; }; }))
#      ((qt6.callPackage (pkgs.path + "/pkgs/development/tools/gammaray") { }).overrideAttrs (o: { buildInputs = o.buildInputs ++ [ qt6.qtbase ]; cmakeFlags = [ "-DQT_VERSION_MAJOR=6" ] }))
      qt6.qttools
      git
      niv
      gdb
      ]; 
    })


