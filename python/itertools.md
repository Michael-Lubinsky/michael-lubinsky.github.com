###  itertools

https://docs.python.org/3/library/itertools.html  
https://realpython.com/python-itertools/  
https://mathspp.com/blog/module-itertools-overview  
https://mathspp.com/books/the-little-book-of-itertools  

### more-itertools

The total list of functions in more-itertools is huge. Here’s the full list.


| Function Name               | Function Name               | Function Name                      |
|-----------------------------|-----------------------------|------------------------------------|
| ichunked                    | collapse                    | distinct_permutations              |
| chunked_even                | interleave                  | distinct_combinations              |
| sliced                      | interleave_longest          | nth_combination_with_replacement   |
| constrained_batches         | interleave_evenly           | circular_shifts                    |
| distribute                  | partial_product             | partitions                         |
| divide                      | sort_together               | set_partitions                     |
| split_at                    | value_chain                 | product_index                      |
| split_before                | zip_offset                  | combination_index                  |
| split_after                 | zip_equal                   | permutation_index                  |
| split_into                  | zip_broadcast               | combination_with_replacement_index |
| split_when                  | flatten                     | gray_product                       |
| bucket                      | roundrobin                  | outer_product                      |
| unzip                       | prepend                     | powerset_of_sets                   |
| batched                     | ilen                        | powerset                           |
| grouper                     | unique_to_each              | random_product                     |
| partition                   | sample                      | random_permutation                 |
| transpose                   | consecutive_groups          | random_combination                 |
| spy                         | map_reduce                  | random_combination_with_replacement|
| windowed                    | join_mappings               | nth_product                        |
| substrings                  | exactly_n                   | nth_permutation                    |
| substrings_indexes          | is_sorted                   | nth_combination                    |
| stagger                     | all_unique                  | always_iterable                    |
| windowed_complete           | minmax                      | always_reversible                  |
| pairwise                    | iequals                     | countable                          |
| triplewise                  | all_equal                   | consumer                           |
| sliding_window              | first_true                  | with_iter                          |       
| subslices                   | quantify                    | callback_iter                      |       
| count_cycle                 | first                       | iter_except                        |       
| intersperse                 | last                        | dft                                |              
| padded                      | one                         | idft                               |       
| mark_ends                   | only                        | convolve                           |       
| repeat_each                 | strictly_n                  | dotproduct                         |
| repeat_last                 | strip                       | factor                             |
| adjacent                    | lstrip                      | matmul                             |
| groupby_transform           | rstrip                      | polynomial_from_roots              |
| padnone                     | filter_except               | polynomial_derivative              |
| pad_none                    | map_except                  | polynomial_eval                    |
| ncycles                     | filter_map                  | sieve                              |
| nth                         | iter_suppress               | sum_of_squares                     |
| before_and_after            | nth_or_last                 | totient                            |
| take                        | unique_in_window            | locate                             |
| tail                        | duplicates_everseen         | rlocate                            |
| unique_everseen             | duplicates_justseen         | replace                            |
| unique_justseen             | classify_unique             | numeric_range                      |
| unique                      | longest_common_prefix       | side_effect                        |
| distinct_permutations       | takewhile_inclusive         | iterate                            |

It’s probably better to visualize these functions in terms of the kind of operations they’re linked to. Here’s that table.


| Category                 | Functions                                                                                            |
|-------------------------|-----------------------------------------------------------------------------------------------------|
| Grouping                 | chunked, ichunked, chunked_even, sliced, constrained_batches, distribute, divide, split_at,          |
|                          | split_before, split_after, split_into, split_when, bucket, unzip, batched, grouper, partition,       |
|                          | transpose                                                                                           |
|--------------------------|-----------------------------------------------------------------------------------------------------|
| Lookahead and lookback   | spy, peekable, seekable                                                                             |
+--------------------------+-----------------------------------------------------------------------------------------------------+
| Windowing                | windowed, substrings, substrings_indexes, stagger, windowed_complete, pairwise, triplewise,         |
|                          | sliding_window, subslices                                                                           |
+--------------------------+-----------------------------------------------------------------------------------------------------+
| Augmenting               | count_cycle, intersperse, padded, repeat_each, mark_ends, repeat_last, adjacent, groupby_transform, |
|                          | pad_none, ncycles                                                                                   |
+--------------------------+-----------------------------------------------------------------------------------------------------+
| Combining                | collapse, sort_together, interleave, interleave_longest, interleave_evenly, zip_offset, zip_equal,  |
|                          | zip_broadcast, flatten, roundrobin, prepend, value_chain, partial_product                           |
+--------------------------+-----------------------------------------------------------------------------------------------------+
| Summarizing              | ilen, unique_to_each, sample, consecutive_groups, run_length, map_reduce, join_mappings, exactly_n, |
|                          | is_sorted, all_equal, all_unique, minmax, first_true, quantify, iequals                             |
+--------------------------+-----------------------------------------------------------------------------------------------------+
| Selecting                | islice_extended, first, last, one, only, strictly_n, strip, lstrip, rstrip, filter_except,          |
|                          | map_except, filter_map, iter_suppress, nth_or_last, unique_in_window, before_and_after, nth, take,  |
|                          | tail, unique_everseen, unique_justseen, unique, duplicates_everseen, duplicates_justseen,           |
|                          | classify_unique, longest_common_prefix, takewhile_inclusive                                         |
+--------------------------+-----------------------------------------------------------------------------------------------------+
| Math                     | dft, idft, convolve, dotproduct, factor, matmul, polynomial_from_roots, polynomial_derivative,      |
|                          | polynomial_eval, sieve, sum_of_squares, totient                                                     |
+--------------------------+-----------------------------------------------------------------------------------------------------+
| Combinatorics            | distinct_permutations, distinct_combinations, circular_shifts, partitions, set_partitions,          |
|                          | product_index, combination_index, permutation_index, combination_with_replacement_index,            |
|                          | gray_product, outer_product, powerset, powerset_of_sets, random_product, random_permutation,        |
|                          | random_combination, random_combination_with_replacement, nth_product, nth_permutation,              |
|                          | nth_combination, nth_combination_with_replacement                                                   |
+--------------------------+-----------------------------------------------------------------------------------------------------+
| Wrapping                 | always_iterable, always_reversible, countable, consumer, with_iter, iter_except                     |
+--------------------------+-----------------------------------------------------------------------------------------------------+
| Others                   | locate, rlocate, replace, numeric_range, side_effect, iterate, difference, make_decorator,          |
|                          | SequenceView, time_limited, map_if, iter_index, consume, tabulate, repeatfunc, reshape,             |
|                          | doublestarmap                                                                                       |
+--------------------------+-----------------------------------------------------------------------------------------------------+

https://more-itertools.readthedocs.io  
https://medium.com/@thomas_reid/introducing-the-more-itertools-python-library-e5a24a901979  
https://python.plainenglish.io/real-world-more-itertools-gideons-blog-a3901c607550  

https://toolz.readthedocs.io/en/latest/api.html

https://python-lenses.readthedocs.io/en/latest/tutorial/intro.html
