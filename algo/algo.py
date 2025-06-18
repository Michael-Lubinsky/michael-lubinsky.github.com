Brackets matching
----------------
class Solution:
    def isValid(self, s: str) -> bool:     
        stack = []
        brackets = {
            ')': '(',
            ']': '[',
            '}': '{'
        }

        for char in s:
            if char in '([{':  #  if char in brackets.keys()
                stack.append(char)
            elif char in ')]}': #  if char in brackets.values()
                if len(stack) == 0 or brackets[char] != stack.pop():
                    return False

        return len(stack) == 0


def longest_increasing_subsequence(nums):
    """
    Finds the longest strictly increasing subsequence in a list of numbers.
    Args:nums (list): A list of integers or floats.
    Returns: list: The longest strictly increasing subsequence.
    """
    if not nums:
        return []

    # Initialize variables to track sequences
    longest_seq = []
    current_seq = [nums[0]]

    for i in range(1, len(nums)):
        if nums[i] > nums[i - 1]:
            current_seq.append(nums[i])  # Continue the increasing sequence
        else:
            if len(current_seq) > len(longest_seq):
                longest_seq = current_seq  # Update the longest sequence
            current_seq = [nums[i]]  # Start a new sequence

    # Final check after the loop
    if len(current_seq) > len(longest_seq):
        longest_seq = current_seq

    return longest_seq
    
Longest increasing subsequence
--------------------------------
https://llego.dev/posts/python-solving-longest-increasing-subsequence/

def findLISLength(arr):

  LIS = [1 for _ in range(len(arr))]

  for i in range(1, len(arr)):
    for j in range(i):
      if arr[i] > arr[j]:
        LIS[i] = max(LIS[i], LIS[j] + 1)

  return max(LIS)

O(n**2)
Better solution:
Initialize with stack containing first array element
For each subsequent element, try to append to existing stacks if order is maintained
If no stack append is possible, make new stack with that element
Track longest stack found to get LIS length
This leverages Python’s deque to simulate the stacks in an efficient way.
By greedily extending stacks that maintain order, we build up the LIS with just one array pass.

The time complexity is O(n log n) due to the stack manipulations, making this a fast optimization over the dynamic programming approach.

from collections import deque

def findLISLength(arr):

  stacks = [deque([arr[0]])]
  longest = 1

  for i in range(1, len(arr)):
    item = arr[i]

    for stack in stacks:
      if stack[-1] < item:
        stack.append(item)
        longest = max(longest, len(stack))
    else:
      stacks.append(deque([item]))

  return longest
    
Length_of_longest_increasing_subsequence
----------------------------------------
import bisect

def length_of_longest_increasing_subsequence(nums):
    increasing_lst = []
    for n in nums:
        pos = bisect.bisect_left(increasing_lst, n)
        if pos < len(increasing_lst):
            increasing_lst[pos] = n
        else:
            increasing_lst.append(n)

    return len(increasing_lst)

# Test:
nums = [11, 5, 2, 5, 3, 7, 101, 18]
print(length_of_longest_increasing_subsequence(nums))  # Answer: 4


3 sum problem
---------------
Given an integer array nums of length n and an integer target, find three integers in nums such that the sum is closest to target.

Return the sum of the three integers

    def threeSumClosest(self, nums: List[int], target: int) -> int:
        diff = float("inf")
        nums.sort()
        for i in range(len(nums)):
            lo, hi = i + 1, len(nums) - 1
            while lo < hi:
                sum = nums[i] + nums[lo] + nums[hi]
                if abs(target - sum) < abs(diff):
                    diff = target - sum
                if sum < target:
                    lo += 1
                else:
                    hi -= 1
            if diff == 0:
                break
        return target - diff
        
Given an integer array nums and an integer k, return the number of pairs (i, j) where i < j 
such that |nums[i] - nums[j]| == k.
https://www.pankajtanwar.in/code/count-number-of-pairs-with-absolute-difference-k

class Solution {
public:
    int countKDifference(vector<int>& nums, int k) {
        int list[201] = {0};
        int res = 0;
        
        for(auto val: nums) {
            res += (val-k >= 0 ? list[val-k] : 0) + list[val+k];
            list[val]++;
        }
        return res;
    }
}
Path from root to given node
https://www.devglan.com/datastructure/print-path-from-root-to-node-binary-tree

https://www.techiedelight.com/print-all-paths-from-root-to-leaf-nodes-binary-tree/

For binary tree find max depth and max wide
----------------------------------------
the breadth-first search algorithm would work best to find the max-width of the tree, and the depth-first search algorithm would work best to find the max-depth.

class TreeNode(object):

      def __init__(self, val=0, left=None, right=None):
         self.val = val
         self.left = left
         self.right = right

      def maxDepth(self, root):
          return 0 if root is None else 1 + max(self.maxDepth(root.left), self.maxDepth(root.right))
https://github.com/GEEGABYTE1/Width-Depth-Tree-Problems

