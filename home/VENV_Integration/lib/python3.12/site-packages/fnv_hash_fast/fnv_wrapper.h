

#include <stdint.h>

using namespace std;


// https://en.wikipedia.org/wiki/Fowler%E2%80%93Noll%E2%80%93Vo_hash_function
uint32_t _cpp_fnv1a_32(std::string data) {
    uint32_t hash = 2166136261U;

    for (uint32_t idx = 0; data[idx] != 0; ++idx) {
        hash = 16777619U * (hash ^ static_cast<unsigned char>(data[idx]));
    }

    return hash;
}
