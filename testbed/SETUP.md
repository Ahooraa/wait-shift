# Testbed machines: step-by-step setup, no help needed

Do Parts 1 to 5 on **each of the four laptops** (about an hour each, mostly downloads). Part 6 is for the one machine that will be
the coordinator. Every command is written out in full. After each step there is a **Check** that shows what the right result looks
like. Nothing in this repository changes a system setting by itself; every `sudo` command here is yours to run.

How to read this file:
- Open a terminal with **Ctrl+Alt+T**. Type (or copy) each grey block exactly. Do not type a leading `$`.
- After `sudo`, Ubuntu asks for your password. Nothing appears while you type it. That is normal.
- **If a command prints an error you do not understand: stop.** Write down the command and the error text (or take a photo of the
  screen) and bring it back to Claude. Do not continue with the next step.
- Keep this file on your phone, on paper, or on a USB stick. The first steps happen before the code is on the machine.

## Part 0: Before you start

- [ ] Each laptop is plugged into power and running Ubuntu **24.04**. Check: `lsb_release -d` must print `Ubuntu 24.04...`.
      If a machine prints something else, stop and tell Claude: the pinned software only works on 24.04.
- [ ] You have the house Wi-Fi password, your GitHub login (account Ahooraa), a USB stick, and a phone for the GitHub login code.
- [ ] You have a way to write things down: use the table in Part 7.

## Part 1: Install (every machine)

**1.1 Connect to the house Wi-Fi.** Open Settings, then Wi-Fi, and choose the network. If the router shows two names (for example
one ending in `-5G`), choose the 5 GHz one. Check:
```bash
nmcli -t -f ACTIVE,SSID,CHAN,RATE,SIGNAL device wifi | grep '^yes'
```
It prints one line with your network name. A channel number above 30 (for example 36 to 165) means 5 GHz.

**1.2 Give the machine its own name** (`dfps-1`, `dfps-2`, `dfps-3`, `dfps-4`: a different one on each machine, because the
checks identify machines by name):
```bash
sudo hostnamectl set-hostname dfps-2
```
Replace `dfps-2` with this machine's number. Check (open a new terminal first):
```bash
hostname
```

**1.3 Update everything, then restart:**
```bash
sudo apt update && sudo apt full-upgrade -y
```
```bash
sudo reboot
```

**1.4 After the restart, write down the kernel version** (all four machines must print the same):
```bash
uname -r
```
If the machines print different versions, stop and tell Claude which ones. Do not go on to Part 2.

**1.5 Install the tools:**
```bash
sudo apt install -y git rsync curl python3-venv python3-pip build-essential gh iw chrony
```
Check: `git --version` and `gh --version` each print a version.

**1.6 Log in to GitHub** (the repository is private):
```bash
gh auth login
```
Answer the questions: `GitHub.com`, then `HTTPS`, then `Y` to authenticate Git with your GitHub credentials, then `Login with a web
browser`. It prints an 8-character code. Open https://github.com/login/device on any device (your phone is fine), type the code and
approve. Check:
```bash
gh auth status
```
It must say `Logged in to github.com account Ahooraa`.

**1.7 Get the code:**
```bash
git clone https://github.com/Ahooraa/wait-shift.git ~/DFPS-implementation
```
```bash
cd ~/DFPS-implementation && git checkout testbed/phase-1
```
Check: `git log --oneline -1` prints a line starting with `meta: testbed phase 1`.

**1.8 Build the Python environment** (several minutes, about 500 MB download):
```bash
cd ~/DFPS-implementation && bash testbed/bootstrap.sh
```
Check: it ends with `environment ready: ...` and a report. Lines marked `WARN` are expected until Part 2 is done. A `FAIL` on
`packages` or `numba` means the install did not work: stop and tell Claude.

You do **not** need the Claude app on these machines.

## Part 2: Settings for measured runs (every machine, in this order)

Check after each step with the **Check** lines. Undo commands are in Part 8.

**2.1 Keep the kernel from changing:**
```bash
dpkg -l | awk '/^ii/ && $2 ~ /^linux-(image|headers|modules|generic)/ {print $2}' | xargs sudo apt-mark hold
```
Check: `apt-mark showhold` lists several `linux-...` names.

**2.2 Turn automatic updates off:**
```bash
sudo systemctl disable --now apt-daily.timer apt-daily-upgrade.timer
```
```bash
printf 'APT::Periodic::Update-Package-Lists "0";\nAPT::Periodic::Unattended-Upgrade "0";\n' | sudo tee /etc/apt/apt.conf.d/20auto-upgrades
```
```bash
sudo snap refresh --hold
```
Check: `systemctl is-enabled apt-daily.timer apt-daily-upgrade.timer` prints `disabled` twice, and `cat /etc/apt/apt.conf.d/20auto-upgrades`
shows two lines ending in `"0";`.

