## Profiling

A profiler is a tool that measures:  
- Where your program spends time (CPU or GPU time)  
- How much memory your program uses  
- How often certain parts of your code are executed  

## Different types of profilers  

### 1. Sampling profilers (statistical)
They periodically "pause" the program and record where it is.  
Example: every 1ms, they check "what function are we in?"  
After thousands of samples, you can statistically see which functions are "hot" (taking most time).

Advantages:
Very low overhead (your program stays fast)  
Good for getting a quick overview

Disadvantages:
Not super precise (it's statistical)  
Hard to see very short-lived functions  

Example sampling profilers:
Linux perf  
Visual Studio Profiler (Sampling mode)  
Xcode Instruments (Sampling mode)

### 2. Instrumentation profilers
They insert extra code into every function (or block) to measure exactly when it starts and stops.
Very precise: you know exactly how long each function takes.

Advantages:
Detailed, fine-grained info (function call trees, exact timing)

Disadvantages:  
High overhead: the profiler slows down your app  
Some small functions may behave differently under instrumentation

Example instrumentation profilers:

Intel VTune (can do both sampling and instrumentation)  
Tracy Profiler  
RAD Telemetry

### Links

<https://github.com/google/benchmark>

<https://github.com/ibogosavljevic/fiya>