2 Heaps pattern Find ( Median from Data Stream)
--------------------------------------------
https://emre.me/coding-patterns/two-heaps/

 we want to know the smallest element in one part and the biggest element in the other part.
 Two Heaps pattern uses two Heap data structure to solve these problems;
 
 a Min Heap to find the smallest element and a Max Heap to find the biggest element.
 
 Design a data structure that supports the following two operations:

void addNum(int num) - Add a integer number from the data stream to the data structure.
double findMedian() - Return the median of all elements so far.
    
Topological sort
-----------------
There are a total of n courses you have to take, labeled from 0 to n - 1.

Some courses may have prerequisites, for example to take course 0 you have to first take course 1, which is expressed as a pair: [0, 1]

Given the total number of courses and a list of prerequisite pairs, is it possible for you to finish all courses?

The aim of topological sort is to provide a partial ordering among the vertices of the graph such that if there is an edge from U to V then U <= V, which means, U comes before V in the ordering.

Source: Any node that has no incoming edge and has only outgoing edges is called a source.
Sink: Any node that has only incoming edges and no outgoing edge is called a sink.
Topological ordering starts with one of the sources and ends at one of the sinks.
A topological ordering is possible only when the graph has no directed cycles, i.e. if the graph is a Directed Acyclic Graph (DAG). If the graph has a cycle, some vertices will have cyclic dependencies which makes it impossible to find a linear ordering among vertices.
To find the topological sort of a graph we can traverse the graph in a Breadth First Search (BFS) way.

a. Initialization

We will store the graph in Adjacency Lists, which means each parent vertex will have a list containing all of its children. We will do this using a Hash Table where the key will be the parent vertex number and the value will be a List containing children vertices.

To find the sources, we will keep a Hash Table to count the in-degrees (count of incoming edges of each vertex). Any vertex with 0 in-degree will be a source.

b. Build the graph and find in-degrees of all vertices

We will build the graph from the input and populate the in-degrees Hash Table.

c. Find all sources

All vertices with 0 in-degrees will be our sources and we will store them in a Queue.

d. Sort

For each source:

Add it to the sorted list.
Get all of its children from the graph.
Decrement the in-degree of each child by 1.
If a child’s in-degree becomes 0, add it to the sources Queue.
Repeat these steps, until the source Queue is empty.

from collections import deque
from typing import List


class Solution:
    def canFinish(self, numCourses: int, prerequisites: List[List[int]]) -> bool:
        sorted_list = []

        if numCourses <= 0:
            return False

        # a. Initialization
        graph = {i: [] for i in range(numCourses)}  # adjacency list graph
        in_degree = {i: 0 for i in range(numCourses)}  # count of incoming edges

        # b. Build the graph
        for prerequisite in prerequisites:
            parent, child = prerequisite[0], prerequisite[1]
            graph[parent].append(child)  # put the child into it's parent's list
            in_degree[child] += 1

        # c. Find all sources
        sources = deque()
        for key in in_degree:
            if in_degree[key] == 0:
                sources.append(key)

        # d. Sort
        while sources:
            vertex = sources.popleft()
            sorted_list.append(vertex)
            for child in graph[vertex]:  # get the node's children to decrement their in-degrees
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    sources.append(child)

        # if sorted_list does not contain all the courses, there is a cyclic dependency between courses
        # scheduling is not possible if there is a cyclic dependency
        return len(sorted_list) == numCourses
Time Complexity: O(V + E) where V is the total number of courses and E is the total number of prerequisites.

Space Complexity: O(V + E) since we are storing all of the prerequisites for each course in an adjacency list.

    Top K numbers
------------------
To have top k largest numbers in the heap. We will use a min-heap for this; Time Complexity: O(N log K).

from heapq import *

class Solution:
    def findKthLargest(self, nums: List[int], k: int) -> int:
        min_heap = []
        
        for i in range(k):
            heappush(min_heap, nums[i])
        
        for i in range(k, len(nums)):
            if nums[i] > min_heap[0]:
                heappop(min_heap)
                heappush(min_heap, nums[i])
            
        return min_heap[0]
        
Given a string s, find the longest palindromic subsequence’s length in s.
------------------------------------------------------------------------
https://emre.me/coding-patterns/palindromes/

Top-down Dynamic Programming with Memoization
-------------------------------------------------
start and end are two changing values of our recursive function in the Brute Force Solution.
So, we can store the results of all subsequences in a two-dimensional array to memoize them.

class Solution:
    def longestPalindromeSubseq(self, s: str) -> int:
        memo = [[-1 for _ in range(len(s))] for _ in range(len(s))]
        return self.longestPalindromeSubseq_recursive(memo, s, 0, len(s) - 1)

    def longestPalindromeSubseq_recursive(self, memo, s, start, end):
        if start > end:
            return 0

        # every sequence with one element is a palindrome of length 1
        if start == end:
            return 1

        if memo[start][end] == -1:
            # case 1: elements at the beginning and the end are the same
            if s[start] == s[end]:
                memo[start][end] = 2 + self.longestPalindromeSubseq_recursive(memo, s, start + 1, end - 1)
            else:
                # case 2: skip one element either from the beginning or the end
                subseq1 = self.longestPalindromeSubseq_recursive(memo, s, start + 1, end)
                subseq2 = self.longestPalindromeSubseq_recursive(memo, s, start, end - 1)
                memo[start][end] = max(subseq1, subseq2)

        return memo[start][end]

