/* SimProxy BBV client.
 *
 * A deliberately small DynamoRIO client that writes SimPoint basic block
 * vectors. It uses a clean call per basic block (no inline counter
 * optimization) so that it stays portable across AArch64 variants; the
 * reference `drpoints` tool shipped with DynamoRIO remains the fast path.
 *
 * Usage:
 *   drrun -t simproxy_bbv -instr_interval 100000000 -out_file prog.bbv -- ./app
 *
 * Output dialect (SimPoint 3.x):
 *   T0: 1:12 3:7 8:1
 *   T1: 2:5 3:9
 *
 * Only single-threaded applications are supported in this first version.
 */

#include "dr_api.h"
#include "drcovlib.h"
#include "drmgr.h"
#include "drx.h"
#include "hashtable.h"

#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define HASH_BITS 13

#define FATAL(...)                       \
    do {                                 \
        dr_fprintf(STDERR, __VA_ARGS__); \
        dr_abort();                      \
    } while (0)

static uint64_t instr_interval = 100000000ULL;
static int64_t instr_count = 0;
static const char *out_path = NULL;
static file_t out_file = INVALID_FILE;
static bool print_stdout = false;

static uint64_t unique_bb_count = 1;
static uint64_t interval_index = 0;
static bool first_pair = true;
static int thread_count = 0;

static hashtable_t bb_id_table;
static hashtable_t bb_count_table;

typedef struct {
    uint modidx;
    uint64_t offset;
} modidx_offset_t;

static uint
bb_id_hash(void *val)
{
    modidx_offset_t *key = (modidx_offset_t *)val;
    uint modidx = key->modidx;
    uint64_t offset = key->offset;
    return offset >= modidx ? (uint)(offset * offset + offset) + modidx
                            : modidx * modidx + (uint)offset;
}

static bool
bb_id_cmp(void *val1, void *val2)
{
    modidx_offset_t *key1 = (modidx_offset_t *)val1;
    modidx_offset_t *key2 = (modidx_offset_t *)val2;
    return key1->modidx == key2->modidx && key1->offset == key2->offset;
}

static void
free_bb_id(void *key)
{
    dr_global_free(key, sizeof(modidx_offset_t));
}

static void
free_count(void *payload)
{
    dr_global_free(payload, sizeof(uint64_t));
}

static void
set_count_to_zero(void *payload)
{
    *(uint64_t *)payload = 0;
}

static void
write_pair(void *key, void *payload, void *user_data)
{
    uint64_t count = *(uint64_t *)payload;
    uint64_t id = (uint64_t)(uintptr_t)key;
    char buffer[80];
    int len;

    (void)user_data;
    if (count == 0)
        return;

    if (first_pair) {
        len = dr_snprintf(buffer, sizeof(buffer), "T%llu: %llu:%llu",
                          (unsigned long long)interval_index,
                          (unsigned long long)id, (unsigned long long)count);
        first_pair = false;
    } else {
        len = dr_snprintf(buffer, sizeof(buffer), " %llu:%llu",
                          (unsigned long long)id, (unsigned long long)count);
    }
    if (len <= 0)
        FATAL("ERROR: failed to format BBV pair\n");

    if (print_stdout)
        dr_fprintf(STDOUT, "%s", buffer);
    if (out_file != INVALID_FILE)
        dr_write_file(out_file, buffer, (size_t)len);
}

static void
save_bbv(void)
{
    first_pair = true;
    hashtable_apply_to_all_key_payload_pairs_user_data(&bb_count_table, write_pair, NULL);
    if (!first_pair) {
        if (print_stdout)
            dr_fprintf(STDOUT, "\n");
        if (out_file != INVALID_FILE)
            dr_write_file(out_file, "\n", 1);
        ++interval_index;
    }
    hashtable_apply_to_all_payloads(&bb_count_table, set_count_to_zero);
    instr_count = (int64_t)instr_interval;
}

static void
bb_hit(uint64_t *count, uintptr_t size)
{
    *count += (uint64_t)size;
    instr_count -= (int64_t)size;
    if (instr_count <= 0)
        save_bbv();
}

