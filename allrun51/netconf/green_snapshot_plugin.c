#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include <libyang/libyang.h>
#include <sysrepo.h>

typedef struct {
    char *snapshot_path;
    char *trace_control_path;
    char *trace_path;
    char *context_path;
    sr_subscription_ctx_t *hardware_subscription;
    sr_subscription_ctx_t *energy_subscription;
} green_plugin_state_t;

static char *read_snapshot(const char *path);

static char *
append_suffix(const char *path, const char *suffix)
{
    size_t path_length = strlen(path);
    size_t suffix_length = strlen(suffix);
    char *result = malloc(path_length + suffix_length + 1);

    if (result) {
        memcpy(result, path, path_length);
        memcpy(result + path_length, suffix, suffix_length + 1);
    }
    return result;
}

static int
trace_is_enabled(const green_plugin_state_t *state)
{
    FILE *control_file = fopen(state->trace_control_path, "r");
    char value = '0';

    if (!control_file) {
        return 0;
    }
    (void)fread(&value, 1, 1, control_file);
    fclose(control_file);
    return value == '1';
}

static void
trace_provider_reply(const green_plugin_state_t *state, const char *module_name,
        const char *schema_path, const char *request_xpath, const char *status,
        const struct lyd_node *data)
{
    FILE *trace_file;
    char *json = NULL;
    char *context = NULL;
    time_t now;
    struct tm utc_time;
    char timestamp[32] = "unknown";

    if (!trace_is_enabled(state)) {
        return;
    }
    if (data && lyd_print_mem(&json, data, LYD_JSON, LYD_PRINT_WITHSIBLINGS) != LY_SUCCESS) {
        json = NULL;
    }
    context = read_snapshot(state->context_path);
    trace_file = fopen(state->trace_path, "a");
    if (!trace_file) {
        free(json);
        free(context);
        return;
    }

    now = time(NULL);
    if (gmtime_r(&now, &utc_time)) {
        (void)strftime(timestamp, sizeof timestamp, "%Y-%m-%dT%H:%M:%SZ", &utc_time);
    }
    fprintf(trace_file, "------------------------------------------------------------------------\n");
    fprintf(trace_file, "%s", context ? context : "NETCONF GET (scenario context unavailable)\n");
    fprintf(trace_file, "------------------------------------------------------------------------\n");
    fprintf(trace_file, "[%s] NETCONF operational-data request\n", timestamp);
    fprintf(trace_file, "operation: <get>\nmodule: %s\npath: %s\n",
            module_name, schema_path);
    fprintf(trace_file, "request-xpath: %s\nstatus: %s\nreply-data-json:\n%s\n\n",
            request_xpath ? request_xpath : "(not provided)", status,
            json ? json : "(empty)");
    fclose(trace_file);
    free(json);
    free(context);
}

static char *
read_snapshot(const char *path)
{
    FILE *file = NULL;
    char *buffer = NULL;
    long length;
    size_t read_length;

    file = fopen(path, "rb");
    if (!file) {
        return NULL;
    }
    if (fseek(file, 0, SEEK_END) != 0 || (length = ftell(file)) < 0 ||
            fseek(file, 0, SEEK_SET) != 0) {
        fclose(file);
        return NULL;
    }

    buffer = malloc((size_t)length + 1);
    if (!buffer) {
        fclose(file);
        return NULL;
    }
    read_length = fread(buffer, 1, (size_t)length, file);
    fclose(file);
    if (read_length != (size_t)length) {
        free(buffer);
        return NULL;
    }
    buffer[read_length] = '\0';
    return buffer;
}

