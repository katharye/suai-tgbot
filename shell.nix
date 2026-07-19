{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  packages = with pkgs; [
    python313
    python313Packages.pip
    python313Packages.setuptools
    python313Packages.wheel
    rustc
    cargo

    pkg-config
    openssl
    libffi
    libxml2
    libxslt
    zlib
  ];

  shellHook = ''
    export PIP_BREAK_SYSTEM_PACKAGES=1

    FIRST_TIME=false

    if [ -z "$VIRTUAL_ENV" ]; then
      if [ ! -d ".venv" ]; then
        echo "Creating Python virtual environment (.venv)..."
        python -m venv .venv
        FIRST_TIME=true
      fi

      source .venv/bin/activate
    fi

    export PKG_CONFIG_PATH=${pkgs.lib.makeSearchPath "lib/pkgconfig" [
      pkgs.openssl
      pkgs.libffi
      pkgs.libxml2
      pkgs.libxslt
    ]}
    
    export LD_LIBRARY_PATH=${pkgs.lib.makeLibraryPath [
      pkgs.stdenv.cc.cc
      pkgs.openssl
      pkgs.zlib
    ]}:$LD_LIBRARY_PATH

    if [ "$FIRST_TIME" = true ]; then
      pip install -r requirements.txt
    fi
  '';
}