# Testbed machine setup: commands for YOU to run

Nothing in this repository changes a system setting. `testbed/preflight.py` only checks. Every command below that needs
`sudo` is yours to run, on **each** of the four machines, in the same order. Python is 3.12 and the OS is Ubuntu 24.04 on all four
(the preflight comparison fails if they differ).

## A. A machine that has just been installed (no repository yet)

```bash
sudo apt update && sudo apt full-upgrade -y
sudo reboot
```

After the reboot, **check that all four report the same kernel** (`uname -r`). If not, upgrade again until they match.

```bash
sudo apt install -y git rsync curl python3-venv python3-pip build-essential gh iw chrony
gh auth login          # GitHub.com, HTTPS, "Authenticate Git", browser (the repository is private)
git clone https://github.com/Ahooraa/wait-shift.git ~/DFPS-implementation
cd ~/DFPS-implementation
git checkout <branch-with-testbed>      # until the testbed is merged into main
bash testbed/bootstrap.sh               # creates ~/venv-dfps with the pinned packages, runs the preflight
```

Only the **coordinator** needs the data (about 11 GB). The coordinator builds the scenario and sends it to the agents, so the
other three machines need the code and the Python packages only. Copy the data to the coordinator exactly as in the first
migration (from the old D: volume, read-only mount), then run
`python testbed/preflight.py report --role coordinator`.

## B. Settings for measured runs (apply on all four, then verify)

Apply one block at a time and re-run `python testbed/preflight.py report --measured` after each. Each block lists how to undo it.

**1. Pin the kernel** (all four machines must already run the same one):
```bash
sudo apt-mark hold linux-image-generic linux-headers-generic linux-generic "linux-image-$(uname -r)" "linux-headers-$(uname -r)"
```
Undo: `sudo apt-mark unhold <the same names>`.

**2. Automatic updates off:**
```bash
sudo systemctl disable --now apt-daily.timer apt-daily-upgrade.timer
printf 'APT::Periodic::Update-Package-Lists "0";\nAPT::Periodic::Unattended-Upgrade "0";\n' | sudo tee /etc/apt/apt.conf.d/20auto-upgrades
sudo snap refresh --hold
```
Undo: `sudo systemctl enable --now apt-daily.timer apt-daily-upgrade.timer`, set both values back to "1", `sudo snap refresh --unhold`.

**3. Swap off** (these machines have 8 or 16 GB; agents use little memory, but check `free -h` during a trial run):
```bash
sudo swapoff -a
sudo sed -i.bak '/\sswap\s/ s/^/#/' /etc/fstab
```
Undo: restore `/etc/fstab.bak`, `sudo swapon -a`.

**4. CPU governor `performance`, persistent:**
```bash
sudo apt install -y linux-tools-common "linux-tools-$(uname -r)"
printf '[Unit]\nDescription=CPU governor performance\n[Service]\nType=oneshot\nExecStart=/usr/bin/cpupower frequency-set -g performance\n[Install]\nWantedBy=multi-user.target\n' | sudo tee /etc/systemd/system/cpu-performance.service
sudo systemctl daemon-reload && sudo systemctl enable --now cpu-performance.service
```
Undo: `sudo systemctl disable --now cpu-performance.service` and `sudo cpupower frequency-set -g powersave`.
Laptops still throttle under sustained heat. Keep the same cooling and room for every run. Turbo is a separate choice: turning it
off (`echo 1 | sudo tee /sys/devices/system/cpu/intel_pstate/no_turbo`, not persistent) lowers variance but also speed; decide once
and do it on all four.

**5. Time sync with chrony** (installed in part A; it replaces systemd-timesyncd):
```bash
sudo systemctl enable --now chrony
chronyc tracking
```
Wait a few minutes; the offset should be a few milliseconds or less. Over Wi-Fi the measured clock offset between laptops
(`netprobe` below) is logged with every run, so residual offset is corrected in the analysis, not ignored.

**6. Wi-Fi power saving off** (drops the Wi-Fi connection for a moment):
```bash
printf '[connection]\nwifi.powersave = 2\n' | sudo tee /etc/NetworkManager/conf.d/wifi-powersave-off.conf
sudo systemctl restart NetworkManager
```
Undo: delete that file and restart NetworkManager.

**7. No sleep, lid closed is fine:**
```bash
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
sudo sed -i 's/^#\?HandleLidSwitch=.*/HandleLidSwitch=ignore/; s/^#\?HandleLidSwitchExternalPower=.*/HandleLidSwitchExternalPower=ignore/' /etc/systemd/logind.conf
```
Undo: `sudo systemctl unmask ...` and restore the two lines.

**8. Text boot target, last, and only for measured sessions.** Before you switch, make the Wi-Fi connect without anyone logged in,
or the machine will boot with no network:
```bash
nmcli connection show                                   # note the Wi-Fi connection name
nmcli connection modify "<name>" connection.autoconnect yes connection.permissions "" 802-11-wireless-security.psk-flags 0
sudo apt install -y openssh-server                      # lets the coordinator start agents on a machine with no desktop
sudo systemctl set-default multi-user.target            # takes effect at the next boot
```
Undo: `sudo systemctl set-default graphical.target`. In text mode the Claude desktop app does not run on that machine, so
use the terminal or SSH. The agents are headless and do not need a desktop.

## C. Verify, then probe the network

On every machine:
```bash
cd ~/DFPS-implementation && source ~/venv-dfps/bin/activate
python testbed/preflight.py report --role agent --measured --out ~/report_$(hostname).json     # the coordinator: --role coordinator
```
Copy the four JSON files to one machine (USB stick or `scp`) and run
`python testbed/preflight.py compare report_*.json`. Every line must be PASS or INFO.

Wi-Fi probe: start the server on every machine (`python testbed/preflight.py netserver`), then on each machine run
`python testbed/preflight.py netprobe --peers IP2,IP3,IP4 --out ~/net_$(hostname).json` with the other three IP addresses
(`hostname -I`). Run it at a quiet time and again at the time of day you plan to run experiments.
