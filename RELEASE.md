# Publishing a release on GitHub

GitHub **Releases** are a simple way to distribute the Windows app: users download one zip, extract it, and run `Labelmate.exe`. No installer required.

## Versioning

Use **0.0.x** while the app is still early and the feature set may change:

| Tag | Meaning |
|---|---|
| `v0.0.1` | First public build — works, but expect rough edges |
| `v0.0.2`, `v0.0.3`, … | Bug fixes and small improvements |
| `v1.0.0` | Save for when you’re happy calling it “stable” for daily use |

Tag format on GitHub: `v0.0.1` (with the `v` prefix).

## One-time setup

1. Create a repository on GitHub (e.g. `labelmate`).
2. Push this project (see commands at the bottom of this file).
3. In the repo README, replace `YOUR_USERNAME` in the Releases link with your GitHub username.

## Each new version

### 1. Build the app

```bat
build_exe.bat
```

### 2. Package for upload

```bat
package_release.bat
```

This creates `dist\Labelmate-windows.zip` ready for GitHub.

### 3. Create the GitHub Release

**On github.com:**

1. Open your repo → **Releases** → **Draft a new release**.
2. **Choose a tag:** e.g. `v0.0.1` → **Create new tag**.
3. **Release title:** e.g. `Labelmate 0.0.1`.
4. **Description:** see template below.
5. **Attach** `dist\Labelmate-windows.zip`.
6. Click **Publish release**.

Users will see the zip on the Releases page and can download it without cloning the repo.

## First release checklist (`v0.0.1`)

- [ ] Test print on your Brother QL-820NWB with DK-44205 tape
- [ ] Run `build_exe.bat` then `package_release.bat`
- [ ] Push source to GitHub (`main` branch)
- [ ] Create release tag `v0.0.1` and upload `Labelmate-windows.zip`
- [ ] Paste release notes (template below)

### Suggested release notes for `v0.0.1`

```markdown
Early preview build — feedback welcome.

**Requirements**
- Windows 10/11
- Brother QL-820NWB with official Brother driver (not Microsoft IPP)
- DK-44205 or compatible 62 mm roll (set in Printer Settings)

**Includes**
- Label catalog (brand / model / size)
- Live print preview
- Silent printing via Windows RAW
- System Check for driver and printer setup

**Known limitations**
- Pre-1.0: layout and features may change between releases
- Brother driver must be installed separately
```

## What to put in later release notes

- Supported printer: Brother QL-820NWB
- Supported roll: DK-44205 (62 mm black/white) and other rolls listed in Printer Settings
- Reminder: Brother driver required, not Microsoft IPP
- What changed since the last tag

## First-time git push (if the repo is not on GitHub yet)

```bat
git add .
git commit -m "Initial Labelmate source"
git branch -M main
git remote add origin https://github.com/Anton-Mergaerts/Labelmate.git
git push -u origin main
```

Then follow **Each new version** for tagged releases with the zip attached.