**2.3 Turn swap off:**
```bash
sudo swapoff -a
```
```bash
sudo sed -i.bak '/\sswap\s/ s/^/#/' /etc/fstab
```
Check: `swapon --show` prints nothing, and `free -h` shows `Swap: 0B`.

**2.4 CPU governor "performance", now and after every restart:**
```bash
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```
```bash
sudo tee /etc/systemd/system/cpu-performance.service >/dev/null <<'EOF'
[Unit]
Description=CPU governor performance
[Service]
Type=oneshot
ExecStart=/bin/sh -c 'for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo performance > "$g"; done'
[Install]
WantedBy=multi-user.target
EOF
```
```bash
sudo systemctl daemon-reload && sudo systemctl enable --now cpu-performance.service
```
Check:
```bash
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor | sort | uniq -c
```
Every line must say `performance`.

**2.5 Clock synchronisation:**
```bash
sudo systemctl enable --now chrony
```
Wait two minutes, then check:
```bash
chronyc tracking
```
`Leap status` must be `Normal`, and `System time` should be a few thousandths of a second at most. `chronyc sources` shows the servers;
the one marked `*` is the one in use. The router must be online for this.

**2.6 Wi-Fi power saving off** (the Wi-Fi drops for about ten seconds):
```bash
sudo tee /etc/NetworkManager/conf.d/wifi-powersave-off.conf >/dev/null <<'EOF'
[connection]
wifi.powersave = 2
EOF
```
```bash
sudo systemctl restart NetworkManager
```
Check: run `iw dev` and note the name after `Interface` (for example `wlo1`), then:
```bash
iw dev wlo1 get power_save
```
Use your own interface name. It must print `Power save: off`.

**2.7 No sleep or suspend, even with the lid closed:**
```bash
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
```
```bash
sudo mkdir -p /etc/systemd/logind.conf.d
```
```bash
sudo tee /etc/systemd/logind.conf.d/testbed.conf >/dev/null <<'EOF'
[Login]
HandleLidSwitch=ignore
HandleLidSwitchExternalPower=ignore
HandleLidSwitchDocked=ignore
EOF
```
Check: `systemctl is-enabled sleep.target` prints `masked`.

**2.8 Restart and check that the settings stuck:**
```bash
sudo reboot
```
Then:
```bash
~/venv-dfps/bin/python ~/DFPS-implementation/testbed/preflight.py report --measured
```
Everything must be `PASS` or `INFO` **except** the line `boot target = multi-user (text)`, which stays FAIL until Part 5. If the governor
went back to `powersave` after the restart, run `sudo systemctl disable --now power-profiles-daemon`, restart again and recheck.
Anything else marked `FAIL`: write down the line and bring it back to Claude.

## Part 3: Compare the machines with each other

**3.1 On every machine, save its report:**
```bash
~/venv-dfps/bin/python ~/DFPS-implementation/testbed/preflight.py report --role agent --measured --out ~/report_$(hostname).json
```
On the coordinator use `--role coordinator` (after Part 6).

**3.2 Copy the four `report_dfps-N.json` files to one machine** with the USB stick (drag them in the file manager from your home
folder), and put them all in one folder there, for example `~/reports`.

**3.3 Compare:**
```bash
~/venv-dfps/bin/python ~/DFPS-implementation/testbed/preflight.py compare ~/reports/report_*.json
```
Every line must say `PASS` or `INFO`. A `FAIL` names the field that differs and the value on each machine: write it down.

## Part 4: Check that the laptops can talk to each other

**4.1 On every machine, find its address and write it in the table in Part 7:**
```bash
hostname -I
```
Use the first number, which looks like `192.168.1.23`.

**4.2 See whether the firewall is on:**
```bash
sudo ufw status
```
`Status: inactive` is fine. If it says `active`, write that down and bring it back.

**4.3 On every machine, start the answering program** (leave this terminal open and open a new one for the next step):
```bash
~/venv-dfps/bin/python ~/DFPS-implementation/testbed/preflight.py netserver
```

**4.4 On each machine, test the other three.** Use their addresses from the table (here `IP2,IP3,IP4` are placeholders):
```bash
~/venv-dfps/bin/python ~/DFPS-implementation/testbed/preflight.py netprobe --peers IP2,IP3,IP4 --out ~/net_$(hostname).json
```
It prints one line per machine with delay, clock difference and speed in MB/s. A `connection refused` or timeout error means the
router is blocking laptop-to-laptop traffic ("AP isolation" or a guest network in the router settings) or the program in 4.3 is not
running. Write down the exact lines, and bring them back. Do this once when the house is quiet and once at the time of day you
plan to run experiments.

