# Porting to Other Samsung A7xx Devices

This repo is hardcoded for Z Flip 5 (F731NKSU5EYD9, kernel 5.15.153)

To move to another device, replace build specific constants in src/exploit.c

Everything else (GPU R/W, Dirty Pagetable, DEFEX handling, init-hook etc..) is Samsung generic.

## Edit in src/exploit.c

### A. KASLR symbols/signature

Update:

- `FW_STEXT_VA`
- `FW_SWAPPER_PG_DIR_VA`
- `FW_INIT_TASK_VA`
- `FW_SELINUX_STATE_VA`
- `FW_STEXT_SIG1`
- `FW_STEXT_SIG2`
- `expected_words[6]`

Get symbol VAs by running cheese-cake helpers/extract-kallsyms.c on the boot kernel and grepping the symbols.

Get the signature by dumping the first 6 words of `_stext`

### B. Physical base / spray

Update only if needed:

- `KERNEL_PHYS_BASE`
- the scan window in `find_fw_stext_for_chain`
- `gPhyAddrs[]`

Usually leave this group as-is

KERNEL_PHYS_BASE is 0xa8000000 on modern SoCs, and the binary already auto-sweeps gPhyAddrs[] on each run through maybe_retry. CHEESE_ATTEMPT is only an optional manual start index.

Revisit this only if every attempt fails. cheese-cake helpers/find_phyaddr.c (root required) can suggest candidates.

### C. Struct offsets

Update:

- `OFFSETOF_TASK_STRUCT_TASKS`
- `OFFSETOF_TASK_STRUCT_MM`
- `OFFSETOF_TASK_STRUCT_PID`
- `OFFSETOF_MM_PGD`
- `OFFSETOF_MM_START_CODE`
- `OFFSETOF_MM_END_CODE`

Run cheese-cake helpers/extract_struct_offsets.sh <vmlinux>

It omits start_code / end_code, so get those separately with:

```bash
pahole -C mm_struct
```

or pull device BTF after permissive:

```bash
adb pull /sys/kernel/btf/vmlinux
```

### D. Init-hook

Update:

- `INIT_TEXT_FILE_VA`
- `INIT_HOOK_PATCH_FILE_VA` (`__system_property_update@plt`)
- `INIT_HOOK_PATCH_EXPECT0..3`
- `INIT_HOOK_CAVE_FILE_VA`
- `INIT_HOOK_CAVE_EXPECT0`

Load /system/bin/init in Decompiler and identify:

- the PLT stub file VA and its 4 expected words,
- a zero-padding cave after the executable LOAD segment,
- the executable LOAD segment p_vaddr

## Images (offline)

Firmware: download via SamFw.. 

For A:

- boot.img -> magiskboot unpack -> kernel

For D:

- super.img -> lpunpack -> simg2img -> system -> /system/bin/init

## SELinux

This device has `CONFIG_SECURITY_SELINUX_DEVELOP=y`, so run_selinux_rmw() just writes selinux_state.enforcing = 0 after the KASLR leak.

If this option is disabled (e.g. S24 Ultra), that field is absent and the write fails.

In that case, manipulate the policy instead, such as forging an ebitmap node or setting allow_unknown.

Check:

```bash
adb shell zcat /proc/config.gz | grep CONFIG_SECURITY_SELINUX_DEVELOP
```

## Build / Run? 

See README.md