Time Complexity: O(N2) because memoization array, memo[len(s)][len(s)].
 We will not have more than N*N subsequences.

Space Complexity: O(N2 + N) == O(N2) because we used N2 for memoization array and N for recursive stack.

Bottom-up Dynamic Programming with Tabulation
---------------------------------------------
We can build our two-dimensional memoization array in a bottom-up fashion, adding one element at a time.

if the element at the start and the end is matching,
the length of Longest Palindromic Substring (LPS) is 2 plus the length of LPS till start+1 and end-1.
if the element at the start does not match the element at the end,
 we will take the max of LPS by either skipping the element at start or end
So the overall algorith will be;

if s[start] == s[end]:
    memo[start][end] = 2 + memo[start + 1][end - 1]
else:
    memo[start][end] = max(memo[start + 1][end], memo[start][end - 1])
and the solution;

class Solution:
    def longestPalindromeSubseq(self, s: str) -> int:
        memo = [[0 for _ in range(len(s))] for _ in range(len(s))]

        # every sequence with one element is a palindrome of length 1
        for i in range(len(s)):
            memo[i][i] = 1

        for start in range(len(s) - 1, -1, -1):
            for end in range(start + 1, len(s)):
                # case 1: elements at the beginning and the end are the same
                if s[start] == s[end]:
                    memo[start][end] = 2 + memo[start + 1][end - 1]
                else:  # case 2: skip one element either from the beginning or the end
                    memo[start][end] = max(memo[start + 1][end], memo[start][end - 1])

        return memo[0][len(s) - 1]

Time Complexity: O(N2)
Space Complexity: O(N2) where N is the input sequence.
    
Longest common substr
https://emre.me/coding-patterns/longest-common-substring-subsequence/

Top-down Dynamic Programming with Memoization
-------------------------------------------
class Solution:
    def longestCommonSubsequence(self, text1: str, text2: str) -> int:
        memo = [[-1 for _ in range(len(text2))] for _ in range(len(text1))]
        return self.longestCommonSubsequence_recursive(memo, text1, text2, 0, 0)

    def longestCommonSubsequence_recursive(self, memo, text1, text2, i, j):
        if i == len(text1) or j == len(text2):
            return 0
        if memo[i][j] == -1:
            if text1[i] == text2[j]:
                memo[i][j] = 1 + self.longestCommonSubsequence_recursive(memo, text1, text2, i + 1, j + 1)
            else:
                memo[i][j] = max(self.longestCommonSubsequence_recursive(memo, text1, text2, i + 1, j),
                                 self.longestCommonSubsequence_recursive(memo, text1, text2, i, j + 1))
        return memo[i][j]


Bottom-up Dynamic Programming with Tabulation
---------------------------------------------
Lets create our two dimensional array in a bottom-up fashion.

if the characters text1[i] matches text2[j], the length of the common subsequence would be one plus the length of the common subsequence until the i-1 and j-1 indexes.
if the characters text1[i] and text2[j] does not match, we take the longest sequence by skipping one character either from ith string or jth character from respective strings.
Our overall algorithm is;

if text1[i] == text2[j]:
    memo[i][j] = 1 + memo[i - 1][j - 1]
else:
    memo[i][j] = max(memo[i - 1][j], memo[i][j - 1])
and the solution is;

class Solution:
    def longestCommonSubsequence(self, text1: str, text2: str) -> int:
        memo = [[0 for _ in range(len(text2) + 1)] for _ in range(len(text1) + 1)]
        max_length = 0
        for i in range(1, len(text1) + 1):
            for j in range(1, len(text2) + 1):
                if text1[i - 1] == text2[j - 1]:
                    memo[i][j] = 1 + memo[i - 1][j - 1]
                else:
                    memo[i][j] = max(memo[i - 1][j], memo[i][j - 1])

                max_length = max(max_length, memo[i][j])
        return max_length
Time Complexity: O(N * M) where N and M are the lengths of two input strings.

Space Complexity: O(N * M)







There are 2 python integer arrays A and B of the same size N.
-----------------------
The goal is to check whether there is a swap operation which can be performed on these arrays
in such a way that the sum of elements in array A equals the sum of elements in array B after the swap.
By swap operation we mean picking one element from array A and
one element from array B and exchanging them.

def can_swap_to_equal_sum(A, B):
    sum_a = sum(A)
    sum_b = sum(B)
    diff = sum_a - sum_b

    # For the swap to equalize sums, the difference must be even
    if diff % 2 != 0:
        return False

    # We want to find two elements a ∈ A and b ∈ B such that:
    # sum_a - a + b == sum_b - b + a
    # Simplifying gives: a - b == (sum_a - sum_b) / 2
    target = diff // 2

    set_b = set(B)
    for a in A:
        b = a - target
        if b in set_b:
            return True  # such a pair exists

    return False  # no such pair found

