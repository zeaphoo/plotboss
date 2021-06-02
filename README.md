# plotboss: a Chia plotting manager

![The view of plotboss](https://github.com/zeaphoo/plotboss/blob/main/docs/images/plotboss-0.1.png?raw=true "View")

##### Development Version: v0.1.0

This is a tool for managing [Chia](https://github.com/Chia-Network/chia-blockchain)
plotting operations, has been tested for **Windows 10**.  This is not a plotter.
The tool runs on the plotting machine and provides the following functionality:

- Automatic spawning of new plotting jobs, possibly overlapping ("staggered or smart")
  on multiple temp directories,  by per-temp-dir limits.

- Monitoring of ongoing plotting and archiving jobs, progress, resources used,
  temp files, etc.


## Functionality

Plotboss tools are stateless. Rather than keep an internal record of what jobs have been started, plotboss relies on the process tables, open files, and logfiles of plot jobs to understand "what's going on".  This means the tools can be stopped and started, even from a different login session, without loss of information.

Plotboss will create a diretory `plotboss_data` in working directory. All the plotter's log to STDOUT and STDERR will redirect to the `plotboss_data/logs` folder. And the log of Plotboss is saved to `plotboss_data/plotboss.log`.

> (Note: The tool relies on reading the chia plot command line arguments and the format of the plot tool output.  Changes in those may break this tool.)

Plots are output to the `final_dir` dirs defined in `settings.toml`.

## Installation

#### NOTE: If `python` does not work, please try `python3`.

1. Download and Install Python 3.7 or higher: https://www.python.org/
2. Open CommandPrompt / PowerShell / Terminal and Install plotboss: `pip install plotboss`
3. `cd` into the your home directory or any working directory where you should always start `plotboss`.
4. Run the plotboss first time: `plotboss` or `python -m plotboss`, then press `q` to exit.
5. A file named `settings.toml` will appear in working directory, modify the setting.toml config.
5. Run the plotboss again: `plotboss` or `python -m plotboss`


## Configuration

``` toml
final_dir = [ ] # For example: ["P:", "T:"], The final directory will plot will saved.

[main]
max_jobs = 10 # default is not set.

[[jobs]]
tmp_dir = "E:/plotting"
# tmp2_dir = "F:/plotting"
# max_jobs = 1
# job_start_mode = "simple"

# size = 32
# nobitfield = false
# farmer_key = ""
# pool_key = ""
# pool_address = ""
# num_threads = 2
# bukets = 128
# buffer = 4_608

[[jobs]]
tmp_dir = "G:/plotting"
# tmp2_dir = "H:/plotting"   # optional
# max_jobs = 1  # default is 1.

# size = 32
# nobitfield = false
# num_threads = 2
# bukets = 128
# buffer = 4_608
```

You can have many `[[jobs]]` section, which contains a tmp_dir and tmp2_dir pair and many parameters for plotter.

* `max_jobs` means the concurrent working plotting jobs
* `job_start_mode` determine how plotboss start the jobs, there are two options `simple` and `smart`.
  * Option `simple` just start as many as jobs under the `max_jobs` control.
  * Option `smart` works more smart, it only allow 1 job in stage 1 to avoid high peaks, even the number of current running jobs much less than the `max_jobs` param.


## Sponsor / Support this tool

This library took a lot of time and effort in order to get it before you today. Consider sponsoring or supporting the library. This is not necessary but more a kind gestures.

* XCH Address: xch168apuc4wsc2s3e6728t8l9xme5l4upnazywu9awymtum75xzh9gqxxy4tj
* ETH Address: 0xf51298d068d7f04ae0b823fb44ef8703101adb9b


## Support / Questions

Please do not use GitHub issues for questions or support regarding your own personal setups. Issues should pertain to actual bugs in the code and ideas. It has been tested to work on Windows. So any questions relating to tech support, configuration setup, or things pertaining to your own personal use cases should be posted at any of the links below.

* GitHub Discussion Board: https://github.com/zeaphoo/plotboss/discussions


## Frequently Asked Questions

##### If I stop Plotboss will it kill my plots?
* No. Plots are kicked off in the background and they will not kill your existing plots. If you want to kill them, you have access to the PIDs which you can use to track them down in Task Manager (or the appropriate software for your OS) and kill them manually. Please note you will have to delete the .tmp files as well. I do not handle this for you.

##### How are destination(`final_dir`) selected?
* They are chosen in order. If you have two directories the first plot will select the first one, the second the second
