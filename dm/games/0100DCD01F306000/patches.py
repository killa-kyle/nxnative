# Mina the Hollower 1.0.6 (0100DCD01F306000) - bring-up patches (loaded by dm/tools/patch_nso.py through DM_GAMES_DIR).
BUILD_ID = 'e86ae07bdfec77ee10d50d2163d0ff2e'
# The Switch reserves 24 GiB across these three regions before engine startup.
# Compact sizing preserves substantially more space than the device maps at startup.
# Bring-up validation covers boot and title rendering only.
CUTS = {
    BUILD_ID: [
        (0x103e8c, '8100c0d2', '0100acd2', 'StandardAllocator reservation: 16 GiB to 1.5 GiB'),
        (0x6d8cc, '2100c0d2', '0100a6d2', 'Default Mem slab reservation: 4 GiB to 768 MiB'),
        (0x6dc2c, '2100c0d2', '0100a6d2', 'Render Mem slab reservation: 4 GiB to 768 MiB'),
    ],
}


# Observation gates for this SDK build (the rewriter's symbol match gave none for cb82ed52): the address-region
# allocate entry, with the requested size in x2 (OBS_REGION_ASK = 22, parameter in bits 8+), so the host logs
# "[mem] Unreal's engine region ... asked" or the region table entry for the failing request.
OBS = {
  'cb82ed52216313df5626154efb64d45f': [
    (0x13fee0, 22 | (2 << 8), 'a9bd7bfd', 'address-region allocate entry (stp x29,x30): size in x2'),
  ],
}

BINDING = [
    {'what': 'three startup virtual reservations', 'now': 'build', 'goal': 'game',
     'purpose': 'memory', 'why': 'the Switch engine reserves 24 GiB across three allocators at startup'},
    {'what': 'SDK address-region observation', 'now': 'build', 'goal': 'sdk',
     'purpose': 'address space', 'why': 'the observation gate is pinned to the 21.4.3 SDK build'},
]