Counting sort O(n + k)
------------------------
Notice that we have to know the range of the sorted values.
First, count the elements in the array of counters.
Next, just iterate through the array of counters in increasing order.

If all the elements are in the set {0, 1, . . . , k},
then the array used for counting should be of size k + 1.

def countingSort(A, k):
  n = len(A)
  count=[0]*(k+1)  # initalize with 0
  for i in range(n):
    count[A[i]] += 1

  p=0
  for i in range(k + 1):
    for j in range(count[i]):
      A[p] = i
      p += 1
  return A

Python Function to Find Majority Element (Occurs More Than Half the Time)
--------------------------------------------------------------------------
Here's a Python function using the Boyer-Moore Voting Algorithm, which works in O(n) time and O(1) space:

def find_majority_element(arr):
    candidate = None
    count = 0

    for num in arr:
        if count == 0:
            candidate = num
            count = 1
        elif num == candidate:
            count += 1
        else:
            count -= 1

    # Optional: Verify that candidate is actually majority
    if arr.count(candidate) > len(arr) // 2:
        return candidate
    return None
    
Most frequent element in Array
------------------------------
from collections import Counter

def most_frequent_element(arr):
    if not arr:
        return None
    counter = Counter(arr)
    return counter.most_common(1)[0][0]
    
Top 10 Most frequent elements in Array
-------------------------------------
from collections import Counter

def top_10_frequent_elements(arr):
    counter = Counter(arr)
    return counter.most_common(10)
    
MAX sum subarray with O(n) time complexity
--------------------------------------------
For each position, we compute the largest sum that ends in that position. 
If we assume that the maximum sum of a slice ending in position i equals max_ending,
then the maximum slice ending in position i+1 equals max(0, max_ending+ ai+1).

def  max_slice(A):
  max_ending = max_slice = 0
  for a in A:
    max_ending = max(0, max_ending + a)
    max_slice = max(max_slice, max_ending)

return max_slice

Python Function to Find Top 10 Most Frequent Elements without Using collections.Counter
----------------------------------------------------
You can use a dictionary to count frequencies manually and then sort the result:

def top_10_frequent_elements(arr):
    freq_map = {}
    for item in arr:
        if item in freq_map:
            freq_map[item] += 1
        else:
            freq_map[item] = 1

    # Sort by frequency in descending order and take top 10
    sorted_items = sorted(freq_map.items(), key=lambda x: x[1], reverse=True)
    return sorted_items[:10]


Given n sticks as array count the number of triangles that can be constructed using these sticks.
--------------------------------------------------------------------------------------------------
we'll sort the array first, we only need to check:

For sorted sides a ≤ b ≤ c, check if a + b > c

def count_possible_triangles(arr):
    arr.sort()
    n = len(arr)
    count = 0

    # Fix the third side (largest) and use two pointers for the rest
    for k in range(n - 1, 1, -1):
        i, j = 0, k - 1
        while i < j:
            if arr[i] + arr[j] > arr[k]:
                count += j - i
                j -= 1
            else:
                i += 1

    return count

    
def triangles(A):
  n = len(A)
  result = 0
  for x in  range(n):
    z=x+2

    for y in  range(x + 1, n):
      while (z < n and A[x] + A[y] > A[z]):
        z += 1
    result += z - y - 1

return result

The time complexity of the above algorithm is O(n^2), because for every stick x the values of y and z increase O(n) number of times.


def move_zeros_to_front(arr):
    result = [0] * arr.count(0)  # Add all zeros first
    for num in arr:
        if num != 0:
            result.append(num)
    return result


def merge_overlapping_intervals(intervals):
    if not intervals:
        return []

    # Step 1: Sort intervals by start time
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]

    # Step 2: Iterate and merge
    for current in intervals[1:]:
        last = merged[-1]

        if current[0] <= last[1]:
            # Overlapping intervals → merge them
            last[1] = max(last[1], current[1])
        else:
            # No overlap → add to result
            merged.append(current)

    return merged


def find_max_intersections(intervals):
    if not intervals:
        return None

    # Sort intervals by their start times
    intervals.sort(key=lambda x: x[0])

    max_intersections = 0
    max_interval = None
    current_intersections = 0
    current_interval = None

    for start, end in intervals:
        if current_interval is None:
            current_interval = (start, end)
            current_intersections = 1
        else:
            if start <= current_interval[1]:
                current_intersections += 1
                current_interval = (start, max(end, current_interval[1]))
            else:
                if current_intersections > max_intersections:
                    max_intersections = current_intersections
                    max_interval = current_interval
                current_interval = (start, end)
                current_intersections = 1

    if current_intersections > max_intersections:
        max_interval = current_interval

    return max_interval

