{
  description = "Flake for slack-react development and packaging";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      nixpkgs,
      flake-utils,
      ...
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs { inherit system; };
        python = pkgs.python312;
        pyPkgs = python.pkgs;
        slackSdk = pyPkgs."slack-sdk";

        slackReact = pyPkgs.buildPythonApplication {
          pname = "slack-react";
          version = "0.3.3";
          src = ./.;
          pyproject = true;
          nativeBuildInputs = with pyPkgs; [
            setuptools
            setuptools-scm
            wheel
          ];
          propagatedBuildInputs = [
            pyPkgs.appdirs
            pyPkgs.certifi
            pyPkgs.rich
            slackSdk
          ];
          pythonImportsCheck = [ "slack_react" ];
          meta = with pkgs.lib; {
            description = "Add reactions that spell out messages to Slack messages";
            homepage = "https://github.com/pschmitt/slack-react";
            license = licenses.gpl3Only;
            maintainers = with maintainers; [ pschmitt ];
            mainProgram = "slack-react";
          };
        };

        devTools = python.withPackages (
          ps: with ps; [
            appdirs
            certifi
            ipython
            rich
            ruff
            black
            typing-extensions
            slackSdk
          ]
        );
      in
      {
        packages = {
          default = slackReact;
          slack-react = slackReact;
        };

        devShells.default = pkgs.mkShell {
          name = "slack-react-devshell";
          packages = [
            devTools
            pkgs.git
            pkgs.pre-commit
            pkgs.uv
          ];
          shellHook = ''
            export PYTHONPATH="''${PWD}:''${PYTHONPATH:-}"
            export UV_PROJECT_ENVIRONMENT=".venv"
            echo "Entering slack-react dev shell (Python ${python.version})."
            echo "Run 'uv sync' to populate .venv and 'slack-react --help' to get started."
          '';
        };
      }
    );
}
