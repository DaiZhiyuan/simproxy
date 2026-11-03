/* Alternating compute and memory phases to create distinct SimPoints. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#define WINDOW (4 * 1024 * 1024)
#define ROUNDS 32

static uint64_t
compute(uint64_t seed, int n)
{
    uint64_t acc = seed;
    for (int i = 0; i < n; ++i)
        acc = acc * 6364136223846793005ULL + 1442695040888963407ULL;
    return acc;
}

int
main(void)
{
    uint64_t *data = malloc(WINDOW * sizeof(uint64_t));
    if (data == NULL)
        return 1;

    uint64_t acc = 1;
    for (int r = 0; r < ROUNDS; ++r) {
        acc = compute(acc, 2000000);
        for (int i = 0; i < WINDOW; ++i)
            data[i] += acc + (uint64_t)i;
    }
    printf("%llu\n", (unsigned long long)data[0]);
    free(data);
    return 0;
}