# Example usage
if __name__ == "__main__":
    intervals = [(1, 3), (2, 6), (4, 8), (5, 7), (7, 9)]

    max_intersection_interval = find_max_intersections(intervals)
    if max_intersection_interval:
        print("Interval with the maximum number of intersections:", max_intersection_interval)
    else:
        print("No intersections found.")



### Permutations without recursion
#---------------------------------
def generate_permutations(input_string):
    if len(input_string) <= 1:
        return [input_string]

    # Initialize the result list with the first character
    result = [input_string[0]]

    for i in range(1, len(input_string)):
        current_char = input_string[i]
        new_permutations = []

        # Iterate through the existing permutations
        for perm in result:
            for j in range(len(perm) + 1):
                new_perm = perm[:j] + current_char + perm[j:]
                new_permutations.append(new_perm)

        result = new_permutations

    return result

# Example usage
if __name__ == "__main__":
    input_string = "abc"

    all_permutations = generate_permutations(input_string)
    for permutation in all_permutations:
        print(permutation)



### All permutations of string

from itertools import permutations

def generate_permutations(input_string):
    perms = permutations(input_string)
    return [''.join(p) for p in perms]

# Example usage
if __name__ == "__main__":
    input_string = "abc"

    all_permutations = generate_permutations(input_string)
    for permutation in all_permutations:
        print(permutation)



def has_triplet_with_sum(arr, target):
    arr.sort()
    n = len(arr)

    for i in range(n - 2):
        left, right = i + 1, n - 1

        while left < right:
            current_sum = arr[i] + arr[left] + arr[right]

            if current_sum == target:
                return True
            elif current_sum < target:
                left += 1
            else:
                right -= 1

    return False


###  Detect if in given array there 4 numbers which will sum up to 0 
#-------------------------------------------------------------------
def four_sum_to_zero(nums):
    nums.sort()  # Sort the array

    result = []

    for i in range(len(nums) - 3):
        if i > 0 and nums[i] == nums[i - 1]:
            continue  # Skip duplicates

        for j in range(i + 1, len(nums) - 2):
            if j > i + 1 and nums[j] == nums[j - 1]:
                continue  # Skip duplicates

            left = j + 1
            right = len(nums) - 1

            while left < right:
                total = nums[i] + nums[j] + nums[left] + nums[right]

                if total == 0:
                    result.append([nums[i], nums[j], nums[left], nums[right]])

                    while left < right and nums[left] == nums[left + 1]:
                        left += 1  # Skip duplicates
                    while left < right and nums[right] == nums[right - 1]:
                        right -= 1  # Skip duplicates

                    left += 1
                    right -= 1
                elif total < 0:
                    left += 1
                else:
                    right -= 1

    return result

# Example usage
if __name__ == "__main__":
    nums = [1, 0, -1, 0, -2, 2]

    result = four_sum_to_zero(nums)
    if result:
        print("Four numbers that sum up to 0:", result)
    else:
        print("No such four numbers found.")

###  Tree sum
# -------------
def three_sum_to_zero(nums):
    nums.sort()  # Sort the array

    result = []

    for i in range(len(nums) - 2):
        if i > 0 and nums[i] == nums[i - 1]:
            continue  # Skip duplicates

        left = i + 1
        right = len(nums) - 1

        while left < right:
            total = nums[i] + nums[left] + nums[right]

            if total == 0:
                result.append([nums[i], nums[left], nums[right]])

                while left < right and nums[left] == nums[left + 1]:
                    left += 1  # Skip duplicates
                while left < right and nums[right] == nums[right - 1]:
                    right -= 1  # Skip duplicates

                left += 1
                right -= 1
            elif total < 0:
                left += 1
            else:
                right -= 1

    return result

# Example usage
if __name__ == "__main__":
    nums = [-1, 0, 1, 2, -1, -4]

    result = three_sum_to_zero(nums)
    if result:
        print("Three numbers that sum up to 0:", result)
    else:
        print("No such three numbers found.")



### Check if binary tree is binary search tree
# --------------------------------------------
class TreeNode:
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None

def is_binary_search_tree(root):
    def in_order_traversal(node, prev):
        if node is None:
            return True

        # Recursively check the left subtree
        if not in_order_traversal(node.left, prev):
            return False

        # Check if the current node's value is greater than the previous node's value
        if node.value <= prev[0]:
            return False

        prev[0] = node.value  # Update the previous value

        # Recursively check the right subtree
        return in_order_traversal(node.right, prev)

    prev = [float('-inf')]  # Initialize the previous value to negative infinity
    return in_order_traversal(root, prev)

# Example usage
if __name__ == "__main__":
    root = TreeNode(2)
    root.left = TreeNode(1)
    root.right = TreeNode(3)

    if is_binary_search_tree(root):
        print("The binary tree is a Binary Search Tree (BST).")
    else:
        print("The binary tree is not a BST.")



### Post order without recursion using 2 stacks
# ---------------------------------------------
class TreeNode:
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None