static dr_emit_flags_t
event_app_instruction(void *drcontext, void *tag, instrlist_t *bb, instr_t *instr,
                      bool for_trace, bool translating, void *user_data)
{
    app_pc bb_pc;
    uint modidx;
    app_pc modbase;
    uint64_t offset;
    modidx_offset_t key;
    uint64_t id;
    uint64_t *count;
    size_t bb_size;

    (void)tag;
    (void)for_trace;
    (void)translating;
    (void)user_data;

    if (!drmgr_is_first_instr(drcontext, instr))
        return DR_EMIT_DEFAULT;

    bb_pc = instr_get_app_pc(instrlist_first_app(bb));
    if (drmodtrack_lookup(drcontext, bb_pc, &modidx, &modbase) == DRCOVLIB_SUCCESS) {
        offset = (uint64_t)(bb_pc - modbase);
    } else {
        /* Fall back to the absolute PC for unregistered modules. */
        modidx = 0;
        offset = (uint64_t)(uintptr_t)bb_pc;
    }
    key.modidx = modidx;
    key.offset = offset;

    id = (uint64_t)(uintptr_t)hashtable_lookup(&bb_id_table, &key);
    if (id == 0) {
        modidx_offset_t *heap_key = dr_global_alloc(sizeof(*heap_key));
        id = unique_bb_count++;
        *heap_key = key;
        hashtable_add(&bb_id_table, heap_key, (void *)(uintptr_t)id);
    }

    count = hashtable_lookup(&bb_count_table, (void *)(uintptr_t)id);
    if (count == NULL) {
        count = dr_global_alloc(sizeof(*count));
        *count = 0;
        hashtable_add(&bb_count_table, (void *)(uintptr_t)id, count);
    }

    bb_size = drx_instrlist_app_size(bb);
    dr_insert_clean_call(drcontext, bb, instr, (void *)bb_hit,
                         /*save_fpstate=*/false, 2, OPND_CREATE_INTPTR(count),
                         OPND_CREATE_INTPTR(bb_size));
    return DR_EMIT_DEFAULT;
}

static void
event_thread_init(void *drcontext)
{
    (void)drcontext;
    if (thread_count > 0)
        FATAL("ERROR: simproxy_bbv supports single-threaded applications only\n");
    ++thread_count;
}

static void
open_output(void)
{
    if (out_path != NULL && out_path[0] != '\0') {
        out_file = dr_open_file(out_path, DR_FILE_WRITE_REQUIRE_NEW);
    } else {
        char cwd[MAXIMUM_PATH];
        char buffer[MAXIMUM_PATH];
        if (!dr_get_current_directory(cwd, sizeof(cwd)))
            FATAL("ERROR: dr_get_current_directory() failed\n");
        out_file = drx_open_unique_appid_file(cwd, dr_get_process_id(), "simproxy",
                                              "bbv", DR_FILE_WRITE_REQUIRE_NEW, buffer,
                                              sizeof(buffer));
        if (out_file != INVALID_FILE)
            dr_fprintf(STDERR, "simproxy_bbv: writing %s\n", buffer);
    }
    if (out_file == INVALID_FILE)
        FATAL("ERROR: unable to open BBV output file\n");
}

static void
event_exit(void)
{
    save_bbv();
    if (out_file != INVALID_FILE)
        dr_close_file(out_file);

    hashtable_delete(&bb_id_table);
    hashtable_delete(&bb_count_table);

    drmodtrack_exit();
    drmgr_unregister_thread_init_event(event_thread_init);
    drmgr_unregister_exit_event(event_exit);
    drx_exit();
    drmgr_exit();
}

static void
parse_args(int argc, const char *argv[])
{
    int i;
    /* argv[0] is the client library path supplied by drrun. */
    for (i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "-instr_interval") == 0 && i + 1 < argc) {
            instr_interval = strtoull(argv[++i], NULL, 0);
        } else if (strcmp(argv[i], "-out_file") == 0 && i + 1 < argc) {
            out_path = argv[++i];
        } else if (strcmp(argv[i], "-print") == 0) {
            print_stdout = true;
        } else if (strcmp(argv[i], "-help") == 0) {
            dr_fprintf(STDOUT,
                       "simproxy_bbv options:\n"
                       "  -instr_interval N  instructions per interval (default 100M)\n"
                       "  -out_file PATH     output .bbv path\n"
                       "  -print             also print to stdout\n");
            dr_exit_process(0);
        } else {
            FATAL("ERROR: unknown option '%s' (use -help)\n", argv[i]);
        }
    }
    if (instr_interval == 0)
        instr_interval = 1;
}

DR_EXPORT void
dr_client_main(client_id_t id, int argc, const char *argv[])
{
    hashtable_config_t config;

    (void)id;
    parse_args(argc, argv);
    dr_set_client_name("SimProxy BBV", "https://github.com/anomalyco/opencode/issues");

    if (drmodtrack_init() != DRCOVLIB_SUCCESS)
        FATAL("ERROR: drmodtrack_init() failed\n");
    if (!drmgr_init() || !drx_init())
        FATAL("ERROR: failed to initialize DynamoRIO extensions\n");

    hashtable_init_ex(&bb_count_table, HASH_BITS, HASH_INTPTR, /*str_dup=*/false,
                      /*synch=*/false, free_count, NULL, NULL);
    hashtable_init_ex(&bb_id_table, HASH_BITS, HASH_INTPTR, /*str_dup=*/false,
                      /*synch=*/false, NULL, bb_id_hash, bb_id_cmp);

    memset(&config, 0, sizeof(config));
    config.size = sizeof(config);
    config.resizable = true;
    config.resize_threshold = 75;
    config.free_key_func = free_bb_id;
    hashtable_configure(&bb_id_table, &config);

    open_output();
    instr_count = (int64_t)instr_interval;

    if (!drmgr_register_thread_init_event(event_thread_init) ||
        !drmgr_register_exit_event(event_exit) ||
        !drmgr_register_bb_instrumentation_event(NULL, event_app_instruction, NULL))
        FATAL("ERROR: failed to register DynamoRIO events\n");
}
