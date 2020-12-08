## Implementation of Pacman using Value Iteration with Embedded Markov Decision Process in a Non-Deterministic Environment
### How to Run
This pacman code runs on **Python2.7**

Run the command below to play pacman using the MDPAgent <br />
```python pacman.py -p MDPAgent -l mediumClassic```

To run multiples games of pacman without the interface displayed <br />
```python pacman.py -q -n <number of games> -p MDPAgent -l mediumClassic```

### Win Rate
**NOTE**: results from table obtained from running <br />
```python pacman.py -q -n 10000 -p MDPAgent -l smallGrid``` <br />
```python pacman.py -q -n 10000 -p MDPAgent -l mediumClassic```
|Layout|Win Rate (%)|
|:---:|:---:|
|smallGrid|65.72|
|mediumClassic|55.74|
