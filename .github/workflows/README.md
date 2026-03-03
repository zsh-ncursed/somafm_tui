# GitHub Actions CI/CD

This project uses GitHub Actions for continuous integration and deployment.

## Workflows

### 1. CI (`.github/workflows/ci.yml`)

Runs on every push and pull request to `main` branch.

**What it does:**
- Tests on Python 3.8–3.12
- Installs system dependencies (MPV)
- Checks Python syntax
- Verifies package can be imported

### 2. Publish to AUR (`.github/workflows/publish-aur.yml`)

Runs automatically when a GitHub release is published.

**What it does:**
- Validates PKGBUILD version matches the release tag
- Updates the AUR package automatically

---

## Setup Instructions

### Required Secrets

To enable automatic AUR deployment, configure these secrets in GitHub repository settings:

**Settings → Secrets and variables → Actions → New repository secret:**

| Secret Name | Description | Value |
|-------------|-------------|-------|
| `AUR_USERNAME` | Your AUR username | `zsh-ncursed` |
| `AUR_EMAIL` | Your email for AUR commits | `zsh.ncursed@gmail.com` |
| `AUR_SSH_PRIVATE_KEY` | SSH private key for AUR access | See below |

### Generate SSH Key for AUR

1. **Generate SSH key:**
   ```bash
   ssh-keygen -t ed25519 -C "aur-somafm_tui" -f ~/.ssh/aur_github_actions
   ```

2. **Add public key to AUR:**
   - Login to https://aur.archlinux.org
   - Go to "SSH Keys" in your account settings
   - Add the content of `~/.ssh/aur_github_actions.pub`

3. **Add private key to GitHub secrets:**
   ```bash
   cat ~/.ssh/aur_github_actions | gh secret set AUR_SSH_PRIVATE_KEY
   ```
   
   Or manually: Settings → Secrets → Actions → New repository secret

---

## Release Process

### 1. Update Version

Update version in `PKGBUILD`:
```bash
pkgver=0.4.5
pkgrel=1
```

Update `source` to use the new tag:
```bash
source=("git+https://github.com/zsh-ncursed/somafm_tui.git#tag=v0.4.5")
```

### 2. Update CHANGELOG

Add new version section to `CHANGELOG.md`.

### 3. Commit and Push

```bash
git add PKGBUILD CHANGELOG.md
git commit -m "release: version 0.4.5"
git push origin main
```

### 4. Create Git Tag

```bash
git tag -a v0.4.5 -m "SomaFM TUI Player v0.4.5"
git push origin v0.4.5
```

### 5. Publish GitHub Release

1. Go to https://github.com/zsh-ncursed/somafm_tui/releases
2. Click "Draft a new release"
3. Select the tag `v0.4.5`
4. Add release title and description
5. Click "Publish release"

**This triggers the AUR deployment workflow!**

### 6. Verify AUR Update

Check the package was updated:
- https://aur.archlinux.org/packages/somafm_tui
- Build logs: https://github.com/zsh-ncursed/somafm_tui/actions

---

## Manual AUR Update

If automatic deployment fails, update manually:

```bash
# Clone AUR package
git clone ssh://aur@aur.archlinux.org/somafm_tui.git
cd somafm_tui

# Update from GitHub
git remote add github https://github.com/zsh-ncursed/somafm_tui.git
git fetch github

# Copy updated PKGBUILD
cp /path/to/github/somafm_tui/PKGBUILD .

# Update .SRCINFO
makepkg --printsrcinfo > .SRCINFO

# Commit and push
git add PKGBUILD .SRCINFO
git commit -m "Update to version 0.4.5"
git push
```

---

## Troubleshooting

### Workflow Fails

1. Check the Actions tab: https://github.com/zsh-ncursed/somafm_tui/actions
2. Review the error logs
3. Fix the issue and re-run

### Version Mismatch

Error: `PKGBUILD version does not match tag version`

**Solution:** Update `pkgver` in PKGBUILD to match the release tag.

### SSH Key Issues

Error: `Permission denied (publickey)`

**Solution:**
1. Verify SSH key is added to AUR account
2. Verify secret is correctly set in GitHub
3. Test SSH connection:
   ```bash
   ssh -T aur@aur.archlinux.org
   ```

---

## Local Testing

Test the workflow locally before pushing:

```bash
# Install act (https://github.com/nektos/act)
brew install act

# Run CI workflow locally
act push

# Run with specific job
act -j test
```
