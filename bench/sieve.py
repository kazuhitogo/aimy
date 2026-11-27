import sys
def count_primes(n):
    is_ = [True]*n; is_[0]=is_[1]=False
    i = 2
    while i*i < n:
        if is_[i]:
            j = i*i
            while j < n: is_[j] = False; j += i
        i += 1
    return sum(is_)
print(count_primes(int(sys.argv[1])))