## Part 5: Text boot mode (last, only after Parts 1 to 4 work)

In text mode the machine starts without the desktop. The experiment programs do not need a desktop, but **you cannot use the
desktop on that machine** until you switch back (Part 8).

**5.1 Let the Wi-Fi connect without anyone logged in.** In Settings, then Wi-Fi, click the gear next to your network. Under
**Identity**, tick **Make available to other users** and **Connect automatically**, then Apply. (Command line alternative, with your
network's name from `nmcli connection show` and its password:)
```bash
nmcli connection modify "NETWORK NAME" connection.autoconnect yes connection.permissions "" 802-11-wireless-security.psk-flags 0 802-11-wireless-security.psk "WIFI PASSWORD"
```

**5.2 Switch the default boot to text mode and restart:**
```bash
sudo systemctl set-default multi-user.target
```
```bash
sudo reboot
```

**5.3 Check:** a text login screen appears. Log in, then:
```bash
nmcli device status
```
The Wi-Fi line must say `connected`. If it does not, go back with `sudo systemctl set-default graphical.target` then `sudo reboot`,
and repeat 5.1.

**5.4 Optional, for starting the programs remotely from another laptop later:**
```bash
sudo apt install -y openssh-server
```
Check: `systemctl is-active ssh` prints `active`.

## Part 6: Coordinator only: the data (about 11 GB)

Only the coordinator needs the data folders; the other three machines do not. If the coordinator is **this** laptop (the one that
already has them) you are done. If it is another machine, copy the four folders `results`, `input/data`, `data` and `library` from
this laptop in one of two ways.

With a USB drive (at least 16 GB): copy `~/DFPS-implementation/results`, `input/data`, `data` and `library` onto it, then onto the
coordinator at the same places under `~/DFPS-implementation`.

Over Wi-Fi (about 20 minutes; the coordinator needs `openssh-server` from 5.4). Run this **on this laptop**, with the coordinator's
address and user name:
```bash
cd ~/DFPS-implementation && for p in results input/data data library; do rsync -a --info=progress2 "$p/" USER@COORDINATOR_IP:~/DFPS-implementation/$p/; done
```
Then on the coordinator:
```bash
echo "$HOME/DFPS-implementation/library" > ~/DFPS-implementation/.research-library
```
```bash
~/venv-dfps/bin/python ~/DFPS-implementation/testbed/preflight.py report --role coordinator --measured
```
The three `data present` lines must say `PASS`.

## Part 7: Record sheet (fill in, then bring it back)

| Machine | Hostname | Wi-Fi address | Kernel (`uname -r`) | Cores and RAM (`lscpu`, `free -h`) | Ethernet port? |
|---|---|---|---|---|---|
| 1 | dfps-1 | | | | |
| 2 | dfps-2 | | | | |
| 3 | dfps-3 | | | | |
| 4 | dfps-4 | | | | |

**Bring back to Claude:** this table; the output of Part 3.3; the printed lines of Part 4.4; any line marked `FAIL`; the result of
`sudo ufw status`; and which machine you think is strongest (most cores and RAM).

## Part 8: Undo (only if you need the old behaviour back)

| Step | Undo |
|---|---|
| 2.1 | `dpkg -l \| awk '/^hi/ {print $2}' \| xargs sudo apt-mark unhold` |
| 2.2 | `sudo systemctl enable --now apt-daily.timer apt-daily-upgrade.timer`, set both values in `/etc/apt/apt.conf.d/20auto-upgrades` back to `"1"`, `sudo snap refresh --unhold` |
| 2.3 | `sudo mv /etc/fstab.bak /etc/fstab && sudo swapon -a` |
| 2.4 | `sudo systemctl disable --now cpu-performance.service`, then `echo powersave \| sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor` |
| 2.5 | `sudo systemctl disable --now chrony` |
| 2.6 | `sudo rm /etc/NetworkManager/conf.d/wifi-powersave-off.conf && sudo systemctl restart NetworkManager` |
| 2.7 | `sudo systemctl unmask sleep.target suspend.target hibernate.target hybrid-sleep.target && sudo rm /etc/systemd/logind.conf.d/testbed.conf` |
| 5.2 | `sudo systemctl set-default graphical.target` then `sudo reboot` |

If a machine boots to a black screen or a text login and you want the desktop: log in at the text screen and run
`sudo systemctl set-default graphical.target && sudo reboot`.