def post_order_traversal(root):
    if root is None:
        return []

    result = []
    stack1 = [root]
    stack2 = []

    while stack1:
        node = stack1.pop()
        stack2.append(node)

        if node.left:
            stack1.append(node.left)
        if node.right:
            stack1.append(node.right)

    while stack2:
        node = stack2.pop()
        result.append(node.value)

    return result

# Example usage
if __name__ == "__main__":
    root = TreeNode(1)
    root.left = TreeNode(2)
    root.right = TreeNode(3)
    root.left.left = TreeNode(4)
    root.left.right = TreeNode(5)
    
    result = post_order_traversal(root)
    print("Post-order traversal:", result)



### In order traversal without recursion using stack
# ---------------------------------------------------
class TreeNode:
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None

def in_order_traversal(root):
    if root is None:
        return []

    result = []
    stack = []

    current = root

    while stack or current:
        if current:
            stack.append(current)
            current = current.left
        else:
            current = stack.pop()
            result.append(current.value)
            current = current.right

    return result

# Example usage
if __name__ == "__main__":
    root = TreeNode(1)
    root.left = TreeNode(2)
    root.right = TreeNode(3)
    root.left.left = TreeNode(4)
    root.left.right = TreeNode(5)
    
    result = in_order_traversal(root)
    print("In-order traversal:", result)



### Preorder traversal without recursion - using stack
#-----------------------------------------------------
class TreeNode:
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None

def depth_first_traversal(root):
    if root is None:
        return []

    result = []
    stack = [root]

    while stack:
        node = stack.pop()
        result.append(node.value)

        # Push the right child first to ensure left child is processed first (LIFO)
        if node.right:
            stack.append(node.right)
        if node.left:
            stack.append(node.left)

    return result

# Example usage
if __name__ == "__main__":
    root = TreeNode(1)
    root.left = TreeNode(2)
    root.right = TreeNode(3)
    root.left.left = TreeNode(4)
    root.left.right = TreeNode(5)
    
    result = depth_first_traversal(root)
    print("Depth-first traversal (pre-order):", result)


### Breadth first (LeVeL order) without recursion using queue
# -----------------------------------------------------------
class TreeNode:
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None

def level_order_traversal(root):
    if root is None:
        return []

    result = []
    queue = [root]

    while queue:
        node = queue.pop(0)
        result.append(node.value)

        if node.left:
            queue.append(node.left)
        if node.right:
            queue.append(node.right)

    return result

# Example usage
if __name__ == "__main__":
    root = TreeNode(1)
    root.left = TreeNode(2)
    root.right = TreeNode(3)
    root.left.left = TreeNode(4)
    root.left.right = TreeNode(5)
    
    result = level_order_traversal(root)
    print("Level-order traversal:", result)

########################


### Diameter of binary tree
#----------------------------
class TreeNode:
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None

class Result:
    def __init__(self):
        self.diameter = 0

def tree_diameter(root, result):
    if root is None:
        return 0

    left_height = tree_diameter(root.left, result)
    right_height = tree_diameter(root.right, result)

    # Calculate the diameter passing through the current node
    diameter_through_node = left_height + right_height

    # Update the maximum diameter found so far
    result.diameter = max(result.diameter, diameter_through_node)

    # Return the height of the subtree rooted at the current node
    return 1 + max(left_height, right_height)

def tree_max_diameter(root):
    result = Result()
    tree_diameter(root, result)
    return result.diameter

# Example usage
if __name__ == "__main__":
    root = TreeNode(1)
    root.left = TreeNode(2)
    root.right = TreeNode(3)
    root.left.left = TreeNode(4)
    root.left.right = TreeNode(5)

    max_diameter = tree_max_diameter(root)
    print("Maximum distance between any two nodes (diameter) of the binary tree is:", max_diameter)



### Height of binary tree

class TreeNode:
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None

def tree_height(root):
    if root is None:
        return -1  # Height of an empty tree is -1

    left_height = tree_height(root.left)
    right_height = tree_height(root.right)

    return 1 + max(left_height, right_height)

# Example usage
if __name__ == "__main__":
    root = TreeNode(1)
    root.left = TreeNode(2)
    root.right = TreeNode(3)
    root.left.left = TreeNode(4)
    root.left.right = TreeNode(5)

    height = tree_height(root)
    print("Height of the binary tree is:", height)



## Least common accessor of 2 nodes (p,q) in binary tree

class TreeNode:
    def __init__(self, val):
        self.val = val
        self.left = None
        self.right = None

def findLCA(root, p, q):
    if root is None:
        return None

    if root.val == p or root.val == q:
        return root

    left_lca = findLCA(root.left, p, q)
    right_lca = findLCA(root.right, p, q)

    if left_lca and right_lca:
        return root

    return left_lca if left_lca else right_lca

# Helper function to check if a node with a given value exists in the tree
def nodeExists(root, value):
    if root is None:
        return False
    if root.val == value:
        return True
    return nodeExists(root.left, value) or nodeExists(root.right, value)

