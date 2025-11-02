# Maintainer: zsh-ncursed <zsh.ncursed@protonmail.com>
pkgname=somafm_tui
pkgver=0.3.1.r1.g832525b
pkgrel=1
pkgdesc="A console-based player for SomaFM internet radio with stream buffering support"
arch=('any')
url="https://github.com/zsh-ncursed/somafm_tui"
license=('MIT')
depends=('python' 'mpv' 'python-requests' 'python-mpv' 'python-urllib3' 'python-dbus-next')
makedepends=('git')
source=("git+https://github.com/zsh-ncursed/somafm_tui.git#tag=v0.3.1")
sha256sums=('SKIP')

pkgver() {
    cd "$pkgname"
    git describe --long --tags | sed 's/\([^-]*-g\)/r\1/;s/-/./g;s/^v//'
}

prepare() {
    cd "$pkgname"
    
    # Create wrapper script for system installation
    cat > somafm_wrapper << 'EOF'
#!/usr/bin/env python3
import os
import sys

# Add system installation directory to PYTHONPATH
sys.path.insert(0, '/usr/lib/somafm_tui')

# Import and run application
from somafm import SomaFMPlayer
player = SomaFMPlayer()
player.run()
EOF
    chmod +x somafm_wrapper
}

package() {
    cd "$pkgname"
    
    # Create directories
    install -dm755 "$pkgdir/usr/bin"
    install -dm755 "$pkgdir/usr/lib/somafm_tui"
    install -dm755 "$pkgdir/usr/share/licenses/$pkgname"
    install -dm755 "$pkgdir/usr/share/doc/$pkgname"
    install -dm755 "$pkgdir/usr/share/bash-completion/completions"
    install -dm755 "$pkgdir/usr/share/fish/vendor_completions.d"
    
    # Install main Python files
    install -Dm755 somafm.py "$pkgdir/usr/lib/somafm_tui/somafm.py"
    install -Dm644 stream_buffer.py "$pkgdir/usr/lib/somafm_tui/stream_buffer.py"
    
    # Install executable wrapper
    install -Dm755 somafm_wrapper "$pkgdir/usr/bin/somafm"
    
    # Install shell completions if they exist
    [[ -f somafm.bash ]] && install -Dm644 somafm.bash "$pkgdir/usr/share/bash-completion/completions/somafm"
    [[ -f somafm.fish ]] && install -Dm644 somafm.fish "$pkgdir/usr/share/fish/vendor_completions.d/somafm"
    
    # Install documentation
    install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
    install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
    [[ -f VERSION ]] && install -Dm644 VERSION "$pkgdir/usr/share/doc/$pkgname/VERSION"
}
