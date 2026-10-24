# SM-R920 ReSukiSU — notas da adaptação (R920XXS2DZE1)

Fork de `ItsJustJoshDev/AlphaKernel-R960` adaptado para o Galaxy Watch 5 `SM-R920`.
Workflow: `.github/workflows/Build-R920.yml`.

## O que mudou em relação ao R960

- Sem `init_boot`: o `SM-R920` não tem partição `init_boot` (`by-name` só tem
  `boot`, `recovery`, `dtbo`, `vbmeta`, `vbmeta_system`). O pacote AP leva só
  `boot.img` + `vbmeta.img`.
- `boot.img` é header **v2**, `page_size 2048`, com ramdisk de 9109284 bytes e
  dtb de 116820 bytes (o R960 era v4 com ramdisk 0). O repack preserva
  ramdisk + dtb do stock e troca só o kernel.
- Partição `boot` = 37748736 bytes (36864 KiB). Com ramdisk + dtb, o kernel
  precisa ficar abaixo de ~28,5 MB — o workflow falha com mensagem clara se
  passar (e tenta desligar `DEBUG_INFO*`).
- `rollback_index 0` (stock), `security_patch 2026-05-05`, `os_version 16`.
- `LOCALVERSION "-ReSukiSU-33003255-abR920XXS2DZE1"`, `TARGET_SOC s5e5515`.
- `DEFCONFIG` padrão `s5e5515-projectxblue_defconfig` (por analogia ao
  `wise6blue`; o workflow lista os candidatos e falha explicando se não achar).

## O que falta (manual, sem como automatizar daqui)

1. Fonte do kernel do R920: em `https://opensource.samsung.com`
   (Mobile > Wearable/IoT > `SM-R920`), baixar o pacote da build `DZE1`
   (ou o compatível mais próximo). O site bloqueia robôs (Cloudflare) —
   baixar no navegador e conferir o conteúdo.
2. No fork, criar a Release `source-tarballs` com `Kernel.tar.gz` +
   o `R920*_Kernel.tar.gz` baixado. O fonte do R960 **não serve**:
   só tem `s5e5515-wise6blue_defconfig` e `s5e5515-fresh6bsue_defconfig`,
   nenhum `projectx`.
3. A Release `firmware-r920-dze1` já está criada com `boot.img` e
   `vbmeta.img` stock do `R920XXS2DZE1` (ZTO).
4. Rodar o workflow `Build SM-R920 ReSukiSU AP` na aba Actions com
   `source_release_tag=source-tarballs`,
   `firmware_release_tag=firmware-r920-dze1` e a URL do `setup.sh` do ReSukiSU.
5. Flash (NÃO feito): só com cradle USB + Odin/NetOdin, bateria 70%+,
   firmware stock de recuperação na mão e ciência de que o unlock apaga
   o relógio e vira `Knox 0x1`.
