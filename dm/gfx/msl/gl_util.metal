// The OpenGL layer's own shaders: a quad that clears what a scissored or masked glClear covers (hle_gl.m)
#include <metal_stdlib>
using namespace metal;
struct V { float4 p [[position]]; };
vertex V clr_vs(uint i [[vertex_id]], constant float &z [[buffer(0)]]) { V o; float2 t = float2((i << 1) & 2, i & 2); o.p = float4(t * 2 - 1, z, 1); return o; }
#define CLEAR_FRAGMENT(slot) \
    struct Output##slot { float4 color [[color(slot)]]; }; \
    fragment Output##slot clr_fs_##slot(constant float4 &c [[buffer(0)]]) { return {c}; }
CLEAR_FRAGMENT(0)
CLEAR_FRAGMENT(1)
CLEAR_FRAGMENT(2)
CLEAR_FRAGMENT(3)
CLEAR_FRAGMENT(4)
CLEAR_FRAGMENT(5)
CLEAR_FRAGMENT(6)
CLEAR_FRAGMENT(7)
