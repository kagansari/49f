## Installation

In order to be able to execute `index.py` you should first install dependencies.

```pip3 install -r requirements.txt```

This will install  and [simpy](https://simpy.readthedocs.io) and [termcolor](https://pypi.python.org/pypi/termcolor). SimPy is a process-based discrete-event simulation framework based on standard Python. It works in the same way we learnt in IE306. Arrival or other activities of users are events and networks are shared resources. TermColor is another python module used only to print to console with colors.

## Usage

To see available arguments run

`python3 index.py —help`

which will will show

```
usage: index.py [-h] [--sim-time SIMULATION_TIME]
                [--sim-count SIMULATION_COUNT] [--log] [--optimum] [--minimum]

Run simulation for SIMULATION_TIME seconds for SIMULATION_COUNT times

optional arguments:
  -h, --help            show this help message and exit
  --sim-time SIMULATION_TIME
                        simulation time in secs (default: 1800)
  --sim-count SIMULATION_COUNT
                        how many time simulation runs (default: 10)
  --log                 show every step of simulation (default: False)
  --optimum             run simulation for only HUs (default: False)
  --minimum             put HUs on only satellite network (default: False)
```



For example, `python3 index.py -—sim-time=60 —-sim-count=1 --log` will run the simulation once for one minute. It is not useful to derive results from throughput since it takes short time but activity of each user can be seen easily.



## Results

The throughput is more in terrestrial network than in satellite network, so if we run the simulation where there is no PU or SU in the network but only HUs and make every HU use terrestrial network, then the throughput is maximised. It is useful to see the limits. That is what `—optimum` options is for. `pyhton3 index.py —optimum`  will run the simulation 10 times for each half an hour and ends up with an average throughput approximately **8.5 - 9.5 Mbit/sec**.

In the other hand, `python3 index.py —minimum` runs the simulation with PUs and SUs, but makes all HUs arrive at satellite network making them wait in the queue if full or drop the ones fetching enhancement chunks and will give the least throughput possible which is around **5 - 5.5 Mbit/sec**.

Since the possible range of throughput is clear, purpose of the algorithm is to approach the optimum result as much as possible. It can be achieved with some simple algorithm. When an HU arrives, if terrestrial network is empty make her use the terrestrial. If terrestrial network is full then make her use satellite network. If both are full then push her in the queue of terrestrial network. If a PU arrives at terrestrial network and there is no SUs in terrestrial, drop HU on terrestrial network and add her back to the queue. If an HU is fetching enhancement chunk at satellite and a PU arrives at satellite network, then interrupt the HU and add her to the queue. The output can be seen with `python3 index.py` which will put out **8 - 9 Mbit/sec**, slightly below the optimum. I did not implement the case in which HU is moved from one network to another, or used any different algorithm for base and enhancement chunks, estimating it would make only a negligible difference.

#### Comparison with random assignment

To compare the algorithm with random assignment of HUs, I used `python3 index.py --sim-count=100 —random`  and `python3 index.py --sim-count=100`. These commands run the simulation for 100 times. First one is for random, the latter is for the algorithm designed. The throughput of random assignment is **~8.1 Mbit/sec**, whereas the one of the algorithm is **~8.5 Mbit/sec**. The reason that the difference is small is that there is a queue for each network and most of users fetch their content after waiting enough time in the queue.

To see the real difference, I implemented `—no-queue` option. When the commands above are executed with this option, the difference between the results is significantly larger. The random assignment puts out throughput of **~6.7 Mbit/sec**. The algorithm this time gives **~8.3 Mbit/sec**. Both throughputs decrease because some HUs are dropped and not added back to the queue, even some of arriving users fetch no content because there is no empty slot in both networks, they simply leave. 

