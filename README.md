# omae-wa-cheese-da

![](./cheese.png)

GPU arbitrary physical R/W (CVE-2025-21479) -> KASLR leak -> SELinux permissive -> RKP-safe init-hook root server -> DEFEX bypass custom binary exec (LD_PRELOAD)

It takes about 6 mins.. Be patient.

I'll optimize it later.

# Tested device

- Galaxy Z Flip 5 (SM-F731N)
- Firmware: F731NKSU5EYD9
- Android: 15
- Security patch: 2025-04-01
- SoC: Snapdragon 8 Gen 2 (SM8550 / kalama)
- GPU: Adreno 740 v2

# Requirements

- Security patch before August 2025
- Adreno A7xx GPU

# Patch check

Use the GPU firmware pattern:
```bash
xxd /vendor/firmware/a740_sqe.fw | grep -i "0300 422a"
```

If it matches, the firmware is vulnerable
```bash 
; vulnerable firmware (v675)
and $04, $12, 0x3

; patched firmware (v676)
and $04, $12, 0x7
```

# Usage

Connect the device with adb and run:
```bash 
./scripts/run.sh
```
The root server is not persistent. Run it once per boot.

Run shell commands as root:
```bash
./scripts/rootsh.sh 'id; getenforce'
```

This uses the resident root server running as u:r:sec_system_init_shell:s0, uid 0.

Stock binaries only. Custom binaries are blocked by DEFEX, so use rootbin.sh.

Run custom native binary as root:
```bash
./scripts/rootbin.sh example.so
```

# Tips

- If it hangs for more than a 15 mins, reboot and let the device cool down.

- GPU spraying is probabilistic. Retry or reboot if it fails.

- Disable software updates 

    Disable:
    ```bash
    pm disable-user --user 0 com.sec.android.soagent
    pm disable-user --user 0 com.wssyncmldm
    ```

    Re-enable:
    ```bash 
    pm enable --user 0 com.sec.android.soagent
    pm enable --user 0 com.wssyncmldm
    ``` 

# Notes

For authorized security research and education only. The exact device and firmware must match.