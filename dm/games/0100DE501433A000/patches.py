# Tetris Effect: Connected 2.0.2 (0100DE501433A000) — local bring-up patches.
# Loaded by dm/tools/patch_nso.py through DM_GAMES_DIR (an out-of-repo profile).
BUILD_ID = '95c56ff872c4f6d85ef97724dcd0b6e9'

CUTS = {
  BUILD_ID: [
    # 1. Unreal Engine 4.27's FMallocBinned3 takes 37 GB of the engine's address region (74 pools of 512 MB). On iOS the whole
    #    guest block is at most ~5 GB, so the allocator is replaced by the host's malloc zone (hle_uemalloc.c). GCreateMalloc
    #    mallocs the 0x1c38-byte object at main+0xd0bfe4 and constructs it at main+0xd0bff0; the constructor call is cut and the
    #    observation gate below hands the new object (x19) to the host, which puts its own vtable in.
    (0xd0bff0, '69820194', '1f2003d5',
     'GCreateMalloc: bl FMallocBinned3 constructor (37 GB of pools) -> nop; the host allocator vtable goes in at the gate'),
    # 2. RedpointEOS: the game asks Unreal for the online subsystem "RedpointEOS" (string at main+0x5a1dc21, loaded at
    #    main+0xb64ad0) and dereferences the result without checking it. The host never loads online SDKs (hle_ro.c: an NRO
    #    exporting EOS_Platform_Create is refused), so the lookup returns null and main+0xb64b7c faults with `ldr x8,[x20]`, x20=0.
    #    The cut skips the null call and the cleanup branch it guards, so online init finishes without it.
    (0xb64b7c, '880240f908bd40f9e00314aa00013fd6', '040000141f2003d51f2003d51f2003d5',
     'RedpointEOS subsystem is null (online SDK refused by design): skip its virtual call'),
  ],
}

OBS = {
  # Right after the cut allocator constructor call: x19 = the new FMallocBinned3 object, before anything calls it.
  # OBS_UE_MALLOC = 21 (dm/host/dm.h); the host writes its allocator vtable there (hle_uemalloc.c).
  BUILD_ID: [
    (0xd0bff4, 21, 'aa1303e0',
     'GCreateMalloc: the allocator object is in x19; the host puts its vtable in (orig mov x0, x19)'),
  ],
}

# How general each patch is and could be (dm/tools/docs_patches.py "Binding", listed in docs/agents/game-patches.md): what, its binding
# now, the loosest it could have (goal), purpose, why; blocked or kept: why the gap stays open
BINDING = [
    {'what': 'Unreal 4.27 FMallocBinned3 constructor cut, the host allocator takes the object',
     'now': 'build', 'goal': 'engine', 'purpose': 'memory',
     'why': "UE 4.27's allocator reserves 37 GB of pools, which no phone address space holds; hle_uemalloc.c puts the host malloc zone in the FMalloc object instead. The constructor call (0xd0bff0) and the after-call gate (0xd0bff4) are fixed offsets of this build",
     'blocked': 'the two sites are not function-matched yet, so another UE 4.27 build keeps the 37 GB allocator; a fingerprint of GCreateMalloc (main+0xd0bfe4 here) would carry it'},
    {'what': 'RedpointEOS: the online-subsystem lookup result is not called',
     'now': 'build', 'goal': 'game', 'purpose': 'runtime',
     'why': 'the host refuses online SDK NROs by design (hle_ro.c), so the RedpointEOS subsystem lookup returns null and the game calls through it (main+0xb64b7c, ldr x8,[x20] with x20=0)',
     'blocked': 'a fixed offset of 2.0.2; a fingerprint of the function that looks the subsystem up (main+0xb64ad0) would carry it to other builds'},
]
