### RANK ():
Assigns the same rank to rows with identical values but leaves gaps in the ranking sequence.  
For example, if 5 rows are tied for rank 1 in above example,  
the next rank assigned will be 6 (skipping rank 2,3,4 and 5).

### DENSE_RANK (): 
Assigns the same rank to rows with identical values but does not leave gaps in the ranking sequence.   
For example, if 5 rows are tied for rank 1, the next rank assigned will be 2 (no gap).