# Example usage
if __name__ == "__main__":
    root = TreeNode(3)
    root.left = TreeNode(5)
    root.right = TreeNode(1)
    root.left.left = TreeNode(6)
    root.left.right = TreeNode(2)
    root.right.left = TreeNode(0)
    root.right.right = TreeNode(8)
    root.left.right.left = TreeNode(7)
    root.left.right.right = TreeNode(4)

    p = 5
    q = 1

    if nodeExists(root, p) and nodeExists(root, q):
        lca = findLCA(root, p, q)
        print("Least Common Ancestor of {} and {} is {}".format(p, q, lca.val))
    else:
        print("Nodes {} and/or {} do not exist in the tree.".format(p, q))


######################

#Given the weights and profits of N items, in the form of {profit, weight} 
#put these items in a knapsack of capacity W to get the maximum total profit in the knapsack. 
#In Fractional Knapsack, we can break items 
#for maximizing the total value of the knapsack.
# Structure for an item which stores weight and corresponding value of Item
class Item:
    def __init__(self, profit, weight):
        self.profit = profit
        self.weight = weight
 
# Main greedy function to solve problem
def fractionalKnapsack(W, arr):
 
    # Sorting Item on basis of ratio
    arr.sort(key=lambda x: (x.profit/x.weight), reverse=True)    
 
    # Result(value in Knapsack)
    finalvalue = 0.0
 
    # Looping through all Items
    for item in arr:
 
        # If adding Item won't overflow, 
        # add it completely
        if item.weight <= W:
            W -= item.weight
            finalvalue += item.profit
 
        # If we can't add current Item, 
        # add fractional part of it
        else:
            finalvalue += item.profit * W / item.weight
            break
     
    # Returning final value
    return finalvalue
 
 
# Driver Code
if __name__ == "__main__":
    W = 50
    arr = [Item(60, 10), Item(100, 20), Item(120, 30)]
 
    # Function call
    max_val = fractionalKnapsack(W, arr)
    print(max_val)

# Find the length of  longest increasing contiguous subarray
#------------------------------------------
def lenOfLongIncSubArr(arr, n) :
    # 'max' to store the length of longest
    # increasing subarray
    # 'len' to store the lengths of longest
    # increasing subarray at different 
    # instants of time
    m = 1
    l = 1
    # traverse the array from the 2nd element
    for i in range(1, n) :
        # if current element if greater than previous
        # element, then this element helps in building
        # up the previous increasing subarray encountered
        # so far
        if (arr[i] > arr[i-1]) :
            l =l + 1
        else :
 
            # check if 'max' length is less than the length
            # of the current increasing subarray. If true, 
            # then update 'max'
            if (m < l)  :
                m = l 
 
            # reset 'len' to 1 as from this element
            # again the length of the new increasing
            # subarray is being calculated    
            l = 1
         
         
    # comparing the length of the last increasing subarray with 'max'
    if (m < l) :
        m = l
      
    # required maximum length
    return m
 
# Driver program to test above
 
arr = [5, 6, 3, 5, 7, 8, 9, 1, 2]
n = len(arr)
print("Length = ", lenOfLongIncSubArr(arr, n))
 

# Longest Increasing Subsequence (LIS)
#-------------------------------------
# https://www.geeksforgeeks.org/longest-increasing-subsequence-dp-3/
'''
The problem can be solved based on the following idea:

Let L(i) be the length of the LIS ending at index i 
such that arr[i] is the last element of the LIS.

Then, L(i) can be recursively written as: 
 L(i) = 1 + max(L(j) ) where 0 < j < i and arr[j] < arr[i]; 
 or
L(i) = 1, if no such j exists.

Formally, the length of LIS ending at index i, 
is 1 greater than the maximum of lengths of all LIS ending at some index j such that arr[j] < arr[i] where j < i.
'''

import sys
 
# To make use of recursive calls, this
# function must return two things:
# 1) Length of LIS ending with element arr[n-1].
#     We use max_ending_here for this purpose
# 2) Overall maximum as the LIS may end with
#     an element before arr[n-1] max_ref is
#     used this purpose.
# The value of LIS of full array of size n
# is stored in *max_ref which is our final result
 
 
def f(idx, prev_idx, n, a, dp):
 
    if (idx == n):
        return 0
 
    if (dp[idx][prev_idx + 1] != -1):
        return dp[idx][prev_idx + 1]
 
    notTake = 0 + f(idx + 1, prev_idx, n, a, dp)
    take = -sys.maxsize - 1
    if (prev_idx == -1 or a[idx] > a[prev_idx]):
        take = 1 + f(idx + 1, idx, n, a, dp)
 
    dp[idx][prev_idx + 1] = max(take, notTake)
    return dp[idx][prev_idx + 1]
 
# Function to find length of longest increasing subsequence.
 
def longestSubsequence(n, a):
 
    dp = [[-1 for i in range(n + 1)]for j in range(n + 1)]
    return f(0, -1, n, a, dp)
 
