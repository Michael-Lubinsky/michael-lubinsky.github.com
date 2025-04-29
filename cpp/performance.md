http://www.brendangregg.com/linuxperf.html

## Latency Comparison Numbers
```
L1 cache reference                           0.5 ns
Branch mispredict                            5   ns
L2 cache reference                           7   ns                      14x L1 cache
Mutex lock/unlock                           25   ns
Main memory reference                      100   ns                      20x L2 cache, 200x L1 cache
Compress 1K bytes with Zippy             3,000   ns        3 us
Send 1K bytes over 1 Gbps network       10,000   ns       10 us
Read 4K randomly from SSD*             150,000   ns      150 us          ~1GB/sec SSD
Read 1 MB sequentially from memory     250,000   ns      250 us
Round trip within same datacenter      500,000   ns      500 us
Read 1 MB sequentially from SSD*     1,000,000   ns    1,000 us    1 ms  ~1GB/sec SSD, 4X memory
Disk seek                           10,000,000   ns   10,000 us   10 ms  20x datacenter roundtrip
Read 1 MB sequentially from disk    20,000,000   ns   20,000 us   20 ms  80x memory, 20X SSD
Send packet CA->Netherlands->CA    150,000,000   ns  150,000 us  150 ms
```

### OpenTelemetry

https://www.causely.ai/blog/using-opentelemetry-and-the-otel-collector-for-logs-metrics-and-traces?utm_source=cncf&utm_medium=referral

https://www.linux.com/news/using-opentelemetry-and-the-otel-collector-for-logs-metrics-and-traces/

### https://perfwiki.github.io/main/

https://perfwiki.github.io/main/tutorial/

https://www.brendangregg.com/perf.html

perf: Linux profiling with performance counters

it can instrument CPU performance counters, tracepoints, kprobes, and uprobes (dynamic tracing). It is capable of lightweight profiling. It is also included in the Linux kernel, under tools/perf, and is frequently updated and enhanced.

### System-wide profiling vs Application level profiling


### http://www.linuxhowtos.org/System/procstat.htm
```c
#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
#include <string.h>

int main(int argc, const char *argv[]) {
    char path[32], data[2048];
    int tps = sysconf(_SC_CLK_TCK);  
    sprintf(path, "/proc/%s/stat", argv[1]);
    int fd = open(path, O_RDONLY);
    if (fd < 0) {
        perror("open");
        return -1;
    }
    if (read(fd, data, 2048) == -1) {
        perror("read");
        return -1;
    }
    close(fd);
    char name[1024];
    long unsigned int utime, virt;
    long int rss;
    sscanf(data, "%*d %s %*c %*d %*d %*d %*d %*d %*u %*u %*u %*u %*u %lu"" %*u %*d %*d %*d %*d %*d %*d %*u %lu %ld", 
    name, &utime, &virt, &rss);
    printf("%s active %lus, virtual size: %ld kB, resident pages: %ld\n", name, utime/tps, virt/1024, rss);
    return 0;
}
```
Usage: program <pid>


## Load average    

http://en.wikipedia.org/wiki/Load_(computing)

http://www.linuxjournal.com/article/9001

Load average (returned by w, uptime and tload) number tells you how many processes on average are using or waiting on CPU for execution.   
If it is close to or over 1.0 * (NUMBER OF CPUs), it means the system is constantly busy with something. 
If load average is constantly raising, it means that system cannot keep up with the demand and tasks start to pile up.   
Monitoring load average instead of CPU utilization for system "health" has two advantages:

1. Load averages given by system are already averaged.  
They don't fluctuate that much so you don't get that problem with parsing "ps" output.

3. Some app may be thrashing disk and rendering system unresponsive.  
In this case CPU utilization might be low, but load average would still be high indicating a problem.

Script to show load average with timestamp
```bash
while true; do
   L=$(awk '{ print $1 }'  /proc/loadavg);
   D=$(date +%H:%M:%S);
   echo -e "$D\t$L";
   sleep 1;
done
```
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

<https://diveintosystems.org/>

<https://www.youtube.com/watch?v=-HNpim5x-IE> How CPU works

<https://github.com/dendibakh/perf-book/tree/main>

<https://en.algorithmica.org/hpc/>

<https://github.com/google/benchmark>

<https://github.com/ibogosavljevic/fiya>

<https://github.com/yse/easy_profiler>

<https://www.oracle.com/application-development/technologies/developerstudio-features.html#performance-analyzer-tab>

<https://habr.com/ru/articles/469409/>
