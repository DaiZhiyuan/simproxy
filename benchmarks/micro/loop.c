/* Tight integer loop: high branch predictability, small working set. */
#include <stdint.h>
#include <stdio.h>

#define ITERS 200000000ULL

int
main(void)
{
    uint64_t acc = 1;
    uint64_t i;
    for (i = 0; i < ITERS; ++i)
        acc = acc * 1664525ULL + 1013904223ULL;
    printf("%llu\n", (unsigned long long)acc);
    return 0;
}
