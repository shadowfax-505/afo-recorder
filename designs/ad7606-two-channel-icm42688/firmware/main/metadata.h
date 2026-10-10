#pragma once
#include <stddef.h>
// Session metadata JSON for the SD header and the laptop preview. Returns the
// snprintf length; a value >= capacity means the text was truncated.
// Plain C with no ESP-IDF calls so host tests can compile it.
int afo_session_metadata(char *out, size_t capacity, const char *trial_name);