static int
provide_operational_data(sr_session_ctx_t *session, uint32_t subscription_id,
        const char *module_name, const char *path, const char *request_xpath,
        uint32_t request_id, struct lyd_node **parent, void *private_data)
{
    green_plugin_state_t *state = private_data;
    const char *schema_path;
    const struct ly_ctx *ly_ctx;
    char *json;
    struct lyd_node *data = NULL;
    struct lyd_node *source = NULL;
    struct lyd_node *copy = NULL;
    LY_ERR ly_result;
    int result = SR_ERR_OK;

    (void)subscription_id;
    (void)request_xpath;
    (void)request_id;

    if (!strcmp(module_name, "ietf-hardware") && !strcmp(path, "/ietf-hardware:hardware")) {
        schema_path = "/ietf-hardware:hardware";
    } else if (!strcmp(module_name, "ietf-power-and-energy") &&
            !strcmp(path, "/ietf-power-and-energy:energy-objects")) {
        schema_path = "/ietf-power-and-energy:energy-objects";
    } else {
        return SR_ERR_OK;
    }

    json = read_snapshot(state->snapshot_path);
    if (!json) {
        if (errno == ENOENT) {
            trace_provider_reply(state, module_name, schema_path, request_xpath,
                    "snapshot-not-yet-created", NULL);
            return SR_ERR_OK;
        }
        fprintf(stderr, "green-snapshot-plugin: cannot read %s\n", state->snapshot_path);
        trace_provider_reply(state, module_name, schema_path, request_xpath,
                "snapshot-read-error", NULL);
        return SR_ERR_SYS;
    }

    ly_ctx = sr_get_context(sr_session_get_connection(session));
    ly_result = lyd_parse_data_mem(ly_ctx, json, LYD_JSON, LYD_PARSE_STRICT,
            LYD_VALIDATE_PRESENT, &data);
    free(json);
    if (ly_result != LY_SUCCESS) {
        fprintf(stderr, "green-snapshot-plugin: failed to parse operational snapshot\n");
        trace_provider_reply(state, module_name, schema_path, request_xpath,
            "snapshot-parse-error", NULL);
        return SR_ERR_VALIDATION_FAILED;
    }

    ly_result = lyd_find_path(data, schema_path, 0, &source);
    if (ly_result == LY_SUCCESS && source) {
        ly_result = lyd_dup_single(source, NULL, LYD_DUP_RECURSIVE, &copy);
        if (ly_result == LY_SUCCESS) {
            if (*parent) {
                ly_result = lyd_insert_child(*parent, copy);
            } else {
                *parent = copy;
            }
        }
    } else if (ly_result == LY_ENOTFOUND) {
        ly_result = LY_SUCCESS;
    }

    trace_provider_reply(state, module_name, schema_path, request_xpath,
            ly_result == LY_SUCCESS ? "ok" : "provider-error", copy);

    lyd_free_all(data);
    if (ly_result != LY_SUCCESS) {
        fprintf(stderr, "green-snapshot-plugin: failed to provide %s\n", schema_path);
        result = SR_ERR_OPERATION_FAILED;
    }
    return result;
}

int
sr_plugin_init_cb(sr_session_ctx_t *session, void **private_data)
{
    green_plugin_state_t *state;
    const char *snapshot_path = getenv("GREEN_NETCONF_STATE_FILE");
    const char *trace_path = getenv("GREEN_NETCONF_TRACE_FILE");
    int result;

    if (!snapshot_path || !snapshot_path[0]) {
        fprintf(stderr, "green-snapshot-plugin: GREEN_NETCONF_STATE_FILE is required\n");
        return SR_ERR_INVAL_ARG;
    }

    state = calloc(1, sizeof *state);
    if (!state) {
        return SR_ERR_NO_MEMORY;
    }
    state->snapshot_path = strdup(snapshot_path);
    state->trace_control_path = append_suffix(snapshot_path, ".netconf-trace-enabled");
        state->trace_path = trace_path && trace_path[0]
            ? strdup(trace_path) : append_suffix(snapshot_path, ".netconf-trace.log");
    state->context_path = append_suffix(snapshot_path, ".netconf-context");
    if (!state->snapshot_path || !state->trace_control_path || !state->trace_path ||
            !state->context_path) {
        free(state->snapshot_path);
        free(state->trace_control_path);
        free(state->trace_path);
        free(state->context_path);
        free(state);
        return SR_ERR_NO_MEMORY;
    }

    result = sr_oper_get_items_subscribe(session, "ietf-hardware", "/ietf-hardware:hardware",
            provide_operational_data, state, 0, &state->hardware_subscription);
    if (result != SR_ERR_OK) {
        free(state->snapshot_path);
        free(state->trace_control_path);
        free(state->trace_path);
        free(state->context_path);
        free(state);
        return result;
    }

    result = sr_oper_get_items_subscribe(session, "ietf-power-and-energy",
            "/ietf-power-and-energy:energy-objects", provide_operational_data,
            state, 0, &state->energy_subscription);
    if (result != SR_ERR_OK) {
        sr_unsubscribe(state->hardware_subscription);
        free(state->snapshot_path);
        free(state->trace_control_path);
        free(state->trace_path);
        free(state->context_path);
        free(state);
        return result;
    }

    *private_data = state;
    return SR_ERR_OK;
}

void
sr_plugin_cleanup_cb(sr_session_ctx_t *session, void *private_data)
{
    green_plugin_state_t *state = private_data;
    (void)session;

    if (!state) {
        return;
    }
    if (state->hardware_subscription) {
        sr_unsubscribe(state->hardware_subscription);
    }
    if (state->energy_subscription) {
        sr_unsubscribe(state->energy_subscription);
    }
    free(state->snapshot_path);
    free(state->trace_control_path);
    free(state->trace_path);
    free(state->context_path);
    free(state);
}
