import itertools
from multiprocessing import Pool, cpu_count
from math import inf, sqrt


def is_prime(n):

    if n < 2:
        return 0
    if n == 2:
        return n
    if n % 2 == 0:
        return 0
    for i in range(3, int(sqrt(n)) + 1, 2):
        if n % i == 0:
            return 0
    return n

if __name__ == '__main__':
    numgen = itertools.count(100000000001, 2)
    cpus = cpu_count()

    primes = []
    print("starting")
    try:
        with Pool(processes=cpus) as pool:
            for result in pool.imap_unordered(is_prime, numgen, chunksize=1000):
                if result:
                    print(result)
                    primes.append(result)
    except KeyboardInterrupt:
        try:
            pool.terminate()
            pool.join()
        except:
            pass
        print("Terminated")
    finally:
        # print(f"Primes: {primes}")
        print(f"Found {len(primes)} primes")
