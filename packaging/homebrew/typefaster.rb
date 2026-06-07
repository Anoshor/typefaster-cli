# Homebrew formula TEMPLATE for the TYPEFASTER CLI.
#
# This lives here for reference. The real formula belongs in your TAP repo
# (e.g. github.com/<you>/homebrew-typefaster as Formula/typefaster.rb).
#
# To produce a working formula:
#   1) Publish to PyPI first (the `url`/`sha256` below point at the PyPI sdist).
#   2) In your tap:  brew create --python https://files.pythonhosted.org/.../typefaster_cli-X.Y.Z.tar.gz
#      (or copy this file and edit url/sha256)
#   3) Auto-fill the dependency `resource` blocks:
#        brew update-python-resources Formula/typefaster.rb
#      (this fetches typer, rich, textual, httpx, websockets, click, etc.)
#   4) Test:  brew install --build-from-source Formula/typefaster.rb && brew test typefaster
#             brew audit --new --formula Formula/typefaster.rb

class Typefaster < Formula
  include Language::Python::Virtualenv

  desc "Terminal-first typing game (MonkeyType/TypeRacer style) with ghosts and multiplayer"
  homepage "https://github.com/<you>/typefaster-cli"
  url "https://files.pythonhosted.org/packages/source/t/typefaster-cli/typefaster_cli-0.1.0.tar.gz"
  sha256 "REPLACE_WITH_SDIST_SHA256"
  license "MIT"

  depends_on "python@3.12"

  # >>> `brew update-python-resources` fills resource "..." blocks here <<<

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "typefaster", shell_output("#{bin}/typefaster version")
  end
end
