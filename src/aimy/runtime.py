"""C runtime prepended to every generated program."""

RUNTIME = r"""
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <inttypes.h>
#include <setjmp.h>
#include <time.h>

static int aim_argc; static char **aim_argv;
static FILE *aim_out;
static int aim_testing = 0;
static jmp_buf aim_test_jmp;

static void aim_json_str(FILE *f, const char *s) {
    fputc('"', f);
    for (; *s; s++) {
        unsigned char c = (unsigned char)*s;
        if (c == '"' || c == '\\') { fputc('\\', f); fputc(c, f); }
        else if (c == '\n') fputs("\\n", f);
        else if (c == '\t') fputs("\\t", f);
        else if (c < 0x20) fprintf(f, "\\u%04x", c);
        else fputc(c, f);
    }
    fputc('"', f);
}

/* Failure report. In test mode it is stored and we longjmp back to the runner. */
static char aim_fail_buf[4096];

__attribute__((noreturn, cold))
static void aim_fail(const char *kind, const char *msg, int line, int col,
                     const char *src, const char *left, const char *right) {
    char *p = aim_fail_buf; size_t n = sizeof aim_fail_buf;
    FILE *f = fmemopen(p, n, "w");
    fprintf(f, "\"kind\":\"%s\",\"msg\":", kind); aim_json_str(f, msg);
    fprintf(f, ",\"line\":%d,\"col\":%d", line, col);
    if (src) { fputs(",\"src\":", f); aim_json_str(f, src); }
    if (left) { fputs(",\"left\":", f); aim_json_str(f, left); }
    if (right) { fputs(",\"right\":", f); aim_json_str(f, right); }
    fclose(f);
    if (aim_testing) longjmp(aim_test_jmp, 1);
    fflush(stdout);
    fprintf(stderr, "{\"error\":\"runtime\",%s}\n", aim_fail_buf);
    exit(101);
}

static void aim_fmt_i64(char *b, size_t n, int64_t v) { snprintf(b, n, "%" PRId64, v); }
static void aim_fmt_f64(char *b, size_t n, double v) {
    if (isnan(v)) { snprintf(b, n, "nan"); return; }
    if (isinf(v)) { snprintf(b, n, v > 0 ? "inf" : "-inf"); return; }
    for (int p = 1; p <= 17; p++) {
        snprintf(b, n, "%.*g", p, v);
        if (strtod(b, NULL) == v) break;
    }
    if (!strpbrk(b, ".e")) { size_t l = strlen(b); if (l + 2 < n) { b[l] = '.'; b[l+1] = '0'; b[l+2] = 0; } }
}
static void aim_fmt_bool(char *b, size_t n, bool v) { snprintf(b, n, "%s", v ? "true" : "false"); }
static void aim_fmt_str(char *b, size_t n, const char *v) { snprintf(b, n, "\"%s\"", v); }

/* bounded string builder for assertion messages */
typedef struct { char *p; size_t n, len; } aim_sb;
static void sb_put(aim_sb *b, const char *s) {
    while (*s && b->len + 1 < b->n) b->p[b->len++] = *s++;
    b->p[b->len] = 0;
}
static void sbf_i64(aim_sb *b, int64_t v) { char t[32]; aim_fmt_i64(t, sizeof t, v); sb_put(b, t); }
static void sbf_f64(aim_sb *b, double v) { char t[64]; aim_fmt_f64(t, sizeof t, v); sb_put(b, t); }
static void sbf_bool(aim_sb *b, bool v) { sb_put(b, v ? "true" : "false"); }
static void sbf_str(aim_sb *b, const char *v) { sb_put(b, "\""); sb_put(b, v); sb_put(b, "\""); }

static void aim_print_i64(int64_t v) { fprintf(aim_out, "%" PRId64, v); }
static void aim_print_f64(double v) { char b[64]; aim_fmt_f64(b, sizeof b, v); fputs(b, aim_out); }
static void aim_print_bool(bool v) { fputs(v ? "true" : "false", aim_out); }
static void aim_print_str(const char *v) { fputs(v, aim_out); }
static void aim_putc(char c) { fputc(c, aim_out); }

#define AIM_LIKELY(x) __builtin_expect(!!(x), 1)

static inline int64_t aim_add(int64_t a, int64_t b, int l, int c) {
    int64_t r; if (__builtin_add_overflow(a, b, &r)) aim_fail("overflow", "i64 addition overflowed", l, c, 0, 0, 0); return r; }
static inline int64_t aim_sub(int64_t a, int64_t b, int l, int c) {
    int64_t r; if (__builtin_sub_overflow(a, b, &r)) aim_fail("overflow", "i64 subtraction overflowed", l, c, 0, 0, 0); return r; }
static inline int64_t aim_mul(int64_t a, int64_t b, int l, int c) {
    int64_t r; if (__builtin_mul_overflow(a, b, &r)) aim_fail("overflow", "i64 multiplication overflowed", l, c, 0, 0, 0); return r; }
static inline int64_t aim_div(int64_t a, int64_t b, int l, int c) {
    if (b == 0) aim_fail("div_by_zero", "division by zero", l, c, 0, 0, 0);
    if (a == INT64_MIN && b == -1) aim_fail("overflow", "i64 division overflowed", l, c, 0, 0, 0);
    return a / b; }
static inline int64_t aim_mod(int64_t a, int64_t b, int l, int c) {
    if (b == 0) aim_fail("div_by_zero", "modulo by zero", l, c, 0, 0, 0);
    if (b == -1) return 0;
    return a % b; }
static inline int64_t aim_neg(int64_t a, int l, int c) {
    if (a == INT64_MIN) aim_fail("overflow", "i64 negation overflowed", l, c, 0, 0, 0); return -a; }
static inline int64_t aim_f2i(double v, int l, int c) {
    if (!(v >= -9223372036854775808.0 && v < 9223372036854775808.0))
        aim_fail("overflow", "f64 value does not fit in i64", l, c, 0, 0, 0);
    return (int64_t)v; }
static inline int64_t aim_absi(int64_t a, int l, int c) { return a < 0 ? aim_neg(a, l, c) : a; }
static inline int64_t aim_mini(int64_t a, int64_t b) { return a < b ? a : b; }
static inline int64_t aim_maxi(int64_t a, int64_t b) { return a > b ? a : b; }
static inline double aim_minf(double a, double b) { return a < b ? a : b; }
static inline double aim_maxf(double a, double b) { return a > b ? a : b; }

static void aim_oob(int64_t i, int64_t len, int l, int c) {
    char m[128]; snprintf(m, sizeof m, "index %" PRId64 " out of range for length %" PRId64, i, len);
    aim_fail("index_out_of_bounds", m, l, c, 0, 0, 0);
}

static void *aim_alloc(size_t n) {
    void *p = malloc(n ? n : 1);
    if (!p) { fputs("{\"error\":\"runtime\",\"kind\":\"out_of_memory\"}\n", stderr); exit(102); }
    return p;
}
static void *aim_realloc(void *p, size_t n) {
    p = realloc(p, n ? n : 1);
    if (!p) { fputs("{\"error\":\"runtime\",\"kind\":\"out_of_memory\"}\n", stderr); exit(102); }
    return p;
}

static int64_t aim_arg(int64_t i, int l, int c) {
    if (i < 0 || i + 1 >= aim_argc) {
        char m[96]; snprintf(m, sizeof m, "command-line argument %" PRId64 " was not given", i);
        aim_fail("missing_arg", m, l, c, 0, 0, 0);
    }
    char *end; long long v = strtoll(aim_argv[i + 1], &end, 10);
    if (*end || end == aim_argv[i + 1]) aim_fail("bad_arg", "command-line argument is not an integer", l, c, 0, 0, 0);
    return (int64_t)v;
}
static double aim_clock(void) {
    struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + ts.tv_nsec * 1e-9;
}
"""

