/*
 * Minimal stand-in for runtime/PLCObject.py, to run a split PLC build
 * (IOs .so + logic .so) where Beremiz_service can't, e.g. under qemu-user.
 *
 * Loads and starts PLC as _LoadPLC and StartPLC do, prints PLC log messages
 * and exits with 0 once one contains expected string, see usage.
 *
 * Link with -lm: as the python interpreter does, it must provide libm to PLC.
 */

#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define LOG_LEVELS 4
#define TIMEOUT_MS 10000
#define POLL_MS 100

static void *sym(void *handle, const char *name)
{
    void *s = dlsym(handle, name);
    if (!s)
        fprintf(stderr, "missing %s: %s\n", name, dlerror());
    return s;
}

int main(int argc, char **argv)
{
    if (argc < 4) {
        fprintf(stderr, "usage: %s IOs.so logic.so expected_log_string\n", argv[0]);
        return 1;
    }

    /* IOs first, RTLD_GLOBAL so that logic resolves its externs */
    void *ios = dlopen(argv[1], RTLD_NOW | RTLD_GLOBAL);
    if (!ios) { fprintf(stderr, "%s\n", dlerror()); return 2; }
    void *logic = dlopen(argv[2], RTLD_NOW);
    if (!logic) { fprintf(stderr, "%s\n", dlerror()); return 2; }

    int (*loadPLCLogic)(void *) = sym(ios, "loadPLCLogic");
    void (*initPLCLogicState)(void) = sym(logic, "__init_PLCLogicState");
    int (*initPLCLogic)(int, char **) = sym(logic, "__init_PLCLogic");
    int (*startPLC)(int, char **) = sym(ios, "startPLC");
    int (*stopPLC)(void) = sym(ios, "stopPLC");
    uint32_t (*GetLogCount)(uint8_t) = sym(ios, "GetLogCount");
    uint32_t (*GetLogMessage)(uint8_t, uint32_t, char *, uint32_t,
                              uint32_t *, uint32_t *, uint32_t *) = sym(ios, "GetLogMessage");
    if (!(loadPLCLogic && initPLCLogicState && initPLCLogic && startPLC &&
          stopPLC && GetLogCount && GetLogMessage))
        return 2;

    if (loadPLCLogic(logic)) { fprintf(stderr, "loadPLCLogic failed\n"); return 3; }
    initPLCLogicState();
    if (initPLCLogic(0, NULL)) { fprintf(stderr, "__init_PLCLogic failed\n"); return 3; }
    char *plc_argv[] = { argv[0], NULL };
    if (startPLC(1, plc_argv)) { fprintf(stderr, "startPLC failed\n"); return 3; }

    uint32_t seen[LOG_LEVELS] = { 0 };
    int found = 0;
    for (int t = 0; t < TIMEOUT_MS && !found; t += POLL_MS) {
        usleep(POLL_MS * 1000);
        for (uint8_t level = 0; level < LOG_LEVELS; level++) {
            for (uint32_t count = GetLogCount(level); seen[level] < count; seen[level]++) {
                char msg[256];
                uint32_t tick, tv_sec, tv_nsec;
                uint32_t size = GetLogMessage(level, seen[level], msg, sizeof(msg) - 1,
                                              &tick, &tv_sec, &tv_nsec);
                msg[size < sizeof(msg) ? size : sizeof(msg) - 1] = '\0';
                printf("PLC log [%u] %s\n", level, msg);
                if (strstr(msg, argv[3]))
                    found = 1;
            }
        }
    }
    stopPLC();

    return found ? 0 : 4;
}
