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

### 3. Manual ("tracing") profilers
You (the programmer) explicitly mark areas of your code ("start event", "stop event").
Profilers just record these events with timestamps.
Very controllable: you decide what to profile.

Advantages:
Extremely low overhead if used wisely
Perfect for custom things (like profiling just AI, physics, etc.)

Disadvantages:
You have to insert the code manually

Example manual profilers:
Tracy  
Remotery  
Chrome’s Trace Event Format (you can view trace JSON in Chrome)

### Specific profilers


#### gprof
Type: Instrumentation (compile-time)
Platform: Linux, Unix
Notes: Old but famous.

Compile with -pg to enable it.

Gives function call counts and time spent.
Problems: Can't handle multithreading well, limited for modern needs.

#### perf (Linux Perf Events)
Type: Sampling (hardware counters)

Platform: Linux
Notes:
Very powerful.

Low overhead, uses CPU's performance monitoring unit (PMU).
Can do CPU, cache, branch mispredictions, etc.
Used heavily for performance tuning in production.

Can be combined with FlameGraphs.

#### Valgrind / Callgrind
Type: Instrumentation (simulated execution)

Platform: Linux, Unix, Mac

Notes:
```
Valgrind is actually a suite.
Callgrind gives very detailed call graphs and timings.
Very slow (your app may run 10–50x slower).
Great for super detailed offline analysis.
```


#### Tracy Profiler
Open source.

Uses manual instrumentation and sampling (for fibers/threads).
Extremely low overhead and real-time.

Features:
```
High-resolution timings.
Real-time remote server to view data.
Memory allocation tracking.
Context switching, lock contention, and more.
Great for games and real-time systems.
Works across threads very nicely.
```
👉 Think of Tracy as a "professional-grade tracing profiler."

#### RAD Telemetry
Commercial product from RAD Game Tools (now Epic Games).
Designed for games and high-performance apps.
Primarily manual instrumentation.

Features:
```
Remote visualization
Multiple platforms (Windows, consoles, mobile)
Timeline view, function call chains
Very low cost on runtime performance
Often used in AAA game development.
```
It is known for excellent scaling even with many threads.

👉 Think of RAD Telemetry as a "studio-grade, battle-tested profiler."

#### Remotery
Open source.
Very lightweight real-time CPU/GPU profiler.
Also uses manual instrumentation.

Designed for:
Web view visualization (you open a browser to see the results)
Very low memory footprint
Embeddable into almost any project

Supports GPU profiling via Direct3D / OpenGL / Metal in addition to CPU.

Simple to integrate.

👉 Think of Remotery as "quick and tiny profiling for small or mid-size projects."

#### Quick comparison

Profiler	Type	Best for	Notes  
Tracy	Manual + sampling	Game engines, real-time apps	Extremely powerful, needs setup  
RAD Telemetry	Manual	AAA game studios	Paid, extremely polished  
Remotery	Manual	Indie games, small apps	Lightweight, very easy   


### Links

https://github.com/dendibakh/perf-book/tree/main

<https://github.com/google/benchmark>

<https://github.com/ibogosavljevic/fiya>

<https://github.com/yse/easy_profiler>

<https://www.oracle.com/application-development/technologies/developerstudio-features.html#performance-analyzer-tab>

<https://habr.com/ru/articles/469409/>
