{
  description = "Development shell for www.bovbel.com";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = {nixpkgs, ...}: let
    system = "x86_64-linux";
    pkgs = import nixpkgs {inherit system;};
    cdk = pkgs.writeShellScriptBin "cdk" ''
      exec npm exec --yes --package aws-cdk@2.1128.1 -- cdk "$@"
    '';
  in {
    devShells.${system}.default = pkgs.mkShell {
      packages = [
        cdk
        pkgs.nodejs
        pkgs.uv
      ];

      LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
        pkgs.stdenv.cc.cc.lib
      ];
    };
  };
}
