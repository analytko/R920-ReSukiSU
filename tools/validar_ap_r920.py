"""Valida o AP SM-R920 antes de gravar no relógio."""

import argparse
import gzip
import hashlib
import struct
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PART_SIZE = 37748736
REQUIRED_DM = ("MD", "BLK_DEV_DM", "DM_VERITY", "DM_CRYPT", "DM_DEFAULT_KEY", "DM_INIT")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def octal(field):
    value = field.strip(b" \x00")
    require(bool(value) and all(c in b"01234567" for c in value), "campo TAR octal invalido")
    return int(value, 8)


def read_ustar(ap_path):
    entries = {}
    with ap_path.open("rb") as source:
        while True:
            header = source.read(512)
            require(len(header) == 512, "TAR truncado")
            if header == bytes(512):
                require(source.read(512) == bytes(512), "fim do TAR sem dois blocos vazios")
                require(not source.read().strip(b"\x00"), "dados apos o fim do TAR")
                break
            require(header[257:263] == b"ustar\x00", "cabecalho TAR nao e USTAR (PAX proibido)")
            require(header[156:157] in (b"0", b"\x00"), "entrada TAR nao regular ou cabecalho PAX")
            require(not header[345:500].strip(b"\x00"), "prefixo USTAR inesperado")
            checksum = octal(header[148:156])
            calculated = sum(header[:148]) + 8 * 32 + sum(header[156:])
            require(checksum == calculated, "checksum do cabecalho TAR invalido")
            name = header[:100].split(b"\x00", 1)[0].decode("ascii")
            require(name in ("boot.img", "vbmeta.img") and name not in entries,
                    f"entrada TAR inesperada ou repetida: {name}")
            size = octal(header[124:136])
            require(size <= PART_SIZE, f"entrada TAR grande demais: {name}")
            data = source.read(size)
            require(len(data) == size, f"entrada TAR truncada: {name}")
            padding = (512 - size % 512) % 512
            require(len(source.read(padding)) == padding, "padding TAR truncado")
            entries[name] = data
    require(set(entries) == {"boot.img", "vbmeta.img"}, "AP deve conter so boot.img e vbmeta.img")
    return entries


def sections(image):
    require(len(image) == PART_SIZE, f"boot.img deve ter {PART_SIZE} bytes")
    require(image[:8] == b"ANDROID!", "boot.img sem magia ANDROID!")
    u32 = lambda offset: struct.unpack_from("<I", image, offset)[0]
    page, version, header_size = u32(36), u32(40), u32(1644)
    require((page, version, header_size) == (2048, 2, 1660), "boot.img nao e header v2/page 2048")
    sizes = (u32(8), u32(16), u32(24), u32(1632), u32(1648))
    pad = lambda size: (size + page - 1) // page * page
    offset = page
    result = []
    for size in sizes:
        require(offset + size <= len(image), "secao boot fora da particao")
        result.append(image[offset:offset + size])
        offset += pad(size)
    recovery_offset = struct.unpack_from("<Q", image, 1636)[0]
    if sizes[3]:
        expected = page + sum(pad(size) for size in sizes[:3])
        require(recovery_offset == expected, "offset recovery DTBO incorreto")
    require(offset + 4096 < PART_SIZE, "boot sem espaco para footer AVB")
    return result


def boot_id(parts):
    sha = hashlib.sha1()
    for part in parts:
        sha.update(part)
        sha.update(struct.pack("<I", len(part)))
    return sha.digest().ljust(32, b"\x00")


def validate(ap_path, config_path, stock_path, image_path=None):
    entries = read_ustar(ap_path)
    boot = entries["boot.img"]
    parts = sections(boot)
    require(parts[0].startswith(b"\x1f\x8b"), "kernel do AP nao esta em gzip")
    require(len(parts[0]) <= 28516000, "kernel gzip excede budget 28516000")
    require(boot[576:608] == boot_id(parts), "id SHA-1 do boot.img nao confere")

    try:
        raw_kernel = gzip.decompress(parts[0])
    except (OSError, EOFError) as exc:
        raise ValueError(f"gzip do kernel invalido: {exc}") from exc
    if image_path is not None:
        require(raw_kernel == image_path.read_bytes(), "kernel gzip difere de Image-ReSukiSU-R920")

    stock = sections(stock_path.read_bytes())
    for index, name in ((1, "ramdisk"), (2, "second"), (3, "recovery DTBO"), (4, "DTB")):
        require(parts[index] == stock[index], f"{name} difere do stock DZE1")

    config = set(config_path.read_text(encoding="utf-8").splitlines())
    for symbol in REQUIRED_DM:
        require(f"CONFIG_{symbol}=y" in config, f"CONFIG_{symbol}=y ausente em resukisu.config")
    require('CONFIG_LOCALVERSION="-33003255-abR920XXS2DZE1"' in config,
            "LOCALVERSION diferente do stock DZE1")
    print(f"AP OK: USTAR, 2 entradas, kernel gzip {len(parts[0])} bytes, id SHA-1, secoes stock e 6 opcoes DM")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ap", nargs="?", type=Path, default=ROOT / "dist/R920_ReSukiSU_AP.tar")
    parser.add_argument("--config", type=Path, default=ROOT / "dist/resukisu.config")
    parser.add_argument("--stock", type=Path,
                        default=Path("C:/GitHub/firmware-watch5/stock-ZTO-DZE1/boot.img"))
    parser.add_argument("--image", type=Path, help="Image bruto para comparar com kernel gzip")
    args = parser.parse_args()
    try:
        validate(args.ap, args.config, args.stock, args.image)
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"AP INVALIDO: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
