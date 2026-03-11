{
  description = "A Nix-flake-based Node.js development environment";

  inputs.nixpkgs.url = "nixpkgs/nixos-unstable";

  outputs = {self, ...} @ inputs: let
    supportedSystems = [
      "x86_64-linux"
      "aarch64-linux"
      "x86_64-darwin"
      "aarch64-darwin"
    ];
    forEachSupportedSystem = f:
      inputs.nixpkgs.lib.genAttrs supportedSystems (
        system:
          f {
            pkgs = import inputs.nixpkgs {
              inherit system;
              overlays = [inputs.self.overlays.default];
            };
          }
      );
    pyVersion = "3.13";
  in {
    overlays.default = final: prev: rec {
      nodejs = prev.nodejs;
      yarn = prev.yarn.override {inherit nodejs;};
    };

    devShells = forEachSupportedSystem (
      {pkgs}: let
        concatMajorMinor = v:
          pkgs.lib.pipe v [
            pkgs.lib.versions.splitVersion
            (pkgs.lib.sublist 0 2)
            pkgs.lib.concatStrings
          ];

        python = pkgs."python${concatMajorMinor pyVersion}";
      in {
        default = pkgs.mkShellNoCC {
          venvDir = ".venv";

          PYTHONPATH = (builtins.getEnv "PWD") + "/py_modules";

          packages = with pkgs;
            [
              nodejs
              nodePackages.pnpm
              yarn
            ]
            ++ (with python.pkgs; [
              venvShellHook
              basedpyright
              pip
              ipython
            ]);
        };
      }
    );
  };
}
