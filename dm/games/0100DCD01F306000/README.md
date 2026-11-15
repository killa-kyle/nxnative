# Mina the Hollower (0100DCD01F306000)

Update 1.0.6 (v327680), SDK 21.4.3, Yacht Club Games engine, NVN.

## iPhone Duo validation

The game booted, rendered the title and name-entry screens, and reached
gameplay. With the full 110-shader cache, portrait name entry rendered the
keyboard and entered glyph. The pass trace recorded four draws on each of three
sampled frames. Long-session allocator headroom remains open.

## Memory

The Switch reserves 16 GiB for StandardAllocator at startup and 4 GiB each
for the Default Mem and Render Mem slab allocators. The first call returns to
main+0x87cbac and aborts at sdk+0x141b9c with the compact phone layout before
NVN starts. The build-specific cuts in patches.py reserve 1.5 GiB, 768 MiB,
and 768 MiB respectively. A 4.5625 GiB alias window then boots on the Duo.
The SDK's node area still takes 1 GiB. Startup mapped about 1.51 GiB of the
alias region. The 5 GiB guest reservation uses the full 6 GiB budget with
alignment slack.

## Shaders

The Yacht Club YCD archive yields 110 distinct NVN shaders. The offline
splitter recovers the code and control sections and the shader compiler builds
all 110 for Mac and iOS. Captured name-entry shaders match the archive
inventory. The saved pipeline manifest covers observed startup draws.