# Driver program to test above function
if __name__ == '__main__':
    a = [3, 10, 2, 1, 20]
    n = len(a)
 
    # Function call
    print("Length of lis is", longestSubsequence(n, a))

# Longest Increasing SUM  
#------------------------------------- 
# https://www.geeksforgeeks.org/maximum-sum-increasing-subsequence-dp-14/
# This problem is a variation of  Longest Increasing Subsequence (LIS) problem. 
# We need a slight change in the Dynamic Programming solution of LIS problem. 
# All we need to change is to use sum as a criteria instead of a length of increasing subsequence.

# maxSumIS() returns the maximum   sum of increasing subsequence  
# in arr[] of size n 
def maxSumIS(arr, n): 
    max = 0
    msis = [0 for x in range(n)] 
  
    # Initialize msis values 
    # for all indexes 
    for i in range(n): 
        msis[i] = arr[i] 
  
    # Compute maximum sum values in bottom up manner 
    for i in range(1, n): 
        for j in range(i): 
            if (arr[i] > arr[j] and
                msis[i] < msis[j] + arr[i]): 

                msis[i] = msis[j] + arr[i] 
  
    # Pick maximum of all msis values 
    for i in range(n): 
        if max < msis[i]: 
            max = msis[i] 
  
    return max
  
# Driver Code 
arr = [1, 101, 2, 3, 100, 4, 5] 
n = len(arr) 
print("Sum of maximum sum increasing " + 
                     "subsequence is " +
                  str(maxSumIS(arr, n))) 




Find the maximum area of connected 0's in a 2D binary array.
-------------------------------------------------------------
The solution uses Depth-First Search (DFS) to explore connected regions of 0s.
The function considers 4-directional connectivity (up, down, left, right).
To include diagonals (8 directions), you'd expand the DFS to check all 8 neighbors.

def max_area_of_zeros(grid):
    if not grid or not grid[0]:
        return 0

    rows, cols = len(grid), len(grid[0])
    visited = [[False] * cols for _ in range(rows)]

    def dfs(r, c):
        if r < 0 or r >= rows or c < 0 or c >= cols:
            return 0
        if grid[r][c] != 0 or visited[r][c]:
            return 0
        visited[r][c] = True
        area = 1
        # Explore neighbors in 4 directions
        area += dfs(r+1, c)
        area += dfs(r-1, c)
        area += dfs(r, c+1)
        area += dfs(r, c-1)
        return area

    max_area = 0
    for i in range(rows):
        for j in range(cols):
            if grid[i][j] == 0 and not visited[i][j]:
                max_area = max(max_area, dfs(i, j))

    return max_area
    
Given the list of integers find the smallest positive interval between them.
---------------------------------------------------------------------------
def smallest_positive_interval(nums):
    if len(nums) < 2:
        return 0

    nums.sort()  # in-place, O(n log n)
    min_diff = float('inf')

    for i in range(1, len(nums)):
        diff = nums[i] - nums[i - 1]
        if diff > 0 and diff < min_diff:
            min_diff = diff
            if min_diff == 1:
                break  # early exit: 1 is the smallest possible

    return min_diff if min_diff != float('inf') else 0
Given list of integers representing monthly profit of company return list of consecutive months that had the most profit.

from typing import List

def most_profitable_months(profits: List[int]) -> List[int]:
    if not profits:
        return []

    max_sum = current_sum = profits[0]
    start = end = temp_start = 0

    for i in range(1, len(profits)):
        if current_sum < 0:
            current_sum = profits[i]
            temp_start = i
        else:
            current_sum += profits[i]

        if current_sum > max_sum:
            max_sum = current_sum
            start = temp_start
            end = i

    return profits[start:end+1]


Usage

profits = [3, -2, 5, -1, 6, -3, 2, 7, -5]
print(most_profitable_months(profits))  # Output: [5, -1, 6, -3, 2, 7]
This output shows the sublist of consecutive months that gave the highest total profit.

Minimum Number of Coins for Given Amount (dynamic programming)
--------------------------------------------------------------
The goal is to find the minimum number of coins needed to make up a given amount.

def min_coins(denominations, amount):
    # Initialize DP array with a large number; dp[0] = 0 (base case)
    dp = [float('inf')] * (amount + 1)
    dp[0] = 0

    for coin in denominations:
        for x in range(coin, amount + 1):
            dp[x] = min(dp[x], dp[x - coin] + 1)

    return dp[amount] if dp[amount] != float('inf') else -1
There are n canoeists with given weighs w[i]

The goal is to seat them in the minimum number of double canoes
whose displacement (the maximum load) equals k. Assume that w[i] <= k.

def greedyCanoeistB(W, k):
  canoes = 0
  j=0
  i=len(W)-1
  while (i >= j):
    if W[i] + W[j] <= k:
        j += 1;
    canoes += 1;
    i -= 1
return canoes
list comprehension to generate a list of odd numbers

odd_numbers = [x for x in range(101) if x % 2 != 0]