ARRAY_TEMPLATE = r"""
static A_{m} *A_{m}_new(int64_t cap) {{
    A_{m} *a = aim_alloc(sizeof(A_{m}));
    a->len = 0; a->cap = cap; a->data = aim_alloc(sizeof({et}) * (size_t)cap);
    return a;
}}
static A_{m} *A_{m}_lit(int64_t n, {et} const *src) {{
    A_{m} *a = A_{m}_new(n); memcpy(a->data, src, sizeof({et}) * (size_t)n); a->len = n; return a;
}}
static inline {et} *A_{m}_at(A_{m} *a, int64_t i, int l, int c) {{
    if (!AIM_LIKELY((uint64_t)i < (uint64_t)a->len)) aim_oob(i, a->len, l, c);
    return &a->data[i];
}}
static void A_{m}_push(A_{m} *a, {et} v) {{
    if (a->len == a->cap) {{
        a->cap = a->cap ? a->cap * 2 : 4;
        a->data = aim_realloc(a->data, sizeof({et}) * (size_t)a->cap);
    }}
    a->data[a->len++] = v;
}}
static {et} A_{m}_pop(A_{m} *a, int l, int c) {{
    if (a->len == 0) aim_fail("empty_pop", "pop from an empty array", l, c, 0, 0, 0);
    return a->data[--a->len];
}}
static A_{m} *A_{m}_fill(int64_t n, {et} v, int l, int c) {{
    if (n < 0) aim_fail("bad_length", "fill() count is negative", l, c, 0, 0, 0);
    A_{m} *a = A_{m}_new(n);
    for (int64_t i = 0; i < n; i++) a->data[i] = {copy_v};
    a->len = n; return a;
}}
static A_{m} *copy_A_{m}(A_{m} *s) {{
    A_{m} *a = A_{m}_new(s->len);
    for (int64_t i = 0; i < s->len; i++) a->data[i] = {copy_elem};
    a->len = s->len; return a;
}}
"""
