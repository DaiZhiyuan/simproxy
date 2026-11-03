/* Streaming memory access over a large array: low reuse, large working set. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#define SIZE (32 * 1024 * 1024)
#define REPEAT 16

int
main(void)
{
    volatile uint64_t *data = malloc(SIZE * sizeof(uint64_t));
    if (data == NULL)
        return 1;

    uint64_t sum = 0;
    for (int r = 0; r < REPEAT; ++r) {
        for (int i = 0; i < SIZE; ++i)
            sum += data[i];
    }
    printf("%llu\n", (unsigned long long)sum);
    free((void *)data);
    return 0;
}
