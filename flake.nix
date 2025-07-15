{
  description = "Flake for Blender plugin development";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs, ... }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs {
        inherit system;
        config = { allowUnfree = true; };
      };
      blender = pkgs.blender;
    in {
      devShells.${system}.default = pkgs.mkShell {
        buildInputs = [
          blender
          pkgs.python311
        ];

        shellHook = ''
          echo "🧩 Using Blender version: ${blender.version}"
          export BLENDER_PATH=${blender}/bin/blender
          export PYTHONPATH=$PWD/src:$PYTHONPATH
          echo "Run: \$BLENDER_PATH --python-expr 'import bpy; print(bpy.app.version)'"
          
          source ./.venv/bin/activate
          pip install -r requirements.txt
        '';
      };
    };
}

